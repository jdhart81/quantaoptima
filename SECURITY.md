# Security model

QuantaOptima authenticates the data explicitly submitted to its audit logger.
It does not establish that an action occurred, authenticate caller-supplied actor
names, prove that omitted actions were logged, or provide regulatory certification.

HMAC verification detects changes to signed records without the key. Anyone
holding the HMAC key can rewrite records and regenerate signatures. Removing a
valid suffix or restoring an older complete snapshot is not detectable without
an independently retained expected chain head/length or external checkpoint.
Protect the key and maintain independent checkpoints when completeness matters.

Records capture independent JSON snapshots; unsupported data and non-finite
numbers should be normalized before logging. Audit payloads may contain sensitive
inputs or outputs: avoid secrets and redact data before logging.

Licenses use a separate Ed25519 keypair. Only the issuer private key signs paid
entitlements; customers hold the public verification key. Legacy HMAC tokens are
not accepted. There is no immediate revocation of offline licenses.

Report suspected vulnerabilities privately to the maintainer using the contact
listed in `pyproject.toml`. Do not put private keys or customer data into public
issues. See [operations and migration](docs/OPERATIONS.md) for key/storage setup.
