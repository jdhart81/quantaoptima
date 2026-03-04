"""
QuantaOptima Licensing — Zero-infrastructure freemium gating.

License keys are HMAC-SHA256 signed JSON tokens that validate locally.
No license server, no database, no hosting costs. The key IS the proof.

Tiers:
  - community (free): Limited objectives, dims, iterations. No benchmark/observe.
  - pro ($29/mo): Full power. All objectives, 100 dims, 5000 iters, all tools.
  - enterprise (custom): Unlimited. Custom objectives API. White-label.

Key format: base64(json({tier, email, expires, features})) + "." + hmac_signature

INVARIANTS:
  1. Free tier is genuinely useful (sphere/rastrigin/rosenbrock, 10 dims, 100 iters)
  2. Pro features are gated by cryptographic signature — can't be spoofed
  3. Keys are self-validating — zero infrastructure cost
  4. Expired keys fall back to community tier (never brick the user)
  5. License check adds <1ms overhead per tool call
"""

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Set


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

# This is the SIGNING key. In production, keep it secret.
# The generate_license.py CLI uses this to mint keys.
# The server uses it to VERIFY keys. Same key = HMAC.
_SIGNING_KEY_ENV = "QUANTAOPTIMA_LICENSE_SECRET"
_DEFAULT_SIGNING_KEY = b"quantaoptima-community-edition-2025"  # Only signs free keys


def _get_signing_key() -> bytes:
    """Get the license signing key from environment or default."""
    env_key = os.environ.get(_SIGNING_KEY_ENV)
    if env_key:
        return env_key.encode("utf-8")
    return _DEFAULT_SIGNING_KEY


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
) -> str:
    """
    Generate a signed license key.

    Args:
        tier: "community", "pro", or "enterprise"
        email: Licensee email
        duration_days: Days until expiry. 0 = never expires.
        features: Optional extra feature flags
        signing_key: Override signing key (for generate_license.py CLI)

    Returns:
        License key string: base64(payload).hmac_signature
    """
    if tier not in TIERS:
        raise ValueError(f"Unknown tier: {tier}. Must be one of: {list(TIERS.keys())}")

    expires = 0.0 if duration_days == 0 else time.time() + (duration_days * 86400)

    payload = {
        "tier": tier,
        "email": email,
        "expires": expires,
        "features": features or {},
        "issued": time.time(),
        "version": 1,
    }

    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()

    key = signing_key or _get_signing_key()
    signature = hmac.new(key, payload_b64.encode(), hashlib.sha256).hexdigest()

    return f"{payload_b64}.{signature}"


def validate_license_key(key: str, signing_key: Optional[bytes] = None) -> License:
    """
    Validate a license key. Returns License with .valid = True/False.

    Never throws — always returns a License (falls back to community on error).
    """
    try:
        if "." not in key:
            return _community_license("Invalid key format")

        payload_b64, signature = key.rsplit(".", 1)

        # Verify HMAC
        sk = signing_key or _get_signing_key()
        expected = hmac.new(sk, payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return _community_license("Invalid signature")

        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)

        tier = payload.get("tier", "community")
        email = payload.get("email", "unknown")
        expires = payload.get("expires", 0)
        features = payload.get("features", {})

        if tier not in TIERS:
            return _community_license(f"Unknown tier: {tier}")

        license = License(
            tier=tier,
            email=email,
            expires=expires,
            features=features,
            valid=True,
            message=f"Valid {TIERS[tier]['label']} license for {email}",
        )

        if license.is_expired:
            license.message = f"License expired. Falling back to Community tier."
            license.valid = False

        return license

    except Exception as e:
        return _community_license(f"Key validation error: {str(e)}")


def _community_license(message: str = "No license key. Using Community (free) tier.") -> License:
    """Return a default community-tier license."""
    return License(
        tier="community",
        email="community@quantaoptima.dev",
        expires=0,
        features={},
        valid=True,  # Community is always valid
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
