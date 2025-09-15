#!/bin/bash
# Create macOS DMG installer for Bitcoin Solo Miner Monitor

APP_DIR="$1"
DMG_PATH="$2"
VERSION="$3"

if [ -z "$APP_DIR" ] || [ -z "$DMG_PATH" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <app_dir> <dmg_path> <version>"
    exit 1
fi

echo "🍎 Creating macOS DMG installer..."

# Configuration
APP_NAME="Bitcoin Solo Miner Monitor"
VOLUME_NAME="${APP_NAME} ${VERSION}"
BACKGROUND_IMG="$(dirname "$0")/../common/assets/dmg_background.png"
ICON_FILE="$(dirname "$0")/../common/assets/app_icon.icns"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
TEMP_DMG="${TEMP_DIR}/temp.dmg"

# Create .app bundle structure
APP_BUNDLE="${TEMP_DIR}/${APP_NAME}.app"
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"

# Copy application files to the bundle
cp -r "${APP_DIR}"/* "${APP_BUNDLE}/Contents/Resources/"

# Create Info.plist
cat > "${APP_BUNDLE}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>BitcoinSoloMinerMonitor</string>
    <key>CFBundleIdentifier</key>
    <string>com.bitcoinsolominormonitor.app</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>BSMM</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
</dict>
</plist>
EOF

# Create executable launcher script
cat > "${APP_BUNDLE}/Contents/MacOS/BitcoinSoloMinerMonitor" << 'EOF'
#!/bin/bash
# Launcher script for Bitcoin Solo Miner Monitor

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${SCRIPT_DIR}/../Resources"

# Change to the application directory
cd "${APP_DIR}"

# Check if Python 3 is available
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    osascript -e 'display dialog "Python 3 is required but not installed. Please install Python 3.11 or later." buttons {"OK"} default button "OK"'
    exit 1
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    ${PYTHON_CMD} -m pip install --user -r requirements.txt >/dev/null 2>&1
fi

# Launch the application
exec ${PYTHON_CMD} run.py "$@"
EOF

chmod +x "${APP_BUNDLE}/Contents/MacOS/BitcoinSoloMinerMonitor"

# Verify the executable was created
if [ ! -x "${APP_BUNDLE}/Contents/MacOS/BitcoinSoloMinerMonitor" ]; then
    echo "❌ Failed to create executable launcher"
    exit 1
fi

# Copy icon if available
if [ -f "${ICON_FILE}" ]; then
    cp "${ICON_FILE}" "${APP_BUNDLE}/Contents/Resources/app_icon.icns"
elif [ -f "${APP_DIR}/assets/bitcoin-symbol.png" ]; then
    # Convert PNG to ICNS if sips is available
    if command -v sips >/dev/null 2>&1; then
        sips -s format icns "${APP_DIR}/assets/bitcoin-symbol.png" --out "${APP_BUNDLE}/Contents/Resources/app_icon.icns" >/dev/null 2>&1
    fi
fi

# Create temporary DMG
echo "Creating temporary DMG..."
hdiutil create -srcfolder "${TEMP_DIR}" -volname "${VOLUME_NAME}" -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" -format UDRW -size 200m "${TEMP_DMG}"

# Mount the temporary DMG
echo "Mounting temporary DMG..."
DEVICE=$(hdiutil attach -readwrite -noverify -noautoopen "${TEMP_DMG}" | \
    egrep '^/dev/' | sed 1q | awk '{print $1}')

# Wait for the mount to complete
sleep 2

# Get the volume path
VOLUME_PATH="/Volumes/${VOLUME_NAME}"

# Create symbolic link to Applications folder
echo "Creating symbolic link to /Applications..."
ln -s /Applications "${VOLUME_PATH}/Applications"

# Set up background image if available
if [ -f "${BACKGROUND_IMG}" ]; then
    echo "Setting up background image..."
    mkdir -p "${VOLUME_PATH}/.background"
    cp "${BACKGROUND_IMG}" "${VOLUME_PATH}/.background/background.png"
fi

# Configure DMG appearance using AppleScript
echo "Configuring DMG appearance..."
cat > "${TEMP_DIR}/configure_dmg.applescript" << EOF
tell application "Finder"
    tell disk "${VOLUME_NAME}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {400, 100, 900, 450}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 72
        
        -- Set background if available
        try
            set background picture of theViewOptions to file ".background:background.png"
        end try
        
        -- Position items
        set position of item "${APP_NAME}.app" of container window to {120, 180}
        set position of item "Applications" of container window to {380, 180}
        
        update without registering applications
        delay 2
        close
    end tell
end tell
EOF

# Run the AppleScript (may fail silently if GUI not available)
osascript "${TEMP_DIR}/configure_dmg.applescript" 2>/dev/null || echo "Note: DMG appearance configuration skipped (no GUI available)"

# Make sure the DMG is not busy
sync
sleep 2

# Unmount the DMG
echo "Unmounting temporary DMG..."
hdiutil detach "${DEVICE}"

# Convert the DMG to compressed format
echo "Creating final DMG..."
hdiutil convert "${TEMP_DMG}" -format UDZO -imagekey zlib-level=9 -o "${DMG_PATH}"

# Add Internet-enable flag
hdiutil internet-enable -yes "${DMG_PATH}"

# Clean up
rm -rf "${TEMP_DIR}"

echo "✅ macOS DMG created: $(basename "${DMG_PATH}")"