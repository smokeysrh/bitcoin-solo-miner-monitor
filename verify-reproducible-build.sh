#!/bin/bash
# verify-reproducible-build.sh

set -euo pipefail

VERSION="$1"
REFERENCE_CHECKSUMS="$2"

if [ -z "$VERSION" ] || [ -z "$REFERENCE_CHECKSUMS" ]; then
    echo "Usage: $0 <version> <reference_checksums_file>"
    exit 1
fi

echo "=== Reproducible Build Verification ==="
echo "Version: $VERSION"
echo "Reference: $REFERENCE_CHECKSUMS"
echo ""

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Clone repository
echo "Cloning repository..."
git clone https://github.com/smokeysrh/bitcoin-solo-miner-monitor.git
cd bitcoin-solo-miner-monitor

# Checkout version
echo "Checking out version $VERSION..."
git checkout "v$VERSION"

# Verify clean checkout
git_status=$(git status --porcelain)
if [ -n "$git_status" ]; then
    echo "Error: Working directory not clean after checkout"
    exit 1
fi

# Run build
echo "Running reproducible build..."
./build-reproducible.sh "$VERSION"

# Compare checksums
echo "Comparing checksums..."
if diff "$REFERENCE_CHECKSUMS" distribution/SHA256SUMS; then
    echo "✅ VERIFICATION PASSED: Checksums match!"
    exit_code=0
else
    echo "❌ VERIFICATION FAILED: Checksums differ!"
    echo ""
    echo "Expected checksums:"
    cat "$REFERENCE_CHECKSUMS"
    echo ""
    echo "Actual checksums:"
    cat distribution/SHA256SUMS
    exit_code=1
fi

# Cleanup
cd /
rm -rf "$TEMP_DIR"

exit $exit_code