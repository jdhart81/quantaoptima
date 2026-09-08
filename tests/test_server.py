import json
import pytest
from quantaoptima import server


@pytest.mark.asyncio
async def test_mcp_tools_restore_audit_after_restart(tmp_path, monkeypatch):
    monkeypatch.setenv('QUANTAOPTIMA_AUDIT_DIR', str(tmp_path))
    monkeypatch.setattr(server, '_audit_chain', None)
    mcp = server._get_mcp()
    assert len(await mcp.list_tools()) == 10
    await mcp.call_tool('quantaoptima_log_action', {'action_type': 'review', 'state_after': '{"ok":true}'})
    first_key = server._audit_chain.secret_key
    monkeypatch.setattr(server, '_audit_chain', None)
    restored = server._get_audit_chain()
    assert len(restored) == 1
    assert restored.secret_key == first_key
    assert restored.verify()
    await mcp.call_tool('quantaoptima_log_action', {'action_type': 'next'})
    assert len(restored) == 2
    assert restored.verify()
