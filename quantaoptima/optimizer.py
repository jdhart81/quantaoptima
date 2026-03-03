"""
QuantaOptimizer: The full quantum-inspired optimization engine.

Ties together:
  - QuantumStateEncoder (population → quantum state)
  - QuantumEvolutionOperators (R, E, S evolution)
  - MeasurementCollapsePruner (adaptive selection)
  - CryptoAuditTrail (verifiable optimization)

INVARIANTS:
  1. Population size is maintained across iterations (survivors + regenerated)
  2. Best solution is never lost (elitism)
  3. Entropy monotonically decreases on average (convergence)
  4. Every step is cryptographically audited
  5. Optimizer terminates within max_iterations
"""

import numpy as np
from typing import Callable, Tuple, Optional, Dict, Any, List
from dataclasses import dataclass

from quantaoptima.core import QuantumStateEncoder, QuantumEvolutionOperators
from quantaoptima.mcp_algorithm import MeasurementCollapsePruner
from quantaoptima.audit import CryptoAuditTrail


@dataclass
class OptimizationResult:
    """Complete result of an optimization run."""
    best_solution: np.ndarray
    best_fitness: float
    n_iterations: int
    n_function_evals: int
    converged: bool
    entropy_trajectory: List[float]
    fitness_trajectory: List[float]
    diversity_trajectory: List[float]
    coherence_trajectory: List[float]
    interference_trajectory: List[float]
    audit_summary: Dict[str, Any]
    final_population: np.ndarray
    final_fitness: np.ndarray


