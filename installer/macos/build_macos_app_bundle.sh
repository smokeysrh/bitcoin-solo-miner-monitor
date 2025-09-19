#!/bin/bash
# Build macOS Application Bundle for Bitcoin Solo Miner Monitor
# This script creates a proper .app bundle with all dependencies and integrations

set -e  # Exit on any error

# Parse command line arguments
VERSION="${1:-0.1.0}"
OUTPUT_DIR="${2:-../../dist}"
APP_NAME="${3:-Bitcoin Solo Miner Monitor}"

echo "🍎 Building macOS Application Bundle"
echo "Version: $VERSION"
echo "Output: $OUTPUT_DIR"
echo "App Name: $APP_NAME"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Create output directory
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"  # Get absolute path

echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Output directory: $OUTPUT_DIR"

# Build frontend first
echo "🔨 Building frontend..."
cd "$PROJECT_ROOT"

if [ -d "src/frontend" ]; then
    cd "src/frontend"
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing frontend dependencies..."
        npm install
    fi
    
    # Build the frontend
    echo "🏗️  Building frontend..."
    npm run build
    
    cd "$PROJECT_ROOT"
else
    echo "⚠️  Frontend directory not found, skipping frontend build"
fi

# Create temporary build directory
TEMP_BUILD_DIR=$(mktemp -d)
echo "🔧 Using temporary build directory: $TEMP_BUILD_DIR"

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up temporary files..."
    rm -rf "$TEMP_BUILD_DIR"
}
trap cleanup EXIT

