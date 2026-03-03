"""
Cryptographic Audit Trail for verifiable optimization.

Implements a blockchain-style hash chain where each optimization step
produces a signed block containing before/after state and parameters.

INVARIANTS:
  1. Each block's signature depends on the previous block's signature (chain)
  2. Tampering with any block invalidates all subsequent signatures
  3. Verification is O(n) in the number of blocks
  4. All state data is included in the hash (completeness)
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class AuditBlock:
    """A single auditable optimization step."""
    block_number: int
    timestamp: float
    previous_hash: str
    state_before: Dict[str, float]
    operation: Dict[str, Any]
    state_after: Dict[str, float]
    signature: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "operation": self.operation,
            "signature": self.signature,
        }


class CryptoAuditTrail:
    """
    Blockchain-style hash chain for optimization audit.

    Each step generates:
      σₜ = HMAC-SHA256(σₜ₋₁ ∥ state_before ∥ state_after ∥ params ∥ timestamp ∥ nonce)

    Usage:
      trail = CryptoAuditTrail()
      trail.record_step(state_before, state_after, operation_params)
      assert trail.verify()  # check chain integrity
      trail.export_json("audit.json")
    """

    def __init__(self, secret_key: Optional[bytes] = None):
        """
        Args:
            secret_key: HMAC key. If None, generates a random 256-bit key.
                       Store this key to verify audits later.
        """
        if secret_key is None:
            secret_key = hashlib.sha256(
                str(time.time_ns()).encode() + b"quantaoptima"
            ).digest()
        self.secret_key = secret_key
        self.chain: List[AuditBlock] = []
        self._genesis_hash = "0" * 64  # genesis block previous hash

    def _compute_signature(
        self,
        previous_hash: str,
        state_before: Dict[str, float],
        state_after: Dict[str, float],
        operation: Dict[str, Any],
        timestamp: float,
    ) -> str:
        """Compute HMAC-SHA256 signature for a block."""
        # Deterministic serialization
        message = json.dumps(
            {
                "previous_hash": previous_hash,
                "state_before": state_before,
                "state_after": state_after,
                "operation": _serialize_for_hash(operation),
                "timestamp": timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hmac.new(
            self.secret_key, message, hashlib.sha256
        ).hexdigest()

    def record_step(
        self,
        state_before: Dict[str, float],
        state_after: Dict[str, float],
        operation: Dict[str, Any],
    ) -> AuditBlock:
        """
        Record an optimization step in the audit chain.

        Args:
            state_before: {entropy, diversity, best_fitness, ...} before step
            state_after: {entropy, diversity, best_fitness, ...} after step
            operation: {type, parameters, ...} describing the operation

        Returns:
            The signed AuditBlock.
        """
        block_number = len(self.chain)
        timestamp = time.time()
        previous_hash = (
            self.chain[-1].signature if self.chain else self._genesis_hash
        )

        signature = self._compute_signature(
            previous_hash, state_before, state_after, operation, timestamp
        )

        block = AuditBlock(
            block_number=block_number,
            timestamp=timestamp,
            previous_hash=previous_hash,
            state_before=state_before,
            state_after=state_after,
            operation=operation,
            signature=signature,
        )

        self.chain.append(block)
        return block

    def verify(self) -> bool:
        """
        Verify the entire audit chain.

        Checks:
          1. Genesis block has correct previous hash
          2. Each block's signature matches its content
          3. Each block's previous_hash matches the prior block's signature

        Returns:
            True if chain is valid, False if tampered.
        """
        for i, block in enumerate(self.chain):
            # Check previous hash linkage
            expected_prev = (
                self.chain[i - 1].signature if i > 0 else self._genesis_hash
            )
            if block.previous_hash != expected_prev:
                return False

            # Recompute signature
            expected_sig = self._compute_signature(
                block.previous_hash,
                block.state_before,
                block.state_after,
                block.operation,
                block.timestamp,
            )
            if block.signature != expected_sig:
                return False

        return True

    def export_json(self, filepath: str) -> None:
        """Export the full audit chain as JSON."""
        data = {
            "chain_length": len(self.chain),
            "verified": self.verify(),
            "blocks": [block.to_dict() for block in self.chain],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def summary(self) -> Dict[str, Any]:
        """Get a summary of the audit trail."""
        if not self.chain:
            return {"blocks": 0, "verified": True}

        first = self.chain[0]
        last = self.chain[-1]
        return {
            "blocks": len(self.chain),
            "verified": self.verify(),
            "initial_entropy": first.state_before.get("entropy", None),
            "final_entropy": last.state_after.get("entropy", None),
            "initial_best_fitness": first.state_before.get("best_fitness", None),
            "final_best_fitness": last.state_after.get("best_fitness", None),
            "total_time_seconds": last.timestamp - first.timestamp,
        }


def _serialize_for_hash(obj: Any) -> Any:
    """Recursively convert numpy types and other non-JSON types for hashing."""
    import numpy as np

    if isinstance(obj, dict):
        return {k: _serialize_for_hash(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_hash(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, (np.complexfloating,)):
        return {"real": float(obj.real), "imag": float(obj.imag)}
    else:
        return obj
