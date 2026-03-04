# QuantaOptima

**Quantum-inspired black-box optimization that uses 7–31× fewer function evaluations.**

QuantaOptima replaces expensive trial-and-error with interference-enhanced selection. Instead of evaluating thousands of candidates blindly, it encodes your population as a quantum-like state, evolves it through rotation/entanglement/scrambling operators, then collapses to survivors via an entropy-constrained measurement — the same math that makes quantum computers fast, running on classical hardware.

```
pip install quantaoptima
```

## Pricing

| | Community (Free) | Pro ($29/mo) | Enterprise |
|---|---|---|---|
| Objectives | 3 (Sphere, Rastrigin, Rosenbrock) | All 6 | All + custom |
| Max Dimensions | 10 | 100 | Unlimited |
| Max Iterations | 100 | 5,000 | Unlimited |
| MCP Tools | optimize, explain | All 6 tools | All + custom API |
| Benchmark Comparison | — | ✓ | ✓ |
| Observability / AI Safety | — | ✓ | ✓ |
| Audit Export | — | ✓ | ✓ |
| Support | Community | Email | Priority + SLA |
| | [Install Free](https://pypi.org/project/quantaoptima/) | [Get Pro](https://buy.stripe.com/6oU28r5tIcpq97Y6egfYY02) | [Contact](mailto:hartjustin6@gmail.com) |

Annual Pro: **$199/year** (save 43%)

## Why This Exists

Every hyperparameter sweep, simulation-based design loop, and neural architecture search burns compute on function evaluations. QuantaOptima's Measurement-Collapse Pruner (MCP) reduces that cost by an order of magnitude on problems where evaluations are expensive and dimensionality is moderate (d ≤ 50).

| Problem | Dimensions | QuantaOptima Evals | Differential Evolution Evals | Speedup |
|---|---|---|---|---|
| Rastrigin | 10 | 1,200 | 9,400 | 7.8× |
| Rosenbrock | 20 | 2,800 | 41,000 | 14.6× |
| Ackley | 20 | 1,500 | 47,000 | 31.3× |

Results from controlled benchmarks (p < 0.001, Wilcoxon signed-rank test). See `benchmarks/` for reproduction.

## Quick Start

### Python API

```python
from quantaoptima import QuantaOptimizer

optimizer = QuantaOptimizer(n_dimensions=10, population_size=50)
result = optimizer.optimize(
    objective_function=lambda x: -sum(x**2),  # minimize sum of squares
    bounds=[(-5, 5)] * 10,
    max_iterations=200,
)

print(f"Best: {result.best_fitness:.6e} in {result.n_function_evals} evals")
print(f"Audit verified: {result.audit_summary['verified']}")
```

### MCP Server (for Claude, GPT, or any MCP-compatible agent)

```bash
pip install quantaoptima[mcp]
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

Then ask Claude: *"Optimize the Rastrigin function in 20 dimensions and explain what the quantum operators did."*

### License Key Setup (Pro/Enterprise)

```bash
# Option 1: Environment variable
export QUANTAOPTIMA_LICENSE="your-key-here"

# Option 2: License file
mkdir -p ~/.quantaoptima
echo "your-key-here" > ~/.quantaoptima/license.key
```

Check your license status by asking your agent to call `quantaoptima_status`.

### Available MCP Tools

| Tool | Tier | Purpose |
|---|---|---|
| `quantaoptima_optimize` | Free | Run optimization on built-in objectives |
| `quantaoptima_explain` | Free | Human-readable explanation of what happened |
| `quantaoptima_status` | Free | Check license status and available features |
| `quantaoptima_benchmark` | Pro | Compare against differential evolution & dual annealing |
| `quantaoptima_observe` | Pro | Inspect landscape, entropy trajectory, phase transitions |
| `quantaoptima_audit` | Pro | Verify and export cryptographic audit trail |

## How It Works

QuantaOptima runs a loop of four steps:

1. **Encode** — Map population fitness to complex amplitudes via Boltzmann weighting: `αᵢ = √(βᵢ/Z) · exp(iφᵢ)`
2. **Evolve** — Apply three quantum-inspired operators:
   - **R(θ)**: Rotation encodes fitness into phases (like Grover's oracle)
   - **E(λ)**: Entanglement creates interference between similar solutions
   - **S(γ)**: Scrambling adds controlled exploration noise
3. **Collapse** — PCA-derived measurement basis + Born rule probabilities + entropy constraint = adaptive selection that provably reduces entropy faster than classical tournament selection
4. **Audit** — Every step is HMAC-SHA256 signed and hash-chained for tamper detection

The key theoretical result (Theorem 1, formally verified in Lean 4): for aligned phases, the entropy reduction rate satisfies `dH/dλ = -Γ(t)` where `Γ(t) ≥ 0` is the interference advantage — extra information extraction that classical methods cannot access.

## Observability Mode (AI Safety)

Every optimization run produces a full telemetry stream:

- **Entropy trajectory** — How the optimizer's "attention" narrows over time
- **Coherence budget** — How much quantum information is available for exploitation
- **Interference advantage** — How much extra selection power comes from cross-solution correlations
- **Phase transitions** — Sharp entropy drops revealing qualitative landscape changes
- **Cryptographic audit** — Tamper-evident record of every decision

This isn't bolted on — it falls out of the math. The same measurement-collapse mechanics that make the optimizer efficient also make it *interpretable*. You can see exactly why it chose what it chose.

Call `quantaoptima_observe` via MCP to inspect the landscape of any run.

## Project Structure

```
quantaoptima/
├── core.py            # Quantum state encoder + evolution operators
├── mcp_algorithm.py   # Measurement-Collapse Pruner
├── optimizer.py       # Full optimizer orchestration
├── audit.py           # Cryptographic audit trail
├── licensing.py       # Freemium license key system
├── server.py          # MCP server (LLM integration)
benchmarks/
├── benchmark.py       # Comparative benchmarks
├── rigorous_validation.py  # Statistical validation suite
lean/
├── quantaoptima_final.lean # Lean 4 / Mathlib formalization
```

## Patent Status

US Provisional Patent Application filed May 25, 2025. Covers:
- Quantum-inspired optimization with measurement collapse
- Entropy-constrained adaptive selection
- Foundation model integration architecture
- Cryptographic audit trail for verifiable optimization

## Citation

```bibtex
@software{hart2025quantaoptima,
  author = {Hart, Justin},
  title = {QuantaOptima: Quantum-Inspired Optimization with Entropy-Constrained Measurement Collapse},
  year = {2025},
  url = {https://github.com/justinhart/quantaoptima}
}
```

## License

Apache 2.0 — use it freely, including commercially. The patent covers the specific algorithm implementation; the Apache license grants you a patent license for use of this software.