# Copy application files to temporary directory
echo "📋 Preparing application files..."
cp -r "$PROJECT_ROOT"/* "$TEMP_BUILD_DIR/" 2>/dev/null || true

# Remove unnecessary files from the build
echo "🗑️  Removing unnecessary files..."
cd "$TEMP_BUILD_DIR"

# Remove development and build artifacts
rm -rf .git .github .pytest_cache __pycache__ node_modules .vscode
rm -rf src/frontend/node_modules src/frontend/dist
rm -rf tests testing debug logs
rm -rf installer distribution verification
rm -rf .gitignore *.md tools/build/build-reproducible.sh

# Remove Python cache files
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create the app bundle using our Python script
echo "📦 Creating macOS application bundle..."
cd "$SCRIPT_DIR"

python3 bundle/create_app_bundle.py \
    --output "$OUTPUT_DIR" \
    --version "$VERSION" \
    --name "$APP_NAME"

APP_BUNDLE="$OUTPUT_DIR/$APP_NAME.app"

# Verify the bundle was created
if [ ! -d "$APP_BUNDLE" ]; then
    echo "❌ Failed to create app bundle"
    exit 1
fi

# Set proper permissions
echo "🔐 Setting proper permissions..."
find "$APP_BUNDLE" -type f -name "*.py" -exec chmod 644 {} \;
find "$APP_BUNDLE" -type f -name "*.sh" -exec chmod 755 {} \;
chmod 755 "$APP_BUNDLE/Contents/MacOS/"*

# Create additional integration files
echo "🔗 Creating additional integration files..."

# Create a simple installer script for users
cat > "$OUTPUT_DIR/Install $APP_NAME.sh" << EOF
#!/bin/bash
# Simple installer script for $APP_NAME

APP_BUNDLE="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)/$APP_NAME.app"
APPLICATIONS_DIR="/Applications"

echo "🍎 Installing $APP_NAME..."

if [ ! -d "\$APP_BUNDLE" ]; then
    echo "❌ App bundle not found: \$APP_BUNDLE"
    exit 1
fi

# Check if Applications directory is writable
if [ ! -w "\$APPLICATIONS_DIR" ]; then
    echo "🔐 Administrator privileges required to install to Applications folder"
    echo "Please enter your password when prompted:"
    sudo cp -R "\$APP_BUNDLE" "\$APPLICATIONS_DIR/"
else
    cp -R "\$APP_BUNDLE" "\$APPLICATIONS_DIR/"
fi

if [ -d "\$APPLICATIONS_DIR/$APP_NAME.app" ]; then
    echo "✅ $APP_NAME installed successfully!"
    echo "📱 The app will appear in Launchpad and Applications folder"
    
    # Refresh Launchpad
    echo "🔄 Refreshing Launchpad..."
    killall Dock 2>/dev/null || true
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user 2>/dev/null || true
    
    echo "🚀 You can now launch $APP_NAME from Launchpad or Applications folder"
else
    echo "❌ Installation failed"
    exit 1
fi
EOF

chmod +x "$OUTPUT_DIR/Install $APP_NAME.sh"

# Create uninstaller script
cat > "$OUTPUT_DIR/Uninstall $APP_NAME.sh" << EOF
#!/bin/bash
# Uninstaller script for $APP_NAME

APPLICATIONS_DIR="/Applications"
APP_PATH="\$APPLICATIONS_DIR/$APP_NAME.app"

echo "🗑️  Uninstalling $APP_NAME..."

if [ ! -d "\$APP_PATH" ]; then
    echo "⚠️  $APP_NAME is not installed in Applications folder"
    exit 1
fi

# Check if Applications directory is writable
if [ ! -w "\$APPLICATIONS_DIR" ]; then
    echo "🔐 Administrator privileges required to uninstall from Applications folder"
    echo "Please enter your password when prompted:"
    sudo rm -rf "\$APP_PATH"
else
    rm -rf "\$APP_PATH"
fi

if [ ! -d "\$APP_PATH" ]; then
    echo "✅ $APP_NAME uninstalled successfully!"
    
    # Refresh Launchpad
    echo "🔄 Refreshing Launchpad..."
    killall Dock 2>/dev/null || true
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user 2>/dev/null || true
else
    echo "❌ Uninstallation failed"
    exit 1
fi
EOF

chmod +x "$OUTPUT_DIR/Uninstall $APP_NAME.sh"

# Create README for the bundle
cat > "$OUTPUT_DIR/README.txt" << EOF
$APP_NAME - macOS Application Bundle

INSTALLATION:
1. Double-click "Install $APP_NAME.sh" for automatic installation
   OR
2. Drag "$APP_NAME.app" to your Applications folder manually

SYSTEM REQUIREMENTS:
- macOS 10.15 (Catalina) or later
- Python 3.11+ (will be installed automatically if needed)
- 2 GB RAM minimum
- 5 GB free disk space

FIRST RUN:
- The application may take a moment to start on first launch
- Python dependencies will be installed automatically if needed
- You may see security warnings - this is normal for open-source software

SECURITY NOTES:
- This is open-source software without expensive code signing certificates
- If you see "unidentified developer" warnings:
  1. Right-click the app and select "Open"
  2. Or go to System Preferences > Security & Privacy and click "Open Anyway"

UNINSTALLATION:
- Double-click "Uninstall $APP_NAME.sh"
- Or simply drag the app from Applications to Trash

SUPPORT:
- Documentation: https://github.com/smokeysrh/bitcoin-solo-miner-monitor
- Issues: https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues

The application will appear in:
- Applications folder
- Launchpad
- Spotlight search
EOF

# Generate checksums
echo "🔐 Generating checksums..."
cd "$OUTPUT_DIR"
shasum -a 256 "$APP_NAME.app/Contents/MacOS/"* > "$APP_NAME-checksums.sha256" 2>/dev/null || true
shasum -a 256 "Install $APP_NAME.sh" >> "$APP_NAME-checksums.sha256"
shasum -a 256 "Uninstall $APP_NAME.sh" >> "$APP_NAME-checksums.sha256"

# Display final information
APP_SIZE=$(du -sh "$APP_BUNDLE" | cut -f1)
echo ""
echo "✅ macOS application bundle created successfully!"
echo "📁 Location: $APP_BUNDLE"
echo "📏 Size: $APP_SIZE"
echo ""
echo "📋 Bundle contents:"
echo "   • $APP_NAME.app - Main application bundle"
echo "   • Install $APP_NAME.sh - Automatic installer"
echo "   • Uninstall $APP_NAME.sh - Automatic uninstaller"
echo "   • README.txt - Installation instructions"
echo "   • $APP_NAME-checksums.sha256 - Security checksums"
echo ""
echo "🧪 Testing the bundle:"
echo "   1. Test launch: open '$APP_BUNDLE'"
echo "   2. Test install: ./\"Install $APP_NAME.sh\""
echo "   3. Check Launchpad for the app icon"
echo ""
echo "🚀 The application bundle includes:"
echo "   • Complete Python runtime support"
echo "   • Automatic dependency installation"
echo "   • Proper macOS integration (Launchpad, Applications folder)"
echo "   • Professional app metadata and icon"
echo "   • Security guidance for open-source software"