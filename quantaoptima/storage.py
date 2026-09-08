"""Durable audit storage with serialized SQLite appends and a separate HMAC key."""
import json
import os
from pathlib import Path
import secrets
import sqlite3

from .audit import AuditChain


class PersistentAuditChain(AuditChain):
    """Restart-safe audit chain. Back up both audit.sqlite3 and audit.key.

    Database transactions coordinate writers in different processes. The key
    must remain private; possession of it permits rewriting the chain. This
    store does not detect rollback of the entire database to an older snapshot.
    """

    def __init__(self, directory, scope="quantaoptima-session", actor="ai-agent"):
        self.directory = Path(directory).expanduser()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database = self.directory / "audit.sqlite3"
        key_path = self.directory / "audit.key"
        # Create restricted database permissions before SQLite opens it.
        fd = os.open(self.database, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS blocks (seq INTEGER PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            saved_scope = db.execute("SELECT value FROM settings WHERE name='scope'").fetchone()
            if saved_scope and saved_scope[0] != scope:
                raise ValueError("Stored audit scope does not match requested scope")
            if not key_path.exists():
                if db.execute("SELECT 1 FROM blocks LIMIT 1").fetchone():
                    raise ValueError("Audit key missing; restore audit.key from backup")
                with os.fdopen(os.open(key_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as f:
                    f.write(secrets.token_bytes(32))
                    f.flush()
                    os.fsync(f.fileno())
            key = key_path.read_bytes()
            if len(key) != 32:
                raise ValueError("Invalid stored audit key")
            super().__init__(scope=scope, secret_key=key, actor=actor)
            db.execute("INSERT OR IGNORE INTO settings VALUES ('scope', ?)", (scope,))
            self._reload(db)

    def _connect(self):
        # A new connection per operation also supports calls from other threads.
        return _Connection(self.database)

    def _reload(self, db):
        rows = db.execute("SELECT seq, data FROM blocks ORDER BY seq").fetchall()
        if any(seq != i for i, (seq, _) in enumerate(rows)):
            raise ValueError("Stored audit block sequence is invalid")
        restored = AuditChain.from_dict({
            "schema_version": 2, "scope": self.scope,
            "chain_length": len(rows), "blocks": [json.loads(data) for _, data in rows],
        }, self.secret_key)
        self.chain = restored.chain

    def refresh(self):
        with self._lock, self._connect() as db:
            self._reload(db)
        return self

    def log(self, *args, **kwargs):
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._reload(db)
            try:
                block = super().log(*args, **kwargs)
                db.execute("INSERT INTO blocks VALUES (?, ?)",
                           (block.block_number, json.dumps(block.to_dict(), allow_nan=False)))
                db.commit()
            except Exception:
                db.rollback()
                self._reload(db)
                raise
            return block


class _Connection:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.db = sqlite3.connect(self.path, timeout=30)
        return self.db

    def __exit__(self, kind, value, traceback):
        try:
            if kind is None:
                self.db.commit()
            else:
                self.db.rollback()
        finally:
            self.db.close()
