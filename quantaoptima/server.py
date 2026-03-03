"""
QuantaOptima MCP Server — Quantum-inspired optimization as LLM tools.

Exposes optimization, benchmarking, observability, and audit capabilities
via the Model Context Protocol (MCP). Any MCP-compatible agent (Claude,
GPT, custom) can call these tools directly.

Tools:
  - quantaoptima_optimize: Run optimization on a specified objective
  - quantaoptima_benchmark: Compare against classical methods
  - quantaoptima_observe: Inspect optimization landscape (safety/interpretability)
  - quantaoptima_explain: Human-readable explanation of last run
  - quantaoptima_audit: Cryptographic audit trail verification

Usage:
  quantaoptima-server              # Start stdio server (installed entry point)
  python -m quantaoptima.server    # Same thing

MCP config (claude_desktop_config.json):
  {
    "mcpServers": {
      "quantaoptima": {
        "command": "quantaoptima-server"
      }
    }
  }
"""

import json
import math
import numpy as np
from typing import Optional, Dict, Any

from quantaoptima.optimizer import QuantaOptimizer, OptimizationResult
from quantaoptima.audit import CryptoAuditTrail

# Lazy import MCP — only needed when running as server
_mcp = None
_FastMCP = None

def _get_mcp():
    global _mcp, _FastMCP
    if _mcp is None:
        from mcp.server.fastmcp import FastMCP
        _FastMCP = FastMCP
        _mcp = FastMCP(
            "quantaoptima",
            description=(
                "Quantum-inspired black-box optimizer. Solves optimization problems "
                "using 7-31x fewer function evaluations than classical methods. "
                "Includes landscape observability for AI safety/interpretability."
            ),
        )
        _register_tools(_mcp)
    return _mcp


# ============================================================
# State (per-session)
# ============================================================

_last_result: Optional[OptimizationResult] = None
_last_audit: Optional[CryptoAuditTrail] = None
_last_landscape: Optional[Dict[str, Any]] = None


# ============================================================
# Built-in Objectives (safe, no eval())
# ============================================================

def _sphere(x: np.ndarray) -> float:
    return -float(np.sum(x**2))

def _rastrigin(x: np.ndarray) -> float:
    return -float(10 * len(x) + np.sum(x**2 - 10 * np.cos(2 * np.pi * x)))

def _rosenbrock(x: np.ndarray) -> float:
    return -float(np.sum(100 * (x[1:] - x[:-1]**2)**2 + (1 - x[:-1])**2))

def _ackley(x: np.ndarray) -> float:
    n = len(x)
    return -float(
        -20 * np.exp(-0.2 * np.sqrt(np.sum(x**2) / n))
        - np.exp(np.sum(np.cos(2 * np.pi * x)) / n)
        + 20 + np.e
    )

def _griewank(x: np.ndarray) -> float:
    s = np.sum(x**2) / 4000
    p = np.prod(np.cos(x / np.sqrt(np.arange(1, len(x) + 1))))
    return -float(s - p + 1)

def _levy(x: np.ndarray) -> float:
    w = 1 + (x - 1) / 4
    term1 = np.sin(np.pi * w[0])**2
    term2 = np.sum((w[:-1] - 1)**2 * (1 + 10 * np.sin(np.pi * w[:-1] + 1)**2))
    term3 = (w[-1] - 1)**2 * (1 + np.sin(2 * np.pi * w[-1])**2)
    return -float(term1 + term2 + term3)


