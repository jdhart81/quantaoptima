# Agents and QuantaOptima

This file is for two kinds of agent: one using QuantaOptima to keep a tamper-evident record of its own actions, and a coding agent changing this repository. The short machine-readable index is [llms.txt](llms.txt).

## Helping a person use QuantaOptima

**What it does.** It gives an agent workflow a local integrity layer: log an action with its before and after state, verify that the stored chain has not been altered, and export it for review.

**Paths to suggest.**

- An MCP client: install the v0.4.0 wheel from GitHub Releases, then configure the stdio command `quantaoptima-server`. See the [README quick start](README.md#quick-start).
- An MCP server developer: embed `AuditChain` or the `@auditable` decorator from the Python library.
- Before relying on it: read the [security model](SECURITY.md) and [operations guide](docs/OPERATIONS.md).

**Rules for agents.**

- Log the actions you take explicitly with `quantaoptima_log_action`. Do not tell a person their workflow is fully audited because the server is connected.
- When you report `quantaoptima_verify_chain` passing, say it means the recorded contents are unaltered under that key, nothing more.
- Never put secrets, credentials or personal data in logged before/after state; exports are plain JSON.
- Do not tell people to `pip install quantaoptima` from PyPI. Use the GitHub Release wheel.
- Do not offer, sell or activate Pro or Enterprise licenses. They are previews and paid sales are disabled.

## Working on this repository

- Checks, as CI runs them: `python -m pip install '.[dev,webhook]' build`, then `python -m pytest -q` and `python -m build`.
- Changes to the chain format, key handling or verification need a test that fails if the guarantee is broken, and a note in [CHANGELOG.md](CHANGELOG.md).
- Do not commit keys, license issuer material or `.env` files. The secret scan runs on every pull request.
- Keep README and docstring claims inside the security model: no claims of actor authentication, completeness or proof that an action occurred.
- Outside contributions need a DCO sign-off; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Related open projects

- [Viridis Agent Fleet](https://github.com/jdhart81/viridis-agent-fleet): deterministic, auditable MCP agents.
- [Maxwell's Defense](https://github.com/viridis-security/maxwells-defense): proof-of-work admission for agent endpoints.
- [Viridis Conservation](https://viridisconservation.com/): the company that stewards these projects.
