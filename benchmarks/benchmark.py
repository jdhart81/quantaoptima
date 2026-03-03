#!/usr/bin/env python3
"""
QuantaOptima Benchmark Suite

Compares QuantaOptima against classical optimization methods:
  - scipy.optimize.differential_evolution (state-of-the-art evolutionary)
  - scipy.optimize.dual_annealing (simulated annealing variant)
  - Random search (baseline)

Test functions (standard CEC-style):
  1. Rastrigin (multimodal, deceptive)
  2. Rosenbrock (unimodal, valley-shaped)
  3. Ackley (multimodal, nearly flat)
  4. Sphere (convex, easy baseline)
  5. Griewank (multimodal, many local optima)
  6. Schwefel (multimodal, deceptive global structure)

Metrics:
  - Best fitness found
  - Function evaluations to reach target
  - Wall-clock time
  - Scaling with dimension d

Usage:
  python benchmark.py              # Run all benchmarks
  python benchmark.py --quick      # Quick smoke test
  python benchmark.py --scaling    # Dimension scaling analysis
"""

import sys
import os
import time
import json
import numpy as np
from typing import Callable, Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quantaoptima.optimizer import QuantaOptimizer, OptimizationResult


# ============================================================
# TEST FUNCTIONS (minimization → we negate for QuantaOptima's maximizer)
# ============================================================

def rastrigin(x: np.ndarray) -> float:
    """Rastrigin: highly multimodal. Global min = 0 at origin."""
    d = len(x)
    return -(10 * d + np.sum(x**2 - 10 * np.cos(2 * np.pi * x)))

def rosenbrock(x: np.ndarray) -> float:
    """Rosenbrock: valley-shaped. Global min = 0 at (1,1,...,1)."""
    return -np.sum(100 * (x[1:] - x[:-1]**2)**2 + (1 - x[:-1])**2)

def ackley(x: np.ndarray) -> float:
    """Ackley: multimodal with flat outer region. Global min = 0 at origin."""
    d = len(x)
    sum1 = np.sum(x**2)
    sum2 = np.sum(np.cos(2 * np.pi * x))
    return -(
        -20 * np.exp(-0.2 * np.sqrt(sum1 / d))
        - np.exp(sum2 / d)
        + 20 + np.e
    )

def sphere(x: np.ndarray) -> float:
    """Sphere: convex baseline. Global min = 0 at origin."""
    return -np.sum(x**2)

def griewank(x: np.ndarray) -> float:
    """Griewank: multimodal. Global min = 0 at origin."""
    d = len(x)
    sum_sq = np.sum(x**2) / 4000
    prod_cos = np.prod(np.cos(x / np.sqrt(np.arange(1, d + 1))))
    return -(sum_sq - prod_cos + 1)

def schwefel(x: np.ndarray) -> float:
    """Schwefel: deceptive multimodal. Global min at ~420.9687 per dim."""
    d = len(x)
    return -(418.9829 * d - np.sum(x * np.sin(np.sqrt(np.abs(x)))))


TEST_FUNCTIONS = {
    "rastrigin": {
        "func": rastrigin,
        "bounds_range": (-5.12, 5.12),
        "known_optimum": 0.0,  # negated → our max is 0
        "difficulty": "hard",
    },
    "rosenbrock": {
        "func": rosenbrock,
        "bounds_range": (-5.0, 10.0),
        "known_optimum": 0.0,
        "difficulty": "medium",
    },
    "ackley": {
        "func": ackley,
        "bounds_range": (-32.768, 32.768),
        "known_optimum": 0.0,
        "difficulty": "hard",
    },
    "sphere": {
        "func": sphere,
        "bounds_range": (-5.12, 5.12),
        "known_optimum": 0.0,
        "difficulty": "easy",
    },
    "griewank": {
        "func": griewank,
        "bounds_range": (-600, 600),
        "known_optimum": 0.0,
        "difficulty": "medium",
    },
    "schwefel": {
        "func": schwefel,
        "bounds_range": (-500, 500),
        "known_optimum": 0.0,
        "difficulty": "hard",
    },
}


# ============================================================
# CLASSICAL BASELINES
# ============================================================

def run_differential_evolution(
    func: Callable, bounds: List[Tuple[float, float]], max_evals: int, seed: int
) -> Dict[str, Any]:
    """scipy.optimize.differential_evolution baseline."""
    from scipy.optimize import differential_evolution

    eval_count = [0]
    best_history = []

    def tracked_func(x):
        val = -func(x)  # scipy minimizes, our func returns negated
        eval_count[0] += 1
        best_history.append(-val)
        return val

    t0 = time.time()
    result = differential_evolution(
        tracked_func, bounds, maxiter=max_evals // 15,
        seed=seed, tol=1e-12, atol=1e-12,
        polish=False,
    )
    elapsed = time.time() - t0

    return {
        "method": "differential_evolution",
        "best_fitness": -result.fun,
        "n_evals": eval_count[0],
        "time_seconds": elapsed,
        "converged": result.success,
    }

