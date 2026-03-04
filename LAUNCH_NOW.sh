#!/bin/bash
# ============================================================
# QuantaOptima v0.2.0 — Simplified Launch (run from this folder)
#
# The commit is ALREADY done. This script just:
#   1. Creates the GitHub repo and pushes
#   2. Enables GitHub Pages
#   3. Creates a GitHub release
#
# Prerequisites: gh (GitHub CLI) — install with: brew install gh
# Then authenticate: gh auth login
# ============================================================

set -e

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║    QuantaOptima v0.2.0 — Push & Release         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Verify we're in the right folder
if [ ! -f "quantaoptima/__init__.py" ]; then
    echo "ERROR: Run this from the QuantaOptima-IQ folder"
    exit 1
fi

# Check gh is installed
if ! command -v gh &> /dev/null; then
    echo "ERROR: GitHub CLI (gh) not found."
    echo "Install it: brew install gh"
    echo "Then authenticate: gh auth login"
    exit 1
fi

# ============================================================
# STEP 1: Create GitHub repo and push
# ============================================================
echo "=== [1/3] Creating GitHub repo and pushing ==="

# Check if remote already exists
if git remote get-url origin &>/dev/null; then
    echo "  Remote already set. Pushing..."
    git push origin main
else
    echo "  Creating new public repo..."
    gh repo create quantaoptima --public \
        --description "Quantum-inspired optimizer. 7-31x fewer evals. MCP server for LLM agents. Free tier + Pro." \
        --source . --push
fi
echo "  ✓ Pushed to GitHub"

# ============================================================
# STEP 2: Enable GitHub Pages
# ============================================================
echo ""
echo "=== [2/3] Enabling GitHub Pages ==="
REPO_NAME=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
gh api "repos/${REPO_NAME}/pages" \
    --method POST \
    --field source='{"branch":"main","path":"/docs"}' \
    --silent 2>/dev/null || echo "  Pages already enabled (or enable manually at Settings → Pages)"
echo "  ✓ GitHub Pages configured"

# ============================================================
# STEP 3: Create GitHub release
# ============================================================
echo ""
echo "=== [3/3] Creating GitHub release ==="
gh release create v0.2.0 dist/* \
    --title "QuantaOptima v0.2.0 — Freemium MCP Server" \
    --notes "## What's New

### Freemium Licensing
- **Community (Free):** 3 objectives, 10 dims, 100 iters, optimize + explain
- **Pro (\$29/mo):** All 6 objectives, 100 dims, 5000 iters, all 6 tools
- **Enterprise:** Custom pricing, unlimited everything

### Stripe Payments
- Live payment links — one click to checkout
- Automated license key delivery via email
- Self-validating HMAC keys — zero infrastructure

### New MCP Tool
- \`quantaoptima_status\` — check license tier and available features

### Install
\`\`\`
pip install quantaoptima
\`\`\`

### Get Pro
- Monthly: https://buy.stripe.com/6oU28r5tIcpq97Y6egfYY02
- Annual: https://buy.stripe.com/00w7sL7BQ2OQ97YfOQfYY03
" 2>/dev/null || echo "  Release may already exist"
echo "  ✓ Release created"

# ============================================================
# DONE
# ============================================================
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              LAUNCH COMPLETE 🚀                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "YOUR LIVE LINKS:"
echo "  GitHub:  https://github.com/${REPO_NAME}"
echo "  Pages:   https://$(echo $REPO_NAME | cut -d'/' -f1).github.io/quantaoptima/"
echo "  Stripe:  https://buy.stripe.com/6oU28r5tIcpq97Y6egfYY02"
echo ""
echo "OPTIONAL NEXT STEPS:"
echo "  1. PyPI upload:  twine upload dist/*"
echo "     (Need account? https://pypi.org/account/register/)"
echo "  2. Deploy webhook: see MONETIZATION.md step 4"
echo "  3. Post launch content: see LAUNCH_POSTS.md"
echo ""
