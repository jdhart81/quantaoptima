#!/usr/bin/env python3
"""
QuantaOptima License Key Generator

This is YOUR admin tool. Run it locally to generate license keys for
paying customers. Never commit your signing secret to git.

Usage:
  # Set your signing secret (keep this PRIVATE — never share it)
  export QUANTAOPTIMA_LICENSE_SECRET="your-very-long-random-secret-here"

  # Generate a Pro key for a customer (30 days)
  python generate_license.py --tier pro --email customer@example.com --days 30

  # Generate a Pro annual key
  python generate_license.py --tier pro --email customer@example.com --days 365

  # Generate an Enterprise key (never expires)
  python generate_license.py --tier enterprise --email big-co@corp.com --days 0

  # Validate a key
  python generate_license.py --validate "eyJ0aWVy..."

Setup:
  1. Generate your secret once:
     python -c "import secrets; print(secrets.token_urlsafe(64))"

  2. Save it somewhere safe (password manager, not git):
     export QUANTAOPTIMA_LICENSE_SECRET="<paste-secret>"

  3. Set the SAME secret on your Gumroad webhook handler (see MONETIZATION.md)

IMPORTANT: The default signing key only validates community-tier keys.
           You MUST set QUANTAOPTIMA_LICENSE_SECRET for Pro/Enterprise keys.
"""

import argparse
import os
import sys
import json

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quantaoptima.licensing import (
    generate_license_key,
    validate_license_key,
    TIERS,
    _SIGNING_KEY_ENV,
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate or validate QuantaOptima license keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--tier",
        choices=["community", "pro", "enterprise"],
        default="pro",
        help="License tier (default: pro)",
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Customer email address",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Days until expiry. 0 = never expires. (default: 30)",
    )
    parser.add_argument(
        "--validate",
        type=str,
        metavar="KEY",
        help="Validate an existing license key instead of generating",
    )
    parser.add_argument(
        "--batch",
        type=str,
        metavar="FILE",
        help="Batch generate from a JSON file with [{email, tier, days}, ...]",
    )

    args = parser.parse_args()

    # Check signing key is set for non-community tiers
    signing_key_raw = os.environ.get(_SIGNING_KEY_ENV)
    if not signing_key_raw and args.tier != "community" and not args.validate:
        print(f"ERROR: {_SIGNING_KEY_ENV} environment variable not set.")
        print(f"Pro/Enterprise keys require a signing secret.")
        print(f"")
        print(f"Generate one:  python -c \"import secrets; print(secrets.token_urlsafe(64))\"")
        print(f"Then set it:   export {_SIGNING_KEY_ENV}=\"<your-secret>\"")
        sys.exit(1)

    signing_key = signing_key_raw.encode("utf-8") if signing_key_raw else None

    # --- VALIDATE MODE ---
    if args.validate:
        license = validate_license_key(args.validate, signing_key=signing_key)
        print(json.dumps({
            "valid": license.valid,
            "tier": license.tier,
            "email": license.email,
            "expired": license.is_expired,
            "message": license.message,
            "limits": {
                "max_dimensions": license.max_dimensions,
                "max_iterations": license.max_iterations,
                "objectives": sorted(license.allowed_objectives),
                "tools": sorted(license.allowed_tools),
            },
        }, indent=2))
        return

    # --- BATCH MODE ---
    if args.batch:
        with open(args.batch) as f:
            customers = json.load(f)

        print(f"Generating {len(customers)} license keys...")
        print("-" * 60)
        for c in customers:
            email = c["email"]
            tier = c.get("tier", "pro")
            days = c.get("days", 30)
            key = generate_license_key(tier, email, days, signing_key=signing_key)
            print(f"{email} ({tier}, {days}d): {key}")
        print("-" * 60)
        print(f"Done. {len(customers)} keys generated.")
        return

    # --- SINGLE KEY MODE ---
    if not args.email:
        parser.error("--email is required when generating a key")

    key = generate_license_key(
        tier=args.tier,
        email=args.email,
        duration_days=args.days,
        signing_key=signing_key,
    )

    tier_info = TIERS[args.tier]
    print(f"")
    print(f"QuantaOptima License Key Generated")
    print(f"{'=' * 50}")
    print(f"Tier:    {tier_info['label']}")
    print(f"Email:   {args.email}")
    print(f"Expires: {'Never' if args.days == 0 else f'in {args.days} days'}")
    print(f"")
    print(f"LICENSE KEY:")
    print(f"{key}")
    print(f"")
    print(f"INSTALL INSTRUCTIONS (send to customer):")
    print(f"-" * 50)
    print(f"Option 1 — Environment variable:")
    print(f"  export QUANTAOPTIMA_LICENSE=\"{key}\"")
    print(f"")
    print(f"Option 2 — License file:")
    print(f"  mkdir -p ~/.quantaoptima")
    print(f"  echo \"{key}\" > ~/.quantaoptima/license.key")
    print(f"")
    print(f"Then restart your MCP server / Claude Desktop.")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
