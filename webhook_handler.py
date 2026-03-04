#!/usr/bin/env python3
"""
Gumroad Webhook → License Key Delivery

When someone buys on Gumroad, this webhook generates a license key
and emails it to the customer. Deploys FREE on:
  - Cloudflare Workers (100K free requests/day)
  - Vercel Serverless (100K free invocations/month)
  - Or run locally with: python webhook_handler.py

Gumroad Setup:
  1. Create product at gumroad.com (free account)
  2. Settings → Webhooks → Add endpoint URL
  3. Set QUANTAOPTIMA_LICENSE_SECRET env var on your host

Flow:
  Customer pays on Gumroad → Gumroad POSTs to this webhook →
  webhook generates signed license key → sends email with key →
  customer sets env var → Pro features unlocked
"""

import hashlib
import hmac
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quantaoptima.licensing import generate_license_key


# ============================================================
# Configuration (set via environment variables)
# ============================================================

LICENSE_SECRET = os.environ.get("QUANTAOPTIMA_LICENSE_SECRET", "")
GUMROAD_PRODUCT_MAP = {
    # Map Gumroad product permalinks to tiers and durations
    "quantaoptima-pro-monthly": {"tier": "pro", "days": 35},    # 30 + 5 grace
    "quantaoptima-pro-annual": {"tier": "pro", "days": 370},    # 365 + 5 grace
    "quantaoptima-enterprise": {"tier": "enterprise", "days": 0},  # Never expires
}

# Email settings (use Gmail SMTP — free)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")  # Your Gmail
SMTP_PASS = os.environ.get("SMTP_PASS", "")  # Gmail App Password
FROM_EMAIL = os.environ.get("FROM_EMAIL", "license@quantaoptima.dev")


def handle_gumroad_webhook(body: dict) -> dict:
    """
    Process a Gumroad sale webhook and generate + deliver a license key.

    Args:
        body: Parsed Gumroad webhook payload

    Returns:
        Response dict with status and message
    """
    # Extract customer info
    email = body.get("email", [""])[0] if isinstance(body.get("email"), list) else body.get("email", "")
    product_permalink = body.get("product_permalink", [""])[0] if isinstance(body.get("product_permalink"), list) else body.get("product_permalink", "")
    product_name = body.get("product_name", ["QuantaOptima Pro"])[0] if isinstance(body.get("product_name"), list) else body.get("product_name", "QuantaOptima Pro")

    if not email:
        return {"status": "error", "message": "No email in webhook payload"}

    # Determine tier from product
    product_config = GUMROAD_PRODUCT_MAP.get(
        product_permalink,
        {"tier": "pro", "days": 35},  # Default to monthly pro
    )

    # Generate license key
    if not LICENSE_SECRET:
        return {"status": "error", "message": "LICENSE_SECRET not configured"}

    signing_key = LICENSE_SECRET.encode("utf-8")
    license_key = generate_license_key(
        tier=product_config["tier"],
        email=email,
        duration_days=product_config["days"],
        signing_key=signing_key,
    )

    # Send email with license key
    email_sent = _send_license_email(email, license_key, product_name, product_config)

    return {
        "status": "success",
        "email": email,
        "tier": product_config["tier"],
        "key_generated": True,
        "email_sent": email_sent,
    }


def _send_license_email(to_email: str, license_key: str, product_name: str, config: dict) -> bool:
    """Send the license key to the customer via email."""
    if not SMTP_USER or not SMTP_PASS:
        print(f"[WARN] SMTP not configured. Key for {to_email}: {license_key}")
        return False

    tier_label = config["tier"].capitalize()
    days = config["days"]
    expiry = f"{days} days" if days > 0 else "never (lifetime)"

    subject = f"Your QuantaOptima {tier_label} License Key"

    html_body = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0a0a; color: #e0e0e0; padding: 40px; border-radius: 12px;">
        <h1 style="color: #ff6b00; margin-bottom: 8px;">QuantaOptima</h1>
        <p style="color: #888; margin-top: 0;">Quantum-inspired optimization for AI</p>

        <hr style="border: 1px solid #333; margin: 24px 0;">

        <h2 style="color: #fff;">Your {tier_label} License</h2>
        <p>Thank you for purchasing {product_name}! Here's your license key:</p>

        <div style="background: #1a1a2e; border: 1px solid #ff6b00; border-radius: 8px; padding: 16px; margin: 24px 0; word-break: break-all; font-family: monospace; font-size: 12px; color: #ff6b00;">
            {license_key}
        </div>

        <h3 style="color: #fff;">Quick Setup (pick one):</h3>

        <p><strong>Option 1 — Environment variable:</strong></p>
        <pre style="background: #1a1a2e; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; color: #0ff;">export QUANTAOPTIMA_LICENSE="{license_key}"</pre>

        <p><strong>Option 2 — License file:</strong></p>
        <pre style="background: #1a1a2e; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; color: #0ff;">mkdir -p ~/.quantaoptima
echo "{license_key}" > ~/.quantaoptima/license.key</pre>

        <p>Then restart your MCP server or Claude Desktop.</p>

        <hr style="border: 1px solid #333; margin: 24px 0;">

        <p style="color: #888; font-size: 13px;">
            Tier: {tier_label}<br>
            Expires: {expiry}<br>
            Support: hartjustin6@gmail.com
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email

    # Plain text fallback
    text_body = f"""
QuantaOptima {tier_label} License Key
=====================================

Thank you for your purchase!

YOUR LICENSE KEY:
{license_key}

SETUP:
Option 1 — export QUANTAOPTIMA_LICENSE="{license_key}"
Option 2 — echo "{license_key}" > ~/.quantaoptima/license.key

Then restart your MCP server or Claude Desktop.

Tier: {tier_label}
Expires: {expiry}
Support: hartjustin6@gmail.com
"""

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
# HTTP Server (for local testing or simple deployment)
# ============================================================

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        data = parse_qs(body)

        result = handle_gumroad_webhook(data)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def log_message(self, format, *args):
        print(f"[WEBHOOK] {args[0]}")


def main():
    port = int(os.environ.get("PORT", "8080"))

    if not LICENSE_SECRET:
        print("WARNING: QUANTAOPTIMA_LICENSE_SECRET not set!")
        print("Keys will be signed with the default (community-only) key.")
        print(f"Set it: export QUANTAOPTIMA_LICENSE_SECRET=\"$(python -c 'import secrets; print(secrets.token_urlsafe(64))')\"")
        print()

    print(f"QuantaOptima Webhook Handler listening on port {port}")
    print(f"POST http://localhost:{port}/ to handle Gumroad webhooks")
    print()

    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
