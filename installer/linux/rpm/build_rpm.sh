#!/bin/bash
# Enhanced RPM package builder for Bitcoin Solo Miner Monitor
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

echo "🔴 Building RPM package using comprehensive build system..."

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

# Run the comprehensive build system for RPM only
"$SCRIPT_DIR/build_packages.sh" --type rpm "${OPTIONS[@]}"

# Check if RPM was created successfully
RPM_FILE=$(find "$DIST_DIR" -name "*.rpm" -type f | head -1)
if [ -n "$RPM_FILE" ]; then
    echo "✅ RPM package created successfully: $(basename "$RPM_FILE")"
    echo "📦 Package details:"
    rpm -qip "$RPM_FILE" 2>/dev/null | head -20 || echo "RPM info not available (rpm command not found)"
else
    echo "❌ RPM package creation failed"
    exit 1
fi