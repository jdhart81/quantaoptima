"""Offline Ed25519 licenses. Only the issuer holds the private signing key.

Version 2 licenses deliberately reject legacy shared-secret HMAC tokens.
Clients configure a trusted public PEM file; no signing secret is distributed.
"""

import base64
import math
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Set

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


# ============================================================
# Tier Definitions
# ============================================================

TIERS = {
    "community": {
        "max_dimensions": 10,
        "max_iterations": 100,
        "max_population": 50,
        "objectives": {"sphere", "rastrigin", "rosenbrock"},
        "tools": {"quantaoptima_optimize", "quantaoptima_explain"},
        "custom_objectives": False,
        "audit_export": False,
        "label": "Community (Free)",
    },
    "pro": {
        "max_dimensions": 100,
        "max_iterations": 5000,
        "max_population": 200,
        "objectives": {"sphere", "rastrigin", "rosenbrock", "ackley", "griewank", "levy"},
        "tools": {
            "quantaoptima_optimize", "quantaoptima_benchmark",
            "quantaoptima_observe", "quantaoptima_explain",
            "quantaoptima_audit",
        },
        "custom_objectives": False,
        "audit_export": True,
        "label": "Pro ($29/month)",
    },
    "enterprise": {
        "max_dimensions": 10000,
        "max_iterations": 50000,
        "max_population": 1000,
        "objectives": {"sphere", "rastrigin", "rosenbrock", "ackley", "griewank", "levy"},
        "tools": {
            "quantaoptima_optimize", "quantaoptima_benchmark",
            "quantaoptima_observe", "quantaoptima_explain",
            "quantaoptima_audit",
        },
        "custom_objectives": True,
        "audit_export": True,
        "label": "Enterprise (Custom)",
    },
}


# ============================================================
# License Key Crypto
# ============================================================

_SIGNING_KEY_ENV = "QUANTAOPTIMA_LICENSE_PRIVATE_KEY_FILE"
_PUBLIC_KEY_ENV = "QUANTAOPTIMA_LICENSE_PUBLIC_KEY_FILE"


def load_private_key(pem: Optional[bytes] = None) -> Ed25519PrivateKey:
    if pem is None:
        path = os.environ.get(_SIGNING_KEY_ENV)
        if not path:
            raise ValueError(f"Set {_SIGNING_KEY_ENV} to the issuer's private PEM file")
        pem = Path(path).read_bytes()
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("License signing requires an Ed25519 private key")
    return key


def load_public_key(pem: Optional[bytes] = None) -> Ed25519PublicKey:
    if pem is None:
        path = os.environ.get(_PUBLIC_KEY_ENV)
        source = Path(path) if path else Path(__file__).with_name("license_public_key.pem")
        if not source.exists():
            raise ValueError(f"No trusted issuer key; configure {_PUBLIC_KEY_ENV}")
        pem = source.read_bytes()
    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("License verification requires an Ed25519 public key")
    return key


@dataclass
class License:
    """A validated license."""
    tier: str
    email: str
    expires: float  # Unix timestamp. 0 = never expires
    features: Dict[str, Any]
    valid: bool
    message: str

    @property
    def is_expired(self) -> bool:
        if self.expires == 0:
            return False
        return time.time() > self.expires

    @property
    def limits(self) -> Dict[str, Any]:
        """Get the effective limits for this license."""
        if not self.valid or self.is_expired:
            return TIERS["community"]
        return TIERS.get(self.tier, TIERS["community"])

    @property
    def allowed_tools(self) -> Set[str]:
        return self.limits["tools"]

    @property
    def allowed_objectives(self) -> Set[str]:
        return self.limits["objectives"]

    @property
    def max_dimensions(self) -> int:
        return self.limits["max_dimensions"]

    @property
    def max_iterations(self) -> int:
        return self.limits["max_iterations"]

    @property
    def max_population(self) -> int:
        return self.limits["max_population"]


def generate_license_key(
    tier: str,
    email: str,
    duration_days: int = 30,
    features: Optional[Dict[str, Any]] = None,
    signing_key: Optional[bytes] = None,
    *,
    expires_at: Optional[float] = None,
) -> str:
    """Issue a v2 token using an Ed25519 private PEM (or configured file).

    expires_at is used by billing to anchor access to a paid service period,
    rather than to the time an event happens to be delivered.
    """
    if tier not in TIERS:
        raise ValueError(f"Unknown tier: {tier}")
    if not isinstance(duration_days, int) or duration_days < 0:
        raise ValueError("duration_days must be a nonnegative integer")
    if not isinstance(email, str) or not email.strip():
        raise ValueError("License email is required")
    expires = expires_at if expires_at is not None else (0 if duration_days == 0 else time.time() + duration_days * 86400)
    if isinstance(expires, bool) or not isinstance(expires, (int, float)) or not math.isfinite(expires) or expires < 0:
        raise ValueError("Invalid license expiry")
    payload = {"tier": tier, "email": email, "expires": expires,
               "features": features or {}, "issued": time.time(), "version": 2}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).decode()
    message = f"qo2.{encoded}"
    signature = load_private_key(signing_key).sign(message.encode())
    return message + "." + base64.urlsafe_b64encode(signature).decode()


