"""Hard evaluation-budget primitives shared by benchmark entry points."""

import math


class BudgetExhausted(RuntimeError):
    """Stop a third-party optimizer before it exceeds the declared budget."""


class EvaluationBudget:
    """Count evaluations and retain the best observed maximization value."""

    def __init__(self, objective, maximum: int):
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
            raise ValueError("evaluation budget must be a positive integer")
        self.objective = objective
        self.maximum = maximum
        self.count = 0
        self.best_fitness = -math.inf

    def minimize(self, x):
        if self.count >= self.maximum:
            raise BudgetExhausted
        fitness = float(self.objective(x))
        self.count += 1
        self.best_fitness = max(self.best_fitness, fitness)
        return -fitness


def quanta_iterations_for_budget(max_evals: int, population_size: int) -> int:
    """Account for initialization plus one full population per iteration."""
    if population_size < 1 or max_evals < population_size * 2:
        raise ValueError("evaluation budget must cover initialization and one iteration")
    return max_evals // population_size - 1


def differential_evolution_plan(max_evals: int, dimensions: int) -> tuple[int, int]:
    """Return scipy popsize multiplier and iterations that cannot exceed budget."""
    if dimensions < 1:
        raise ValueError("dimensions must be positive")
    multiplier = max(1, min(15, max_evals // dimensions))
    population = multiplier * dimensions
    iterations = max(0, max_evals // population - 1)
    return multiplier, iterations