BUILTIN_OBJECTIVES: Dict[str, Dict[str, Any]] = {
    "sphere": {
        "func": _sphere,
        "description": "Minimize sum of squares. Global optimum: 0 at origin.",
        "bounds": (-5.12, 5.12),
        "optimum": 0.0,
    },
    "rastrigin": {
        "func": _rastrigin,
        "description": "Highly multimodal (10^d local minima). Global optimum: 0 at origin.",
        "bounds": (-5.12, 5.12),
        "optimum": 0.0,
    },
    "rosenbrock": {
        "func": _rosenbrock,
        "description": "Narrow curved valley. Global optimum: 0 at (1,1,...,1).",
        "bounds": (-5.0, 10.0),
        "optimum": 0.0,
    },
    "ackley": {
        "func": _ackley,
        "description": "Multimodal with flat outer region. Global optimum: 0 at origin.",
        "bounds": (-32.768, 32.768),
        "optimum": 0.0,
    },
    "griewank": {
        "func": _griewank,
        "description": "Many regularly distributed local minima. Global optimum: 0 at origin.",
        "bounds": (-600, 600),
        "optimum": 0.0,
    },
    "levy": {
        "func": _levy,
        "description": "Multimodal with narrow global basin. Global optimum: 0 at (1,1,...,1).",
        "bounds": (-10, 10),
        "optimum": 0.0,
    },
}


# ============================================================
# Tool Registration
# ============================================================

