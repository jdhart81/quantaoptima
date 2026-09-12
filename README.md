# QuantaOptima

**Auditable AI Actions — cryptographic audit trails for AI agent workflows.**

QuantaOptima authenticates explicitly logged AI agent action records. It ships as an MCP server that any LLM agent can call, and as a Python library that any MCP server developer can embed. Explicitly recorded actions are authenticated with HMAC-SHA256 and linked in a hash chain. Verification detects changes to authenticated record contents; it does not establish that an action occurred or that all actions were recorded.

```
pip install https://github.com/jdhart81/quantaoptima/releases/download/v0.4.0/quantaoptima-0.4.0-py3-none-any.whl
```

The package is distributed through GitHub Releases; it is not currently listed on PyPI.

## Release status and migration

Version **0.4.0 is an alpha release**. The MCP server now persists its audit chain
under `~/.quantaoptima/audit` (override with `QUANTAOPTIMA_AUDIT_DIR`). Back up both
the database and its private audit key. Imported JSON is unverified until checked
with that key; HTML itself is not cryptographic evidence.

Paid licenses now use Ed25519. Existing HMAC licenses must be reissued, and
clients need the issuer's trusted public PEM. No production issuer key is bundled
in this checkout. See [operations and migration](docs/OPERATIONS.md),
[release notes](CHANGELOG.md), and [security limitations](SECURITY.md).

## Why This Exists

Agent tracing tools help developers inspect workflow activity. QuantaOptima provides a local integrity layer for explicitly recorded actions: authenticate records, check the stored chain, and export it for inspection.

A valid chain authenticates recorded contents under its key; it does not prove actor identity, real-world execution, or completeness. Detecting a removed suffix requires an independent checkpoint. See the [security model](SECURITY.md).

The MCP server exposes these operations:

- **`quantaoptima_log_action`** — Log any action with before/after state to the audit chain
- **`quantaoptima_verify_chain`** — Verify the HMAC-SHA256 chain integrity
- **`quantaoptima_export_chain`** — Export the full audit trail as JSON
- **`quantaoptima_chain_status`** — View chain statistics and health

Plus a built-in quantum-inspired optimizer that demonstrates the audit chain in action:

- **`quantaoptima_optimize`** — Run optimization with every step automatically audited
- **`quantaoptima_explain`** — Human-readable explanation of what the optimizer did
- **`quantaoptima_benchmark`** — Compare against scipy's classical methods [PRO]
- **`quantaoptima_observe`** — Inspect entropy, interference, phase transitions [PRO]
- **`quantaoptima_audit`** — Verify the optimizer's audit trail [PRO]

## What Makes It Different

### 1. Every Action Is Tamper-Evident

Every logged action produces an HMAC-SHA256 signature chained to the previous action. Modifying signed contents makes chain verification fail. This authenticates recorded data; it does not prove actions occurred, authenticate actor names, or detect a deleted suffix without an independent checkpoint. See the [security model](SECURITY.md).

### 2. Built for AI Agents (MCP-Native)

Ships as an MCP server. After installing the package and configuring a compatible client, an agent can explicitly log actions, verify the chain, and export records. Other agent actions are not automatically captured merely because this server is connected.

### 3. Works as a Library Too

Other MCP server developers can embed QuantaOptima's audit chain in their own tools:

```python
from quantaoptima import AuditChain, auditable

chain = AuditChain(scope="my-mcp-server")

# Log actions explicitly
chain.log("query", {"question": "What's the revenue?"}, {"answer": "$4.2M", "source": "db"})
chain.log("decision", {"options": ["A", "B"]}, {"chosen": "A", "reason": "lower risk"})

# Or use the decorator to auto-audit any function
@auditable(chain, action_type="calculation")
def compute_risk(portfolio: dict) -> dict:
    return {"risk_score": 0.42}

result = compute_risk({"stocks": ["AAPL", "GOOG"]})

# Verify and export
assert chain.verify()
chain.export_json("audit_trail.json")
```

### 4. Built-In Optimizer Demo

The quantum-inspired optimizer shows the audit chain at work. Every optimization step is cryptographically signed, producing a complete provenance record from start to finish. The optimizer features:

- Quantum-inspired Measurement-Collapse Pruner algorithm
- Built-in interpretability: entropy trajectories, interference metrics, phase transitions
- Six built-in benchmark objectives; convergence quality depends on the problem and budget

## Quick Start

### MCP Server (for Claude, GPT, or any MCP-compatible agent)

```bash
pip install https://github.com/jdhart81/quantaoptima/releases/download/v0.4.0/quantaoptima-0.4.0-py3-none-any.whl
quantaoptima-server
```

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "quantaoptima": {
      "command": "quantaoptima-server"
    }
  }
}
```

Then ask Claude:

- *"Log a decision to the audit chain: I chose option A because it had lower risk."*
- *"Verify the audit chain and show me the status."*
- *"Optimize the Rastrigin function in 10 dimensions, then verify the audit trail."*
- *"Export the full audit chain to audit_trail.json."*

### Python Library (for MCP server developers)

```python
from quantaoptima import AuditChain

