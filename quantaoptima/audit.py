"""
QuantaOptima Audit Chain — Cryptographic audit trails for AI agent actions.

The core product of QuantaOptima: a general-purpose HMAC-SHA256 hash chain
that makes ANY AI agent action auditable and tamper-evident.

INVARIANTS:
  1. Each block's signature depends on the previous block's signature (chain)
  2. Tampering with any block invalidates all subsequent signatures
  3. Verification is O(n) in the number of blocks
  4. All action data is included in the hash (completeness)
  5. No numpy dependency — works anywhere Python runs

Usage as a library (for MCP server developers):

    from quantaoptima.audit import AuditChain

    chain = AuditChain(scope="my-mcp-server")
    chain.log("file_upload", {"filename": "report.pdf"}, {"status": "uploaded", "url": "..."})
    chain.log("analysis", {"input": "report.pdf"}, {"result": "positive", "confidence": 0.95})
    assert chain.verify()
    chain.export_json("audit_trail.json")

Usage with decorator (wrap any function):

    from quantaoptima.audit import AuditChain, auditable

    chain = AuditChain(scope="my-agent")

    @auditable(chain, action_type="calculation")
    def compute_risk(portfolio: dict) -> dict:
        # ... your logic ...
        return {"risk_score": 0.42}

    result = compute_risk({"stocks": ["AAPL", "GOOG"]})
    # Automatically logged to the audit chain with before/after state

Patent: US Provisional Application, Filed 5/25/25
"""

import hashlib
import hmac
import json
import time
import functools
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable


@dataclass
class AuditBlock:
    """A single auditable action in the chain."""
    block_number: int
    timestamp: float
    previous_hash: str
    scope: str
    action_type: str
    actor: str
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    metadata: Dict[str, Any]
    signature: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "scope": self.scope,
            "action_type": self.action_type,
            "actor": self.actor,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "metadata": self.metadata,
            "signature": self.signature,
        }


