"""
Measurement-Collapse Pruner (MCP) Algorithm.

The core innovation: entropy-constrained selection in an adaptively
chosen measurement basis (PCA of population covariance).

INVARIANTS:
  1. Post-collapse entropy H(q) ≤ H* (target entropy)
  2. Diversity D(survivors) ≥ β (diversity threshold)
  3. Born rule probabilities: qₖ = |⟨φₖ|ψ⟩|²
  4. Probability conservation: Σqₖ = 1
"""

import numpy as np
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class CollapseResult:
    """Result of a measurement-collapse step."""
    survivor_indices: np.ndarray   # indices into original population
    survivor_probs: np.ndarray     # probabilities of survivors
    measurement_basis: np.ndarray  # PCA basis vectors used
    entropy_before: float          # H(p) before collapse
    entropy_after: float           # H(q) after collapse
    diversity: float               # population diversity metric
    born_probs: np.ndarray         # full Born rule probability vector
    n_components_used: int         # how many PCA components selected


class MeasurementCollapsePruner:
    """
    Implements entropy-constrained measurement collapse:

    1. Compute adaptive measurement basis via PCA of population covariance
    2. Calculate Born rule probabilities in that basis
    3. Iteratively collapse to meet entropy target while preserving diversity
    4. Return survivor set with audit data

    The key insight: PCA basis approximates the eigenbasis of the population
    mixed state ρ_pop, giving minimum-entropy measurement (Wehrl, 1978).
    """

    def __init__(
        self,
        entropy_target: float = 1.0,
        diversity_threshold: float = 0.1,
        min_survivors: int = 4,
    ):
        """
        Args:
            entropy_target: H* — target entropy after collapse.
                           Lower = more aggressive selection.
            diversity_threshold: β — minimum population diversity.
            min_survivors: Minimum number of survivors to maintain.
        """
        self.entropy_target = entropy_target
        self.diversity_threshold = diversity_threshold
        self.min_survivors = min_survivors

    def _compute_measurement_basis(
        self,
        population: np.ndarray,
        probs: np.ndarray,
    ) -> np.ndarray:
        """
        Compute adaptive measurement basis via weighted PCA.

        The eigenvectors of the probability-weighted covariance matrix
        approximate the eigenbasis of ρ_pop, which gives minimum-entropy
        measurement by the measurement entropy inequality.

        Args:
            population: Solution matrix (N, d)
            probs: Probability weights (N,)

        Returns:
            Measurement basis vectors (d, d) — columns are basis vectors,
            ordered by decreasing variance explained.
        """
        N, d = population.shape

        # Weighted mean
        mean = np.average(population, weights=probs, axis=0)

        # Weighted covariance
        centered = population - mean
        # Σ = Σᵢ pᵢ (wᵢ - μ)(wᵢ - μ)ᵀ
        cov = (centered * probs[:, np.newaxis]).T @ centered

        # Regularize for numerical stability
        cov += 1e-10 * np.eye(d)

        # Eigendecomposition (returns ascending order)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)

        # Reverse to get descending order (most variance first)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvectors = eigenvectors[:, idx]

        return eigenvectors

    def _born_rule_probabilities(
        self,
        population: np.ndarray,
        amplitudes: np.ndarray,
        basis: np.ndarray,
    ) -> np.ndarray:
        """
        Compute Born rule probabilities in the measurement basis.

        qₖ = |⟨φₖ|ψ⟩|²

        where |ψ⟩ = Σᵢ αᵢ|wᵢ⟩ and {|φₖ⟩} is the PCA basis.

        In practice: project solutions onto PCA components, weight by
        amplitudes, compute probability of each component.

        Args:
            population: Solution matrix (N, d)
            amplitudes: Complex amplitudes (N,)
            basis: Measurement basis (d, d)

        Returns:
            Born rule probabilities (d,) — probability of each basis state.
        """
        N, d = population.shape

        # Project each solution onto the measurement basis
        # projections[i, k] = ⟨φₖ|wᵢ⟩ = wᵢ · φₖ
        projections = population @ basis  # (N, d)

        # Amplitude-weighted projection onto each basis state
        # ⟨φₖ|ψ⟩ = Σᵢ αᵢ ⟨φₖ|wᵢ⟩
        psi_in_basis = amplitudes @ projections  # (d,) complex

        # Born rule: qₖ = |⟨φₖ|ψ⟩|²
        born_probs = np.abs(psi_in_basis) ** 2

        # Normalize (projections may not be perfectly orthonormal on discrete pop)
        total = born_probs.sum()
        if total > 1e-15:
            born_probs /= total
        else:
            born_probs = np.ones(d) / d

        return born_probs

    def _compute_diversity(self, population: np.ndarray) -> float:
        """
        Compute population diversity as mean pairwise distance.
        D(W) = (1/N²) Σᵢⱼ ‖wᵢ - wⱼ‖²
        """
        N = len(population)
        if N <= 1:
            return 0.0
        # Efficient computation using identity: Σᵢⱼ‖xᵢ-xⱼ‖² = 2N·Σᵢ‖xᵢ‖² - 2‖Σᵢxᵢ‖²
        sq_norms = np.sum(population ** 2, axis=1)
        sum_vec = population.sum(axis=0)
        diversity = (2 * N * sq_norms.sum() - 2 * np.dot(sum_vec, sum_vec)) / (N * N)
        return diversity

    def _shannon_entropy(self, probs: np.ndarray) -> float:
        """H(p) = -Σ pᵢ log₂ pᵢ"""
        p = probs[probs > 1e-30]
        return -np.sum(p * np.log2(p))

    def collapse(
        self,
        population: np.ndarray,
        amplitudes: np.ndarray,
        fitness: np.ndarray,
    ) -> CollapseResult:
        """
        Perform entropy-constrained measurement collapse.

        Algorithm:
          1. Compute PCA measurement basis
          2. Compute Born rule probabilities
          3. Rank solutions by alignment with top principal components
          4. Select survivors to meet entropy target
          5. Verify diversity constraint

        Args:
            population: Solution matrix (N, d)
            amplitudes: Complex amplitudes (N,)
            fitness: Fitness values (N,)

        Returns:
            CollapseResult with survivor indices and audit data.
        """
        N, d = population.shape
        probs = np.abs(amplitudes) ** 2
        probs /= probs.sum()

        entropy_before = self._shannon_entropy(probs)

        # Step 1: Compute adaptive measurement basis
        basis = self._compute_measurement_basis(population, probs)

        # Step 2: Born rule probabilities
        born_probs = self._born_rule_probabilities(population, amplitudes, basis)

        # Step 3: Score each solution by its alignment with the
        # top Born-probability components
        # Each solution gets a score = weighted sum of its projection
        # onto high-probability basis vectors
        projections = population @ basis  # (N, d)
        projection_magnitudes = np.abs(projections) ** 2  # (N, d)

        # Weight projections by Born probabilities
        solution_scores = projection_magnitudes @ born_probs  # (N,)

        # Combine with fitness: composite score
        # Normalize both to [0,1] and combine
        f_min, f_max = fitness.min(), fitness.max()
        if f_max - f_min > 1e-15:
            f_norm = (fitness - f_min) / (f_max - f_min)
        else:
            f_norm = np.ones(N) * 0.5

        s_min, s_max = solution_scores.min(), solution_scores.max()
        if s_max - s_min > 1e-15:
            s_norm = (solution_scores - s_min) / (s_max - s_min)
        else:
            s_norm = np.ones(N) * 0.5

        # Composite: quantum score + fitness (equal weight)
        composite = 0.5 * s_norm + 0.5 * f_norm

        # Step 4: Entropy-constrained collapse
        # Sort by composite score (descending)
        ranked = np.argsort(composite)[::-1]

        # Determine how many survivors to keep
        # Start with all, remove one at a time until entropy target met
        n_survivors = N
        for k in range(self.min_survivors, N + 1):
            survivor_idx = ranked[:k]
            survivor_probs = probs[survivor_idx]
            survivor_probs /= survivor_probs.sum()
            h = self._shannon_entropy(survivor_probs)
            if h <= self.entropy_target:
                n_survivors = k
                break
        else:
            # Could not reach target — use minimum survivors
            n_survivors = self.min_survivors

        survivor_indices = ranked[:n_survivors]

        # Step 5: Diversity check
        survivors_pop = population[survivor_indices]
        diversity = self._compute_diversity(survivors_pop)

        if diversity < self.diversity_threshold and n_survivors < N:
            # Add diverse solutions to maintain exploration
            remaining = np.setdiff1d(np.arange(N), survivor_indices)
            if len(remaining) > 0:
                # Find the solution most distant from current survivors
                mean_survivor = survivors_pop.mean(axis=0)
                dists = np.linalg.norm(population[remaining] - mean_survivor, axis=1)
                diverse_idx = remaining[np.argsort(dists)[::-1]]

                # Add diverse solutions until threshold met or pool exhausted
                for idx in diverse_idx:
                    test_pop = np.vstack([survivors_pop, population[idx:idx+1]])
                    test_div = self._compute_diversity(test_pop)
                    survivor_indices = np.append(survivor_indices, idx)
                    survivors_pop = test_pop
                    diversity = test_div
                    if diversity >= self.diversity_threshold:
                        break

        # Final survivor probabilities
        survivor_probs = probs[survivor_indices]
        survivor_probs /= survivor_probs.sum()
        entropy_after = self._shannon_entropy(survivor_probs)

        # Count effective PCA components
        cumvar = np.cumsum(born_probs)
        n_components = int(np.searchsorted(cumvar, 0.95)) + 1

        return CollapseResult(
            survivor_indices=survivor_indices,
            survivor_probs=survivor_probs,
            measurement_basis=basis,
            entropy_before=entropy_before,
            entropy_after=entropy_after,
            diversity=diversity,
            born_probs=born_probs,
            n_components_used=min(n_components, d),
        )
