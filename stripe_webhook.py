"""Stripe subscription fulfillment. See docs/OPERATIONS.md for setup.

Only verified invoice.paid events for configured Pro prices issue licenses.
Checkout events never grant access. SQLite records delivery attempts so retries
reuse the same token and already delivered invoices do not issue twice.
"""

import math
import sqlite3
import ssl
from contextlib import contextmanager
from pathlib import Path
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

from quantaoptima.licensing import generate_license_key, load_private_key


# ============================================================
# Configuration
# ============================================================

STRIPE_API_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_API_VERSION = "2026-07-29.dahlia"
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PRO_PRICE_IDS = {p.strip() for p in os.environ.get("STRIPE_PRO_PRICE_IDS", "").split(",") if p.strip()}
DELIVERY_DB = os.environ.get("QUANTAOPTIMA_DELIVERY_DB", str(Path.home() / ".quantaoptima" / "billing" / "delivery.sqlite3"))

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "license@quantaoptima.dev")

GRACE_SECONDS = 5 * 86400
MAX_BODY_BYTES = 1024 * 1024


def _as_dict(value):
    return value if isinstance(value, dict) else value.to_dict()


def _client():
    return stripe.StripeClient(STRIPE_API_KEY, stripe_version=STRIPE_API_VERSION)


@contextmanager
def _delivery_store():
    path = Path(DELIVERY_DB).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    db = sqlite3.connect(path, timeout=30)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS deliveries (invoice TEXT PRIMARY KEY, subscription TEXT NOT NULL, email TEXT NOT NULL, token TEXT NOT NULL, expires REAL NOT NULL, delivered INTEGER NOT NULL DEFAULT 0)")
        db.commit()
        yield db
    finally:
        db.close()


def handle_checkout_completed(event):
    # invoice.paid is the single fulfillment source for initial and renewal invoices.
    return {"status": "ignored", "reason": "Fulfillment waits for invoice.paid"}


def _subscription_id(invoice):
    parent = invoice.get("parent") or {}
    details = parent.get("subscription_details") or {}
    value = details.get("subscription") or invoice.get("subscription")
    return value.get("id") if isinstance(value, dict) else value


def handle_invoice_paid(event):
    invoice = _as_dict(event["data"]["object"])
    if invoice.get("status") != "paid":
        return {"status": "ignored", "reason": "Invoice is not paid"}
    subscription_id = _subscription_id(invoice)
    if not subscription_id:
        return {"status": "ignored", "reason": "Not a subscription invoice"}
    if not PRO_PRICE_IDS:
        raise RuntimeError("Pro price allowlist is not configured")
    client = _client()
    subscription = _as_dict(client.v1.subscriptions.retrieve(subscription_id))
    if subscription.get("status") != "active":
        return {"status": "ignored", "reason": "Subscription is not active"}
    # Use the paid invoice's service period, never a newer, possibly unpaid one.
    period_ends = []
    for line in client.v1.invoices.list_lines(invoice["id"]).auto_paging_iter():
        line = _as_dict(line)
        pricing = line.get("pricing") or {}
        details = pricing.get("price_details") or {}
        legacy_price = line.get("price") or {}
        price_id = details.get("price") or legacy_price.get("id")
        parent = line.get("parent") or {}
        subscription_line = parent.get("subscription_item_details") or {}
        is_subscription_line = parent.get("type") == "subscription_item_details" or line.get("type") == "subscription"
        line_subscription = subscription_line.get("subscription") or line.get("subscription")
        if price_id not in PRO_PRICE_IDS or not is_subscription_line or line.get("amount", 0) < 0:
            continue
        if line_subscription and line_subscription != subscription_id:
            continue
        end = (line.get("period") or {}).get("end")
        if not isinstance(end, (int, float)) or isinstance(end, bool) or not math.isfinite(end):
            raise ValueError("Missing paid service period")
        period_ends.append(end)
    if not period_ends:
        return {"status": "ignored", "reason": "No configured Pro subscription price"}
    expires = max(period_ends) + GRACE_SECONDS
    if expires <= time.time():
        return {"status": "ignored", "reason": "Paid service period has already expired"}
    email = invoice.get("customer_email")
    if not email or not isinstance(email, str) or any(c in email for c in "\r\n"):
        raise ValueError("Customer email is missing or invalid")
    with _delivery_store() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT email, token, expires, delivered FROM deliveries WHERE invoice=?", (invoice["id"],)).fetchone()
        if row and row[3]:
            return {"status": "duplicate", "email_sent": True}
        newest = db.execute("SELECT MAX(expires) FROM deliveries WHERE subscription=? AND delivered=1", (subscription_id,)).fetchone()[0]
        if newest is not None and expires <= newest:
            return {"status": "ignored", "reason": "A newer or equivalent license was already delivered"}
        if row is None:
            token = generate_license_key("pro", email, expires_at=expires, features={
                "stripe_customer": invoice.get("customer", ""),
                "stripe_subscription": subscription_id, "stripe_invoice": invoice["id"],
            })
            db.execute("INSERT INTO deliveries (invoice, subscription, email, token, expires) VALUES (?, ?, ?, ?, ?)",
                       (invoice["id"], subscription_id, email, token, expires))
        db.commit()  # Persist the token before attempting delivery.
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT email, token, expires, delivered FROM deliveries WHERE invoice=?", (invoice["id"],)).fetchone()
        if row[3]:
            return {"status": "duplicate", "email_sent": True}
        # Another worker may have delivered a newer invoice since the first transaction.
        newest = db.execute("SELECT MAX(expires) FROM deliveries WHERE subscription=? AND delivered=1", (subscription_id,)).fetchone()[0]
        if newest is not None and row[2] <= newest:
            return {"status": "ignored", "reason": "A newer license was already delivered"}
        days = max(1, math.ceil((row[2] - time.time()) / 86400))
        if not _send_license_email(row[0], row[1], "Subscription", days):
            raise RuntimeError("License email delivery failed; retry required")
        db.execute("UPDATE deliveries SET delivered=1 WHERE invoice=?", (invoice["id"],))
        db.commit()
    return {"status": "success", "email_sent": True, "expires": expires}


