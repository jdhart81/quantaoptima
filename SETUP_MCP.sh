#!/bin/bash
# ============================================================
# QuantaOptima MCP Setup — One-click Claude Desktop integration
#
# This script:
#   1. Fixes your .zshrc unmatched quote error
#   2. Installs uv (if needed)
#   3. Configures Claude Desktop to use QuantaOptima MCP server
# ============================================================

set -e

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║    QuantaOptima MCP — Claude Desktop Setup       ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ============================================================
# STEP 1: Fix .zshrc unmatched quote
# ============================================================
echo "=== [1/3] Fixing .zshrc ==="
if grep -n "unmatched" <(zsh -c 'source ~/.zshrc' 2>&1) >/dev/null 2>&1; then
    # Find and remove lines with unmatched quotes (likely old Stripe export)
    # Back up first
    cp ~/.zshrc ~/.zshrc.backup.$(date +%s)
    echo "  Backed up ~/.zshrc"

    # Remove lines containing STRIPE_SECRET_KEY or sk_live that have quote issues
    sed -i '' '/sk_live/d' ~/.zshrc 2>/dev/null || true
    sed -i '' '/STRIPE_SECRET_KEY/d' ~/.zshrc 2>/dev/null || true

    echo "  ✓ Removed problematic Stripe export lines"
else
    echo "  ✓ .zshrc is clean (no errors found)"
fi

# ============================================================
# STEP 2: Install uv (if needed)
# ============================================================
echo ""
echo "=== [2/3] Checking uv ==="
if command -v uv &> /dev/null; then
    echo "  ✓ uv already installed ($(uv --version))"
elif command -v brew &> /dev/null; then
    echo "  Installing uv via Homebrew..."
    brew install uv
    echo "  ✓ uv installed"
else
    echo "  Installing uv via installer script..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "  ✓ uv installed"
fi

# ============================================================
# STEP 3: Configure Claude Desktop
# ============================================================
echo ""
echo "=== [3/3] Configuring Claude Desktop ==="
CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

# Create directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Check if config file exists and has content
if [ -f "$CONFIG_FILE" ] && [ -s "$CONFIG_FILE" ]; then
    # File exists — check if quantaoptima is already configured
    if grep -q "quantaoptima" "$CONFIG_FILE"; then
        echo "  ✓ QuantaOptima already in Claude Desktop config"
    else
        # Back up existing config
        cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%s)"
        echo "  Backed up existing config"

        # Use python to merge the new server into existing config
        python3 -c "
import json, sys

with open('$CONFIG_FILE', 'r') as f:
    config = json.load(f)

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['quantaoptima'] = {
    'command': 'uvx',
    'args': ['--from', 'git+https://github.com/jdhart81/quantaoptima.git', 'quantaoptima-server']
}

with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')

print('  ✓ Added QuantaOptima to existing Claude Desktop config')
"
    fi
else
    # No config file — create one
    cat > "$CONFIG_FILE" << 'CONFIGEOF'
{
  "mcpServers": {
    "quantaoptima": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/jdhart81/quantaoptima.git", "quantaoptima-server"]
    }
  }
}
CONFIGEOF
    echo "  ✓ Created Claude Desktop config with QuantaOptima"
fi

# ============================================================
# DONE
# ============================================================
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              SETUP COMPLETE ✓                    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "NEXT: Restart Claude Desktop (Cmd+Q, then reopen)"
echo ""
echo "Then try asking Claude:"
echo '  "Optimize a sphere function in 10 dimensions"'
echo '  "What is my QuantaOptima license status?"'
echo ""
