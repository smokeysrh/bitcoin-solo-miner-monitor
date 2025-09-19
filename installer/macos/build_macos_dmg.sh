#!/bin/bash
# Build script for creating macOS DMG installer
# This script prepares the application directory and calls create_dmg.sh

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build/macos"
DIST_DIR="${PROJECT_ROOT}/dist"
VERSION="${1:-0.1.0}"

echo "🏗️  Building macOS DMG installer for version ${VERSION}..."

# Create build directories
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Clean previous build
rm -rf "$BUILD_DIR"/*

echo "📦 Preparing application files..."

# Copy application source files
cp -r "$PROJECT_ROOT/src" "$BUILD_DIR/"
cp -r "$PROJECT_ROOT/config" "$BUILD_DIR/"
cp "$PROJECT_ROOT/run.py" "$BUILD_DIR/"
cp "$PROJECT_ROOT/requirements.txt" "$BUILD_DIR/"

# Copy assets if they exist
if [ -d "$PROJECT_ROOT/assets" ]; then
    cp -r "$PROJECT_ROOT/assets" "$BUILD_DIR/"
fi

# Copy frontend build if it exists
if [ -d "$PROJECT_ROOT/src/frontend/dist" ]; then
    cp -r "$PROJECT_ROOT/src/frontend/dist" "$BUILD_DIR/frontend_dist"
fi

# Build frontend if package.json exists and dist doesn't exist
if [ -f "$PROJECT_ROOT/package.json" ] && [ ! -d "$PROJECT_ROOT/src/frontend/dist" ]; then
    echo "🔧 Building frontend..."
    cd "$PROJECT_ROOT"
    if command -v npm >/dev/null 2>&1; then
        npm install
        npm run build
        if [ -d "src/frontend/dist" ]; then
            cp -r "src/frontend/dist" "$BUILD_DIR/frontend_dist"
        fi
    else
        echo "⚠️  npm not found, skipping frontend build"
    fi
    cd "$SCRIPT_DIR"
fi

# Create DMG
DMG_NAME="BitcoinSoloMinerMonitor-${VERSION}.dmg"
DMG_PATH="${DIST_DIR}/${DMG_NAME}"

echo "🍎 Creating DMG installer..."
"$SCRIPT_DIR/create_dmg.sh" "$BUILD_DIR" "$DMG_PATH" "$VERSION"

echo "✅ macOS DMG build complete!"
echo "📁 Output: $DMG_PATH"

# List the contents of the dist directory
echo ""
echo "📋 Build artifacts:"
ls -la "$DIST_DIR"