#!/bin/bash
# Build RPM package for Bitcoin Solo Miner Monitor

APP_DIR="$1"
DIST_DIR="$2"
VERSION="$3"

if [ -z "$APP_DIR" ] || [ -z "$DIST_DIR" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <app_dir> <dist_dir> <version>"
    exit 1
fi

echo "🔴 Building RPM package..."

# Configuration
APP_NAME="bitcoin-solo-miner-monitor"
DISPLAY_NAME="Bitcoin Solo Miner Monitor"
MAINTAINER="bitcoin-solo-miner-monitor@example.com"
DESCRIPTION="A unified monitoring and management solution for Bitcoin mining hardware"
LICENSE="MIT"
WEBSITE="https://github.com/bitcoin-solo-miner-monitor"
REQUIRES="python3 >= 3.11, nodejs >= 18.0"
INSTALL_DIR="/opt/${APP_NAME}"

# Create temporary directory for RPM packaging
TEMP_DIR=$(mktemp -d)
RPM_DIR="${TEMP_DIR}/rpm"

# Create RPM build directory structure
mkdir -p "${RPM_DIR}/SPECS"
mkdir -p "${RPM_DIR}/SOURCES"
mkdir -p "${RPM_DIR}/BUILD"
mkdir -p "${RPM_DIR}/RPMS"
mkdir -p "${RPM_DIR}/SRPMS"

# Create source directory
SOURCE_DIR="${RPM_DIR}/SOURCES/${APP_NAME}-${VERSION}"
mkdir -p "${SOURCE_DIR}${INSTALL_DIR}"
mkdir -p "${SOURCE_DIR}/usr/bin"
mkdir -p "${SOURCE_DIR}/usr/share/applications"
mkdir -p "${SOURCE_DIR}/usr/share/icons/hicolor/256x256/apps"

# Copy application files
cp -r "${APP_DIR}"/* "${SOURCE_DIR}${INSTALL_DIR}/"

# Create launcher script
cat > "${SOURCE_DIR}/usr/bin/${APP_NAME}" << EOF
#!/bin/bash
cd ${INSTALL_DIR}
exec python3 run.py "\$@"
EOF
chmod +x "${SOURCE_DIR}/usr/bin/${APP_NAME}"

# Create desktop entry
cat > "${SOURCE_DIR}/usr/share/applications/${APP_NAME}.desktop" << EOF
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
    cp "${APP_DIR}/assets/bitcoin-symbol.png" "${SOURCE_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
else
    # Create a simple placeholder icon
    echo "Creating placeholder icon..."
    if command -v convert >/dev/null 2>&1; then
        convert -size 256x256 xc:orange -fill black -gravity center -pointsize 24 -annotate +0+0 "BTC" "${SOURCE_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png" 2>/dev/null
    else
        # Create empty placeholder file if ImageMagick not available
        touch "${SOURCE_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    fi
fi

# Create source tarball
cd "${RPM_DIR}/SOURCES"
tar -czf "${APP_NAME}-${VERSION}.tar.gz" "${APP_NAME}-${VERSION}"
cd - > /dev/null

# Create RPM spec file
cat > "${RPM_DIR}/SPECS/${APP_NAME}.spec" << EOF
Name:           ${APP_NAME}
Version:        ${VERSION}
Release:        1%{?dist}
Summary:        ${DESCRIPTION}
License:        ${LICENSE}
URL:            ${WEBSITE}
Source0:        %{name}-%{version}.tar.gz
BuildArch:      x86_64
Requires:       ${REQUIRES}

%description
${DISPLAY_NAME} is a unified monitoring and management solution
for Bitcoin mining hardware, specifically targeting solo miners
running Magic Miner, Avalon Nano, and Bitaxe devices on a local network.

Features include real-time monitoring, historical data analysis,
and device management capabilities through an intuitive user interface.

%prep
%setup -q

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}
cp -r * %{buildroot}/

%post
# Create application data directory
mkdir -p "/etc/${APP_NAME}"
mkdir -p "/var/lib/${APP_NAME}"

# Set permissions
chmod 755 "${INSTALL_DIR}/run.py"

# Update desktop database
update-desktop-database -q || true

echo "${DISPLAY_NAME} installed successfully!"
echo "Run '${APP_NAME}' to start the application."

%preun
# Stop any running instances
pkill -f "${INSTALL_DIR}/run.py" || true

%files
%defattr(-,root,root,-)
${INSTALL_DIR}
/usr/bin/${APP_NAME}
/usr/share/applications/${APP_NAME}.desktop
/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png

%changelog
* $(date "+%a %b %d %Y") ${MAINTAINER} ${VERSION}-1
- Initial package release
EOF

# Build RPM package
rpmbuild --define "_topdir ${RPM_DIR}" -ba "${RPM_DIR}/SPECS/${APP_NAME}.spec"

# Copy the built RPM to the distribution directory
RPM_FILE=$(find "${RPM_DIR}/RPMS" -name "*.rpm" | head -1)
if [ -n "$RPM_FILE" ]; then
    cp "$RPM_FILE" "${DIST_DIR}/"
    echo "✅ RPM package created: $(basename "$RPM_FILE")"
else
    echo "❌ RPM package creation failed"
    exit 1
fi

# Clean up
rm -rf "${TEMP_DIR}"