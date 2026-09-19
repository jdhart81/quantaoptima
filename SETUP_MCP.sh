#!/bin/sh
set -eu

cat >&2 <<'EOF'
SETUP_MCP.sh is retired. It no longer edits shell startup files, installs remote
software, or changes desktop configuration. Install the reviewed v0.4.1 package
and copy the MCP configuration from README.md manually.
EOF
exit 2
