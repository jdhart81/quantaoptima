#!/usr/bin/env python3
"""
QuantaOptima Stripe Webhook — License key delivery + subscription management.

Handles:
  - checkout.session.completed → Generate Pro key, email to customer
  - customer.subscription.deleted → (Log churn, optional: notify)
  - customer.subscription.updated → (Handle plan changes)
  - invoice.payment_failed → (Alert, grace period logic)

Deploys FREE on:
  - Cloudflare Workers (100K free requests/day)
  - Vercel Serverless (100K free invocations/month)
  - Railway.app (free tier available)
  - Or run locally with: python stripe_webhook.py

Setup:
  1. Run stripe_setup.py first to create products + payment links
  2. Set environment variables:
     - STRIPE_SECRET_KEY      (from Stripe dashboard)
     - STRIPE_WEBHOOK_SECRET  (from stripe_setup.py --webhook or Stripe dashboard)
     - QUANTAOPTIMA_LICENSE_SECRET (your signing key for license keys)
     - SMTP_USER / SMTP_PASS  (Gmail app password for email delivery)
  3. Deploy and register webhook URL in Stripe dashboard

Flow:
  Customer clicks Payment Link → Stripe Checkout → Payment succeeds →
  Stripe POSTs to this webhook → Generate signed license key →
  Email key to customer → Customer sets env var → Pro unlocked
"""

import hashlib
import hmac
import json
import os
import smtplib
import sys
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import stripe
except ImportError:
    print("ERROR: stripe not installed. Run: pip install stripe")
    sys.exit(1)

from quantaoptima.licensing import generate_license_key


# ============================================================
# Configuration
# ============================================================

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
LICENSE_SECRET = os.environ.get("QUANTAOPTIMA_LICENSE_SECRET", "")

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "license@quantaoptima.dev")

# Map Stripe price intervals to license durations
PLAN_DURATION = {
    "month": 35,    # 30 days + 5 grace
    "year": 370,    # 365 days + 5 grace
}


# ============================================================
# Event Handlers
# ============================================================

def handle_checkout_completed(event):
    """
    A customer just paid. Generate a license key and email it.
    """
    session = event["data"]["object"]
    customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email", "")

    if not customer_email:
        print(f"[WARN] No email in checkout session {session['id']}")
        return {"status": "error", "message": "No customer email"}

    # Determine plan duration from subscription
    subscription_id = session.get("subscription")
    duration_days = 35  # Default to monthly

    if subscription_id:
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            if sub.items.data:
                interval = sub.items.data[0].price.recurring.interval
                duration_days = PLAN_DURATION.get(interval, 35)
        except Exception as e:
            print(f"[WARN] Could not fetch subscription: {e}")

    # Generate license key
    if not LICENSE_SECRET:
        print("[ERR] QUANTAOPTIMA_LICENSE_SECRET not set — cannot generate keys")
        return {"status": "error", "message": "License secret not configured"}

    signing_key = LICENSE_SECRET.encode("utf-8")
    license_key = generate_license_key(
        tier="pro",
        email=customer_email,
        duration_days=duration_days,
        features={
            "stripe_customer": session.get("customer", ""),
            "stripe_subscription": subscription_id or "",
            "checkout_session": session["id"],
        },
        signing_key=signing_key,
    )

    # Email the key
    plan_label = "Annual" if duration_days > 100 else "Monthly"
    email_sent = _send_license_email(customer_email, license_key, plan_label, duration_days)

    print(f"[OK] License generated for {customer_email} ({plan_label}, {duration_days}d)")
    return {
        "status": "success",
        "email": customer_email,
        "plan": plan_label,
        "key_generated": True,
        "email_sent": email_sent,
    }


def handle_subscription_deleted(event):
    """Customer cancelled. Log it."""
    sub = event["data"]["object"]
    customer_id = sub.get("customer", "unknown")
    print(f"[CHURN] Subscription cancelled: customer={customer_id}")
    # Their key will naturally expire (35 or 370 day TTL)
    # No need to revoke — the crypto expiry handles it
    return {"status": "logged", "event": "subscription_deleted"}


