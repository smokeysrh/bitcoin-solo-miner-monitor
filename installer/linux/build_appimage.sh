#!/bin/bash
# Build AppImage for Bitcoin Solo Miner Monitor

APP_DIR="$1"
DIST_DIR="$2"
VERSION="$3"

if [ -z "$APP_DIR" ] || [ -z "$DIST_DIR" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <app_dir> <dist_dir> <version>"
    exit 1
fi

echo "📦 Building AppImage..."

# Configuration
APP_NAME="bitcoin-solo-miner-monitor"
DISPLAY_NAME="Bitcoin Solo Miner Monitor"
DESCRIPTION="A unified monitoring and management solution for Bitcoin mining hardware"

# Create temporary directory for AppImage packaging
TEMP_DIR=$(mktemp -d)
APPDIR="${TEMP_DIR}/BitcoinSoloMinerMonitor.AppDir"

# Create AppDir structure
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${APPDIR}/opt/${APP_NAME}"

# Copy application files
cp -r "${APP_DIR}"/* "${APPDIR}/opt/${APP_NAME}/"

# Create AppRun script
cat > "${APPDIR}/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export APPDIR="${HERE}"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"

# Change to the application directory
cd "${HERE}/opt/bitcoin-solo-miner-monitor"

# Run the application
exec python3 run.py "$@"
EOF
chmod +x "${APPDIR}/AppRun"

# Create desktop entry
cat > "${APPDIR}/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Name=${DISPLAY_NAME}
Comment=${DESCRIPTION}
Exec=AppRun
Icon=${APP_NAME}
Terminal=false
Type=Application
Categories=Utility;Network;
StartupNotify=true
EOF

# Copy desktop entry to the standard location
cp "${APPDIR}/${APP_NAME}.desktop" "${APPDIR}/usr/share/applications/"

# Copy icon (use a placeholder if not available)
if [ -f "${APP_DIR}/assets/bitcoin-symbol.png" ]; then
    cp "${APP_DIR}/assets/bitcoin-symbol.png" "${APPDIR}/${APP_NAME}.png"
    cp "${APP_DIR}/assets/bitcoin-symbol.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
else
    # Create a simple placeholder icon
    echo "Creating placeholder icon..."
    if command -v convert >/dev/null 2>&1; then
        convert -size 256x256 xc:orange -fill black -gravity center -pointsize 24 -annotate +0+0 "BTC" "${APPDIR}/${APP_NAME}.png"
        cp "${APPDIR}/${APP_NAME}.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    else
        # Create empty placeholder files
        touch "${APPDIR}/${APP_NAME}.png"
        touch "${APPDIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    fi
fi

# Download appimagetool if not available
APPIMAGETOOL="appimagetool-x86_64.AppImage"
if [ ! -f "${TEMP_DIR}/${APPIMAGETOOL}" ]; then
    echo "Downloading appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/${APPIMAGETOOL}" -O "${TEMP_DIR}/${APPIMAGETOOL}"
    chmod +x "${TEMP_DIR}/${APPIMAGETOOL}"
fi

# Build AppImage
APPIMAGE_FILE="${DIST_DIR}/BitcoinSoloMinerMonitor-${VERSION}-x86_64.AppImage"

if [ -f "${TEMP_DIR}/${APPIMAGETOOL}" ]; then
    echo "Building AppImage with appimagetool..."
    "${TEMP_DIR}/${APPIMAGETOOL}" "${APPDIR}" "${APPIMAGE_FILE}"
    
    if [ -f "${APPIMAGE_FILE}" ]; then
        chmod +x "${APPIMAGE_FILE}"
        echo "✅ AppImage created: $(basename "${APPIMAGE_FILE}")"
    else
        echo "❌ AppImage creation failed"
        exit 1
    fi
else
    echo "⚠️  appimagetool not available, creating portable archive instead..."
    # Fallback: create a portable tar.gz
    PORTABLE_FILE="${DIST_DIR}/BitcoinSoloMinerMonitor-${VERSION}-portable.tar.gz"
    tar -czf "${PORTABLE_FILE}" -C "${TEMP_DIR}" "BitcoinSoloMinerMonitor.AppDir"
    echo "✅ Portable archive created: $(basename "${PORTABLE_FILE}")"
fi

# Clean up
rm -rf "${TEMP_DIR}"