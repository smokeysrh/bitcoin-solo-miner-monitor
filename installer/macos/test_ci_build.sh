#!/bin/bash
# Test script for macOS CI/CD build validation
# This script validates that all macOS build components are working correctly

set -e

echo "🧪 Testing macOS CI/CD build system..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Test configuration
TEST_VERSION="test-0.1.0"
TEST_OUTPUT_DIR="${PROJECT_ROOT}/test_build_output"
TEST_DMG_NAME="BitcoinSoloMinerMonitor-${TEST_VERSION}.dmg"

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up test files..."
    rm -rf "$TEST_OUTPUT_DIR" 2>/dev/null || true
    # Unmount any test DMGs
    hdiutil detach "/tmp/test_mount_"* 2>/dev/null || true
}
trap cleanup EXIT

echo "📁 Project root: $PROJECT_ROOT"
echo "🔧 Test output directory: $TEST_OUTPUT_DIR"

# Create test output directory
mkdir -p "$TEST_OUTPUT_DIR"

# Test 1: Validate required tools are available
echo ""
echo "🔍 Test 1: Checking required macOS build tools..."

required_tools=("hdiutil" "sips" "plutil" "codesign" "shasum" "python3")
for tool in "${required_tools[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✅ $tool: $(which $tool)"
    else
        echo "❌ $tool: not found"
        exit 1
    fi
done

# Test 2: Validate Python environment
echo ""
echo "🐍 Test 2: Checking Python environment..."

python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo "✅ Python version: $python_version"

if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "✅ Python version meets minimum requirement (3.11+)"
else
    echo "❌ Python version too old (requires 3.11+)"
    exit 1
fi

# Test pip availability
if python3 -m pip --version >/dev/null 2>&1; then
    echo "✅ pip is available"
else
    echo "❌ pip is not available"
    exit 1
fi

# Test 3: Validate project structure
echo ""
echo "📂 Test 3: Checking project structure..."

required_files=(
    "run.py"
    "requirements.txt"
    "src"
    "config"
    "installer/macos/create_dmg.sh"
    "installer/macos/bundle/create_app_bundle.py"
    "scripts/create-distribution.py"
)

for file in "${required_files[@]}"; do
    if [ -e "$PROJECT_ROOT/$file" ]; then
        echo "✅ Found: $file"
    else
        echo "❌ Missing: $file"
        exit 1
    fi
done

# Test 4: Test app bundle creation
echo ""
echo "📦 Test 4: Testing app bundle creation..."

cd "$SCRIPT_DIR"
if python3 bundle/create_app_bundle.py --output "$TEST_OUTPUT_DIR" --version "$TEST_VERSION" --name "Bitcoin Solo Miner Monitor"; then
    echo "✅ App bundle creation successful"
else
    echo "❌ App bundle creation failed"
    exit 1
fi

# Verify app bundle was created
app_bundle="$TEST_OUTPUT_DIR/Bitcoin Solo Miner Monitor.app"
if [ -d "$app_bundle" ]; then
    echo "✅ App bundle exists: $app_bundle"
else
    echo "❌ App bundle not created"
    exit 1
fi

# Test 5: Validate app bundle structure
echo ""
echo "🔍 Test 5: Validating app bundle structure..."

bundle_files=(
    "Contents/Info.plist"
    "Contents/MacOS/BitcoinSoloMinerMonitor"
    "Contents/Resources/run.py"
    "Contents/Resources/requirements.txt"
)

for file in "${bundle_files[@]}"; do
    if [ -e "$app_bundle/$file" ]; then
        echo "✅ Bundle file exists: $file"
    else
        echo "❌ Bundle file missing: $file"
        exit 1
    fi
done

# Check executable permissions
if [ -x "$app_bundle/Contents/MacOS/BitcoinSoloMinerMonitor" ]; then
    echo "✅ Main executable has correct permissions"
else
    echo "❌ Main executable is not executable"
    exit 1
fi

# Test Info.plist validity
if plutil -lint "$app_bundle/Contents/Info.plist" >/dev/null 2>&1; then
    echo "✅ Info.plist is valid"
else
    echo "❌ Info.plist is invalid"
    exit 1
fi

# Test 6: Test DMG creation
echo ""
echo "💾 Test 6: Testing DMG creation..."