def handle_subscription_event(event):
    # Offline licenses remain valid through their signed expiry; no new key is issued.
    return {"status": "logged", "event": event["type"]}


EVENT_HANDLERS = {
    "checkout.session.completed": handle_checkout_completed,
    "invoice.paid": handle_invoice_paid,
    "customer.subscription.deleted": handle_subscription_event,
    "customer.subscription.updated": handle_subscription_event,
    "invoice.payment_failed": handle_subscription_event,
}


def _send_license_email(to_email: str, license_key: str, plan_label: str, days: int) -> bool:
    """Send the license key to the customer via email."""
    if not SMTP_USER or not SMTP_PASS:
        print("[ERR] SMTP not configured; delivery requires retry")
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

        <p>Install the issuer public.pem from the official release and set <code>QUANTAOPTIMA_LICENSE_PUBLIC_KEY_FILE</code> to its path. Never install a private signing key on a client.</p>
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

Install the issuer public.pem from the official release and set
QUANTAOPTIMA_LICENSE_PUBLIC_KEY_FILE to its path. No private key is needed.
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
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(SMTP_USER, SMTP_PASS)
            if server.send_message(msg):
                return False
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

    def _respond(self, code, result):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_POST(self):
        if not WEBHOOK_SECRET:
            self._respond(503, {"error": "Webhook verification is not configured"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._respond(400, {"error": "Invalid content length"})
            return
        if not 0 < length <= MAX_BODY_BYTES:
            self._respond(413, {"error": "Invalid payload size"})
            return
        payload = self.rfile.read(length)
        try:
            event = _as_dict(stripe.Webhook.construct_event(payload, self.headers.get("Stripe-Signature", ""), WEBHOOK_SECRET))
        except Exception:
            self._respond(400, {"error": "Webhook verification failed"})
            return
        try:
            handler = EVENT_HANDLERS.get(event.get("type"))
            result = handler(event) if handler else {"status": "ignored"}
        except Exception as exc:
            print(f"[ERR] Fulfillment failed ({type(exc).__name__}); retry required")
            self._respond(500, {"error": "Fulfillment failed; retry required"})
            return
        self._respond(200, result)

    def log_message(self, format, *args):
        print(f"[STRIPE] {args[0]}")


# ============================================================
# Stripe CLI Testing Helper
# ============================================================

def validate_config():
    required = {"STRIPE_SECRET_KEY": STRIPE_API_KEY,
                "STRIPE_WEBHOOK_SECRET": WEBHOOK_SECRET,
                "STRIPE_PRO_PRICE_IDS": PRO_PRICE_IDS,
                "SMTP_USER": SMTP_USER, "SMTP_PASS": SMTP_PASS}
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError("Missing required configuration: " + ", ".join(missing))
    load_private_key()
    with _delivery_store():
        pass


def main():
    validate_config()
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), StripeWebhookHandler)
    print(f"QuantaOptima Stripe webhook listening on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
