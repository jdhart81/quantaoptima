# QuantaOptima v0.2.0 Launch Posts

Copy-paste these to get the word out. Post in this order for maximum signal.

---

## 1. Reddit r/MachineLearning (Post as [P] Project)

**Title:** [P] QuantaOptima: The first auditable black-box optimizer built as an MCP server for LLM agents

**Body:**

I built an optimization engine that ships as an MCP server — giving Claude or any LLM agent the ability to optimize parameters, benchmark results, and cryptographically verify every decision.

**The problem:** AI agents are increasingly asked to tune hyperparameters and optimize configurations, but they have no native optimization tools. They brute-force, guess, or punt to you.

**What QuantaOptima does:**

- Quantum-inspired metaheuristic (encode population as quantum-like state → evolve via interference → collapse via entropy-constrained measurement)
- Every step HMAC-SHA256 signed and hash-chained — full audit trail
- Built-in interpretability: entropy trajectories, interference metrics, phase transition detection
- 6 MCP tools: optimize, explain, benchmark (vs scipy), observe, audit, status
- Reliably converges on all 6 standard benchmarks up to 100D

**What it does NOT do:** outperform scipy's Dual Annealing on raw solution quality. DA finds better answers at similar eval budgets on standard benchmarks. We're transparent about that in the README.

**What's actually novel:**
1. First optimizer shipped as an MCP server (AI-agent native)
2. Built-in HMAC-SHA256 audit chain (no other optimizer does this)
3. Interference metric as an interpretability signal (bits of selection advantage from cross-solution correlations)

If your agents need to optimize with auditability and interpretability, this is the tool. If you just need the best answer and don't care about the path, use scipy.

`pip install quantaoptima`

GitHub: https://github.com/jdhart81/quantaoptima

Free tier to try it. Pro ($29/mo) for full power. Happy to discuss the architecture or take feedback.

---

## 2. Reddit r/ClaudeAI

**Title:** Built an MCP server that gives Claude auditable optimization capabilities — free tier available

**Body:**

I built an MCP server that adds black-box optimization to Claude with something no other optimizer has: a cryptographic audit trail and built-in interpretability.

Setup takes 30 seconds:

```
pip install quantaoptima
```

Add to your claude_desktop_config.json:

```json
{
  "mcpServers": {
    "quantaoptima": {
      "command": "quantaoptima-server"
    }
  }
}
```

Then ask Claude: "Optimize the Rastrigin function in 10 dimensions, explain what the quantum operators did, and verify the audit trail."

**6 tools your agent gets:**
- `optimize` — Run optimization on 6 benchmark functions
- `explain` — Human-readable explanation of what happened
- `benchmark` — Head-to-head vs scipy (Pro)
- `observe` — Entropy trajectories, interference metrics, phase transitions (Pro)
- `audit` — Verify HMAC-SHA256 cryptographic chain (Pro)
- `status` — License check

**What makes it different from just calling scipy:** Every optimization step is cryptographically signed and hash-chained. The observe tool exposes how the optimizer explored the landscape — entropy, coherence, interference, phase transitions. It's interpretable optimization, not just a black box that spits out an answer.

**Free tier:** 3 objectives, 10 dims, 100 iters
**Pro ($29/mo):** All 6 objectives, 100 dims, 5000 iters, all tools

GitHub: https://github.com/jdhart81/quantaoptima
Pro: https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04

---

## 3. HuggingFace (Discussion / Space)

**Title:** QuantaOptima: Auditable Quantum-Inspired Optimizer as MCP Server for AI Agents

**Summary:**
QuantaOptima is the first black-box optimizer built specifically for AI agents. It ships as an MCP server with 6 tools (optimize, explain, benchmark, observe, audit, status) and includes features no other optimizer has: HMAC-SHA256 cryptographic audit trails and built-in interpretability telemetry (entropy trajectories, interference metrics, phase transition detection). The quantum-inspired algorithm reliably converges across 6 standard benchmarks up to 100 dimensions. Free tier available, Pro unlocks full capabilities for $29/mo.

