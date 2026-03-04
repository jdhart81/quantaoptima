#!/bin/bash
# ============================================================
# QuantaOptima Launch Script
# Run this from the project root on your local machine.
# Prerequisites: gh (GitHub CLI), pip, twine
# ============================================================

set -e

echo "=== STEP 2: Create GitHub repo and push ==="
# Create public repo (change 'justinhart' to your GitHub username if different)
gh repo create quantaoptima --public --description "Quantum-inspired black-box optimizer. 7-31x fewer function evaluations. MCP server for LLM agents." --source . --push

echo ""
echo "=== STEP 3: Enable GitHub Pages ==="
# Enable Pages from docs/ folder on main branch
gh api repos/justinhart/quantaoptima/pages \
  --method POST \
  --field source='{"branch":"main","path":"/docs"}' \
  --silent 2>/dev/null || echo "Pages may already be enabled or needs manual setup at: https://github.com/justinhart/quantaoptima/settings/pages"

echo ""
echo "=== STEP 4: Publish to PyPI ==="
# Build fresh
pip install build twine
python -m build

# Upload (will prompt for PyPI token)
# Get your token at: https://pypi.org/manage/account/token/
echo ""
echo "To upload to PyPI, run:"
echo "  twine upload dist/*"
echo ""
echo "If you don't have a PyPI account yet:"
echo "  1. Go to https://pypi.org/account/register/"
echo "  2. Verify email"
echo "  3. Go to https://pypi.org/manage/account/token/"
echo "  4. Create token (scope: entire account for first upload)"
echo "  5. Run: twine upload dist/*"
echo "     Username: __token__"
echo "     Password: <your-token>"
echo ""

echo "=== STEP 5: Create GitHub release ==="
gh release create v0.1.0 dist/* \
  --title "QuantaOptima v0.1.0" \
  --notes "Initial release. Quantum-inspired black-box optimizer with MCP server for LLM agents. See README for details."

echo ""
echo "=== DONE ==="
echo "Your project is live at:"
echo "  GitHub: https://github.com/justinhart/quantaoptima"
echo "  Pages:  https://justinhart.github.io/quantaoptima/"
echo "  PyPI:   https://pypi.org/project/quantaoptima/"
echo ""
echo "Now share the launch posts (see LAUNCH_POSTS.md)"