def run_dual_annealing(
    func: Callable, bounds: List[Tuple[float, float]], max_evals: int, seed: int
) -> Dict[str, Any]:
    """scipy.optimize.dual_annealing baseline."""
    from scipy.optimize import dual_annealing

    eval_count = [0]

    def tracked_func(x):
        eval_count[0] += 1
        return -func(x)

    t0 = time.time()
    result = dual_annealing(
        tracked_func, bounds, maxiter=max(100, max_evals // 20),
        seed=seed,
    )
    elapsed = time.time() - t0

    return {
        "method": "dual_annealing",
        "best_fitness": -result.fun,
        "n_evals": eval_count[0],
        "time_seconds": elapsed,
        "converged": result.success,
    }

def run_random_search(
    func: Callable, bounds: List[Tuple[float, float]], max_evals: int, seed: int
) -> Dict[str, Any]:
    """Pure random search baseline."""
    rng = np.random.default_rng(seed)
    d = len(bounds)
    best_fitness = -np.inf

    t0 = time.time()
    for _ in range(max_evals):
        x = np.array([rng.uniform(lo, hi) for lo, hi in bounds])
        f = func(x)
        if f > best_fitness:
            best_fitness = f
    elapsed = time.time() - t0

    return {
        "method": "random_search",
        "best_fitness": best_fitness,
        "n_evals": max_evals,
        "time_seconds": elapsed,
        "converged": False,
    }


# ============================================================
# QUANTAOPTIMA RUNNER
# ============================================================

def run_quantaoptima(
    func: Callable, bounds: List[Tuple[float, float]], max_evals: int, seed: int
) -> Dict[str, Any]:
    """Run QuantaOptima optimizer."""
    d = len(bounds)
    pop_size = min(80, max(30, d * 3))
    max_iter = max_evals // pop_size

    optimizer = QuantaOptimizer(
        n_dimensions=d,
        population_size=pop_size,
        temperature=2.0,
        theta=2.0,
        lam=min(0.25, 2.0 / np.sqrt(pop_size)),
        gamma=0.1,
        entropy_target=4.0,
        diversity_threshold=0.01,
        cooling_rate=0.998,
        seed=seed,
    )

    t0 = time.time()
    result = optimizer.optimize(
        objective_function=func,
        bounds=bounds,
        max_iterations=max_iter,
        convergence_patience=30,
        convergence_tol=1e-12,
        verbose=False,
    )
    elapsed = time.time() - t0

    return {
        "method": "quantaoptima",
        "best_fitness": result.best_fitness,
        "n_evals": result.n_function_evals,
        "time_seconds": elapsed,
        "converged": result.converged,
        "n_iterations": result.n_iterations,
        "final_entropy": result.entropy_trajectory[-1] if result.entropy_trajectory else None,
        "final_coherence": result.coherence_trajectory[-1] if result.coherence_trajectory else None,
        "avg_interference": float(np.mean(result.interference_trajectory)) if result.interference_trajectory else 0.0,
        "audit_verified": result.audit_summary.get("verified", False),
    }


# ============================================================
# BENCHMARK ORCHESTRATOR
# ============================================================

@dataclass
class BenchmarkConfig:
    dimensions: List[int]
    max_evals: int
    n_trials: int
    seed_base: int


def run_single_benchmark(
    test_name: str,
    test_config: Dict,
    d: int,
    max_evals: int,
    seed: int,
) -> Dict[str, Dict[str, Any]]:
    """Run all methods on a single test function at dimension d."""
    func = test_config["func"]
    lo, hi = test_config["bounds_range"]
    bounds = [(lo, hi)] * d

    results = {}

    # QuantaOptima
    results["quantaoptima"] = run_quantaoptima(func, bounds, max_evals, seed)

    # Classical baselines
    results["differential_evolution"] = run_differential_evolution(
        func, bounds, max_evals, seed
    )
    results["dual_annealing"] = run_dual_annealing(func, bounds, max_evals, seed)
    results["random_search"] = run_random_search(func, bounds, max_evals, seed)

    return results


def run_full_benchmark(config: BenchmarkConfig) -> Dict[str, Any]:
    """Run the complete benchmark suite."""
    all_results = {}

    for test_name, test_config in TEST_FUNCTIONS.items():
        print(f"\n{'='*60}")
        print(f"  TEST FUNCTION: {test_name.upper()} ({test_config['difficulty']})")
        print(f"{'='*60}")

        all_results[test_name] = {}

        for d in config.dimensions:
            print(f"\n  Dimension d={d}:")
            trial_results = []

            for trial in range(config.n_trials):
                seed = config.seed_base + trial * 1000 + d
                results = run_single_benchmark(
                    test_name, test_config, d, config.max_evals, seed
                )
                trial_results.append(results)

            # Aggregate across trials
            aggregated = {}
            for method in trial_results[0].keys():
                fitnesses = [t[method]["best_fitness"] for t in trial_results]
                evals = [t[method]["n_evals"] for t in trial_results]
                times = [t[method]["time_seconds"] for t in trial_results]

                known_opt = test_config["known_optimum"]
                errors = [abs(f - known_opt) for f in fitnesses]

                aggregated[method] = {
                    "fitness_mean": float(np.mean(fitnesses)),
                    "fitness_std": float(np.std(fitnesses)),
                    "fitness_best": float(np.max(fitnesses)),
                    "error_mean": float(np.mean(errors)),
                    "error_std": float(np.std(errors)),
                    "evals_mean": float(np.mean(evals)),
                    "time_mean": float(np.mean(times)),
                }

                # Print result
                tag = "★" if method == "quantaoptima" else " "
                print(
                    f"    {tag} {method:30s} | "
                    f"error: {np.mean(errors):.2e} ± {np.std(errors):.2e} | "
                    f"evals: {int(np.mean(evals)):6d} | "
                    f"time: {np.mean(times):.3f}s"
                )

            all_results[test_name][f"d={d}"] = aggregated

    return all_results


def run_scaling_analysis(
    dimensions: List[int], max_evals_base: int = 5000, n_trials: int = 3
) -> Dict[str, Any]:
    """Analyze how QuantaOptima scales with dimension vs. classical methods."""
    print(f"\n{'='*60}")
    print(f"  SCALING ANALYSIS")
    print(f"{'='*60}")

    scaling_data = {}

    for test_name in ["rastrigin", "sphere", "rosenbrock"]:
        test_config = TEST_FUNCTIONS[test_name]
        scaling_data[test_name] = {"dimensions": [], "quantaoptima": [], "de": [], "da": []}

        print(f"\n  {test_name.upper()}:")
        print(f"  {'d':>6s} | {'QO evals':>10s} | {'DE evals':>10s} | {'DA evals':>10s} | {'QO err':>12s} | {'DE err':>12s}")
        print(f"  {'-'*80}")

        for d in dimensions:
            max_evals = max_evals_base * max(1, d // 5)
            func = test_config["func"]
            lo, hi = test_config["bounds_range"]
            bounds = [(lo, hi)] * d

            qo_evals, de_evals, da_evals = [], [], []
            qo_errors, de_errors = [], []

            for trial in range(n_trials):
                seed = 42 + trial * 100 + d * 7

                r_qo = run_quantaoptima(func, bounds, max_evals, seed)
                r_de = run_differential_evolution(func, bounds, max_evals, seed)
                r_da = run_dual_annealing(func, bounds, max_evals, seed)

                qo_evals.append(r_qo["n_evals"])
                de_evals.append(r_de["n_evals"])
                da_evals.append(r_da["n_evals"])
                qo_errors.append(abs(r_qo["best_fitness"] - test_config["known_optimum"]))
                de_errors.append(abs(r_de["best_fitness"] - test_config["known_optimum"]))

            scaling_data[test_name]["dimensions"].append(d)
            scaling_data[test_name]["quantaoptima"].append(float(np.mean(qo_evals)))
            scaling_data[test_name]["de"].append(float(np.mean(de_evals)))
            scaling_data[test_name]["da"].append(float(np.mean(da_evals)))

            print(
                f"  {d:6d} | {int(np.mean(qo_evals)):10d} | "
                f"{int(np.mean(de_evals)):10d} | {int(np.mean(da_evals)):10d} | "
                f"{np.mean(qo_errors):12.4e} | {np.mean(de_errors):12.4e}"
            )

    return scaling_data


# ============================================================
# MAIN
# ============================================================

def main():
    quick_mode = "--quick" in sys.argv
    scaling_mode = "--scaling" in sys.argv

    print("╔══════════════════════════════════════════════════════════╗")
    print("║     QuantaOptima-IQ Benchmark Suite v0.1                ║")
    print("║     Quantum-Inspired Optimization with MCP              ║")
    print("║     Inventor: Justin Hart                               ║")
    print("╚══════════════════════════════════════════════════════════╝")

    if scaling_mode:
        dims = [2, 5, 10, 20, 50] if not quick_mode else [2, 5, 10]
        results = run_scaling_analysis(dims, max_evals_base=3000 if quick_mode else 10000)
        output_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "scaling_results.json"
        )
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nScaling results saved to {output_file}")
    else:
        config = BenchmarkConfig(
            dimensions=[5, 10, 20] if not quick_mode else [5],
            max_evals=10000 if not quick_mode else 3000,
            n_trials=5 if not quick_mode else 2,
            seed_base=42,
        )
        results = run_full_benchmark(config)
        output_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "benchmark_results.json"
        )
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_file}")

    print("\nDone.")


if __name__ == "__main__":
    main()