# Create a chain for your server
chain = AuditChain(scope="my-server", actor="my-agent")

# Log any action
chain.log(
    action_type="api_call",
    state_before={"endpoint": "/users", "method": "GET"},
    state_after={"status": 200, "count": 42},
    metadata={"duration_ms": 150},
)

# Verify chain integrity
print(chain.verify())        # True
print(chain.summary())       # Stats and health
print(chain.verify_detailed())  # Per-block verification

# Export
chain.export_json("trail.json")
```

### Decorator Pattern

```python
from quantaoptima import AuditChain, auditable

chain = AuditChain(scope="data-pipeline")

@auditable(chain, action_type="transform")
def clean_data(raw: list) -> list:
    return [x for x in raw if x is not None]

@auditable(chain, action_type="analysis")
def compute_stats(data: list) -> dict:
    return {"mean": sum(data) / len(data), "count": len(data)}

# Both calls are automatically logged to the audit chain
clean = clean_data([1, None, 3, None, 5])
stats = compute_stats(clean)

assert chain.verify()
print(f"Audit trail: {len(chain)} blocks, verified")
```

## Pricing

| | Community (Free) | Pro ($29/mo) | Enterprise |
|---|---|---|---|
| Audit Chain | Unlimited | Unlimited + analytics | Custom |
| Log Actions | ✓ | ✓ | ✓ |
| Verify Chain | ✓ | ✓ | ✓ |
| Export Chain | ✓ | ✓ + formats | ✓ + custom |
| Optimizer Objectives | 3 | All 6 | All + custom |
| Max Dimensions | 10 | 100 | Unlimited |
| Max Iterations | 100 | 5,000 | Unlimited |
| Benchmark vs scipy | — | ✓ | ✓ |
| Observability | — | ✓ | ✓ |
| Support | Community | Email | Priority + SLA |
| | [Install Free](https://github.com/jdhart81/quantaoptima/releases/tag/v0.4.0) | [Get Pro](https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04) | [Contact](mailto:hartjustin6@gmail.com) |

Annual Pro: **$199/year** (save 43%)

## How the Audit Chain Works

```
Action 1                    Action 2                    Action 3
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ action: "query"  │         │ action: "decide" │         │ action: "execute"│
│ before: {...}    │         │ before: {...}    │         │ before: {...}    │
│ after: {...}     │         │ after: {...}     │         │ after: {...}     │
│ sig: HMAC(       │──chain──│ sig: HMAC(       │──chain──│ sig: HMAC(       │
│   prev_sig +     │         │   prev_sig +     │         │   prev_sig +     │
│   data           │         │   data           │         │   data           │
│ )                │         │ )                │         │ )                │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

Each block's signature depends on the previous block's signature. Verification checks each block’s content signature, block number, and link to its predecessor. A content change fails verification. A key holder can re-sign history; completeness requires an independently retained checkpoint.

## How the Optimizer Works

The built-in quantum-inspired optimizer runs a loop of four steps:

1. **Encode** — Map population fitness to complex amplitudes via Boltzmann weighting
2. **Evolve** — Apply three quantum-inspired operators: Rotation R(θ), Entanglement E(λ), Scrambling S(γ)
3. **Collapse** — PCA-derived measurement basis + Born rule probabilities + entropy constraint = adaptive selection
4. **Audit** — Every step is HMAC-SHA256 signed and hash-chained

## Project Structure

```
quantaoptima/
├── audit.py           # Core: AuditChain, AuditBlock, @auditable decorator
├── core.py            # Quantum state encoder + evolution operators
├── mcp_algorithm.py   # Measurement-Collapse Pruner
├── optimizer.py       # Full optimizer orchestration
├── licensing.py       # Ed25519 license issuance and public-key verification
├── storage.py         # Durable SQLite audit chain and separate HMAC key
├── server.py          # MCP server (10 tools)
```

## Patent Status

US Provisional Patent Application filed May 25, 2025. Covers:
- Cryptographic audit trail for AI agent actions
- Quantum-inspired optimization with measurement collapse
- Entropy-constrained adaptive selection
- Foundation model integration architecture

## Citation

```bibtex
@software{hart2025quantaoptima,
  author = {Hart, Justin},
  title = {QuantaOptima: Auditable AI Actions},
  year = {2025},
  url = {https://github.com/jdhart81/quantaoptima}
}
```

## License

Apache 2.0 — use it freely, including commercially. The patent covers the specific algorithm implementation; the Apache license grants you a patent license for use of this software.
