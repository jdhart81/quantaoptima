import asyncio
import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from quantaoptima import AuditChain, PersistentAuditChain, auditable
from quantaoptima.viewer import render_chain_html


def test_secure_keys_do_not_repeat_when_clock_repeats(monkeypatch):
    monkeypatch.setattr('quantaoptima.audit.time.time_ns', lambda: 1234)
    assert AuditChain(scope='same').secret_key != AuditChain(scope='same').secret_key


def test_log_and_export_capture_independent_snapshots():
    chain = AuditChain()
    state = {'items': [1]}
    metadata = {'tags': ['initial']}
    chain.log('read', state, state, metadata)
    state['items'].append(2)
    metadata['tags'].append('changed')
    exported = chain.export_dict()
    exported['blocks'][0]['state_after']['items'].append(3)
    assert chain.chain[0].state_before == {'items': [1]}
    assert chain.chain[0].metadata == {'tags': ['initial']}
    assert chain.verify()


@pytest.mark.parametrize('asynchronous', [False, True])
def test_decorator_records_before_mutation_and_after_snapshot(asynchronous):
    chain = AuditChain()
    def mutate(values):
        values.append(2)
        return values
    async def async_mutate(values):
        return mutate(values)
    fn = auditable(chain)(async_mutate if asynchronous else mutate)
    values = [1]
    result = asyncio.run(fn(values)) if asynchronous else fn(values)
    result.append(3)
    block = chain.chain[0]
    assert block.state_before['args'] == [[1]]
    assert block.state_after['result'] == [1, 2]
    assert chain.verify()


def test_decorator_records_failure():
    chain = AuditChain()
    @auditable(chain)
    def fail():
        raise ValueError('expected')
    with pytest.raises(ValueError):
        fail()
    assert chain.chain[0].state_after['status'] == 'failed'
    assert chain.verify()


@pytest.mark.parametrize('field,value', [('block_number', 999), ('scope', 'changed'), ('actor', 'changed'), ('state_after', {'changed': True}), ('previous_hash', 'f'*64)])
def test_tampering_is_rejected(field, value):
    chain = AuditChain()
    chain.log('test', {}, {})
    setattr(chain.chain[0], field, value)
    assert not chain.verify()
    assert not chain.verify_detailed()['chain_valid']


def test_json_roundtrip_with_numpy(tmp_path):
    chain = AuditChain()
    chain.log('array', {'x': np.array([1, 2])}, {'n': np.int64(2)})
    path = tmp_path / 'audit.json'
    chain.export_json(path)
    restored = AuditChain.from_dict(json.loads(path.read_text()), chain.secret_key)
    assert restored.verify()
    with pytest.raises(ValueError):
        AuditChain.from_dict(chain.export_dict(), b'wrong')


def test_concurrent_library_logging():
    chain = AuditChain()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: chain.log('thread', {'i': i}, {}), range(40)))
    assert len(chain) == 40
    assert chain.verify()


def test_persistence_restarts_and_multiple_writers(tmp_path):
    first = PersistentAuditChain(tmp_path)
    first.log('first', {}, {})
    second = PersistentAuditChain(tmp_path)
    assert second.secret_key == first.secret_key
    assert len(second) == 1
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: (first if i % 2 else second).log('next', {'i': i}, {}), range(20)))
    restored = PersistentAuditChain(tmp_path)
    assert len(restored) == 21
    assert restored.verify()
    assert (tmp_path / 'audit.key').stat().st_mode & 0o777 == 0o600
    assert (tmp_path / 'audit.sqlite3').stat().st_mode & 0o777 == 0o600


def test_missing_persistent_key_never_replaces_history(tmp_path):
    chain = PersistentAuditChain(tmp_path)
    chain.log('test', {}, {})
    (tmp_path / 'audit.key').unlink()
    with pytest.raises(ValueError, match='key missing'):
        PersistentAuditChain(tmp_path)
    assert not (tmp_path / 'audit.key').exists()


def test_corrupt_persistent_history_is_rejected(tmp_path):
    chain = PersistentAuditChain(tmp_path)
    chain.log('test', {}, {})
    with sqlite3.connect(tmp_path / 'audit.sqlite3') as db:
        data = json.loads(db.execute('SELECT data FROM blocks').fetchone()[0])
        data['actor'] = 'intruder'
        db.execute('UPDATE blocks SET data=?', (json.dumps(data),))
    with pytest.raises(ValueError, match='verification failed'):
        PersistentAuditChain(tmp_path)


def test_viewer_never_trusts_imported_verified_flag(tmp_path):
    chain = AuditChain()
    chain.log('decision', {}, {'approved': False})
    data = chain.export_dict()
    data['blocks'][0]['state_after']['approved'] = True
    path = tmp_path / 'viewer.html'
    render_chain_html(data, str(path))
    assert '>UNVERIFIED<' in path.read_text()
    render_chain_html(data, str(path), secret_key=chain.secret_key)
    assert '>INVALID ✗<' in path.read_text()
    render_chain_html(chain.export_dict(), str(path), secret_key=chain.secret_key)
    assert '>VERIFIED ✓<' in path.read_text()


def test_imported_viewer_escapes_block_fields(tmp_path):
    chain = AuditChain()
    chain.log('test', {}, {})
    data = chain.export_dict()
    data['blocks'][0]['block_number'] = '<script>alert(1)</script>'
    data['blocks'][0]['signature'] = '<img src=x>'
    path = tmp_path / 'viewer.html'
    render_chain_html(data, str(path))
    assert '<script>alert(1)</script>' not in path.read_text()
    assert '<img src=x>' not in path.read_text()