class QuantaOptimizer:
    """
    Quantum-Inspired Optimization with Measurement-Collapse Pruning.

    Usage:
        optimizer = QuantaOptimizer(n_dimensions=10)
        result = optimizer.optimize(
            objective_function=my_func,
            bounds=[(-5, 5)] * 10,
            max_iterations=500,
        )
        print(f"Best: {result.best_fitness} at {result.best_solution}")
        print(f"Audit: {result.audit_summary}")
    """

    def __init__(
        self,
        n_dimensions: int,
        population_size: int = 50,
        temperature: float = 1.0,
        theta: float = 1.0,
        lam: float = 0.1,
        gamma: float = 0.05,
        entropy_target: float = 2.0,
        diversity_threshold: float = 0.01,
        cooling_rate: float = 0.995,
        seed: Optional[int] = None,
    ):
        """
        Args:
            n_dimensions: Problem dimensionality d.
            population_size: N — number of candidate solutions.
            temperature: T — Boltzmann temperature for encoding.
            theta: θ — rotation operator strength.
            lam: λ — entanglement operator strength. Keep < 1/√N.
            gamma: γ — scrambling noise strength.
            entropy_target: H* — target entropy for MCP collapse.
            diversity_threshold: β — minimum population diversity.
            cooling_rate: Annealing factor for temperature per iteration.
            seed: Random seed for reproducibility.
        """
        self.n_dim = n_dimensions
        self.pop_size = population_size
        self.temperature = temperature
        self.theta = theta
        self.lam = lam
        self.gamma = gamma
        self.entropy_target = entropy_target
        self.diversity_threshold = diversity_threshold
        self.cooling_rate = cooling_rate

        self.rng = np.random.default_rng(seed)
        self.encoder = QuantumStateEncoder(temperature=temperature)
        self.operators = QuantumEvolutionOperators(rng=self.rng)
        self.mcp = MeasurementCollapsePruner(
            entropy_target=entropy_target,
            diversity_threshold=diversity_threshold,
            min_survivors=max(4, population_size // 10),
        )
        self.audit = CryptoAuditTrail()

    def _initialize_population(
        self,
        bounds: List[Tuple[float, float]],
    ) -> np.ndarray:
        """Initialize population uniformly within bounds."""
        N = self.pop_size
        d = self.n_dim
        population = np.zeros((N, d))
        for j in range(d):
            lo, hi = bounds[j]
            population[:, j] = self.rng.uniform(lo, hi, size=N)
        return population

    def _regenerate(
        self,
        survivors: np.ndarray,
        survivor_fitness: np.ndarray,
        bounds: List[Tuple[float, float]],
        iteration: int = 0,
        max_iterations: int = 500,
    ) -> np.ndarray:
        """
        Regenerate population from survivors.

        Three-strategy regeneration inspired by quantum superposition:
          1. Crossover children (exploitation — combine good solutions)
          2. Mutated clones (local exploration — perturb good solutions)
          3. Random immigrants (global exploration — prevent stagnation)

        The mix shifts from exploration → exploitation over iterations.
        """
        N_target = self.pop_size
        N_survivors = len(survivors)
        d = self.n_dim

        if N_survivors >= N_target:
            return survivors[:N_target]

        new_pop = list(survivors)
        bounds_range = np.array([bounds[k][1] - bounds[k][0] for k in range(d)])

        # Adaptive strategy mix: more exploration early, more exploitation late
        progress = iteration / max(max_iterations, 1)
        crossover_frac = 0.3 + 0.3 * progress    # 30% → 60%
        mutation_frac = 0.4 - 0.1 * progress      # 40% → 30%
        # immigrant_frac = 1 - crossover - mutation  # 30% → 10%

        n_needed = N_target - N_survivors
        n_crossover = int(n_needed * crossover_frac)
        n_mutation = int(n_needed * mutation_frac)
        n_immigrant = n_needed - n_crossover - n_mutation

        # Fitness-proportional parent selection
        fit_shifted = survivor_fitness - survivor_fitness.min() + 1e-10
        parent_probs = fit_shifted / fit_shifted.sum()

        # Strategy 1: Crossover children
        for _ in range(n_crossover):
            i, j = self.rng.choice(N_survivors, size=2, p=parent_probs, replace=True)
            # SBX-like crossover (spread factor)
            beta = self.rng.random(d)
            child = beta * survivors[i] + (1 - beta) * survivors[j]
            # Small mutation
            sigma = 0.02 * bounds_range * (1 - progress)
            child += self.rng.normal(0, sigma)
            child = np.clip(child, [b[0] for b in bounds], [b[1] for b in bounds])
            new_pop.append(child)

        # Strategy 2: Mutated clones (Gaussian perturbation of good solutions)
        for _ in range(n_mutation):
            idx = self.rng.choice(N_survivors, p=parent_probs)
            # Adaptive mutation: larger early, smaller late
            sigma = bounds_range * 0.15 * (1 - 0.8 * progress)
            child = survivors[idx] + self.rng.normal(0, sigma)
            child = np.clip(child, [b[0] for b in bounds], [b[1] for b in bounds])
            new_pop.append(child)

        # Strategy 3: Random immigrants (maintain diversity)
        for _ in range(n_immigrant):
            # Partially random: blend random point with best survivor
            random_point = np.array([
                self.rng.uniform(bounds[k][0], bounds[k][1]) for k in range(d)
            ])
            # Bias toward good regions with some probability
            if self.rng.random() < 0.3:
                best_idx = np.argmax(survivor_fitness)
                alpha = self.rng.uniform(0.2, 0.8)
                child = alpha * random_point + (1 - alpha) * survivors[best_idx]
            else:
                child = random_point
            new_pop.append(child)

        return np.array(new_pop[:N_target])

    def _check_convergence(
        self,
        fitness: np.ndarray,
        fitness_history: List[float],
        patience: int = 20,
        tol: float = 1e-8,
    ) -> bool:
        """Check if optimization has converged."""
        if len(fitness_history) < patience:
            return False
        recent = fitness_history[-patience:]
        improvement = abs(recent[-1] - recent[0])
        return improvement < tol

    def optimize(
        self,
        objective_function: Callable[[np.ndarray], float],
        bounds: List[Tuple[float, float]],
        max_iterations: int = 500,
        convergence_patience: int = 30,
        convergence_tol: float = 1e-10,
        verbose: bool = False,
    ) -> OptimizationResult:
        """
        Run the full quantum-inspired optimization.

        Args:
            objective_function: f(x) → float. We MAXIMIZE this.
            bounds: List of (lower, upper) bounds for each dimension.
            max_iterations: Maximum number of iterations.
            convergence_patience: Iterations without improvement → converged.
            convergence_tol: Minimum improvement to not be considered converged.
            verbose: Print progress every 50 iterations.

        Returns:
            OptimizationResult with full trajectory and audit.
        """
        assert len(bounds) == self.n_dim, "Bounds must match n_dimensions"

        # Initialize
        population = self._initialize_population(bounds)
        n_evals = 0

        # Evaluate initial fitness
        fitness = np.array([objective_function(x) for x in population])
        n_evals += len(population)

        # Track best ever
        best_idx = np.argmax(fitness)
        best_solution = population[best_idx].copy()
        best_fitness = fitness[best_idx]

        # Trajectory tracking
        entropy_traj = []
        fitness_traj = [best_fitness]
        diversity_traj = []
        coherence_traj = []
        interference_traj = []

        # Adaptive parameters
        current_temp = self.temperature
        current_entropy_target = self.entropy_target

        converged = False

        for iteration in range(max_iterations):
            # --- Step 1: Quantum State Encoding ---
            self.encoder.temperature = current_temp
            amplitudes = self.encoder.encode(fitness)

            entropy = self.encoder.shannon_entropy(amplitudes)
            entropy_traj.append(entropy)

            # --- Step 2: Quantum Evolution ---
            # Normalize fitness for operators
            f_min, f_max = fitness.min(), fitness.max()
            if f_max - f_min > 1e-15:
                f_norm = (fitness - f_min) / (f_max - f_min)
            else:
                f_norm = np.ones(len(fitness)) * 0.5

            # Track coherence before evolution
            coherence = self.operators.compute_coherence(amplitudes)
            coherence_traj.append(coherence)

            # Evolve
            evolved = self.operators.evolve(
                amplitudes, population, f_norm,
                theta=self.theta, lam=self.lam, gamma=self.gamma,
            )

            # Track interference advantage
            gamma_val = self.operators.compute_interference_advantage(
                amplitudes, population, fitness, self.theta, self.lam
            )
            interference_traj.append(gamma_val)

            # --- Step 3: Measurement-Collapse Pruning ---
            self.mcp.entropy_target = current_entropy_target
            collapse = self.mcp.collapse(population, evolved, fitness)

            diversity_traj.append(collapse.diversity)

            # --- Step 4: Audit ---
            state_before = {
                "entropy": float(collapse.entropy_before),
                "diversity": float(diversity_traj[-1]) if diversity_traj else 0.0,
                "best_fitness": float(best_fitness),
                "population_size": int(len(population)),
                "coherence": float(coherence),
                "interference_advantage": float(gamma_val),
            }

            # --- Step 5: Regenerate Population ---
            survivors = population[collapse.survivor_indices]
            survivor_fitness = fitness[collapse.survivor_indices]

            # Elitism: ensure best-ever solution is in survivors
            if best_fitness > survivor_fitness.max():
                # Replace worst survivor with best-ever
                worst_idx = np.argmin(survivor_fitness)
                survivors[worst_idx] = best_solution.copy()
                survivor_fitness[worst_idx] = best_fitness

            population = self._regenerate(
                survivors, survivor_fitness, bounds, iteration, max_iterations
            )

            # Evaluate new population
            fitness = np.array([objective_function(x) for x in population])
            n_evals += len(population)

            # Update best
            current_best_idx = np.argmax(fitness)
            if fitness[current_best_idx] > best_fitness:
                best_fitness = fitness[current_best_idx]
                best_solution = population[current_best_idx].copy()

            fitness_traj.append(best_fitness)

            # Record audit
            state_after = {
                "entropy": float(collapse.entropy_after),
                "diversity": float(collapse.diversity),
                "best_fitness": float(best_fitness),
                "population_size": int(len(population)),
                "n_survivors": int(len(collapse.survivor_indices)),
                "n_components_used": int(collapse.n_components_used),
            }
            operation = {
                "type": "quantum_evolution_and_mcp",
                "theta": float(self.theta),
                "lambda": float(self.lam),
                "gamma": float(self.gamma),
                "temperature": float(current_temp),
                "entropy_target": float(current_entropy_target),
                "iteration": iteration,
            }
            self.audit.record_step(state_before, state_after, operation)

            # --- Step 6: Adaptive Parameter Update ---
            current_temp *= self.cooling_rate
            current_temp = max(current_temp, 0.01)  # floor

            # Anneal entropy target
            progress = iteration / max_iterations
            current_entropy_target = self.entropy_target * (1 - 0.5 * progress)

            # --- Convergence Check ---
            if self._check_convergence(
                fitness, fitness_traj, convergence_patience, convergence_tol
            ):
                converged = True
                if verbose:
                    print(f"Converged at iteration {iteration}")
                break

            if verbose and iteration % 50 == 0:
                print(
                    f"  Iter {iteration:4d} | Best: {best_fitness:.8f} | "
                    f"H: {entropy:.3f} | C: {coherence:.3f} | "
                    f"Γ: {gamma_val:.4f} | T: {current_temp:.4f}"
                )

        return OptimizationResult(
            best_solution=best_solution,
            best_fitness=best_fitness,
            n_iterations=iteration + 1 if not converged else iteration + 1,
            n_function_evals=n_evals,
            converged=converged,
            entropy_trajectory=entropy_traj,
            fitness_trajectory=fitness_traj,
            diversity_trajectory=diversity_traj,
            coherence_trajectory=coherence_traj,
            interference_trajectory=interference_traj,
            audit_summary=self.audit.summary(),
            final_population=population,
            final_fitness=fitness,
        )
