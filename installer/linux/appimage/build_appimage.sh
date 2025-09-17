#!/bin/bash
# Enhanced AppImage builder for Bitcoin Solo Miner Monitor
# This script uses the comprehensive build system

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check arguments
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <app_dir> <dist_dir> <version> [options]"
    echo "Options:"
    echo "  -v, --verbose    Enable verbose output"
    echo "  -c, --clean      Clean build before packaging"
    exit 1
fi

APP_DIR="$1"
DIST_DIR="$2"
VERSION="$3"
shift 3

# Parse additional options
OPTIONS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            OPTIONS+=("--verbose")
            shift
            ;;
        -c|--clean)
            OPTIONS+=("--clean")
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "📦 Building AppImage using comprehensive build system..."

# Prepare build directory structure
BUILD_DIR="$(dirname "$DIST_DIR")/build"
mkdir -p "$BUILD_DIR/linux"

# Copy application files to build directory
if [ -d "$APP_DIR" ]; then
    cp -r "$APP_DIR"/* "$BUILD_DIR/linux/"
else
    echo "Error: Application directory not found: $APP_DIR"
    exit 1
fi

# Set version in build system
export VERSION="$VERSION"

# Run the comprehensive build system for AppImage only
"$SCRIPT_DIR/build_packages.sh" --type appimage "${OPTIONS[@]}"

# Check if AppImage was created successfully
APPIMAGE_FILE=$(find "$DIST_DIR" -name "*.AppImage" -type f | head -1)
PORTABLE_FILE=$(find "$DIST_DIR" -name "*portable*.tar.gz" -type f | head -1)

if [ -n "$APPIMAGE_FILE" ]; then
    echo "✅ AppImage created successfully: $(basename "$APPIMAGE_FILE")"
    echo "📦 AppImage details:"
    ls -lh "$APPIMAGE_FILE"
    echo "🔧 AppImage is executable and portable"
elif [ -n "$PORTABLE_FILE" ]; then
    echo "✅ Portable archive created: $(basename "$PORTABLE_FILE")"
    echo "📦 Portable archive details:"
    ls -lh "$PORTABLE_FILE"
    echo "ℹ️  Extract and run AppRun to start the application"
else
    echo "❌ AppImage/Portable package creation failed"
    exit 1
fi