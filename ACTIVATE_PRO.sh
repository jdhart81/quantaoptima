#!/bin/bash
# QuantaOptima Pro License Activation
# Run: bash ACTIVATE_PRO.sh

LICENSE_KEY="eyJlbWFpbCI6ImhhcnRqdXN0aW42QGdtYWlsLmNvbSIsImV4cGlyZXMiOjE4MDQxMzAwNzkuMTc5MTQ5MiwiZmVhdHVyZXMiOnt9LCJpc3N1ZWQiOjE3NzI1OTQwNzkuMTc5MTQ5OSwidGllciI6InBybyIsInZlcnNpb24iOjF9.7e1720305d9dc1e92f6705879e1b9de081ed00c3a6715fa4479f9df41aeb96d1"

echo "=== QuantaOptima Pro Activation ==="
echo ""

# Method 1: Save to license file
mkdir -p ~/.quantaoptima
echo "$LICENSE_KEY" > ~/.quantaoptima/license.key
echo "[1/2] License key saved to ~/.quantaoptima/license.key"

# Method 2: Add to .zshrc as env var (backup approach)
if ! grep -q "QUANTAOPTIMA_LICENSE" ~/.zshrc 2>/dev/null; then
    echo "" >> ~/.zshrc
    echo "# QuantaOptima Pro License" >> ~/.zshrc
    echo "export QUANTAOPTIMA_LICENSE=\"$LICENSE_KEY\"" >> ~/.zshrc
    echo "[2/2] Added QUANTAOPTIMA_LICENSE to ~/.zshrc"
else
    # Update existing entry
    sed -i '' "s|export QUANTAOPTIMA_LICENSE=.*|export QUANTAOPTIMA_LICENSE=\"$LICENSE_KEY\"|" ~/.zshrc
    echo "[2/2] Updated QUANTAOPTIMA_LICENSE in ~/.zshrc"
fi

echo ""
echo "=== DONE ==="
echo ""
echo "Now restart Claude Desktop to activate Pro."
echo "Then ask Claude: 'Run quantaoptima status'"
echo "You should see: tier = pro"
echo ""
echo "Pro unlocks:"
echo "  - 100 dimensions (was 10)"
echo "  - 5,000 iterations (was 100)"
echo "  - All 6 objectives (was 3)"
echo "  - Benchmarking vs scipy"
echo "  - AI safety observability"
echo "  - Cryptographic audit export"