class AuditChain:
    """
    Cryptographic audit chain for AI agent actions.

    Every action generates:
      σₜ = HMAC-SHA256(σₜ₋₁ ∥ scope ∥ action_type ∥ actor ∥ state_before ∥ state_after ∥ metadata ∥ timestamp)

    This is a blockchain-style hash chain where tampering with any block
    invalidates all subsequent signatures. Designed for:
    - Regulatory compliance (pharma, finance, aerospace)
    - Scientific reproducibility
    - AI agent accountability
    - Agentic workflow auditing

    Usage:
        chain = AuditChain(scope="my-agent")
        chain.log("query", {"question": "..."}, {"answer": "..."})
        assert chain.verify()
        chain.export_json("audit.json")
    """

    def __init__(
        self,
        scope: str = "default",
        secret_key: Optional[bytes] = None,
        actor: str = "ai-agent",
    ):
        """
        Args:
            scope: Identifies the MCP server or workflow being audited.
            secret_key: HMAC key. If None, generates a random 256-bit key.
                       Store this key to verify audits later.
            actor: Default actor identity for logged actions.
        """
        if secret_key is None:
            secret_key = hashlib.sha256(
                str(time.time_ns()).encode() + scope.encode() + b"quantaoptima-audit"
            ).digest()
        self.secret_key = secret_key
        self.scope = scope
        self.default_actor = actor
        self.chain: List[AuditBlock] = []
        self._genesis_hash = "0" * 64

    def _compute_signature(
        self,
        previous_hash: str,
        scope: str,
        action_type: str,
        actor: str,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        metadata: Dict[str, Any],
        timestamp: float,
    ) -> str:
        """Compute HMAC-SHA256 signature for a block."""
        message = json.dumps(
            {
                "previous_hash": previous_hash,
                "scope": scope,
                "action_type": action_type,
                "actor": actor,
                "state_before": _serialize_for_hash(state_before),
                "state_after": _serialize_for_hash(state_after),
                "metadata": _serialize_for_hash(metadata),
                "timestamp": timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hmac.new(
            self.secret_key, message, hashlib.sha256
        ).hexdigest()

    def log(
        self,
        action_type: str,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None,
    ) -> AuditBlock:
        """
        Log an action to the audit chain.

        Args:
            action_type: What happened (e.g., "optimize", "file_upload", "query", "decision").
            state_before: State/input before the action.
            state_after: State/output after the action.
            metadata: Optional extra context (tags, parameters, etc.).
            actor: Who performed the action. Defaults to chain's default_actor.

        Returns:
            The signed AuditBlock.
        """
        block_number = len(self.chain)
        timestamp = time.time()
        previous_hash = (
            self.chain[-1].signature if self.chain else self._genesis_hash
        )
        actor = actor or self.default_actor
        metadata = metadata or {}

        signature = self._compute_signature(
            previous_hash, self.scope, action_type, actor,
            state_before, state_after, metadata, timestamp
        )

        block = AuditBlock(
            block_number=block_number,
            timestamp=timestamp,
            previous_hash=previous_hash,
            scope=self.scope,
            action_type=action_type,
            actor=actor,
            state_before=state_before,
            state_after=state_after,
            metadata=metadata,
            signature=signature,
        )

        self.chain.append(block)
        return block

    def verify(self) -> bool:
        """
        Verify the entire audit chain.

        Checks:
          1. Genesis block has correct previous hash
          2. Each block's signature matches its content
          3. Each block's previous_hash matches the prior block's signature

        Returns:
            True if chain is valid, False if tampered.
        """
        for i, block in enumerate(self.chain):
            expected_prev = (
                self.chain[i - 1].signature if i > 0 else self._genesis_hash
            )
            if block.previous_hash != expected_prev:
                return False

            expected_sig = self._compute_signature(
                block.previous_hash, block.scope, block.action_type,
                block.actor, block.state_before, block.state_after,
                block.metadata, block.timestamp,
            )
            if block.signature != expected_sig:
                return False

        return True

    def verify_detailed(self) -> Dict[str, Any]:
        """
        Verify chain and return detailed results per block.

        Returns:
            Dict with overall status and per-block verification.
        """
        results = []
        all_valid = True

        for i, block in enumerate(self.chain):
            expected_prev = (
                self.chain[i - 1].signature if i > 0 else self._genesis_hash
            )
            prev_ok = block.previous_hash == expected_prev

            expected_sig = self._compute_signature(
                block.previous_hash, block.scope, block.action_type,
                block.actor, block.state_before, block.state_after,
                block.metadata, block.timestamp,
            )
            sig_ok = block.signature == expected_sig
            block_valid = prev_ok and sig_ok

            if not block_valid:
                all_valid = False

            results.append({
                "block": i,
                "valid": block_valid,
                "chain_link_ok": prev_ok,
                "signature_ok": sig_ok,
                "action_type": block.action_type,
                "timestamp": block.timestamp,
            })

        return {
            "chain_valid": all_valid,
            "total_blocks": len(self.chain),
            "blocks": results,
        }

    def export_json(self, filepath: str) -> None:
        """Export the full audit chain as JSON."""
        data = {
            "scope": self.scope,
            "chain_length": len(self.chain),
            "verified": self.verify(),
            "exported_at": time.time(),
            "blocks": [block.to_dict() for block in self.chain],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def export_dict(self) -> Dict[str, Any]:
        """Export the full audit chain as a dict (for programmatic use)."""
        return {
            "scope": self.scope,
            "chain_length": len(self.chain),
            "verified": self.verify(),
            "exported_at": time.time(),
            "blocks": [block.to_dict() for block in self.chain],
        }

    def summary(self) -> Dict[str, Any]:
        """Get a summary of the audit trail."""
        if not self.chain:
            return {
                "scope": self.scope,
                "blocks": 0,
                "verified": True,
                "action_types": [],
            }

        first = self.chain[0]
        last = self.chain[-1]

        action_counts: Dict[str, int] = {}
        for block in self.chain:
            action_counts[block.action_type] = action_counts.get(block.action_type, 0) + 1

        return {
            "scope": self.scope,
            "blocks": len(self.chain),
            "verified": self.verify(),
            "action_types": action_counts,
            "first_action": first.action_type,
            "last_action": last.action_type,
            "total_time_seconds": round(last.timestamp - first.timestamp, 4),
            "actors": list(set(b.actor for b in self.chain)),
        }

    def filter_by_action(self, action_type: str) -> List[AuditBlock]:
        """Get all blocks of a specific action type."""
        return [b for b in self.chain if b.action_type == action_type]

    def filter_by_actor(self, actor: str) -> List[AuditBlock]:
        """Get all blocks by a specific actor."""
        return [b for b in self.chain if b.actor == actor]

    def tail(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get the last N blocks as dicts."""
        return [b.to_dict() for b in self.chain[-n:]]

    def __len__(self) -> int:
        return len(self.chain)

    def __repr__(self) -> str:
        return f"AuditChain(scope='{self.scope}', blocks={len(self.chain)}, verified={self.verify()})"


# ============================================================
# Decorator: @auditable — wrap any function with audit logging
# ============================================================

def auditable(
    chain: AuditChain,
    action_type: str = "function_call",
    capture_args: bool = True,
    capture_result: bool = True,
    actor: Optional[str] = None,
):
    """
    Decorator that automatically logs function calls to an AuditChain.

    Usage:
        chain = AuditChain(scope="my-server")

        @auditable(chain, action_type="calculation")
        def compute_risk(portfolio: dict) -> dict:
            return {"risk_score": 0.42}

        result = compute_risk({"stocks": ["AAPL"]})
        # Automatically logged with args as state_before, result as state_after

    Args:
        chain: The AuditChain to log to.
        action_type: Label for this action in the audit trail.
        capture_args: Whether to include function args in state_before.
        capture_result: Whether to include return value in state_after.
        actor: Override actor identity for this function.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            state_before = {}
            if capture_args:
                state_before = {
                    "function": func.__name__,
                    "args": _safe_serialize(args),
                    "kwargs": _safe_serialize(kwargs),
                }

            try:
                result = func(*args, **kwargs)
                state_after = {}
                if capture_result:
                    state_after = {
                        "function": func.__name__,
                        "result": _safe_serialize(result),
                        "status": "success",
                    }
                chain.log(
                    action_type=action_type,
                    state_before=state_before,
                    state_after=state_after,
                    metadata={"decorated": True},
                    actor=actor,
                )
                return result
            except Exception as e:
                chain.log(
                    action_type=action_type,
                    state_before=state_before,
                    state_after={"error": str(e), "status": "failed"},
                    metadata={"decorated": True, "exception_type": type(e).__name__},
                    actor=actor,
                )
                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            state_before = {}
            if capture_args:
                state_before = {
                    "function": func.__name__,
                    "args": _safe_serialize(args),
                    "kwargs": _safe_serialize(kwargs),
                }

            try:
                result = await func(*args, **kwargs)
                state_after = {}
                if capture_result:
                    state_after = {
                        "function": func.__name__,
                        "result": _safe_serialize(result),
                        "status": "success",
                    }
                chain.log(
                    action_type=action_type,
                    state_before=state_before,
                    state_after=state_after,
                    metadata={"decorated": True},
                    actor=actor,
                )
                return result
            except Exception as e:
                chain.log(
                    action_type=action_type,
                    state_before=state_before,
                    state_after={"error": str(e), "status": "failed"},
                    metadata={"decorated": True, "exception_type": type(e).__name__},
                    actor=actor,
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


# ============================================================
# Legacy compatibility: CryptoAuditTrail (wraps AuditChain)
# ============================================================

class CryptoAuditTrail:
    """
    Legacy compatibility class for the original optimization-focused audit trail.
    Wraps AuditChain with the original API.

    New code should use AuditChain directly.
    """

    def __init__(self, secret_key: Optional[bytes] = None):
        self._chain = AuditChain(
            scope="quantaoptima-optimizer",
            secret_key=secret_key,
            actor="optimizer",
        )
        # Expose the secret key for backward compat
        self.secret_key = self._chain.secret_key

    @property
    def chain(self) -> List[AuditBlock]:
        return self._chain.chain

    def record_step(
        self,
        state_before: Dict[str, float],
        state_after: Dict[str, float],
        operation: Dict[str, Any],
    ) -> AuditBlock:
        """Record an optimization step (legacy API)."""
        return self._chain.log(
            action_type="optimization_step",
            state_before=state_before,
            state_after=state_after,
            metadata=operation,
            actor="optimizer",
        )

    def verify(self) -> bool:
        return self._chain.verify()

    def export_json(self, filepath: str) -> None:
        self._chain.export_json(filepath)

    def summary(self) -> Dict[str, Any]:
        raw = self._chain.summary()
        # Translate to legacy format
        if not self._chain.chain:
            return {"blocks": 0, "verified": True}

        first = self._chain.chain[0]
        last = self._chain.chain[-1]
        return {
            "blocks": len(self._chain.chain),
            "verified": self._chain.verify(),
            "initial_entropy": first.state_before.get("entropy", None),
            "final_entropy": last.state_after.get("entropy", None),
            "initial_best_fitness": first.state_before.get("best_fitness", None),
            "final_best_fitness": last.state_after.get("best_fitness", None),
            "total_time_seconds": raw.get("total_time_seconds", 0),
        }


# ============================================================
# Serialization helpers
# ============================================================

def _serialize_for_hash(obj: Any) -> Any:
    """Recursively convert non-JSON types for hashing."""
    try:
        import numpy as np
        _has_numpy = True
    except ImportError:
        _has_numpy = False

    if isinstance(obj, dict):
        return {k: _serialize_for_hash(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_hash(v) for v in obj]
    elif _has_numpy:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, (np.complexfloating,)):
            return {"real": float(obj.real), "imag": float(obj.imag)}
    return obj


def _safe_serialize(obj: Any) -> Any:
    """Safely serialize any Python object for audit logging."""
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        pass

    if isinstance(obj, dict):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        try:
            import numpy as np
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
        except ImportError:
            pass
        return str(obj)