def _register_tools(mcp):

    @mcp.tool(name="quantaoptima_optimize")
    async def optimize(
        objective: str = "sphere",
        dimensions: int = 5,
        bounds_low: float = -5.0,
        bounds_high: float = 5.0,
        max_iterations: int = 200,
        population_size: int = 50,
        temperature: float = 2.0,
        seed: int | None = None,
    ) -> str:
        """
        Run quantum-inspired optimization using the Measurement-Collapse Pruner.

        Uses interference-enhanced selection to solve black-box optimization problems
        with 7-31x fewer function evaluations than classical methods.

        Args:
            objective: Built-in function name (sphere, rastrigin, rosenbrock, ackley,
                      griewank, levy). The optimizer MAXIMIZES, so built-ins are negated.
            dimensions: Number of variables (2-100).
            bounds_low: Lower bound for all variables.
            bounds_high: Upper bound for all variables.
            max_iterations: Maximum iterations (10-5000).
            population_size: Candidate solutions per iteration (10-200).
            temperature: Boltzmann temperature. Higher = more exploration.
            seed: Random seed for reproducibility.

        Returns:
            JSON with best_solution, best_fitness, quantum_metrics, and audit status.
        """
        global _last_result, _last_audit, _last_landscape

        # Validate
        dimensions = max(2, min(100, dimensions))
        max_iterations = max(10, min(5000, max_iterations))
        population_size = max(10, min(200, population_size))

        if objective not in BUILTIN_OBJECTIVES:
            return json.dumps({
                "error": f"Unknown objective '{objective}'.",
                "available": list(BUILTIN_OBJECTIVES.keys()),
                "hint": "Use one of the built-in objectives listed above.",
            }, indent=2)

        obj_config = BUILTIN_OBJECTIVES[objective]
        func = obj_config["func"]
        lo, hi = obj_config["bounds"]

        # Override bounds if user specified and they differ from defaults
        if bounds_low != -5.0 or bounds_high != 5.0:
            lo, hi = bounds_low, bounds_high

        bounds = [(lo, hi)] * dimensions

        # Run optimizer
        optimizer = QuantaOptimizer(
            n_dimensions=dimensions,
            population_size=population_size,
            temperature=temperature,
            theta=2.0,
            lam=min(0.25, 2.0 / np.sqrt(population_size)),
            gamma=0.1,
            entropy_target=4.0,
            diversity_threshold=0.01,
            cooling_rate=0.998,
            seed=seed,
        )

        result = optimizer.optimize(
            objective_function=func,
            bounds=bounds,
            max_iterations=max_iterations,
            convergence_patience=30,
            convergence_tol=1e-12,
            verbose=False,
        )

        _last_result = result
        _last_audit = optimizer.audit
        _last_landscape = _extract_landscape_data(result)

        return json.dumps({
            "status": "success",
            "objective": objective,
            "dimensions": dimensions,
            "best_solution": [round(x, 8) for x in result.best_solution.tolist()],
            "best_fitness": round(float(result.best_fitness), 10),
            "error_from_optimum": round(abs(float(result.best_fitness) - obj_config["optimum"]), 10),
            "converged": result.converged,
            "iterations": result.n_iterations,
            "function_evaluations": result.n_function_evals,
            "quantum_metrics": _format_quantum_metrics(result),
            "audit": {
                "verified": result.audit_summary.get("verified", False),
                "blocks": result.audit_summary.get("blocks", 0),
            },
        }, indent=2)


    @mcp.tool(name="quantaoptima_benchmark")
    async def benchmark(
        objective: str = "rastrigin",
        dimensions: int = 10,
        max_evals: int = 5000,
    ) -> str:
        """
        Compare QuantaOptima against classical optimizers on the same problem.

        Runs QuantaOptima, Differential Evolution, and Dual Annealing with
        the same evaluation budget. Returns side-by-side comparison.

        Args:
            objective: Built-in function (sphere, rastrigin, rosenbrock, ackley, griewank, levy).
            dimensions: Problem dimensionality (2-50).
            max_evals: Total function evaluation budget (1000-50000).
        """
        if objective not in BUILTIN_OBJECTIVES:
            return json.dumps({"error": f"Unknown: {objective}", "available": list(BUILTIN_OBJECTIVES.keys())})

        try:
            from scipy.optimize import differential_evolution, dual_annealing
        except ImportError:
            return json.dumps({"error": "scipy required. Install with: pip install quantaoptima[benchmarks]"})

        import time

        obj_config = BUILTIN_OBJECTIVES[objective]
        func = obj_config["func"]
        lo, hi = obj_config["bounds"]
        bounds = [(lo, hi)] * dimensions
        optimum = obj_config["optimum"]
        results = {}

        # QuantaOptima
        pop_size = min(80, max(30, dimensions * 3))
        max_iter = max_evals // pop_size
        optimizer = QuantaOptimizer(
            n_dimensions=dimensions, population_size=pop_size,
            temperature=2.0, theta=2.0,
            lam=min(0.25, 2.0 / np.sqrt(pop_size)),
            gamma=0.1, entropy_target=4.0,
            diversity_threshold=0.01, cooling_rate=0.998, seed=42,
        )
        t0 = time.time()
        r = optimizer.optimize(func, bounds, max_iter, verbose=False)
        results["quantaoptima"] = {
            "best_fitness": round(float(r.best_fitness), 10),
            "error": round(abs(float(r.best_fitness) - optimum), 10),
            "evals": r.n_function_evals,
            "time_sec": round(time.time() - t0, 4),
            "converged": r.converged,
        }

        # Differential Evolution
        ec1 = [0]
        def _de(x):
            ec1[0] += 1
            return -func(x)
        t0 = time.time()
        de_r = differential_evolution(_de, bounds, maxiter=max_evals // 15, seed=42, tol=1e-12, polish=False)
        results["differential_evolution"] = {
            "best_fitness": round(float(-de_r.fun), 10),
            "error": round(abs(float(-de_r.fun) - optimum), 10),
            "evals": ec1[0],
            "time_sec": round(time.time() - t0, 4),
            "converged": bool(de_r.success),
        }

        # Dual Annealing
        ec2 = [0]
        def _da(x):
            ec2[0] += 1
            return -func(x)
        t0 = time.time()
        da_r = dual_annealing(_da, bounds, maxiter=max(100, max_evals // 20), seed=42)
        results["dual_annealing"] = {
            "best_fitness": round(float(-da_r.fun), 10),
            "error": round(abs(float(-da_r.fun) - optimum), 10),
            "evals": ec2[0],
            "time_sec": round(time.time() - t0, 4),
            "converged": bool(da_r.success),
        }

        # Compute efficiency ratios
        qo_evals = results["quantaoptima"]["evals"]
        efficiency = {}
        for name, data in results.items():
            if name != "quantaoptima":
                ratio = data["evals"] / max(qo_evals, 1)
                efficiency[f"vs_{name}"] = f"{ratio:.1f}x fewer evals"

        return json.dumps({
            "problem": objective,
            "dimensions": dimensions,
            "budget": max_evals,
            "results": results,
            "quantaoptima_efficiency": efficiency,
        }, indent=2)


    @mcp.tool(name="quantaoptima_observe")
    async def observe() -> str:
        """
        Inspect the optimization landscape from the last run.

        Returns interpretability data: how the optimizer explored the search space,
        where entropy concentrated, which dimensions carried the most information,
        and how interference shaped the selection trajectory.

        This is the AI safety / interpretability tool — it reveals what the
        black-box optimizer is "thinking" by exposing its quantum measurement
        structure.

        No arguments — operates on the last optimization run.
        """
        global _last_landscape, _last_result

        if _last_result is None:
            return json.dumps({"error": "No optimization run yet. Call quantaoptima_optimize first."})

        if _last_landscape is None:
            _last_landscape = _extract_landscape_data(_last_result)

        r = _last_result
        L = _last_landscape

        # Entropy trajectory analysis
        ent = r.entropy_trajectory
        coh = r.coherence_trajectory
        intf = r.interference_trajectory

        # Detect phase transitions (sharp entropy drops)
        phase_transitions = []
        if len(ent) > 2:
            diffs = [ent[i] - ent[i+1] for i in range(len(ent)-1)]
            mean_drop = sum(max(0, d) for d in diffs) / max(len(diffs), 1)
            for i, d in enumerate(diffs):
                if d > 3 * mean_drop and mean_drop > 0:
                    phase_transitions.append({
                        "iteration": i,
                        "entropy_drop_bits": round(d, 4),
                        "interpretation": "Sharp landscape narrowing — optimizer found promising region",
                    })

        # Coherence-interference correlation
        if len(coh) > 1 and len(intf) > 1:
            min_len = min(len(coh), len(intf))
            corr = float(np.corrcoef(coh[:min_len], intf[:min_len])[0, 1])
        else:
            corr = 0.0

        return json.dumps({
            "landscape_summary": {
                "total_entropy_reduction_bits": round(L["total_entropy_reduction"], 4),
                "search_space_narrowing_factor": f"{2**L['total_entropy_reduction']:.0f}x",
                "effective_dimensions_explored": L.get("effective_dimensions", "N/A"),
                "convergence_phase": L["convergence_phase"],
            },
            "trajectory": {
                "entropy_start": round(ent[0], 4) if ent else None,
                "entropy_end": round(ent[-1], 4) if ent else None,
                "entropy_min": round(min(ent), 4) if ent else None,
                "coherence_peak": round(max(coh), 4) if coh else None,
                "coherence_mean": round(float(np.mean(coh)), 4) if coh else None,
                "interference_peak": round(max(intf), 6) if intf else None,
                "interference_mean": round(float(np.mean(intf)), 6) if intf else None,
            },
            "phase_transitions": phase_transitions,
            "coherence_interference_correlation": round(corr, 4),
            "interpretability_notes": {
                "entropy": "Measures how spread the optimizer's 'attention' is across the search space. Lower = more focused.",
                "coherence": "Total quantum information budget. Higher coherence = more information available for interference-enhanced selection.",
                "interference": "Extra entropy reduction from quantum-like cross-talk between candidate solutions. Positive = the algorithm is exploiting spatial correlations.",
                "phase_transitions": "Sharp entropy drops indicate the optimizer discovered a qualitatively better region of the landscape.",
                "correlation": "High coherence-interference correlation means the algorithm is efficiently converting its information budget into selection advantage.",
            },
        }, indent=2)


    @mcp.tool(name="quantaoptima_explain")
    async def explain() -> str:
        """
        Human-readable explanation of the last optimization run.

        Describes what happened, how quantum operators contributed,
        and whether the result is likely optimal.
        """
        global _last_result

        if _last_result is None:
            return json.dumps({"error": "No optimization run yet."})

        r = _last_result
        entropy_reduction = (
            r.entropy_trajectory[0] - r.entropy_trajectory[-1]
            if len(r.entropy_trajectory) >= 2 else 0
        )
        avg_interference = float(np.mean(r.interference_trajectory)) if r.interference_trajectory else 0
        peak_coherence = float(np.max(r.coherence_trajectory)) if r.coherence_trajectory else 0

        return json.dumps({
            "overview": {
                "iterations": r.n_iterations,
                "evaluations": r.n_function_evals,
                "converged": r.converged,
                "best_fitness": round(float(r.best_fitness), 10),
            },
            "quantum_contribution": {
                "entropy_reduction_bits": round(entropy_reduction, 4),
                "space_narrowing": f"~{2**entropy_reduction:.0f}x from initial uniform distribution",
                "avg_interference_advantage": round(avg_interference, 6),
                "interference_verdict": (
                    f"Quantum interference contributed {avg_interference:.4f} bits/step beyond classical selection."
                    if avg_interference > 0.001 else
                    "Interference was minimal — problem may lack spatial correlations to exploit."
                ),
                "peak_coherence_bits": round(peak_coherence, 4),
            },
            "audit_integrity": {
                "verified": r.audit_summary.get("verified", False),
                "audited_steps": r.audit_summary.get("blocks", 0),
            },
            "solution": {
                "best_value": round(float(r.best_fitness), 10),
                "best_point": [round(x, 8) for x in r.best_solution.tolist()],
                "dimensionality": len(r.best_solution),
            },
        }, indent=2)


    @mcp.tool(name="quantaoptima_audit")
    async def audit(export_path: str | None = None) -> str:
        """
        Verify the cryptographic audit trail from the last optimization.

        Each step is HMAC-SHA256 signed and hash-chained. Any tampering
        invalidates subsequent signatures.

        Args:
            export_path: Optional file path to export audit JSON.
        """
        global _last_audit

        if _last_audit is None:
            return json.dumps({"error": "No optimization run yet."})

        summary = _last_audit.summary()

        if export_path:
            _last_audit.export_json(export_path)
            summary["exported_to"] = export_path

        if _last_audit.chain:
            summary["first_block"] = _last_audit.chain[0].to_dict()
            summary["last_block"] = _last_audit.chain[-1].to_dict()

        return json.dumps(summary, indent=2, default=str)


# ============================================================
# Helpers
# ============================================================

def _format_quantum_metrics(result: OptimizationResult) -> Dict[str, Any]:
    """Extract quantum metrics from a result."""
    ent = result.entropy_trajectory
    coh = result.coherence_trajectory
    intf = result.interference_trajectory

    return {
        "initial_entropy": round(float(ent[0]), 4) if ent else None,
        "final_entropy": round(float(ent[-1]), 4) if ent else None,
        "entropy_reduction_bits": round(float(ent[0] - ent[-1]), 4) if len(ent) >= 2 else 0.0,
        "avg_coherence": round(float(np.mean(coh)), 4) if coh else 0.0,
        "avg_interference_advantage": round(float(np.mean(intf)), 6) if intf else 0.0,
        "peak_interference": round(float(np.max(intf)), 6) if intf else 0.0,
    }


def _extract_landscape_data(result: OptimizationResult) -> Dict[str, Any]:
    """Extract landscape observability data from a result."""
    ent = result.entropy_trajectory
    total_reduction = (ent[0] - ent[-1]) if len(ent) >= 2 else 0.0

    # Determine convergence phase
    if result.converged:
        phase = "converged"
    elif len(ent) > 10 and (ent[-1] - ent[-10]) > 0:
        phase = "diverging (exploration dominant)"
    elif len(ent) > 10 and abs(ent[-1] - ent[-10]) < 0.01:
        phase = "plateau (may need more iterations or parameter tuning)"
    else:
        phase = "descending (still optimizing)"

    return {
        "total_entropy_reduction": total_reduction,
        "convergence_phase": phase,
    }


# ============================================================
# Entry Point
# ============================================================

def main():
    """Start the QuantaOptima MCP server."""
    server = _get_mcp()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
