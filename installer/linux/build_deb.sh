#!/bin/bash
# Build DEB package for Bitcoin Solo Miner Monitor

APP_DIR="$1"
DIST_DIR="$2"
VERSION="$3"

if [ -z "$APP_DIR" ] || [ -z "$DIST_DIR" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <app_dir> <dist_dir> <version>"
    exit 1
fi

echo "🐧 Building DEB package..."

# Configuration
APP_NAME="bitcoin-solo-miner-monitor"
DISPLAY_NAME="Bitcoin Solo Miner Monitor"
MAINTAINER="bitcoin-solo-miner-monitor@example.com"
DESCRIPTION="A unified monitoring and management solution for Bitcoin mining hardware"
DEPENDS="python3 (>= 3.11), nodejs (>= 18.0)"
INSTALL_DIR="/opt/${APP_NAME}"

# Create temporary directory for DEB packaging
TEMP_DIR=$(mktemp -d)
DEB_DIR="${TEMP_DIR}/deb"

# Create directory structure
mkdir -p "${DEB_DIR}${INSTALL_DIR}"
mkdir -p "${DEB_DIR}/usr/bin"
mkdir -p "${DEB_DIR}/usr/share/applications"
mkdir -p "${DEB_DIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${DEB_DIR}/DEBIAN"

# Copy application files
cp -r "${APP_DIR}"/* "${DEB_DIR}${INSTALL_DIR}/"

# Create launcher script
cat > "${DEB_DIR}/usr/bin/${APP_NAME}" << EOF
#!/bin/bash
cd ${INSTALL_DIR}
exec python3 run.py "\$@"
EOF
chmod +x "${DEB_DIR}/usr/bin/${APP_NAME}"

# Create desktop entry
cat > "${DEB_DIR}/usr/share/applications/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Name=${DISPLAY_NAME}
Comment=${DESCRIPTION}
Exec=${APP_NAME}
Icon=${APP_NAME}
Terminal=false
Type=Application
Categories=Utility;Network;
StartupNotify=true
EOF

# Copy icon (use a placeholder if not available)
if [ -f "${APP_DIR}/assets/bitcoin-symbol.png" ]; then
    cp "${APP_DIR}/assets/bitcoin-symbol.png" "${DEB_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
else
    # Create a simple placeholder icon
    echo "Creating placeholder icon..."
    if command -v convert >/dev/null 2>&1; then
        convert -size 256x256 xc:orange -fill black -gravity center -pointsize 24 -annotate +0+0 "BTC" "${DEB_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png" 2>/dev/null
    else
        # Create empty placeholder file if ImageMagick not available
        touch "${DEB_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    fi
fi

# Create control file
cat > "${DEB_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Depends: ${DEPENDS}
Maintainer: ${MAINTAINER}
Description: ${DESCRIPTION}
 ${DISPLAY_NAME} is a unified monitoring and management solution
 for Bitcoin mining hardware, specifically targeting solo miners
 running Magic Miner, Avalon Nano, and Bitaxe devices on a local network.
 .
 Features include real-time monitoring, historical data analysis,
 and device management capabilities through an intuitive user interface.
EOF

# Create post-installation script
cat > "${DEB_DIR}/DEBIAN/postinst" << EOF
#!/bin/bash
set -e

# Create application data directory
mkdir -p "/etc/${APP_NAME}"
mkdir -p "/var/lib/${APP_NAME}"

# Set permissions
chmod 755 "${INSTALL_DIR}/run.py"

# Update desktop database
update-desktop-database -q || true

echo "${DISPLAY_NAME} installed successfully!"
echo "Run '${APP_NAME}' to start the application."
EOF
chmod 755 "${DEB_DIR}/DEBIAN/postinst"

# Create pre-removal script
cat > "${DEB_DIR}/DEBIAN/prerm" << EOF
#!/bin/bash
set -e

# Stop any running instances
pkill -f "${INSTALL_DIR}/run.py" || true

echo "${DISPLAY_NAME} stopped."
EOF
chmod 755 "${DEB_DIR}/DEBIAN/prerm"

# Calculate installed size
DEB_SIZE=$(du -s "${DEB_DIR}" | cut -f1)
echo "Installed-Size: ${DEB_SIZE}" >> "${DEB_DIR}/DEBIAN/control"

# Build the DEB package
DEB_FILE="${DIST_DIR}/${APP_NAME}_${VERSION}_amd64.deb"
dpkg-deb --build "${DEB_DIR}" "${DEB_FILE}"

# Clean up
rm -rf "${TEMP_DIR}"

echo "✅ DEB package created: $(basename "${DEB_FILE}")"