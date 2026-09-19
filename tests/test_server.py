import json
from pathlib import Path
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


def test_export_paths_are_confined_and_do_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.setenv('QUANTAOPTIMA_EXPORT_DIR', str(tmp_path))
    destination = server._resolve_export_path('review', '.json')
    assert destination == tmp_path / 'review.json'
    with pytest.raises(ValueError, match='filename only'):
        server._resolve_export_path('../outside.json', '.json')
    with pytest.raises(ValueError, match='filename only'):
        server._resolve_export_path(str(tmp_path / 'absolute.json'), '.json')

    chain = server.AuditChain()
    chain.log('review', {}, {'ok': True})
    chain.export_json(destination, overwrite=False)
    with pytest.raises(FileExistsError):
        chain.export_json(destination, overwrite=False)


def test_hard_evaluation_budget_and_quanta_iteration_accounting():
    budget = server._EvaluationBudget(lambda x: -float(x[0] ** 2), 2)
    assert budget.minimize([2.0]) == 4.0
    assert budget.minimize([1.0]) == 1.0
    assert budget.count == 2
    assert budget.best_fitness == -1.0
    with pytest.raises(server._BudgetExhausted):
        budget.minimize([0.0])
    assert server._quanta_iterations_for_budget(1000, 30) == 32
    assert 30 * (1 + server._quanta_iterations_for_budget(1000, 30)) <= 1000
    multiplier, iterations = server.differential_evolution_plan(1000, 10)
    assert multiplier * 10 * (iterations + 1) <= 1000


def test_legacy_server_and_setup_script_are_non_executing():
    root = Path(__file__).resolve().parents[1]
    legacy = (root / 'mcp_server' / 'server.py').read_text()
    setup = (root / 'SETUP_MCP.sh').read_text()
    stripe_setup = (root / 'stripe_setup.py').read_text()
    assert 'eval(' not in legacy
    assert 'curl ' not in setup
    assert 'sed -i' not in setup
    assert 'retired' in legacy.lower() and 'retired' in setup.lower()
    assert '--allow-live' in stripe_setup
    assert 'live Stripe mutation is blocked' in stripe_setup


def test_active_surfaces_do_not_advertise_checkout_links():
    root = Path(__file__).resolve().parents[1]
    active_surfaces = (
        root / 'README.md',
        root / 'docs' / 'index.html',
        root / 'docs' / 'OPERATIONS.md',
        root / 'quantaoptima' / 'server.py',
        root / 'quantaoptima' / 'licensing.py',
    )
    for surface in active_surfaces:
        assert 'buy.stripe.com' not in surface.read_text(), surface
