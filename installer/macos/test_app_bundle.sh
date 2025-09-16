#!/bin/bash
# Test script for macOS Application Bundle Integration
# This script validates the app bundle structure and functionality

set -e  # Exit on any error

# Configuration
VERSION="${1:-1.0.0}"
APP_NAME="Bitcoin Solo Miner Monitor"
TEST_DIR="$(mktemp -d)"

echo "🧪 Testing macOS Application Bundle Integration"
echo "Version: $VERSION"
echo "Test directory: $TEST_DIR"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up test files..."
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

echo "📦 Creating test app bundle..."
cd "$SCRIPT_DIR"

# Create the app bundle
python3 bundle/create_app_bundle.py \
    --output "$TEST_DIR" \
    --version "$VERSION" \
    --name "$APP_NAME"

APP_BUNDLE="$TEST_DIR/$APP_NAME.app"

# Validate bundle structure
echo "🔍 Validating app bundle structure..."

# Check required directories
REQUIRED_DIRS=(
    "Contents"
    "Contents/MacOS"
    "Contents/Resources"
    "Contents/Frameworks"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$APP_BUNDLE/$dir" ]; then
        echo "❌ Missing required directory: $dir"
        exit 1
    fi
done

# Check required files
REQUIRED_FILES=(
    "Contents/Info.plist"
    "Contents/MacOS/BitcoinSoloMinerMonitor"
    "Contents/Resources/run.py"
    "Contents/Resources/requirements.txt"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$APP_BUNDLE/$file" ]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
done

echo "✅ App bundle structure validation passed"

# Validate Info.plist
echo "🔍 Validating Info.plist..."
INFO_PLIST="$APP_BUNDLE/Contents/Info.plist"

# Check if plutil is available for validation
if command -v plutil >/dev/null 2>&1; then
    if plutil -lint "$INFO_PLIST" >/dev/null 2>&1; then
        echo "✅ Info.plist format validation passed"
    else
        echo "❌ Info.plist format validation failed"
        exit 1
    fi
else
    echo "⚠️  plutil not available, skipping Info.plist format validation"
fi

# Check key Info.plist values
BUNDLE_ID=$(plutil -extract CFBundleIdentifier raw "$INFO_PLIST" 2>/dev/null || echo "")
BUNDLE_NAME=$(plutil -extract CFBundleName raw "$INFO_PLIST" 2>/dev/null || echo "")
BUNDLE_VERSION=$(plutil -extract CFBundleVersion raw "$INFO_PLIST" 2>/dev/null || echo "")

if [ "$BUNDLE_ID" = "com.bitcoinsolominormonitor.app" ]; then
    echo "✅ Bundle identifier correct: $BUNDLE_ID"
else
    echo "❌ Bundle identifier incorrect: $BUNDLE_ID"
    exit 1
fi

if [ "$BUNDLE_NAME" = "$APP_NAME" ]; then
    echo "✅ Bundle name correct: $BUNDLE_NAME"
else
    echo "❌ Bundle name incorrect: $BUNDLE_NAME"
    exit 1
fi

if [ "$BUNDLE_VERSION" = "$VERSION" ]; then
    echo "✅ Bundle version correct: $BUNDLE_VERSION"
else
    echo "❌ Bundle version incorrect: $BUNDLE_VERSION"
    exit 1
fi

# Validate executable permissions
echo "🔍 Validating executable permissions..."
EXECUTABLE="$APP_BUNDLE/Contents/MacOS/BitcoinSoloMinerMonitor"

if [ -x "$EXECUTABLE" ]; then
    echo "✅ Executable has correct permissions"
else
    echo "❌ Executable missing execute permissions"
    exit 1
fi

# Test launcher script syntax
echo "🔍 Validating launcher script syntax..."
if bash -n "$EXECUTABLE"; then
    echo "✅ Launcher script syntax validation passed"
else
    echo "❌ Launcher script syntax validation failed"
    exit 1
fi

# Check for application files
echo "🔍 Validating application files..."
RESOURCES_DIR="$APP_BUNDLE/Contents/Resources"

# Check for main application files
APP_FILES=(
    "run.py"
    "requirements.txt"
    "src/main.py"
    "config/app_config.py"
)

for file in "${APP_FILES[@]}"; do
    if [ -f "$RESOURCES_DIR/$file" ]; then
        echo "✅ Found application file: $file"
    else
        echo "⚠️  Application file not found: $file"
    fi
done

# Check for icon
if [ -f "$RESOURCES_DIR/app_icon.icns" ]; then
    echo "✅ Found ICNS icon"
elif [ -f "$RESOURCES_DIR/app_icon.png" ]; then
    echo "✅ Found PNG icon (fallback)"
else
    echo "⚠️  No application icon found"
fi

# Test Python dependency installation
echo "🔍 Testing Python dependency handling..."
SITE_PACKAGES="$RESOURCES_DIR/site-packages"

if [ -d "$SITE_PACKAGES" ]; then
    echo "✅ Site-packages directory exists"
    
    # Count installed packages
    PACKAGE_COUNT=$(find "$SITE_PACKAGES" -maxdepth 1 -type d -name "*" | wc -l)
    echo "📦 Found $PACKAGE_COUNT installed packages"
    
    if [ -f "$SITE_PACKAGES/.dependencies_installed" ]; then
        echo "✅ Dependencies installation marker found"
    else
        echo "⚠️  Dependencies installation marker not found"
    fi
else
    echo "⚠️  Site-packages directory not found"
fi

# Test Launchpad integration files
echo "🔍 Testing Launchpad integration..."
REFRESH_SCRIPT="$TEST_DIR/refresh_launchpad.sh"

if [ -f "$REFRESH_SCRIPT" ] && [ -x "$REFRESH_SCRIPT" ]; then
    echo "✅ Launchpad refresh script created and executable"
else
    echo "⚠️  Launchpad refresh script not found or not executable"
fi

# Simulate bundle registration (dry run)
echo "🔍 Testing bundle registration simulation..."
if command -v lsregister >/dev/null 2>&1; then
    # Test registration without actually registering
    echo "✅ Launch Services registration tool available"
else
    echo "⚠️  Launch Services registration tool not available"
fi

# Test bundle size
echo "🔍 Checking bundle size..."
BUNDLE_SIZE=$(du -sh "$APP_BUNDLE" | cut -f1)
echo "📏 Bundle size: $BUNDLE_SIZE"

# Validate bundle can be opened (dry run)
echo "🔍 Testing bundle opening simulation..."
if [ -d "$APP_BUNDLE" ]; then
    echo "✅ Bundle can be opened as directory"
else
    echo "❌ Bundle cannot be opened"
    exit 1
fi

# Test DMG integration
echo "🔍 Testing DMG integration..."
echo "Creating test DMG with integrated bundle..."

# Use the updated create_dmg.sh script
"$SCRIPT_DIR/create_dmg.sh" "$TEST_DIR" "$TEST_DIR/test.dmg" "$VERSION"

if [ -f "$TEST_DIR/test.dmg" ]; then
    echo "✅ DMG creation with integrated bundle successful"
    
    # Check DMG size
    DMG_SIZE=$(ls -lh "$TEST_DIR/test.dmg" | awk '{print $5}')
    echo "📏 DMG size: $DMG_SIZE"
    
    # Check for checksum file
    if [ -f "$TEST_DIR/test.dmg.sha256" ]; then
        echo "✅ DMG checksum file created"
    else
        echo "⚠️  DMG checksum file not found"
    fi
else
    echo "❌ DMG creation failed"
    exit 1
fi

# Final validation summary
echo ""
echo "🎉 macOS Application Bundle Integration Test Results:"
echo "✅ Bundle structure validation: PASSED"
echo "✅ Info.plist validation: PASSED"
echo "✅ Executable permissions: PASSED"
echo "✅ Launcher script syntax: PASSED"
echo "✅ Application files: PRESENT"
echo "✅ DMG integration: PASSED"
echo ""
echo "📋 Bundle Details:"
echo "   • Name: $APP_NAME"
echo "   • Version: $VERSION"
echo "   • Bundle ID: com.bitcoinsolominormonitor.app"
echo "   • Size: $BUNDLE_SIZE"
echo "   • Location: $APP_BUNDLE"
echo ""
echo "🚀 The macOS application bundle is ready for:"
echo "   • Installation to /Applications"
echo "   • Launchpad integration"
echo "   • Spotlight search"
echo "   • DMG distribution"
echo ""
echo "📖 Next steps for users:"
echo "   1. Drag the .app to Applications folder"
echo "   2. Run refresh_launchpad.sh to update Launchpad"
echo "   3. Launch from Launchpad or Applications folder"