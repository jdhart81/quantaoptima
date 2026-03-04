#!/usr/bin/env python3
"""
QuantaOptima Stripe Setup — Creates products, prices, and checkout links.

Run this ONCE to set up your Stripe catalog. It creates:
  - Product: "QuantaOptima Pro"
  - Price: $29/month (recurring)
  - Price: $199/year (recurring)
  - Payment Links for each price (shareable URLs)

Prerequisites:
  pip install stripe
  export STRIPE_SECRET_KEY="sk_live_..."   # or sk_test_ for testing

Usage:
  python stripe_setup.py              # Create products + payment links
  python stripe_setup.py --test       # Use test mode
  python stripe_setup.py --webhook    # Also create webhook endpoint

Output:
  Prints the payment link URLs to embed in your landing page and README.
  Save these — they're your checkout URLs.
"""

import argparse
import json
import os
import sys

try:
    import stripe
except ImportError:
    print("ERROR: stripe package not installed.")
    print("Run: pip install stripe")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Set up QuantaOptima Stripe products")
    parser.add_argument("--test", action="store_true", help="Use Stripe test mode key")
    parser.add_argument("--webhook", type=str, metavar="URL",
                        help="Create webhook endpoint at this URL")
    parser.add_argument("--list", action="store_true",
                        help="List existing products and prices")
    args = parser.parse_args()

    # Get API key
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        print("ERROR: STRIPE_SECRET_KEY environment variable not set.")
        print("")
        print("Get your key from: https://dashboard.stripe.com/apikeys")
        print("  Test mode: export STRIPE_SECRET_KEY=\"sk_test_...\"")
        print("  Live mode: export STRIPE_SECRET_KEY=\"sk_live_...\"")
        sys.exit(1)

    stripe.api_key = key
    mode = "TEST" if "test" in key else "LIVE"
    print(f"Using Stripe in {mode} mode")
    print("=" * 60)

    if args.list:
        _list_products()
        return

    # ============================================================
    # Step 1: Create Product
    # ============================================================
    print("\n[1/4] Creating product...")

    # Check if product already exists
    existing = stripe.Product.list(limit=100)
    product = None
    for p in existing.data:
        if p.name == "QuantaOptima Pro":
            product = p
            print(f"  Product already exists: {product.id}")
            break

    if product is None:
        product = stripe.Product.create(
            name="QuantaOptima Pro",
            description=(
                "Full-power quantum-inspired optimization. "
                "All 6 objectives, 100 dimensions, 5000 iterations, "
                "benchmarking, observability, audit export."
            ),
            metadata={
                "tier": "pro",
                "app": "quantaoptima",
            },
        )
        print(f"  Created product: {product.id}")

    # ============================================================
    # Step 2: Create Prices
    # ============================================================
    print("\n[2/4] Creating prices...")

    # Check existing prices
    existing_prices = stripe.Price.list(product=product.id, limit=100)
    monthly_price = None
    annual_price = None

    for p in existing_prices.data:
        if p.recurring and p.recurring.interval == "month" and p.unit_amount == 2900:
            monthly_price = p
            print(f"  Monthly price already exists: {monthly_price.id}")
        if p.recurring and p.recurring.interval == "year" and p.unit_amount == 19900:
            annual_price = p
            print(f"  Annual price already exists: {annual_price.id}")

    if monthly_price is None:
        monthly_price = stripe.Price.create(
            product=product.id,
            unit_amount=2900,  # $29.00 in cents
            currency="usd",
            recurring={"interval": "month"},
            metadata={"plan": "pro-monthly"},
        )
        print(f"  Created monthly price: {monthly_price.id} ($29/mo)")

    if annual_price is None:
        annual_price = stripe.Price.create(
            product=product.id,
            unit_amount=19900,  # $199.00 in cents
            currency="usd",
            recurring={"interval": "year"},
            metadata={"plan": "pro-annual"},
        )
        print(f"  Created annual price: {annual_price.id} ($199/yr)")

    # ============================================================
    # Step 3: Create Payment Links
    # ============================================================
    print("\n[3/4] Creating payment links...")

    monthly_link = stripe.PaymentLink.create(
        line_items=[{"price": monthly_price.id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {
                "url": "https://justinhart.github.io/quantaoptima/thanks?session_id={CHECKOUT_SESSION_ID}",
            },
        },
        metadata={"plan": "pro-monthly", "tier": "pro"},
    )
    print(f"  Monthly link: {monthly_link.url}")

    annual_link = stripe.PaymentLink.create(
        line_items=[{"price": annual_price.id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {
                "url": "https://justinhart.github.io/quantaoptima/thanks?session_id={CHECKOUT_SESSION_ID}",
            },
        },
        metadata={"plan": "pro-annual", "tier": "pro"},
    )
    print(f"  Annual link:  {annual_link.url}")

    # ============================================================
    # Step 4: Create Webhook Endpoint (optional)
    # ============================================================
    if args.webhook:
        print(f"\n[4/4] Creating webhook endpoint...")
        endpoint = stripe.WebhookEndpoint.create(
            url=args.webhook,
            enabled_events=[
                "checkout.session.completed",
                "customer.subscription.deleted",
                "customer.subscription.updated",
                "invoice.payment_failed",
            ],
            metadata={"app": "quantaoptima"},
        )
        print(f"  Webhook endpoint: {endpoint.id}")
        print(f"  Webhook secret: {endpoint.secret}")
        print(f"  SAVE THIS SECRET: export STRIPE_WEBHOOK_SECRET=\"{endpoint.secret}\"")
    else:
        print(f"\n[4/4] Skipping webhook (use --webhook URL to create one)")

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print(f"\nProduct ID:      {product.id}")
    print(f"Monthly Price:   {monthly_price.id} ($29/mo)")
    print(f"Annual Price:    {annual_price.id} ($199/yr)")
    print(f"\nPAYMENT LINKS (use these in your landing page):")
    print(f"  Monthly: {monthly_link.url}")
    print(f"  Annual:  {annual_link.url}")
    print(f"\nNext steps:")
    print(f"  1. Replace Gumroad URLs in docs/index.html with these payment links")
    print(f"  2. Deploy stripe_webhook.py and register the webhook URL")
    print(f"  3. Test with Stripe's test card: 4242 4242 4242 4242")

    # Save config for other scripts
    config = {
        "product_id": product.id,
        "monthly_price_id": monthly_price.id,
        "annual_price_id": annual_price.id,
        "monthly_link": monthly_link.url,
        "annual_link": annual_link.url,
        "mode": mode.lower(),
    }

    config_path = os.path.join(os.path.dirname(__file__), ".stripe_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\nConfig saved to: {config_path}")
    print("(This file is gitignored — contains your payment link URLs)")


def _list_products():
    """List existing Stripe products and prices."""
    products = stripe.Product.list(limit=100)
    for p in products.data:
        print(f"\nProduct: {p.name} ({p.id})")
        prices = stripe.Price.list(product=p.id, limit=100)
        for pr in prices.data:
            interval = pr.recurring.interval if pr.recurring else "one-time"
            print(f"  Price: ${pr.unit_amount/100:.2f}/{interval} ({pr.id})")


if __name__ == "__main__":
    main()