**Tags:** optimization, quantum-inspired, mcp, llm-tools, black-box-optimization, ai-safety, interpretability

**Install:** `pip install quantaoptima`

**Links:** [GitHub](https://github.com/jdhart81/quantaoptima) | [Get Pro](https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04)

---

## 4. MCP Community Discord / Anthropic Discord

**Post:**

New MCP server: **quantaoptima** — auditable black-box optimizer for AI agents

`pip install quantaoptima` and add to your claude_desktop_config:

```json
{"mcpServers": {"quantaoptima": {"command": "quantaoptima-server"}}}
```

6 tools: optimize, benchmark (vs scipy), observe (interpretability), explain, audit (crypto chain), status.

**Why this instead of just calling scipy from a script:**
- Every step HMAC-SHA256 signed and hash-chained (auditable)
- Built-in interpretability: entropy, coherence, interference, phase transitions
- MCP-native: your agent can optimize, interpret, and verify without writing any code
- Freemium: free tier to test, Pro ($29/mo) for full power

The `observe` tool is the interesting one — it exposes the optimizer's internal state as structured data. Your agent can understand *how* it explored the landscape, not just the final answer.

GitHub: https://github.com/jdhart81/quantaoptima

---

## 5. X/Twitter Thread

**Tweet 1:**
Built the first black-box optimizer designed for AI agents.

Ships as an MCP server with cryptographic audit trails and full interpretability.

No other optimizer does this.

`pip install quantaoptima`

Thread on what makes it different 🧵

**Tweet 2:**
Problem: AI agents are asked to optimize parameters constantly — hyperparameters, configs, calibration.

But they have zero native optimization tools. They guess or brute-force it.

QuantaOptima gives them 6 optimization tools through MCP. Setup takes 30 seconds.

**Tweet 3:**
What makes it different from scipy:

Every optimization step is HMAC-SHA256 signed and hash-chained. The observe tool exposes entropy trajectories, interference metrics, and phase transitions.

It's interpretable, auditable optimization — not just a number at the end.

**Tweet 4:**
Honest take: scipy's Dual Annealing finds better solutions on standard benchmarks at similar eval budgets.

But it can't talk to your AI agent, can't prove its work, and can't explain how it got there.

Different tools for different problems.

**Tweet 5:**
Free tier: 3 objectives, 10 dims, 100 iters — enough to try it.
Pro ($29/mo): all objectives, 100 dims, all 6 tools including benchmarking and audit.

GitHub: https://github.com/jdhart81/quantaoptima
Pro: https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04

---

## 6. LinkedIn

**Post:**

Sharing QuantaOptima v0.2.0 — the first auditable black-box optimizer built for AI agents.

The problem: AI agents are increasingly responsible for tuning hyperparameters, calibrating models, and optimizing configurations. But they have no native optimization tools — and classical optimizers can't explain their work or prove their decisions.

What QuantaOptima does differently:

→ Ships as an MCP server — any AI agent can call it as a tool through natural language
→ Every optimization step is HMAC-SHA256 signed and hash-chained (tamper-evident audit trail)
→ Built-in interpretability: entropy trajectories, interference metrics, phase transition detection
→ Quantum-inspired algorithm that reliably converges across 6 benchmark functions up to 100 dimensions

Honest positioning: on raw solution quality, scipy's classical methods still win on standard benchmarks. But they can't talk to your AI agent, can't prove their work cryptographically, and can't explain how they explored the landscape. For regulated industries, scientific reproducibility, and agentic workflows — that matters.

The monetization model: MCP server with freemium tiers. Free to try, Pro ($29/mo) for full power. The server itself handles upgrade prompts when agents hit tier limits.

If your team uses AI agents for optimization work, or needs auditable results for compliance, check it out:

GitHub: https://github.com/jdhart81/quantaoptima
Get Pro: https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04

`pip install quantaoptima`

#optimization #AI #MCP #AIAgents #opensource #MachineLearning #SaaS
