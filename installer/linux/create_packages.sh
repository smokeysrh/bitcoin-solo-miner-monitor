#!/bin/bash
# Script to create Linux packages (.deb and .rpm) for Bitcoin Solo Miner Monitor

# Configuration
APP_NAME="bitcoin-solo-miner-monitor"
DISPLAY_NAME="Bitcoin Solo Miner Monitor"
VERSION="0.1.0"
PUBLISHER="Bitcoin Solo Miner Monitor"
WEBSITE="https://github.com/bitcoin-solo-miner-monitor"
DESCRIPTION="A unified monitoring and management solution for Bitcoin mining hardware"
LICENSE="MIT"
MAINTAINER="bitcoin-solo-miner-monitor@example.com"
SECTION="utils"
DEPENDS="python3 (>= 3.11), nodejs (>= 18.0)"
INSTALL_DIR="/opt/${APP_NAME}"
SOURCE_DIR="../build/linux"
OUTPUT_DIR="./dist"

# Check for configuration file
CONFIG_FILE=""
if [ "$1" != "" ] && [ -f "$1" ]; then
    CONFIG_FILE="$1"
    echo "Using configuration file: $CONFIG_FILE"
fi

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

# Make sure directories exist
mkdir -p "${OUTPUT_DIR}"

# Check if the build directory exists
if [ ! -d "${SOURCE_DIR}" ]; then
    echo "Error: Build directory not found at ${SOURCE_DIR}"
    exit 1
fi

# Create a temporary directory for packaging
TEMP_DIR=$(mktemp -d)
echo "Created temporary directory: ${TEMP_DIR}"

# Function to clean up on exit
cleanup() {
    echo "Cleaning up..."
    rm -rf "${TEMP_DIR}"
}
trap cleanup EXIT

# Create directory structure for .deb package
mkdir -p "${TEMP_DIR}/deb/${INSTALL_DIR}"
mkdir -p "${TEMP_DIR}/deb/usr/bin"
mkdir -p "${TEMP_DIR}/deb/usr/share/applications"
mkdir -p "${TEMP_DIR}/deb/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${TEMP_DIR}/deb/DEBIAN"

# Create directory structure for .rpm package
mkdir -p "${TEMP_DIR}/rpm/SPECS"
mkdir -p "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}"
mkdir -p "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}/usr/bin"
mkdir -p "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}/usr/share/applications"
mkdir -p "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}${INSTALL_DIR}"

