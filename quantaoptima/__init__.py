"""
QuantaOptima — Auditable AI Actions.

The first cryptographic audit trail built for AI agent workflows.
Every action is HMAC-SHA256 signed and hash-chained — tamper-evident by design.

Core components:
  - AuditChain: General-purpose cryptographic audit chain for any AI action
  - auditable: Decorator to automatically audit any function call
  - CryptoAuditTrail: Legacy optimizer audit (wraps AuditChain)

Built-in demo (Quantum-Inspired Optimizer):
  - QuantumStateEncoder: Maps classical populations to quantum representations
  - QuantumEvolutionOperators: R(θ), E(λ), S(γ) operators
  - MeasurementCollapsePruner: Entropy-constrained adaptive selection
  - QuantaOptimizer: Full optimizer combining all components

Usage (audit chain):
    from quantaoptima import AuditChain, auditable

    chain = AuditChain(scope="my-agent")
    chain.log("decision", {"options": [1, 2, 3]}, {"chosen": 2, "reason": "lowest cost"})
    assert chain.verify()

Usage (decorator):
    from quantaoptima import AuditChain, auditable

    chain = AuditChain(scope="my-server")

    @auditable(chain, action_type="calculation")
    def compute(data):
        return {"result": sum(data)}

Patent: US Provisional Application, Filed 5/25/25
Inventor: Justin Hart
"""

from quantaoptima.audit import AuditChain, AuditBlock, CryptoAuditTrail, auditable
from quantaoptima.core import QuantumStateEncoder, QuantumEvolutionOperators
from quantaoptima.mcp_algorithm import MeasurementCollapsePruner
from quantaoptima.optimizer import QuantaOptimizer

__version__ = "0.3.0"
__author__ = "Justin Hart"

__all__ = [
    # Core product: Audit Chain
    "AuditChain",
    "AuditBlock",
    "auditable",
    "CryptoAuditTrail",  # Legacy compat
    # Built-in demo: Optimizer
    "QuantumStateEncoder",
    "QuantumEvolutionOperators",
    "MeasurementCollapsePruner",
    "QuantaOptimizer",
]
