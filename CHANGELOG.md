# Changelog

## 0.4.1 — unreleased

- Retire the legacy expression-evaluating MCP server and the setup script that
  modified shell startup files.
- Confine agent-requested exports to `QUANTAOPTIMA_EXPORT_DIR`, reject paths,
  and refuse to overwrite existing files.
- Enforce hard function-evaluation ceilings for benchmark participants and
  correct QuantaOptima's initialization accounting.
- Disable public paid calls to action until issuer trust distribution and
  end-to-end Stripe fulfillment are independently verified.
- Bound provenance language to explicitly recorded data and mark historical
  benchmark/capability reports as non-validating archives.
- Align Enterprise metadata with the built-in-objectives-only MCP surface.

## 0.4.0 — 2026-09-08

- Capture independent audit snapshots, generate secure random audit keys, sign
  block numbers, and serialize concurrent in-memory appends.
- Add schema-v2 authenticated import and SQLite-backed MCP audit persistence,
  with a separately retained key and explicit corruption/missing-key failures.
- Treat imported viewer data as unverified until signatures are checked; escape
  imported block fields and identify HTML badges as render-time results.
- Replace shared-secret license tokens with Ed25519 public-key verification.
  **Migration required:** reissue old HMAC tokens and distribute a trusted public PEM.
- Fulfill both initial and renewal subscriptions from verified `invoice.paid`
  events, restrict issuance to configured Pro prices, and anchor expiry to paid
  invoice periods. Persist delivery state and retry failed email delivery.
- Fail closed on missing webhook configuration and retire unauthenticated Gumroad
  fulfillment and hardcoded license activation.
- Add regression tests, package CI, the Apache 2.0 license text, and operational
  documentation. Require Python 3.10+ and constrain MCP to its compatible v1 API.

No production issuer keys, deployment, publication, or customer messages are
included in this release preparation.
