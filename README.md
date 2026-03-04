# QuantaOptima

**The first auditable black-box optimizer built for AI agents.**

QuantaOptima is a quantum-inspired optimization engine that ships as an MCP server — giving Claude, GPT, or any MCP-compatible agent the ability to optimize parameters, benchmark results, and cryptographically verify every decision. No other optimizer does this.

```
pip install quantaoptima
```

## Why This Exists

AI agents are increasingly asked to tune hyperparameters, calibrate simulations, and optimize configurations. But they have no native optimization tools. They either brute-force it, call out to scripts you have to write, or guess.

QuantaOptima gives agents a first-class optimization toolkit:

- **`quantaoptima_optimize`** — Run optimization on 6 built-in benchmark functions (2–100 dimensions)
- **`quantaoptima_explain`** — Get a human-readable explanation of what the optimizer did and why
- **`quantaoptima_benchmark`** — Compare head-to-head against scipy's Differential Evolution and Dual Annealing
- **`quantaoptima_observe`** — Inspect entropy trajectories, interference metrics, and phase transitions (interpretability)
- **`quantaoptima_audit`** — Verify and export the HMAC-SHA256 cryptographic audit trail
- **`quantaoptima_status`** — Check license tier and available features

## What Makes It Different

### 1. Built for AI Agents (MCP-Native)
No other optimizer ships as an MCP server. Your agent can optimize, interpret results, and verify the audit trail — all through natural language. Setup takes 30 seconds.

### 2. Every Step Is Auditable
Every optimization step is HMAC-SHA256 signed and hash-chained. Tamper with one step and all subsequent signatures break. This matters for regulated industries (pharma, finance, aerospace) and scientific reproducibility.

### 3. Interpretable by Design
The `observe` tool exposes the optimizer's internal state: entropy trajectories, coherence budgets, interference advantages, and phase transition detection. You can see *how* the optimizer explored the landscape, not just the final answer.

### 4. Quantum-Inspired Algorithm
The Measurement-Collapse Pruner encodes populations as quantum-like states, evolves them through rotation/entanglement/scrambling operators, and collapses to survivors via entropy-constrained measurement. The interference metric measures bits of information advantage from cross-solution correlations — a novel interpretability signal.

## Honest Performance Assessment

QuantaOptima is a functional metaheuristic optimizer that reliably converges across all 6 benchmark functions up to 100 dimensions. It is **not** faster or more accurate than scipy's Dual Annealing on standard benchmarks at equivalent evaluation budgets.

| What QuantaOptima Does Well | Where Classical Methods Win |
|---|---|
| MCP delivery for AI agents (unique) | Raw solution quality (Dual Annealing) |
| Cryptographic audit trail (unique) | Computation speed (Dual Annealing is 3-5x faster) |
| Full interpretability telemetry (unique) | Mature, battle-tested over 30 years |
| Reproducible across seeds | Wider ecosystem and documentation |
| Scales to 100D | Better convergence on smooth problems |

**Use QuantaOptima when** you need an AI agent to optimize autonomously with auditable, interpretable results. **Use scipy when** you're writing a script and only care about the final answer.

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
| | [Install Free](https://pypi.org/project/quantaoptima/) | [Get Pro](https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04) | [Contact](mailto:hartjustin6@gmail.com) |

Annual Pro: **$199/year** (save 43%)

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

Then ask Claude: *"Optimize the Rastrigin function in 10 dimensions, then explain what the quantum operators did and show me the audit trail."*

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

### License Key Setup (Pro/Enterprise)

```bash
# Option 1: Environment variable
export QUANTAOPTIMA_LICENSE="your-key-here"

# Option 2: License file
mkdir -p ~/.quantaoptima
echo "your-key-here" > ~/.quantaoptima/license.key
```

## How It Works

QuantaOptima runs a loop of four steps:

1. **Encode** — Map population fitness to complex amplitudes via Boltzmann weighting: `αᵢ = √(βᵢ/Z) · exp(iφᵢ)`
2. **Evolve** — Apply three quantum-inspired operators:
   - **R(θ)**: Rotation encodes fitness into phases (like Grover's oracle)
   - **E(λ)**: Entanglement creates interference between similar solutions
   - **S(γ)**: Scrambling adds controlled exploration noise
3. **Collapse** — PCA-derived measurement basis + Born rule probabilities + entropy constraint = adaptive selection
4. **Audit** — Every step is HMAC-SHA256 signed and hash-chained for tamper detection

## Observability & Interpretability

Every optimization run produces a full telemetry stream:

- **Entropy trajectory** — How the optimizer's "attention" narrows over time
- **Coherence budget** — How much quantum information is available for exploitation
- **Interference advantage** — Bits of selection power from cross-solution correlations
- **Phase transitions** — Sharp entropy drops revealing qualitative landscape changes
- **Cryptographic audit** — Tamper-evident record of every decision

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
  title = {QuantaOptima: Auditable Quantum-Inspired Optimization for AI Agents},
  year = {2025},
  url = {https://github.com/jdhart81/quantaoptima}
}
```

## License

Apache 2.0 — use it freely, including commercially. The patent covers the specific algorithm implementation; the Apache license grants you a patent license for use of this software.