dmg_path="$TEST_OUTPUT_DIR/$TEST_DMG_NAME"
if bash "$SCRIPT_DIR/create_dmg.sh" "$TEST_OUTPUT_DIR" "$dmg_path" "$TEST_VERSION"; then
    echo "✅ DMG creation successful"
else
    echo "❌ DMG creation failed"
    exit 1
fi

# Verify DMG was created
if [ -f "$dmg_path" ]; then
    echo "✅ DMG file exists: $dmg_path"
    dmg_size=$(stat -f%z "$dmg_path" 2>/dev/null || echo "0")
    echo "📏 DMG size: $dmg_size bytes"
else
    echo "❌ DMG file not created"
    exit 1
fi

# Test 7: Test DMG integrity and contents
echo ""
echo "🔍 Test 7: Testing DMG integrity and contents..."

# Verify DMG integrity
if hdiutil verify "$dmg_path" >/dev/null 2>&1; then
    echo "✅ DMG integrity check passed"
else
    echo "❌ DMG integrity check failed"
    exit 1
fi

# Mount DMG and check contents
test_mount_point="/tmp/test_mount_$(date +%s)"
if hdiutil attach "$dmg_path" -mountpoint "$test_mount_point" -readonly -nobrowse >/dev/null 2>&1; then
    echo "✅ DMG mounted successfully"
else
    echo "❌ Failed to mount DMG"
    exit 1
fi

# Check DMG contents
dmg_contents=(
    "Bitcoin Solo Miner Monitor.app"
    "Applications"
    "Installation Instructions.txt"
)

for item in "${dmg_contents[@]}"; do
    if [ -e "$test_mount_point/$item" ]; then
        echo "✅ DMG contains: $item"
    else
        echo "❌ DMG missing: $item"
        hdiutil detach "$test_mount_point" || true
        exit 1
    fi
done

# Verify Applications symlink
if [ -L "$test_mount_point/Applications" ] && [ "$(readlink "$test_mount_point/Applications")" = "/Applications" ]; then
    echo "✅ Applications symlink is correct"
else
    echo "❌ Applications symlink is incorrect"
    hdiutil detach "$test_mount_point" || true
    exit 1
fi

# Unmount DMG
if hdiutil detach "$test_mount_point" >/dev/null 2>&1; then
    echo "✅ DMG unmounted successfully"
else
    echo "⚠️  Warning: Could not unmount DMG cleanly"
    hdiutil detach "$test_mount_point" -force >/dev/null 2>&1 || true
fi

# Test 8: Test checksum generation
echo ""
echo "🔐 Test 8: Testing checksum generation..."

cd "$TEST_OUTPUT_DIR"
if shasum -a 256 "$TEST_DMG_NAME" > SHA256SUMS; then
    echo "✅ SHA256 checksum generated"
else
    echo "❌ Failed to generate SHA256 checksum"
    exit 1
fi

# Verify checksum
if shasum -a 256 -c SHA256SUMS >/dev/null 2>&1; then
    echo "✅ Checksum verification passed"
else
    echo "❌ Checksum verification failed"
    exit 1
fi

# Test 9: Test distribution script integration
echo ""
echo "🚀 Test 9: Testing distribution script integration..."

cd "$PROJECT_ROOT"
if python3 scripts/create-distribution.py --platform macos --version "$TEST_VERSION" >/dev/null 2>&1; then
    echo "✅ Distribution script integration successful"
else
    echo "❌ Distribution script integration failed"
    exit 1
fi

# Check if distribution created files
if [ -d "distribution/macos" ] && [ -n "$(ls -A distribution/macos 2>/dev/null)" ]; then
    echo "✅ Distribution files created"
    echo "📋 Distribution contents:"
    ls -la distribution/macos/
else
    echo "❌ No distribution files created"
    exit 1
fi

# Final summary
echo ""
echo "🎉 All macOS CI/CD build tests passed successfully!"
echo ""
echo "📊 Test Summary:"
echo "✅ Required tools available"
echo "✅ Python environment valid"
echo "✅ Project structure complete"
echo "✅ App bundle creation working"
echo "✅ App bundle structure valid"
echo "✅ DMG creation working"
echo "✅ DMG integrity and contents valid"
echo "✅ Checksum generation working"
echo "✅ Distribution script integration working"
echo ""
echo "🚀 macOS build system is ready for CI/CD deployment!"