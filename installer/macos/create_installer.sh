#!/bin/bash
# Script to create a macOS installer for Bitcoin Solo Miner Monitor

# Configuration
APP_NAME="Bitcoin Solo Miner Monitor"
VERSION="0.1.0"
PUBLISHER="Bitcoin Solo Miner Monitor"
WEBSITE="https://github.com/bitcoin-solo-miner-monitor"
DMG_NAME="BitcoinSoloMinerMonitor-${VERSION}"
VOLUME_NAME="${APP_NAME} Installer"
SOURCE_DIR="../build/macos"
DMG_DIR="./dist"
BACKGROUND_IMG="../common/assets/dmg_background.png"
ICON_FILE="../common/assets/app_icon.icns"
DMG_TEMP="${DMG_DIR}/${DMG_NAME}-temp.dmg"
DMG_FINAL="${DMG_DIR}/${DMG_NAME}.dmg"

# Check for configuration file
CONFIG_FILE=""
if [ "$1" != "" ] && [ -f "$1" ]; then
    CONFIG_FILE="$1"
    echo "Using configuration file: $CONFIG_FILE"
fi

# Make sure directories exist
mkdir -p "${DMG_DIR}"

# Check if the application bundle exists
if [ ! -d "${SOURCE_DIR}/${APP_NAME}.app" ]; then
    echo "Error: Application bundle not found at ${SOURCE_DIR}/${APP_NAME}.app"
    exit 1
fi

# Create a temporary DMG
echo "Creating temporary DMG..."
hdiutil create -srcfolder "${SOURCE_DIR}" -volname "${VOLUME_NAME}" -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" -format UDRW -size 200m "${DMG_TEMP}"

# Mount the temporary DMG
echo "Mounting temporary DMG..."
DEVICE=$(hdiutil attach -readwrite -noverify -noautoopen "${DMG_TEMP}" | \
    egrep '^/dev/' | sed 1q | awk '{print $1}')

# Wait for the mount to complete
sleep 2

# Get the volume path
VOLUME_PATH="/Volumes/${VOLUME_NAME}"

# Create the .background directory and copy the background image
echo "Setting up background image..."
mkdir -p "${VOLUME_PATH}/.background"
cp "${BACKGROUND_IMG}" "${VOLUME_PATH}/.background/background.png"

# Create symbolic link to Applications folder
echo "Creating symbolic link to /Applications..."
ln -s /Applications "${VOLUME_PATH}/Applications"

# Set up the DMG window appearance using AppleScript
echo "Configuring DMG appearance..."
cat <<EOF > configure_dmg.applescript
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
        set background picture of theViewOptions to file ".background:background.png"
        
        -- Create position for app and Applications folder
        set position of item "${APP_NAME}.app" of container window to {120, 180}
        set position of item "Applications" of container window to {380, 180}
        
        -- Add custom icon to the volume
        set icon of disk "${VOLUME_NAME}" to file "${ICON_FILE}"
        
        update without registering applications
        delay 2
        close
    end tell
end tell
EOF

# Run the AppleScript
osascript configure_dmg.applescript

# Clean up
rm configure_dmg.applescript

# Make sure the DMG is not busy
sync

# Unmount the DMG
echo "Unmounting temporary DMG..."
hdiutil detach "${DEVICE}"

# Convert the DMG to compressed format
echo "Creating final DMG..."
hdiutil convert "${DMG_TEMP}" -format UDZO -imagekey zlib-level=9 -o "${DMG_FINAL}"

# Remove the temporary DMG
rm "${DMG_TEMP}"

# Add Internet-enable flag
hdiutil internet-enable -yes "${DMG_FINAL}"

echo "DMG created at ${DMG_FINAL}"

# Set default values
NETWORK_DISCOVERY_ENABLED=1
NETWORK_RANGE="192.168.1.0/24"
START_ON_BOOT=1
COMPONENT_DATABASE=1
COMPONENT_DASHBOARD=1
COMPONENT_ALERT=1
COMPONENT_API=1
COMPONENT_DOCS=1