def validate_license_key(key: str, public_key: Optional[bytes] = None) -> License:
    """Verify against the independently trusted public PEM. Fail to free access."""
    try:
        prefix, encoded, signature = key.split(".")
        if prefix != "qo2":
            raise ValueError("Legacy licenses must be reissued")
        load_public_key(public_key).verify(
            base64.b64decode(signature, altchars=b"-_", validate=True),
            f"{prefix}.{encoded}".encode(),
        )
        payload = json.loads(base64.b64decode(encoded, altchars=b"-_", validate=True))
        tier, email, expires = payload["tier"], payload["email"], payload["expires"]
        if payload.get("version") != 2 or tier not in TIERS:
            raise ValueError("Unsupported license")
        if isinstance(expires, bool) or not isinstance(expires, (int, float)) or not math.isfinite(expires) or expires < 0:
            raise ValueError("Invalid expiry")
        if not isinstance(email, str) or not email or not isinstance(payload.get("features"), dict):
            raise ValueError("Invalid license fields")
        result = License(tier=tier, email=email, expires=expires,
                         features=payload["features"], valid=True,
                         message=f"Valid {TIERS[tier]['label']} license for {email}")
        if result.is_expired:
            return _community_license("License expired; using Community", valid=False)
        return result
    except Exception:
        # Never leak key paths, token contents, or parser details to clients.
        return _community_license("License invalid or issuer key unavailable; using Community. Legacy keys must be reissued.", valid=False)


def _community_license(message: str = "No license key. Using Community (free) tier.", valid: bool = True) -> License:
    """Return a default community-tier license."""
    return License(
        tier="community",
        email="community@quantaoptima.dev",
        expires=0,
        features={},
        valid=valid,
        message=message,
    )


# ============================================================
# License Loading (from file or env)
# ============================================================

_LICENSE_FILE_LOCATIONS = [
    Path.home() / ".quantaoptima" / "license.key",
    Path.home() / ".config" / "quantaoptima" / "license.key",
    Path("quantaoptima.key"),
]

_cached_license: Optional[License] = None


def load_license() -> License:
    """
    Load license from (in priority order):
      1. QUANTAOPTIMA_LICENSE env var
      2. ~/.quantaoptima/license.key file
      3. ~/.config/quantaoptima/license.key file
      4. ./quantaoptima.key file
      5. Fall back to community tier

    Caches result for session lifetime.
    """
    global _cached_license
    if _cached_license is not None:
        return _cached_license

    # Try env var first
    env_key = os.environ.get("QUANTAOPTIMA_LICENSE")
    if env_key:
        _cached_license = validate_license_key(env_key.strip())
        return _cached_license

    # Try file locations
    for path in _LICENSE_FILE_LOCATIONS:
        try:
            if path.exists():
                key = path.read_text().strip()
                if key:
                    _cached_license = validate_license_key(key)
                    return _cached_license
        except (OSError, PermissionError):
            continue

    # Default to community
    _cached_license = _community_license()
    return _cached_license


def clear_license_cache():
    """Clear the cached license (for testing or key rotation)."""
    global _cached_license
    _cached_license = None


# ============================================================
# Gate Decorators (for use in server.py)
# ============================================================

def check_tool_access(tool_name: str) -> Optional[str]:
    """
    Check if the current license allows access to a tool.

    Returns None if allowed, or an upgrade message string if blocked.
    """
    license = load_license()
    if tool_name in license.allowed_tools:
        return None

    tier = license.limits["label"]
    return json.dumps({
        "error": "upgrade_required",
        "tool": tool_name,
        "current_tier": tier,
        "message": (
            f"The '{tool_name}' tool requires a Pro license. "
            f"You're on the {tier} tier."
        ),
        "upgrade_url": "https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04",
        "hint": (
            "Set QUANTAOPTIMA_LICENSE env var or save your key to "
            "~/.quantaoptima/license.key"
        ),
    }, indent=2)


def check_limits(
    dimensions: int,
    iterations: int,
    population_size: int,
    objective: str,
) -> Optional[str]:
    """
    Check if parameters are within the current license limits.

    Returns None if within limits, or a limit message with what to adjust.
    """
    license = load_license()
    limits = license.limits
    violations = []

    if dimensions > limits["max_dimensions"]:
        violations.append(
            f"dimensions={dimensions} exceeds {limits['label']} limit of {limits['max_dimensions']}"
        )

    if iterations > limits["max_iterations"]:
        violations.append(
            f"max_iterations={iterations} exceeds {limits['label']} limit of {limits['max_iterations']}"
        )

    if population_size > limits["max_population"]:
        violations.append(
            f"population_size={population_size} exceeds {limits['label']} limit of {limits['max_population']}"
        )

    if objective not in limits["objectives"]:
        violations.append(
            f"objective='{objective}' not available in {limits['label']}. "
            f"Available: {sorted(limits['objectives'])}"
        )

    if not violations:
        return None

    return json.dumps({
        "error": "limit_exceeded",
        "current_tier": limits["label"],
        "violations": violations,
        "upgrade_url": "https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04",
        "hint": "Upgrade to Pro for higher limits and all objectives.",
    }, indent=2)