def handle_subscription_updated(event):
    """Plan change (upgrade/downgrade). Generate new key if needed."""
    sub = event["data"]["object"]
    customer_id = sub.get("customer", "unknown")
    status = sub.get("status", "unknown")
    print(f"[UPDATE] Subscription updated: customer={customer_id}, status={status}")
    return {"status": "logged", "event": "subscription_updated"}


def handle_payment_failed(event):
    """Payment failed. Log and optionally alert."""
    invoice = event["data"]["object"]
    customer_email = invoice.get("customer_email", "unknown")
    print(f"[ALERT] Payment failed for {customer_email}")
    # Stripe handles retries automatically via dunning
    # The license key's built-in expiry handles access revocation
    return {"status": "logged", "event": "payment_failed"}


EVENT_HANDLERS = {
    "checkout.session.completed": handle_checkout_completed,
    "customer.subscription.deleted": handle_subscription_deleted,
    "customer.subscription.updated": handle_subscription_updated,
    "invoice.payment_failed": handle_payment_failed,
}


# ============================================================
# Email Delivery
# ============================================================

def _send_license_email(to_email: str, license_key: str, plan_label: str, days: int) -> bool:
    """Send the license key to the customer via email."""
    if not SMTP_USER or not SMTP_PASS:
        print(f"[WARN] SMTP not configured. Key for {to_email}:")
        print(f"  {license_key}")
        return False

    expiry = f"{days} days" if days > 0 else "never (lifetime)"

    subject = f"Your QuantaOptima Pro License Key"

    html_body = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0a0a; color: #e0e0e0; padding: 40px; border-radius: 12px;">
        <h1 style="color: #ff6b00; margin-bottom: 8px;">QuantaOptima</h1>
        <p style="color: #888; margin-top: 0;">Quantum-inspired optimization for AI</p>

        <hr style="border: 1px solid #333; margin: 24px 0;">

        <h2 style="color: #fff;">Your Pro License ({plan_label})</h2>
        <p>Thank you for subscribing! Here's your license key:</p>

        <div style="background: #1a1a2e; border: 1px solid #ff6b00; border-radius: 8px; padding: 16px; margin: 24px 0; word-break: break-all; font-family: monospace; font-size: 12px; color: #ff6b00;">
            {license_key}
        </div>

        <h3 style="color: #fff;">Quick Setup (pick one):</h3>

        <p><strong>Option 1 — Environment variable:</strong></p>
        <pre style="background: #1a1a2e; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; color: #0ff;">export QUANTAOPTIMA_LICENSE="{license_key}"</pre>

        <p><strong>Option 2 — License file:</strong></p>
        <pre style="background: #1a1a2e; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; color: #0ff;">mkdir -p ~/.quantaoptima
echo "{license_key}" > ~/.quantaoptima/license.key</pre>

        <p><strong>Option 3 — MCP config (Claude Desktop):</strong></p>
        <pre style="background: #1a1a2e; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; color: #0ff;">{{
  "mcpServers": {{
    "quantaoptima": {{
      "command": "quantaoptima-server",
      "env": {{
        "QUANTAOPTIMA_LICENSE": "{license_key}"
      }}
    }}
  }}
}}</pre>

        <p>Then restart your MCP server or Claude Desktop. Call <code>quantaoptima_status</code> to verify.</p>

        <hr style="border: 1px solid #333; margin: 24px 0;">

        <h3 style="color: #fff;">What's Unlocked:</h3>
        <ul style="color: #ccc; line-height: 2;">
            <li>All 6 objectives (Sphere, Rastrigin, Rosenbrock, Ackley, Griewank, Levy)</li>
            <li>Up to 100 dimensions</li>
            <li>Up to 5,000 iterations</li>
            <li>Benchmark comparisons vs classical methods</li>
            <li>Full observability / AI safety telemetry</li>
            <li>Cryptographic audit export</li>
        </ul>

        <hr style="border: 1px solid #333; margin: 24px 0;">

        <p style="color: #888; font-size: 13px;">
            Plan: Pro {plan_label}<br>
            Expires: {expiry}<br>
            Manage subscription: <a href="https://billing.stripe.com/p/login/test" style="color: #818cf8;">Billing Portal</a><br>
            Support: hartjustin6@gmail.com
        </p>
    </div>
    """

    text_body = f"""