# Copy application files
echo "Copying application files..."
cp -r "${SOURCE_DIR}"/* "${TEMP_DIR}/deb/${INSTALL_DIR}"
cp -r "${SOURCE_DIR}"/* "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}${INSTALL_DIR}"

# Create launcher script
cat > "${TEMP_DIR}/deb/usr/bin/${APP_NAME}" << EOF
#!/bin/bash
exec ${INSTALL_DIR}/bin/bitcoin-solo-miner-monitor "\$@"
EOF
chmod +x "${TEMP_DIR}/deb/usr/bin/${APP_NAME}"

# Copy launcher script to RPM structure
cp "${TEMP_DIR}/deb/usr/bin/${APP_NAME}" "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}/usr/bin/"

# Create desktop entry
cat > "${TEMP_DIR}/deb/usr/share/applications/${APP_NAME}.desktop" << EOF
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

# Copy desktop entry to RPM structure
cp "${TEMP_DIR}/deb/usr/share/applications/${APP_NAME}.desktop" "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}/usr/share/applications/"

# Copy icon
cp "../common/assets/app_icon_256.png" "${TEMP_DIR}/deb/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
cp "../common/assets/app_icon_256.png" "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"

# Create post-installation script for .deb
cat > "${TEMP_DIR}/deb/DEBIAN/postinst" << EOF
#!/bin/bash
set -e

# Create application data directory
mkdir -p "/etc/${APP_NAME}"
mkdir -p "/var/lib/${APP_NAME}"

# Set up first run configuration
cat > "/etc/${APP_NAME}/first_run.ini" << CONFIG
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

# Set permissions
chmod 755 "${INSTALL_DIR}/bin/bitcoin-solo-miner-monitor"
chmod 644 "/etc/${APP_NAME}/first_run.ini"

# Create systemd service file
cat > "/etc/systemd/system/${APP_NAME}.service" << SERVICE
[Unit]
Description=${DISPLAY_NAME}
After=network.target

[Service]
Type=simple
User=\$(logname)
ExecStart=${INSTALL_DIR}/bin/bitcoin-solo-miner-monitor --service
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=${APP_NAME}

[Install]
WantedBy=multi-user.target
SERVICE

# Enable and start the service if configured
if [ ${START_ON_BOOT} -eq 1 ]; then
  systemctl daemon-reload
  systemctl enable ${APP_NAME}.service
  systemctl start ${APP_NAME}.service || true
else
  systemctl daemon-reload
fi

# Update desktop database
update-desktop-database -q || true
EOF
chmod 755 "${TEMP_DIR}/deb/DEBIAN/postinst"

# Create pre-removal script for .deb
cat > "${TEMP_DIR}/deb/DEBIAN/prerm" << EOF
#!/bin/bash
set -e

# Stop and disable the service
systemctl stop ${APP_NAME}.service || true
systemctl disable ${APP_NAME}.service || true

# Remove systemd service file
rm -f "/etc/systemd/system/${APP_NAME}.service"
systemctl daemon-reload
EOF
chmod 755 "${TEMP_DIR}/deb/DEBIAN/prerm"

# Create control file for .deb
cat > "${TEMP_DIR}/deb/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: ${SECTION}
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

# Create RPM spec file
cat > "${TEMP_DIR}/rpm/SPECS/${APP_NAME}.spec" << EOF
Name:           ${APP_NAME}
Version:        ${VERSION}
Release:        1%{?dist}
Summary:        ${DESCRIPTION}
License:        ${LICENSE}
URL:            ${WEBSITE}
BuildArch:      x86_64
Requires:       python3 >= 3.11, nodejs >= 18.0

%description
${DISPLAY_NAME} is a unified monitoring and management solution
for Bitcoin mining hardware, specifically targeting solo miners
running Magic Miner, Avalon Nano, and Bitaxe devices on a local network.

Features include real-time monitoring, historical data analysis,
and device management capabilities through an intuitive user interface.

%prep
%setup -q

%install
cp -r * %{buildroot}

%post
# Create application data directory
mkdir -p "/etc/${APP_NAME}"
mkdir -p "/var/lib/${APP_NAME}"

# Set up first run configuration
cat > "/etc/${APP_NAME}/first_run.ini" << CONFIG
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

# Set permissions
chmod 755 "${INSTALL_DIR}/bin/bitcoin-solo-miner-monitor"
chmod 644 "/etc/${APP_NAME}/first_run.ini"

# Create systemd service file
cat > "/etc/systemd/system/${APP_NAME}.service" << SERVICE
[Unit]
Description=${DISPLAY_NAME}
After=network.target

[Service]
Type=simple
User=\$(logname)
ExecStart=${INSTALL_DIR}/bin/bitcoin-solo-miner-monitor --service
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=${APP_NAME}

[Install]
WantedBy=multi-user.target
SERVICE

# Enable and start the service if configured
if [ ${START_ON_BOOT} -eq 1 ]; then
  systemctl daemon-reload
  systemctl enable ${APP_NAME}.service
  systemctl start ${APP_NAME}.service || true
else
  systemctl daemon-reload
fi

# Update desktop database
update-desktop-database -q || true

%preun
# Stop and disable the service
systemctl stop ${APP_NAME}.service || true
systemctl disable ${APP_NAME}.service || true

# Remove systemd service file
rm -f "/etc/systemd/system/${APP_NAME}.service"
systemctl daemon-reload

%files
%defattr(-,root,root,-)
${INSTALL_DIR}
/usr/bin/${APP_NAME}
/usr/share/applications/${APP_NAME}.desktop
/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png

%changelog
* $(date "+%a %b %d %Y") ${MAINTAINER} ${VERSION}-1
- Initial package
EOF

# Create .deb package
echo "Creating .deb package..."
DEB_SIZE=$(du -s "${TEMP_DIR}/deb" | cut -f1)
echo "Installed-Size: ${DEB_SIZE}" >> "${TEMP_DIR}/deb/DEBIAN/control"
dpkg-deb --build "${TEMP_DIR}/deb" "${OUTPUT_DIR}/${APP_NAME}_${VERSION}_amd64.deb"

# Create source tarball for RPM
echo "Creating source tarball for RPM..."
tar -czf "${TEMP_DIR}/rpm/SOURCES/${APP_NAME}-${VERSION}.tar.gz" -C "${TEMP_DIR}/rpm/SOURCES" "${APP_NAME}-${VERSION}"

# Build RPM package
echo "Creating .rpm package..."
rpmbuild --define "_topdir ${TEMP_DIR}/rpm" -ba "${TEMP_DIR}/rpm/SPECS/${APP_NAME}.spec"
cp "${TEMP_DIR}/rpm/RPMS/x86_64/${APP_NAME}-${VERSION}-1.*.rpm" "${OUTPUT_DIR}/"

echo "Packages created successfully:"
echo "  - ${OUTPUT_DIR}/${APP_NAME}_${VERSION}_amd64.deb"
echo "  - ${OUTPUT_DIR}/${APP_NAME}-${VERSION}-1.*.rpm"
