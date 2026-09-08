# QuantaOptima 0.4 operations and migration

This is an alpha release with changes to license and audit formats. Do not reuse
0.3 signing secrets or treat old exported `verified` flags as evidence.

## Install and test

Python 3.10 or newer is required (the MCP server uses modern type annotations).
From the repository:

```bash
python -m pip install '.[dev,webhook]' build
python -m pytest -q
python -m build
```

The CI workflow runs tests and builds packages on Python 3.10, 3.12, and 3.14.
The legacy `LAUNCH*.sh` scripts are retired; they contain obsolete release and
configuration assumptions. Build and review the 0.4 artifacts before publishing.

## Issuer keys and existing customers

Licenses now use Ed25519 signatures. The issuer alone holds `private.pem`; client
installations use `public.pem`. A public verification key cannot issue licenses.
Legacy HMAC licenses are rejected and must be reissued after reconciling each
customer's entitlement. Community functionality continues to work without keys.

Generate a new keypair once, in a private directory outside the repository:

```bash
python generate_license.py --init-keys /secure/quantaoptima-issuer
export QUANTAOPTIMA_LICENSE_PRIVATE_KEY_FILE=/secure/quantaoptima-issuer/private.pem
python generate_license.py --tier pro --email customer@example.com --days 30
```

The generator refuses to overwrite an existing keypair and creates the private
file with owner-only permissions. Back it up in the issuer's secret store. The
private PEM is unencrypted on disk and relies on filesystem access controls.
No production issuer key is generated or bundled by this update.

Distribute the public PEM through a trusted release channel. Either include it
as `quantaoptima/license_public_key.pem` in an issuer-specific wheel before
building, or have customers configure:

```bash
export QUANTAOPTIMA_LICENSE_PUBLIC_KEY_FILE=/trusted/location/public.pem
export QUANTAOPTIMA_LICENSE='the-issued-qo2-token'
```

The verifier never trusts a key embedded in a license and never reads a private
key. Customers can instead save their token to `~/.quantaoptima/license.key`.
Keep the public key environment setting in the MCP configuration. Key rotation
currently requires redistributing the trusted public key and reissuing active
licenses; there is no multi-key rotation window.

This is an offline entitlement check, not DRM against an owner modifying their
own open-source installation. Cancellations and refunds cannot instantly revoke
an already issued offline token; its signed expiry remains the access boundary.

## Audit persistence, recovery, and verification

The MCP server uses `~/.quantaoptima/audit` by default. Set
`QUANTAOPTIMA_AUDIT_DIR` to a dedicated persistent directory to isolate workflows.
It contains `audit.sqlite3` and a separate 32-byte `audit.key`, both created with
owner-only permissions. SQLite transactions serialize appends across server
processes. Existing state is authenticated before accepting another entry.
Missing keys or corrupted history stop recovery instead of silently replacing it.

Stop writers and back up the directory, including the key. Protect backups as
secrets. To restore, place both files in the configured directory and restart.
Do not place the directory on an ephemeral deployment filesystem.

For library use:

```python
from quantaoptima import PersistentAuditChain, AuditChain
from pathlib import Path
import json

chain = PersistentAuditChain('/private/workflow-audit', scope='my-workflow')
chain.log('decision', {'options': ['A', 'B']}, {'chosen': 'A'})
chain.export_json('audit.json')
restored = AuditChain.from_dict(
    json.loads(Path('audit.json').read_text()),
    Path('/private/workflow-audit/audit.key').read_bytes(),
)
assert restored.verify()
```

Each persistent writer refreshes history before appending. A long-lived library
reader can call `refresh()` to see other writers' entries. In-memory `AuditChain`
remains available for explicitly ephemeral workflows. Optimizer demo step traces
remain in memory; export them before closing the process. The durable MCP chain
records optimizer start/completion, not the full step trace.

Schema v2 signs block numbers and captures independent JSON snapshots. Old
schema-v1 exports must be retained with their original verifier and key; they
cannot be silently converted into authenticated v2 history. The old MCP server
did not persist its key, so an old export without that key cannot be recovered
as cryptographic evidence.

Imported JSON defaults to **UNVERIFIED** in the viewer. To verify with the
separately retained audit HMAC key:

```bash
python -m quantaoptima.viewer audit.json --key-file /private/workflow-audit/audit.key --output audit.html
```

The key is never embedded in the HTML. A viewer badge describes verification at
render time; the resulting editable HTML is not itself a verification proof.

## Stripe fulfillment

Install `.[webhook]` and configure these values in the hosting platform's secret
store/environment before starting `python stripe_webhook.py`:

| Setting | Purpose |
| --- | --- |
| `STRIPE_SECRET_KEY` | Prefer a restricted key with subscription and invoice read permissions |
| `STRIPE_WEBHOOK_SECRET` | Endpoint signing secret; missing or invalid signatures never grant access |
| `STRIPE_PRO_PRICE_IDS` | Comma-separated allowlist of this product's monthly and annual price IDs |
| `QUANTAOPTIMA_LICENSE_PRIVATE_KEY_FILE` | Issuer's mounted private PEM |
| `SMTP_USER`, `SMTP_PASS` | Mail account credentials |
| `SMTP_HOST`, `SMTP_PORT`, `FROM_EMAIL` | Mail service settings; defaults are documented in the service |
| `QUANTAOPTIMA_DELIVERY_DB` | SQLite path on a durable private volume |
| `PORT` | HTTP listen port, default 8080 |

Serve the endpoint behind HTTPS. It supports one local SQLite database shared
by service processes; it is not designed for horizontally scaled hosts without
shared transactional storage. The service validates required configuration and
key parsing before listening.

Register **invoice.paid**, including on existing Stripe endpoints. Changing
`stripe_setup.py` only changes newly created endpoint configurations. Checkout
completion does not grant access. Paid invoices for active subscriptions and
allowlisted recurring prices issue licenses for that invoice's service period
plus five days of grace. This handles initial and renewal invoices and delayed
payment methods. It does not extend access from the event's arrival time.

The database stores the pending token before delivery, returns a retryable HTTP
500 on delivery failure, and records delivery only after SMTP accepts the
message. Duplicate invoices reuse the same token; successfully delivered
invoices are skipped. Older invoices cannot replace a newer delivered license.
A crash after SMTP acceptance but before recording success can send the same
email twice. SMTP acceptance does not establish inbox delivery; monitor bounces.
Back up the delivery database, which contains customer emails and license tokens.

The unauthenticated Gumroad endpoint now returns HTTP 410 and never issues keys.
Existing Gumroad customers require sale reconciliation and manual v2 reissuance.

Before enabling this release, provision issuer keys, distribute the public key,
register `invoice.paid`, configure durable storage, reissue active entitlements,
and exercise signed test-mode initial/renewal events with the real mail service.
No live billing, endpoint registration, license delivery, or deployment is
performed by the repository update or its tests.

The renewal flow follows Stripe's [subscription webhook guidance](https://docs.stripe.com/billing/subscriptions/webhooks)
and [signature and retry guidance](https://docs.stripe.com/webhooks).