QuantaOptima Pro License Key ({plan_label})
=============================================

Thank you for subscribing!

YOUR LICENSE KEY:
{license_key}

SETUP (pick one):

Option 1 — Environment variable:
  export QUANTAOPTIMA_LICENSE="{license_key}"

Option 2 — License file:
  mkdir -p ~/.quantaoptima
  echo "{license_key}" > ~/.quantaoptima/license.key

Then restart your MCP server or Claude Desktop.

WHAT'S UNLOCKED:
- All 6 objectives
- Up to 100 dimensions
- Up to 5,000 iterations
- Benchmark comparisons
- Full observability / AI safety
- Audit export

Plan: Pro {plan_label}
Expires: {expiry}
Support: hartjustin6@gmail.com
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"[OK] License email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[ERR] Failed to send email to {to_email}: {e}")
        return False


# ============================================================
# HTTP Server
# ============================================================

class StripeWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler that verifies Stripe signatures and dispatches events."""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length)

        # Verify Stripe signature
        sig_header = self.headers.get("Stripe-Signature", "")

        if WEBHOOK_SECRET:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, WEBHOOK_SECRET
                )
            except stripe.error.SignatureVerificationError:
                print("[ERR] Invalid Stripe signature — rejecting")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid signature"}')
                return
            except Exception as e:
                print(f"[ERR] Webhook verification failed: {e}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Verification failed"}')
                return
        else:
            # No webhook secret — parse without verification (dev only)
            print("[WARN] No STRIPE_WEBHOOK_SECRET — skipping signature verification")
            event = json.loads(payload)

        # Dispatch to handler
        event_type = event.get("type", "unknown")
        handler = EVENT_HANDLERS.get(event_type)

        if handler:
            result = handler(event)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            print(f"[SKIP] Unhandled event: {event_type}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ignored"}')

    def log_message(self, format, *args):
        print(f"[STRIPE] {args[0]}")


# ============================================================
# Stripe CLI Testing Helper
# ============================================================

def test_locally():
    """
    Instructions for testing with Stripe CLI:

    1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
    2. Login: stripe login
    3. Forward events to your local server:
       stripe listen --forward-to localhost:8080
    4. Trigger a test event:
       stripe trigger checkout.session.completed
    5. Or use the test payment link from stripe_setup.py
    """
    print("=" * 60)
    print("LOCAL TESTING WITH STRIPE CLI")
    print("=" * 60)
    print()
    print("1. In terminal 1, start this server:")
    print("   python stripe_webhook.py")
    print()
    print("2. In terminal 2, forward Stripe events:")
    print("   stripe listen --forward-to localhost:8080")
    print("   (Copy the webhook signing secret it shows)")
    print()
    print("3. Set the webhook secret:")
    print("   export STRIPE_WEBHOOK_SECRET=\"whsec_...\"")
    print()
    print("4. Trigger a test checkout:")
    print("   stripe trigger checkout.session.completed")
    print()
    print("5. Or visit your test payment link in a browser")
    print("   Use test card: 4242 4242 4242 4242")


def main():
    if "--help-test" in sys.argv:
        test_locally()
        return

    port = int(os.environ.get("PORT", "8080"))

    # Validate config
    missing = []
    if not stripe.api_key:
        missing.append("STRIPE_SECRET_KEY")
    if not LICENSE_SECRET:
        missing.append("QUANTAOPTIMA_LICENSE_SECRET")

    if missing:
        print(f"WARNING: Missing environment variables: {', '.join(missing)}")
        print("The server will start but may not function correctly.")
        print()

    if not WEBHOOK_SECRET:
        print("WARNING: STRIPE_WEBHOOK_SECRET not set — signature verification disabled")
        print("This is OK for local development but NOT for production.")
        print()

    if not SMTP_USER:
        print("NOTE: SMTP not configured — license keys will be printed to console only")
        print()

    print(f"QuantaOptima Stripe Webhook listening on port {port}")
    print(f"POST http://localhost:{port}/ to handle Stripe webhooks")
    print(f"Run with --help-test for local testing instructions")
    print()

    server = HTTPServer(("0.0.0.0", port), StripeWebhookHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
