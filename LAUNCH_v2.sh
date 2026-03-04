#!/bin/bash
# ============================================================
# QuantaOptima v0.2.0 Launch Script — Monetized MCP Server
#
# Run this from the project root on your Mac.
# Prerequisites: gh (GitHub CLI), pip, twine
#
# What's new in v0.2.0:
#   - Freemium licensing (Community free / Pro $29/mo / Enterprise)
#   - Stripe payment integration (live payment links)
#   - 6 MCP tools (added quantaoptima_status)
#   - Upgrade nudges in free tier responses
# ============================================================

set -e
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║    QuantaOptima v0.2.0 — Launch Sequence        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ============================================================
# STEP 1: Stage + Commit new files
# ============================================================
echo "=== [1/6] Staging and committing v0.2.0 ==="
git add quantaoptima/licensing.py \
        quantaoptima/server.py \
        quantaoptima/__init__.py \
        generate_license.py \
        stripe_setup.py \
        stripe_webhook.py \
        webhook_handler.py \
        Procfile \
        requirements-webhook.txt \
        pyproject.toml \
        README.md \
        MONETIZATION.md \
        LAUNCH_POSTS.md \
        docs/index.html \
        .gitignore \
        tests/

git commit -m "v0.2.0: Freemium licensing + Stripe payments + monetization

- Add self-validating HMAC license keys (zero infrastructure)
- Tier-gated MCP tools: Community (free) / Pro (\$29/mo) / Enterprise
- Stripe Checkout integration with live payment links
- Webhook handler for automated key delivery
- License CLI for manual key generation
- Landing page with pricing section
- Upgrade nudges in free-tier responses
- quantaoptima_status tool for license checking"

echo "  ✓ Committed v0.2.0"

# ============================================================
# STEP 2: Push to GitHub
# ============================================================
echo ""
echo "=== [2/6] Pushing to GitHub ==="
git push origin main 2>/dev/null || {
    echo "  Creating repo first..."
    gh repo create quantaoptima --public \
        --description "Quantum-inspired optimizer. 7-31x fewer evals. MCP server for LLM agents. Free tier + Pro." \
        --source . --push
}
echo "  ✓ Pushed to GitHub"

# ============================================================
# STEP 3: Enable GitHub Pages
# ============================================================
echo ""
echo "=== [3/6] Enabling GitHub Pages ==="
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/pages \
    --method POST \
    --field source='{"branch":"main","path":"/docs"}' \
    --silent 2>/dev/null || echo "  Pages already enabled or needs manual setup"
echo "  ✓ GitHub Pages configured"

# ============================================================
# STEP 4: Build + Publish to PyPI
# ============================================================
echo ""
echo "=== [4/6] Building and publishing to PyPI ==="
pip install build twine 2>/dev/null

# Clean old builds
rm -rf dist/ build/ *.egg-info
python -m build

echo ""
echo "Ready to upload v0.2.0 to PyPI."
echo "Run: twine upload dist/*"
echo "  Username: __token__"
echo "  Password: (your PyPI token from https://pypi.org/manage/account/token/)"
echo ""
read -p "Press Enter after PyPI upload (or 's' to skip): " pypi_choice
if [ "$pypi_choice" != "s" ]; then
    twine upload dist/*
fi

# ============================================================
# STEP 5: Create GitHub Release
# ============================================================
echo ""
echo "=== [5/6] Creating GitHub release ==="
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

### Get Pro
- Monthly: https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04
- Annual: https://buy.stripe.com/4gM14nbS6exycka5acfYY05
"
echo "  ✓ Release v0.2.0 created"

# ============================================================
# STEP 6: Deploy Webhook (Railway)
# ============================================================
echo ""
echo "=== [6/6] Webhook Deployment ==="
echo ""
echo "Your Stripe webhook needs a public URL. Easiest free option:"
echo ""
echo "  OPTION A — Railway.app (recommended, free tier):"
echo "    1. Go to https://railway.app — sign up with GitHub"
echo "    2. New Project → Deploy from GitHub → select quantaoptima"
echo "    3. Add environment variables in Railway dashboard:"
echo "       STRIPE_SECRET_KEY=sk_live_... (your NEW rotated key)"
echo "       STRIPE_WEBHOOK_SECRET=(get from Stripe dashboard)"
echo "       QUANTAOPTIMA_LICENSE_SECRET=(your license signing secret)"
echo "       SMTP_USER=hartjustin6@gmail.com"
echo "       SMTP_PASS=(Gmail app password)"
echo "       PORT=8080"
echo "    4. Railway gives you a URL like https://quantaoptima-production.up.railway.app"
echo "    5. Register that URL in Stripe Dashboard → Webhooks"
echo ""
echo "  OPTION B — Local with ngrok (for testing):"
echo "    python stripe_webhook.py &"
echo "    ngrok http 8080"
echo "    # Use the ngrok URL in Stripe webhooks"
echo ""

# ============================================================
# DONE
# ============================================================
echo "╔══════════════════════════════════════════════════╗"
echo "║              LAUNCH COMPLETE 🚀                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "YOUR LIVE LINKS:"
echo "  GitHub:   https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo 'justinhart/quantaoptima')"
echo "  PyPI:     https://pypi.org/project/quantaoptima/"
echo "  Pages:    https://justinhart.github.io/quantaoptima/"
echo "  Stripe Monthly: https://buy.stripe.com/8x24gze0edtu1FwgSUfYY04"
echo "  Stripe Annual:  https://buy.stripe.com/4gM14nbS6exycka5acfYY05"
echo ""
echo "NEXT: Post your launch content → see LAUNCH_POSTS.md"
echo ""
