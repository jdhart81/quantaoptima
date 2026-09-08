#!/bin/bash
# Activate a customer-supplied v2 token using a trusted issuer public PEM.
set -euo pipefail
: "${QUANTAOPTIMA_LICENSE:?Set your issued v2 license token}"
: "${QUANTAOPTIMA_LICENSE_PUBLIC_KEY_FILE:?Set the trusted issuer public PEM path}"
python3 - <<'PY'
import os
from pathlib import Path
from quantaoptima.licensing import validate_license_key
key = os.environ['QUANTAOPTIMA_LICENSE']
license = validate_license_key(key)
if not license.valid or license.tier == 'community':
    raise SystemExit('License verification failed; nothing was saved')
directory = Path.home() / '.quantaoptima'
directory.mkdir(mode=0o700, parents=True, exist_ok=True)
path = directory / 'license.key'
with os.fdopen(os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600), 'w') as f:
    f.write(key + '\n')
print('License saved. Keep the public key path in your MCP environment and restart the server.')
PY
