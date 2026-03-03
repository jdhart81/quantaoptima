"""Tests for QuantaOptima core functionality."""

import numpy as np
import pytest
from quantaoptima import QuantaOptimizer, QuantumStateEncoder, QuantumEvolutionOperators, MeasurementCollapsePruner


class TestQuantumStateEncoder:
    def test_normalization_invariant(self):
        """Amplitudes must satisfy Σ|αᵢ|² = 1."""
        encoder = QuantumStateEncoder(temperature=1.0)
        fitness = np.array([1.0, 2.0, 3.0, 0.5, 4.0])
        amps = encoder.encode(fitness)
        norm = np.sum(np.abs(amps) ** 2)
        assert abs(norm - 1.0) < 1e-10

    def test_uniform_at_equal_fitness(self):
        """Equal fitness → uniform distribution."""
        encoder = QuantumStateEncoder(temperature=1.0)
        fitness = np.ones(10) * 5.0
        amps = encoder.encode(fitness)
        probs = np.abs(amps) ** 2
        assert np.allclose(probs, 0.1, atol=1e-10)

    def test_peaked_at_low_temperature(self):
        """Low T → distribution peaked on best."""
        encoder = QuantumStateEncoder(temperature=0.01)
        fitness = np.array([1.0, 5.0, 2.0])
        amps = encoder.encode(fitness)
        probs = np.abs(amps) ** 2
        assert probs[1] > 0.99  # best solution dominates

    def test_entropy_decreases_with_temperature(self):
        """Lower T → lower entropy."""
        fitness = np.random.default_rng(42).random(20)
        enc_high = QuantumStateEncoder(temperature=10.0)
        enc_low = QuantumStateEncoder(temperature=0.1)
        h_high = enc_high.shannon_entropy(enc_high.encode(fitness))
        h_low = enc_low.shannon_entropy(enc_low.encode(fitness))
        assert h_high > h_low


class TestQuantumEvolutionOperators:
    def test_rotation_preserves_probabilities(self):
        """Rotation is diagonal unitary → probabilities unchanged."""
        rng = np.random.default_rng(42)
        ops = QuantumEvolutionOperators(rng=rng)
        amps = np.array([0.5 + 0.5j, 0.5 - 0.5j]) / np.sqrt(2)
        amps /= np.sqrt(np.sum(np.abs(amps)**2))
        fitness = np.array([0.3, 0.7])
        probs_before = np.abs(amps) ** 2
        rotated = ops.rotation(amps, fitness, theta=2.0)
        probs_after = np.abs(rotated) ** 2
        assert np.allclose(probs_before, probs_after, atol=1e-10)

    def test_scrambling_preserves_probabilities(self):
        """Scrambling is diagonal random unitary → probabilities unchanged."""
        rng = np.random.default_rng(42)
        ops = QuantumEvolutionOperators(rng=rng)
        amps = np.array([0.6, 0.8]) * np.exp(1j * np.array([0.1, 0.5]))
        amps /= np.sqrt(np.sum(np.abs(amps)**2))
        probs_before = np.abs(amps) ** 2
        scrambled = ops.scrambling(amps, gamma=0.5)
        probs_after = np.abs(scrambled) ** 2
        assert np.allclose(probs_before, probs_after, atol=1e-10)

    def test_entanglement_changes_probabilities(self):
        """Entanglement is non-diagonal → probabilities change."""
        rng = np.random.default_rng(42)
        ops = QuantumEvolutionOperators(rng=rng)
        N, d = 5, 3
        encoder = QuantumStateEncoder(temperature=1.0)
        fitness = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        amps = encoder.encode(fitness)
        pop = rng.standard_normal((N, d))
        probs_before = np.abs(amps) ** 2
        entangled = ops.entanglement(amps, pop, lam=0.3)
        probs_after = np.abs(entangled) ** 2
        # Should change (unless population is pathological)
        assert not np.allclose(probs_before, probs_after, atol=1e-6)

    def test_full_evolution_preserves_normalization(self):
        """Full R→E→S pipeline preserves normalization."""
        rng = np.random.default_rng(42)
        ops = QuantumEvolutionOperators(rng=rng)
        N, d = 10, 5
        encoder = QuantumStateEncoder(temperature=1.0)
        fitness = rng.random(N)
        amps = encoder.encode(fitness)
        pop = rng.standard_normal((N, d))
        evolved = ops.evolve(amps, pop, fitness, theta=1.0, lam=0.1, gamma=0.05)
        norm = np.sum(np.abs(evolved) ** 2)
        assert abs(norm - 1.0) < 1e-8


