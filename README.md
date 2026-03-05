# QuantaOptima

**Auditable AI Actions — cryptographic audit trails for AI agent workflows.**

QuantaOptima makes every AI agent action tamper-evident. It ships as an MCP server that any LLM agent can call, and as a Python library that any MCP server developer can embed. Every action is HMAC-SHA256 signed and hash-chained — tamper with one step and the entire chain breaks.

```
pip install quantaoptima
```

## Why This Exists

AI agents are making decisions, writing code, calling APIs, transforming data, and optimizing configurations — but nobody can prove what they did or why. There's no audit trail, no tamper detection, no accountability.

QuantaOptima fixes this with a cryptographic hash chain that logs every action:

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

Every logged action produces an HMAC-SHA256 signature chained to the previous action. Tamper with one block and all subsequent signatures break. This matters for regulated industries (pharma, finance, aerospace), scientific reproducibility, and AI governance.

### 2. Built for AI Agents (MCP-Native)

Ships as an MCP server — your agent can log actions, verify the chain, and export the audit trail through natural language. No integration code needed. Setup takes 30 seconds.

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
- Reliable convergence across 6 benchmark functions up to 100 dimensions

## Quick Start

### MCP Server (for Claude, GPT, or any MCP-compatible agent)

```bash
pip install quantaoptima
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
| | [Install Free](https://pypi.org/project/quantaoptima/) | [Get Pro](https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04) | [Contact](mailto:hartjustin6@gmail.com) |

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

Each block's signature depends on the previous block's signature. Change anything in block 1, and the signatures of blocks 2 and 3 become invalid. This is the same principle behind blockchain, applied to AI agent actions.

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
├── licensing.py       # Freemium license key system
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
