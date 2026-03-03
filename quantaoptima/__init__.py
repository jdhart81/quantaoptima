"""
QuantaOptima-IQ: Quantum-Inspired Optimization with Entropy-Constrained
Measurement Collapse and Foundation Model Integration.

Patent: US Provisional Application, Filed 5/25/25
Inventor: Justin Hart

Core components:
  - QuantumStateEncoder: Maps classical populations to quantum representations
  - QuantumEvolutionOperators: R(θ), E(λ), S(γ) operators
  - MeasurementCollapsePruner: Entropy-constrained adaptive selection
  - CryptoAuditTrail: Verifiable hash-chain audit
  - QuantaOptimizer: Full optimizer combining all components
"""

from quantaoptima.core import QuantumStateEncoder, QuantumEvolutionOperators
from quantaoptima.mcp_algorithm import MeasurementCollapsePruner
from quantaoptima.audit import CryptoAuditTrail
from quantaoptima.optimizer import QuantaOptimizer

__version__ = "0.1.0"
__author__ = "Justin Hart"

__all__ = [
    "QuantumStateEncoder",
    "QuantumEvolutionOperators",
    "MeasurementCollapsePruner",
    "CryptoAuditTrail",
    "QuantaOptimizer",
]
