#!/bin/bash
# build-reproducible.sh - Master build script for reproducible builds

set -euo pipefail

# Configuration
VERSION="${1:-dev-build}"
PLATFORM="${2:-$(uname -s | tr '[:upper:]' '[:lower:]')}"
BUILD_ROOT="${BUILD_ROOT:-$(pwd)}"
DIST_ROOT="${DIST_ROOT:-${BUILD_ROOT}/distribution}"

# Logging setup
LOG_FILE="${BUILD_ROOT}/build-${PLATFORM}-${VERSION}.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

echo "=== Bitcoin Solo Miner Monitor Reproducible Build ==="
echo "Version: $VERSION"
echo "Platform: $PLATFORM"
echo "Build Root: $BUILD_ROOT"
echo "Started: $(date -u)"
echo "Git Commit: $(git rev-parse HEAD)"
echo "Git Tag: $(git describe --tags --exact-match 2>/dev/null || echo 'none')"
echo ""

# Environment verification
echo "=== Environment Verification ==="
python3 --version
node --version
npm --version
git --version

# Set reproducible environment
export SOURCE_DATE_EPOCH="1704067200"
export PYTHONHASHSEED="0"
export PYTHONDONTWRITEBYTECODE="1"
export LC_ALL="C.UTF-8"
export LANG="C.UTF-8"
export TZ="UTC"

echo "Environment variables set for reproducibility"
echo ""

# Clean previous builds
echo "=== Cleaning Previous Builds ==="
rm -rf "$DIST_ROOT"
mkdir -p "$DIST_ROOT"
echo "Build directory cleaned"
echo ""

# Verify source integrity
echo "=== Source Code Verification ==="
if [ -f ".git/HEAD" ]; then
    git_status=$(git status --porcelain)
    if [ -n "$git_status" ]; then
        echo "Warning: Working directory has uncommitted changes:"
        echo "$git_status"
    else
        echo "Working directory is clean"
    fi
fi
echo ""

# Install dependencies
echo "=== Installing Dependencies ==="
if [ -f "requirements-lock.txt" ]; then
    echo "Installing Python dependencies from requirements-lock.txt..."
    python3 -m pip install --no-cache-dir --require-hashes -r requirements-lock.txt
else
    echo "Installing Python dependencies from requirements.txt..."
    python3 -m pip install --no-cache-dir -r requirements.txt
fi

echo "Installing Node.js dependencies..."
npm ci --production
echo ""

# Build frontend
echo "=== Building Frontend ==="
if [ -d "src/frontend" ]; then
    cd src/frontend
    npm ci
    npm run build
    cd "$BUILD_ROOT"
    echo "Frontend build completed"
else
    echo "No frontend directory found, skipping"
fi
echo ""

# Platform-specific build
echo "=== Platform-Specific Build ==="
case "$PLATFORM" in
    "linux")
        python3 scripts/create-distribution.py --platform linux --version "$VERSION"
        ;;
    "windows")
        python3 scripts/create-distribution.py --platform windows --version "$VERSION"
        ;;
    "darwin"|"macos")
        python3 scripts/create-distribution.py --platform macos --version "$VERSION"
        ;;
    *)
        echo "Error: Unsupported platform: $PLATFORM"
        exit 1
        ;;
esac
echo ""

# Generate checksums
echo "=== Generating Checksums ==="
cd "$DIST_ROOT"
find . -name "*.exe" -o -name "*.dmg" -o -name "*.deb" -o -name "*.rpm" -o -name "*.AppImage" | \
    xargs sha256sum > SHA256SUMS 2>/dev/null || echo "No installer files found"
if [ -f SHA256SUMS ]; then
    echo "Checksums generated:"
    cat SHA256SUMS
else
    echo "No checksums to generate"
fi
echo ""

# Build report
echo "=== Build Report ==="
cat > BUILD_REPORT.txt << EOF
Bitcoin Solo Miner Monitor Build Report
======================================

Version: $VERSION
Platform: $PLATFORM
Build Date: $(date -u)
Git Commit: $(git rev-parse HEAD)
Git Tag: $(git describe --tags --exact-match 2>/dev/null || echo 'none')

Environment:
- Python: $(python3 --version)
- Node.js: $(node --version)
- npm: $(npm --version)
- OS: $(uname -a)

Build Configuration:
- SOURCE_DATE_EPOCH: $SOURCE_DATE_EPOCH
- PYTHONHASHSEED: $PYTHONHASHSEED
- LC_ALL: $LC_ALL
- TZ: $TZ

Generated Files:
$(ls -la)

Checksums:
$(cat SHA256SUMS 2>/dev/null || echo "No checksums available")
EOF

echo "Build completed successfully!"
echo "Build report saved to: $DIST_ROOT/BUILD_REPORT.txt"
echo "Build log saved to: $LOG_FILE"