class TestMeasurementCollapsePruner:
    def test_survivors_have_valid_probabilities(self):
        """Survivor probabilities must sum to 1."""
        rng = np.random.default_rng(42)
        mcp = MeasurementCollapsePruner(entropy_target=2.0, min_survivors=3)
        N, d = 20, 5
        pop = rng.standard_normal((N, d))
        fitness = rng.random(N)
        encoder = QuantumStateEncoder(temperature=1.0)
        amps = encoder.encode(fitness)
        result = mcp.collapse(pop, amps, fitness)
        assert abs(result.survivor_probs.sum() - 1.0) < 1e-10

    def test_entropy_reduced(self):
        """Post-collapse entropy should be ≤ pre-collapse entropy."""
        rng = np.random.default_rng(42)
        mcp = MeasurementCollapsePruner(entropy_target=2.0, min_survivors=3)
        N, d = 30, 5
        pop = rng.standard_normal((N, d))
        fitness = rng.random(N)
        encoder = QuantumStateEncoder(temperature=2.0)
        amps = encoder.encode(fitness)
        result = mcp.collapse(pop, amps, fitness)
        assert result.entropy_after <= result.entropy_before + 0.01  # small tolerance

    def test_min_survivors_respected(self):
        """Must keep at least min_survivors."""
        rng = np.random.default_rng(42)
        mcp = MeasurementCollapsePruner(entropy_target=0.01, min_survivors=5)
        N, d = 20, 3
        pop = rng.standard_normal((N, d))
        fitness = rng.random(N)
        encoder = QuantumStateEncoder(temperature=0.1)
        amps = encoder.encode(fitness)
        result = mcp.collapse(pop, amps, fitness)
        assert len(result.survivor_indices) >= 5


class TestQuantaOptimizer:
    def test_sphere_optimization(self):
        """Should find near-zero on sphere function."""
        optimizer = QuantaOptimizer(
            n_dimensions=5, population_size=30,
            temperature=2.0, theta=2.0, lam=0.1,
            gamma=0.1, entropy_target=4.0, seed=42,
        )
        result = optimizer.optimize(
            objective_function=lambda x: -np.sum(x**2),
            bounds=[(-5, 5)] * 5,
            max_iterations=100,
            verbose=False,
        )
        # Should get reasonably close to 0
        assert result.best_fitness > -1.0
        assert result.n_function_evals > 0
        assert result.audit_summary["verified"]

    def test_elitism_invariant(self):
        """Best solution should never be lost."""
        optimizer = QuantaOptimizer(
            n_dimensions=3, population_size=20,
            temperature=1.0, seed=42,
        )
        result = optimizer.optimize(
            objective_function=lambda x: -np.sum(x**2),
            bounds=[(-5, 5)] * 3,
            max_iterations=50,
            verbose=False,
        )
        # Fitness trajectory should be monotonically non-decreasing
        for i in range(1, len(result.fitness_trajectory)):
            assert result.fitness_trajectory[i] >= result.fitness_trajectory[i-1] - 1e-10

    def test_audit_chain_integrity(self):
        """Audit trail should verify cleanly."""
        optimizer = QuantaOptimizer(n_dimensions=3, population_size=15, seed=42)
        result = optimizer.optimize(
            objective_function=lambda x: -np.sum(x**2),
            bounds=[(-5, 5)] * 3,
            max_iterations=20,
            verbose=False,
        )
        assert result.audit_summary["verified"] is True
        assert result.audit_summary["blocks"] > 0

    def test_reproducibility(self):
        """Same seed → same result."""
        def run(seed):
            opt = QuantaOptimizer(n_dimensions=5, population_size=20, seed=seed)
            return opt.optimize(
                lambda x: -np.sum(x**2), [(-5, 5)] * 5, 30, verbose=False
            )
        r1 = run(123)
        r2 = run(123)
        assert np.allclose(r1.best_solution, r2.best_solution)
        assert abs(r1.best_fitness - r2.best_fitness) < 1e-10
