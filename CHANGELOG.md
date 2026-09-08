# Changelog

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