# Extract values from configuration file if provided
if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    # Extract network discovery settings
    ENABLED_VALUE=$(grep -A 1 "\[NetworkDiscovery\]" "$CONFIG_FILE" | grep "Enabled" | cut -d= -f2)
    if [ -n "$ENABLED_VALUE" ]; then
        NETWORK_DISCOVERY_ENABLED=$ENABLED_VALUE
    fi
    
    RANGE_VALUE=$(grep -A 2 "\[NetworkDiscovery\]" "$CONFIG_FILE" | grep "Range" | cut -d= -f2)
    if [ -n "$RANGE_VALUE" ]; then
        NETWORK_RANGE=$RANGE_VALUE
    fi
    
    # Extract startup preference
    BOOT_VALUE=$(grep -A 3 "\[Installation\]" "$CONFIG_FILE" | grep "StartOnBoot" | cut -d= -f2)
    if [ -n "$BOOT_VALUE" ]; then
        START_ON_BOOT=$BOOT_VALUE
    fi
    
    # Extract component selections
    DB_VALUE=$(grep -A 2 "\[Components\]" "$CONFIG_FILE" | grep "Database" | cut -d= -f2)
    if [ -n "$DB_VALUE" ]; then
        COMPONENT_DATABASE=$DB_VALUE
    fi
    
    DASH_VALUE=$(grep -A 3 "\[Components\]" "$CONFIG_FILE" | grep "Dashboard" | cut -d= -f2)
    if [ -n "$DASH_VALUE" ]; then
        COMPONENT_DASHBOARD=$DASH_VALUE
    fi
    
    ALERT_VALUE=$(grep -A 4 "\[Components\]" "$CONFIG_FILE" | grep "Alert" | cut -d= -f2)
    if [ -n "$ALERT_VALUE" ]; then
        COMPONENT_ALERT=$ALERT_VALUE
    fi
    
    API_VALUE=$(grep -A 5 "\[Components\]" "$CONFIG_FILE" | grep "API" | cut -d= -f2)
    if [ -n "$API_VALUE" ]; then
        COMPONENT_API=$API_VALUE
    fi
    
    DOCS_VALUE=$(grep -A 6 "\[Components\]" "$CONFIG_FILE" | grep "Documentation" | cut -d= -f2)
    if [ -n "$DOCS_VALUE" ]; then
        COMPONENT_DOCS=$DOCS_VALUE
    fi
fi

# Create a post-installation script that will be run after the app is installed
cat <<EOF > "${SOURCE_DIR}/post_install.sh"
#!/bin/bash

# Create application support directory
mkdir -p "\${HOME}/Library/Application Support/${APP_NAME}"

# Set up LaunchAgent for auto-start if enabled
if [ ${START_ON_BOOT} -eq 1 ]; then
    mkdir -p "\${HOME}/Library/LaunchAgents"
    cat <<PLIST > "\${HOME}/Library/LaunchAgents/com.bitcoinsolominormonitor.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bitcoinsolominormonitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/${APP_NAME}.app/Contents/MacOS/BitcoinSoloMinerMonitor</string>
        <string>--minimized</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
PLIST

    # Set execute permissions
    chmod +x "\${HOME}/Library/LaunchAgents/com.bitcoinsolominormonitor.plist"
fi

# Create first run configuration
mkdir -p "/Applications/${APP_NAME}.app/Contents/Resources/config"
cat <<CONFIG > "/Applications/${APP_NAME}.app/Contents/Resources/config/first_run.ini"
[NetworkDiscovery]
Enabled=${NETWORK_DISCOVERY_ENABLED}
Range=${NETWORK_RANGE}

[Components]
Core=1
Database=${COMPONENT_DATABASE}
Dashboard=${COMPONENT_DASHBOARD}
Alert=${COMPONENT_ALERT}
API=${COMPONENT_API}
Documentation=${COMPONENT_DOCS}
CONFIG

echo "Post-installation setup completed."
EOF

# Make the post-installation script executable
chmod +x "${SOURCE_DIR}/post_install.sh"

echo "Installation package created successfully."