"""Retired pre-0.4 MCP entry point.

This module previously accepted Python expressions and is intentionally kept as
a non-executing compatibility notice. Use the packaged, built-in-objectives-only
server instead: ``quantaoptima-server`` or ``python -m quantaoptima.server``.
"""

import sys


def main() -> int:
    print(
        "mcp_server.server is retired because its expression evaluator was unsafe. "
        "Run 'quantaoptima-server' instead.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
