"""
Core quantum-inspired representations and evolution operators.

INVARIANTS:
  1. Amplitudes are always normalized: sum(|α_i|²) = 1
  2. Unitary operators preserve normalization
  3. Fitness encoding preserves probability ordering at T→0
  4. All operators are deterministic given fixed random seed (reproducibility)
"""

import numpy as np
from typing import Tuple, Optional


class QuantumStateEncoder:
    """
    Encodes a classical population of solutions with fitness values
    into a quantum-like state vector |ψ⟩ = Σ αᵢ|wᵢ⟩.

    The encoding uses Boltzmann weighting:
      βᵢ = exp(f̃ᵢ / T)
      αᵢ = √(βᵢ / Σβⱼ) · exp(iφᵢ)

    where f̃ᵢ are normalized fitness values in [0, 1].
    """

    def __init__(self, temperature: float = 1.0):
        """
        Args:
            temperature: Boltzmann temperature. Lower T → more peaked distribution.
                         T→∞ gives uniform, T→0 gives delta on best solution.
        """
        assert temperature > 0, "Temperature must be positive"
        self.temperature = temperature

    def encode(
        self,
        fitness: np.ndarray,
        phases: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Encode fitness values into complex amplitude vector.

        Args:
            fitness: Real-valued fitness array of shape (N,)
            phases: Optional phase assignments of shape (N,). If None, phases = 0.

        Returns:
            Complex amplitude vector α of shape (N,) with Σ|αᵢ|² = 1.
        """
        N = len(fitness)
        assert N > 0, "Population must be non-empty"

        # Normalize fitness to [0, 1]
        f_min, f_max = fitness.min(), fitness.max()
        if f_max - f_min < 1e-15:
            # All fitness equal → uniform distribution
            f_norm = np.ones(N) * 0.5
        else:
            f_norm = (fitness - f_min) / (f_max - f_min)

        # Boltzmann weights with numerical stability
        log_beta = f_norm / self.temperature
        log_beta -= log_beta.max()  # shift for numerical stability
        beta = np.exp(log_beta)

        # Amplitudes (magnitudes)
        magnitudes = np.sqrt(beta / beta.sum())

        # Phases
        if phases is None:
            phases = np.zeros(N)

        # Complex amplitudes
        amplitudes = magnitudes * np.exp(1j * phases)

        # INVARIANT CHECK: normalization
        norm = np.sum(np.abs(amplitudes) ** 2)
        assert abs(norm - 1.0) < 1e-10, f"Normalization violated: {norm}"

        return amplitudes

    def decode_probabilities(self, amplitudes: np.ndarray) -> np.ndarray:
        """Extract classical probabilities from quantum amplitudes."""
        probs = np.abs(amplitudes) ** 2
        probs /= probs.sum()  # ensure exact normalization
        return probs

    def shannon_entropy(self, amplitudes: np.ndarray) -> float:
        """Compute Shannon entropy H(p) = -Σ pᵢ log pᵢ of measurement probs."""
        probs = self.decode_probabilities(amplitudes)
        # Filter out zeros to avoid log(0)
        probs = probs[probs > 1e-30]
        return -np.sum(probs * np.log2(probs))


class QuantumEvolutionOperators:
    """
    Three quantum-inspired evolution operators:
      R(θ): Rotation — fitness-dependent phase rotation
      E(λ): Entanglement — inter-solution correlation via inner products
      S(γ): Scrambling — controlled random phase noise

    INVARIANTS:
      - R(θ) preserves |αᵢ|² (diagonal unitary)
      - E(λ) modifies |αᵢ|² via interference (non-diagonal)
      - S(γ) preserves |αᵢ|² on average (diagonal random unitary)
      - Combined evolution preserves normalization
    """

    def __init__(self, rng: Optional[np.random.Generator] = None):
        self.rng = rng or np.random.default_rng()

    def rotation(
        self,
        amplitudes: np.ndarray,
        fitness: np.ndarray,
        theta: float,
    ) -> np.ndarray:
        """
        Rotation operator R(θ): αᵢ → αᵢ · exp(iθf̃ᵢ)

        Encodes fitness information into phases. Does NOT change probabilities.
        This is the quantum analog of Grover's phase oracle.

        Args:
            amplitudes: Complex amplitude vector (N,)
            fitness: Normalized fitness values (N,) in [0, 1]
            theta: Rotation strength

        Returns:
            Rotated amplitude vector (N,)
        """
        phase_kicks = np.exp(1j * theta * fitness)
        result = amplitudes * phase_kicks

        # INVARIANT: normalization preserved (diagonal unitary)
        assert abs(np.sum(np.abs(result) ** 2) - 1.0) < 1e-10
        return result

    def entanglement(
        self,
        amplitudes: np.ndarray,
        population: np.ndarray,
        lam: float,
    ) -> np.ndarray:
        """
        Entanglement operator E(λ): creates inter-solution correlations.

        First-order approximation:
          α'ⱼ = αⱼ + iλ Σ_{k≠j} ⟨wⱼ|wₖ⟩ αₖ + O(λ²)

        This is the KEY non-diagonal operator that enables interference.
        The inner products ⟨wⱼ|wₖ⟩ couple nearby solutions.

        Args:
            amplitudes: Complex amplitude vector (N,)
            population: Solution matrix (N, d)
            lam: Entanglement strength. Keep |λ| < 1/√N for perturbative regime.

        Returns:
            Entangled amplitude vector (N,), renormalized.
        """
        N = len(amplitudes)

        # Compute inner product matrix (normalized)
        # Using cosine similarity for scale-invariance
        norms = np.linalg.norm(population, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-15)  # avoid division by zero
        pop_normalized = population / norms
        similarity = pop_normalized @ pop_normalized.T  # (N, N) cosine similarity

        # Zero out diagonal (no self-entanglement)
        np.fill_diagonal(similarity, 0.0)

        # Apply entanglement: α' = α + iλ · S · α
        # This is first-order expansion of exp(iλS)|ψ⟩
        delta = 1j * lam * (similarity @ amplitudes)
        result = amplitudes + delta

        # Renormalize (necessary because we used first-order approx, not exact unitary)
        norm = np.sqrt(np.sum(np.abs(result) ** 2))
        result /= norm

        return result

    def scrambling(
        self,
        amplitudes: np.ndarray,
        gamma: float,
    ) -> np.ndarray:
        """
        Scrambling operator S(γ): αᵢ → αᵢ · exp(iγξᵢ), ξᵢ ~ N(0,1)

        Introduces controlled decoherence for exploration.
        Preserves probabilities (diagonal random unitary).

        Args:
            amplitudes: Complex amplitude vector (N,)
            gamma: Scrambling strength. γ=0 is identity, γ→∞ is full randomization.

        Returns:
            Scrambled amplitude vector (N,)
        """
        N = len(amplitudes)
        xi = self.rng.standard_normal(N)
        phase_noise = np.exp(1j * gamma * xi)
        result = amplitudes * phase_noise

        # INVARIANT: diagonal unitary preserves probabilities
        assert abs(np.sum(np.abs(result) ** 2) - 1.0) < 1e-10
        return result

    def evolve(
        self,
        amplitudes: np.ndarray,
        population: np.ndarray,
        fitness: np.ndarray,
        theta: float,
        lam: float,
        gamma: float,
    ) -> np.ndarray:
        """
        Full evolution step: |ψ(t+1)⟩ = S(γ) E(λ) R(θ) |ψ(t)⟩

        Applied in order: rotation → entanglement → scrambling.

        Returns:
            Evolved amplitude vector (N,), normalized.
        """
        # Step 1: Rotation (encode fitness into phases)
        state = self.rotation(amplitudes, fitness, theta)

        # Step 2: Entanglement (create interference structure)
        state = self.entanglement(state, population, lam)

        # Step 3: Scrambling (controlled exploration noise)
        state = self.scrambling(state, gamma)

        # Final normalization check
        norm = np.sum(np.abs(state) ** 2)
        assert abs(norm - 1.0) < 1e-8, f"Evolution broke normalization: {norm}"

        return state

    def compute_coherence(self, amplitudes: np.ndarray) -> float:
        """
        Compute relative entropy of coherence C(ρ) = S(Δ(ρ)) - S(ρ).
        For pure states: C = H(p) since S(|ψ⟩⟨ψ|) = 0.

        This measures the total quantum information budget available
        for exploitation during measurement.
        """
        probs = np.abs(amplitudes) ** 2
        probs = probs[probs > 1e-30]
        return -np.sum(probs * np.log2(probs))

    def compute_interference_advantage(
        self,
        amplitudes: np.ndarray,
        population: np.ndarray,
        fitness: np.ndarray,
        theta: float,
        lam: float,
    ) -> float:
        """
        Compute the interference advantage Γ(t) from Theorem 1.

        Γ = -2λ Σⱼ (Σ_{k≠j} √(pⱼpₖ) ⟨wⱼ|wₖ⟩ sin(θΔf̃+Δφ)) log pⱼ

        Returns non-negative value when phases are aligned with fitness.
        """
        N = len(amplitudes)
        probs = np.abs(amplitudes) ** 2
        phases = np.angle(amplitudes)

        # Normalized inner products
        norms = np.linalg.norm(population, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-15)
        pop_norm = population / norms
        similarity = pop_norm @ pop_norm.T

        # Normalize fitness
        f_min, f_max = fitness.min(), fitness.max()
        if f_max - f_min < 1e-15:
            f_norm = np.ones(N) * 0.5
        else:
            f_norm = (fitness - f_min) / (f_max - f_min)

        gamma_total = 0.0
        for j in range(N):
            interference_j = 0.0
            for k in range(N):
                if k == j:
                    continue
                weight = np.sqrt(probs[j] * probs[k]) * similarity[j, k]
                phase_diff = theta * (f_norm[k] - f_norm[j]) + phases[k] - phases[j]
                interference_j += weight * np.sin(phase_diff)
            if probs[j] > 1e-30:
                gamma_total += -2 * interference_j * np.log2(probs[j])

        return lam * gamma_total
