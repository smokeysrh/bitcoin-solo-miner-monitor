#!/bin/bash
# Enhanced Linux Package Build System for Bitcoin Solo Miner Monitor
# This script creates DEB, RPM, and AppImage packages with automated dependency resolution

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_DIR="${PROJECT_ROOT}/distribution"
TEMPLATES_DIR="${SCRIPT_DIR}/templates"

# Load configuration from common installer config
CONFIG_FILE="${PROJECT_ROOT}/installer/common/installer_config.json"

# Default values (will be overridden by config file)
APP_NAME="bitcoin-solo-miner-monitor"
DISPLAY_NAME="Bitcoin Solo Miner Monitor"
VERSION="1.0.0"
DESCRIPTION="A unified monitoring and management solution for Bitcoin mining hardware"
MAINTAINER="bitcoin-solo-miner-monitor@example.com"
WEBSITE="https://github.com/smokeysrh/bitcoin-solo-miner-monitor"
LICENSE="MIT"

# Parse command line arguments
PACKAGE_TYPES="all"
VERBOSE=false
CLEAN_BUILD=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -t, --type TYPE     Package type to build (deb, rpm, appimage, all) [default: all]"
    echo "  -v, --verbose       Enable verbose output"
    echo "  -c, --clean         Clean build directory before building"
    echo "  -h, --help          Show this help message"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            PACKAGE_TYPES="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Logging functions
log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_error() {
    echo "❌ $1" >&2
}

log_warning() {
    echo "⚠️  $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo "🔍 $1"
    fi
}

# Load configuration from JSON file
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        log_verbose "Loading configuration from $CONFIG_FILE"
        
        # Extract values using Python (more reliable than jq for complex JSON)
        if command -v python3 >/dev/null 2>&1; then
            eval $(python3 -c "
import json
import sys

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    
    print(f'DISPLAY_NAME=\"{config.get(\"app_name\", \"$DISPLAY_NAME\")}\"')
    print(f'VERSION=\"{config.get(\"version\", \"$VERSION\")}\"')
    print(f'DESCRIPTION=\"{config.get(\"description\", \"$DESCRIPTION\")}\"')
    print(f'WEBSITE=\"{config.get(\"website\", \"$WEBSITE\")}\"')
    
    # Extract Linux-specific settings
    linux_config = config.get('min_system_requirements', {}).get('linux', {})
    deps = config.get('dependencies', {})
    
    python_version = deps.get('python', '>=3.11.0').replace('>=', '')
    nodejs_version = deps.get('nodejs', '>=18.0.0').replace('>=', '')
    
    print(f'PYTHON_MIN_VERSION=\"{python_version}\"')
    print(f'NODEJS_MIN_VERSION=\"{nodejs_version}\"')
    
except Exception as e:
    print(f'# Error loading config: {e}', file=sys.stderr)
")
        else
            log_warning "Python3 not available, using default configuration values"
        fi
    else
        log_warning "Configuration file not found at $CONFIG_FILE, using defaults"
    fi
}

# Validate build environment
validate_environment() {
    log_info "Validating build environment..."
    
    # Check for required tools
    local missing_tools=()
    
    # Check for DEB building tools
    if [[ "$PACKAGE_TYPES" == "all" || "$PACKAGE_TYPES" == "deb" ]]; then
        if ! command -v dpkg-deb >/dev/null 2>&1; then
            missing_tools+=("dpkg-deb (install with: apt-get install dpkg-dev)")
        fi
    fi
    
    # Check for RPM building tools
    if [[ "$PACKAGE_TYPES" == "all" || "$PACKAGE_TYPES" == "rpm" ]]; then
        if ! command -v rpmbuild >/dev/null 2>&1; then
            missing_tools+=("rpmbuild (install with: apt-get install rpm or yum install rpm-build)")
        fi
    fi
    
    # Check for AppImage building tools
    if [[ "$PACKAGE_TYPES" == "all" || "$PACKAGE_TYPES" == "appimage" ]]; then
        if ! command -v wget >/dev/null 2>&1; then
            missing_tools+=("wget")
        fi
    fi
    
    # Check for Python and Node.js
    if ! command -v python3 >/dev/null 2>&1; then
        missing_tools+=("python3")
    fi
    
    if ! command -v node >/dev/null 2>&1; then
        missing_tools+=("nodejs")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Missing required tools:"
        for tool in "${missing_tools[@]}"; do
            log_error "  - $tool"
        done
        exit 1
    fi
    
    log_success "Build environment validation passed"
}

# Prepare application build
prepare_build() {
    log_info "Preparing application build..."
    
    # Clean build directory if requested
    if [ "$CLEAN_BUILD" = true ]; then
        log_verbose "Cleaning build directory"
        rm -rf "$BUILD_DIR"
    fi
    
    # Create build directories
    mkdir -p "$BUILD_DIR/linux"
    mkdir -p "$DIST_DIR"
    
    # Build frontend
    log_info "Building frontend..."
    cd "$PROJECT_ROOT/src/frontend"
    if [ -f "package.json" ]; then
        npm install
        npm run build
        log_success "Frontend build completed"
    else
        log_warning "No frontend package.json found, skipping frontend build"
    fi
    
    # Copy application files to build directory
    log_info "Copying application files..."
    cd "$PROJECT_ROOT"
    
    # Copy Python backend
    cp -r src "$BUILD_DIR/linux/"
    cp -r config "$BUILD_DIR/linux/"
    cp run.py "$BUILD_DIR/linux/"
    cp requirements.txt "$BUILD_DIR/linux/"
    
    # Copy assets
    if [ -d "assets" ]; then
        cp -r assets "$BUILD_DIR/linux/"
    fi
    
    # Copy documentation
    if [ -f "README.md" ]; then
        cp README.md "$BUILD_DIR/linux/"
    fi
    
    log_success "Application build prepared"
}

# Create desktop entry file using comprehensive desktop integration
create_desktop_entry() {
    local desktop_file="$1"
    
    log_verbose "Creating comprehensive desktop entry: $desktop_file"
    
    # Use the template if available
    if [ -f "$TEMPLATES_DIR/bitcoin-solo-miner-monitor.desktop" ]; then
        log_verbose "Using desktop entry template"
        cp "$TEMPLATES_DIR/bitcoin-solo-miner-monitor.desktop" "$desktop_file"
    else
        # Use the comprehensive desktop integration script to create the desktop entry
        local temp_desktop_script="$SCRIPT_DIR/desktop_integration.sh"
        if [ -f "$temp_desktop_script" ]; then
            # Create a temporary directory for the desktop integration
            local temp_dir=$(mktemp -d)
            local temp_home="$temp_dir/home"
            mkdir -p "$temp_home/.local/share/applications"
            
            # Run desktop integration in the temporary environment
            HOME="$temp_home" "$temp_desktop_script" --user-local --mime-types --actions --dry-run >/dev/null 2>&1 || true
            
            # Copy the generated desktop file if it exists
            local generated_file="$temp_home/.local/share/applications/$APP_NAME.desktop"
            if [ -f "$generated_file" ]; then
                cp "$generated_file" "$desktop_file"
            else
                # Fallback to basic desktop entry
                create_basic_desktop_entry "$desktop_file"
            fi
            
            # Clean up temporary directory
            rm -rf "$temp_dir"
        else
            # Fallback if desktop integration script is not available
            log_warning "Desktop integration script not found, using basic desktop entry"
            create_basic_desktop_entry "$desktop_file"
        fi
    fi
}

# Create basic desktop entry as fallback
create_basic_desktop_entry() {
    local desktop_file="$1"
    
    cat > "$desktop_file" << EOF
[Desktop Entry]
Name=$DISPLAY_NAME
GenericName=Mining Monitor
Comment=$DESCRIPTION
Keywords=bitcoin;mining;monitor;cryptocurrency;solo;miner;hardware;network;blockchain;asic
Exec=$APP_NAME %F
Icon=$APP_NAME
Terminal=false
Type=Application
Categories=Utility;Network;System;Monitor;HardwareSettings
StartupNotify=true
StartupWMClass=bitcoin-solo-miner-monitor
MimeType=application/x-bitcoin-miner-config;application/x-mining-pool-config;

# Multi-language support
Name[es]=Monitor de Minería Bitcoin Solo
GenericName[es]=Monitor de Minería
Comment[es]=Monitorear y gestionar hardware de minería Bitcoin en su red local
Name[fr]=Moniteur de Minage Bitcoin Solo
GenericName[fr]=Moniteur de Minage
Comment[fr]=Surveiller et gérer le matériel de minage Bitcoin sur votre réseau local
Name[de]=Bitcoin Solo Mining Monitor
GenericName[de]=Mining Monitor
Comment[de]=Bitcoin-Mining-Hardware in Ihrem lokalen Netzwerk überwachen und verwalten
Name[zh_CN]=比特币独立挖矿监控器
GenericName[zh_CN]=挖矿监控器
Comment[zh_CN]=监控和管理本地网络上的比特币挖矿硬件

# Desktop actions
Actions=StartService;StopService;ViewLogs;OpenConfig;CheckStatus;

[Desktop Action StartService]
Name=Start Mining Monitor Service
Name[es]=Iniciar Servicio de Monitor de Minería
Name[fr]=Démarrer le Service de Moniteur de Minage
Name[de]=Mining Monitor Service starten
Name[zh_CN]=启动挖矿监控服务
Exec=systemctl --user start bitcoin-solo-miner-monitor@%u.service
Icon=media-playback-start

[Desktop Action StopService]
Name=Stop Mining Monitor Service
Name[es]=Detener Servicio de Monitor de Minería
Name[fr]=Arrêter le Service de Moniteur de Minage
Name[de]=Mining Monitor Service stoppen
Name[zh_CN]=停止挖矿监控服务
Exec=systemctl --user stop bitcoin-solo-miner-monitor@%u.service
Icon=media-playback-stop

[Desktop Action ViewLogs]
Name=View Application Logs
Name[es]=Ver Registros de Aplicación
Name[fr]=Voir les Journaux d'Application
Name[de]=Anwendungsprotokolle anzeigen
Name[zh_CN]=查看应用程序日志
Exec=journalctl --user -u bitcoin-solo-miner-monitor@%u.service -f
Icon=utilities-log-viewer
Terminal=true

[Desktop Action OpenConfig]
Name=Open Configuration
Name[es]=Abrir Configuración
Name[fr]=Ouvrir la Configuration
Name[de]=Konfiguration öffnen
Name[zh_CN]=打开配置
Exec=$APP_NAME --config
Icon=preferences-system

[Desktop Action CheckStatus]
Name=Check Service Status
Name[es]=Verificar Estado del Servicio
Name[fr]=Vérifier l'État du Service
Name[de]=Service-Status prüfen
Name[zh_CN]=检查服务状态
Exec=systemctl --user status bitcoin-solo-miner-monitor@%u.service
Icon=dialog-information
Terminal=true
EOF
}

# Create systemd service file template
create_systemd_service() {
    local service_file="$1"
    
    log_verbose "Creating systemd service: $service_file"
    
    # Use the template if available
    if [ -f "$TEMPLATES_DIR/bitcoin-solo-miner-monitor@.service" ]; then
        log_verbose "Using systemd service template"
        cp "$TEMPLATES_DIR/bitcoin-solo-miner-monitor@.service" "$service_file"
    else
        # Create basic service file
        cat > "$service_file" << EOF
[Unit]
Description=$DISPLAY_NAME
Documentation=$WEBSITE
After=network.target
Wants=network.target

[Service]
Type=simple
User=%i
Group=%i
WorkingDirectory=/opt/$APP_NAME
ExecStart=/usr/bin/python3 /opt/$APP_NAME/run.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$APP_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/$APP_NAME /etc/$APP_NAME

[Install]
WantedBy=multi-user.target
EOF
    fi
}

# Build DEB package
build_deb() {
    log_info "Building DEB package..."
    
    local temp_dir=$(mktemp -d)
    local deb_dir="$temp_dir/deb"
    local install_dir="/opt/$APP_NAME"
    
    # Create directory structure
    mkdir -p "$deb_dir$install_dir"
    mkdir -p "$deb_dir/usr/bin"
    mkdir -p "$deb_dir/usr/share/applications"
    mkdir -p "$deb_dir/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$deb_dir/usr/lib/systemd/user"
    mkdir -p "$deb_dir/DEBIAN"
    
    # Copy application files
    cp -r "$BUILD_DIR/linux"/* "$deb_dir$install_dir/"
    
    # Create launcher script
    cat > "$deb_dir/usr/bin/$APP_NAME" << EOF
#!/bin/bash
cd $install_dir
exec python3 run.py "\$@"
EOF
    chmod +x "$deb_dir/usr/bin/$APP_NAME"
    
    # Create desktop entry
    create_desktop_entry "$deb_dir/usr/share/applications/$APP_NAME.desktop"
    
    # Copy icon
    if [ -f "$PROJECT_ROOT/installer/common/assets/app_icon_256.png" ]; then
        cp "$PROJECT_ROOT/installer/common/assets/app_icon_256.png" "$deb_dir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    elif [ -f "$PROJECT_ROOT/assets/bitcoin-symbol.png" ]; then
        cp "$PROJECT_ROOT/assets/bitcoin-symbol.png" "$deb_dir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    else
        log_warning "No icon found, creating placeholder"
        # Create a simple placeholder
        echo "PNG placeholder" > "$deb_dir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    fi
    
    # Create systemd service
    create_systemd_service "$deb_dir/usr/lib/systemd/user/$APP_NAME@.service"
    
    # Create control file
    cat > "$deb_dir/DEBIAN/control" << EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: python3 (>= ${PYTHON_MIN_VERSION:-3.11}), python3-pip, nodejs (>= ${NODEJS_MIN_VERSION:-18.0})
Recommends: python3-venv
Maintainer: $MAINTAINER
Description: $DESCRIPTION
 $DISPLAY_NAME is a unified monitoring and management solution
 for Bitcoin mining hardware, specifically targeting solo miners
 running Magic Miner, Avalon Nano, and Bitaxe devices on a local network.
 .
 Features include real-time monitoring, historical data analysis,
 and device management capabilities through an intuitive user interface.
Homepage: $WEBSITE
EOF
    
    # Create post-installation script
    cat > "$deb_dir/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

APP_NAME="bitcoin-solo-miner-monitor"
INSTALL_DIR="/opt/$APP_NAME"

# Create application data directories
mkdir -p "/etc/$APP_NAME"
mkdir -p "/var/lib/$APP_NAME"

# Install Python dependencies
cd "$INSTALL_DIR"
if [ -f "requirements.txt" ]; then
    python3 -m pip install --user -r requirements.txt || {
        echo "Warning: Failed to install Python dependencies automatically"
        echo "Please run: cd $INSTALL_DIR && python3 -m pip install -r requirements.txt"
    }
fi

# Set permissions
chmod 755 "$INSTALL_DIR/run.py"
chown -R root:root "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"

# Create default configuration if template exists
if [ -f "$INSTALL_DIR/installer/linux/templates/config.ini" ]; then
    if [ ! -f "/etc/$APP_NAME/config.ini" ]; then
        cp "$INSTALL_DIR/installer/linux/templates/config.ini" "/etc/$APP_NAME/config.ini"
        chown root:root "/etc/$APP_NAME/config.ini"
        chmod 644 "/etc/$APP_NAME/config.ini"
    fi
else
    # Create basic default configuration
    if [ ! -f "/etc/$APP_NAME/config.ini" ]; then
        cat > "/etc/$APP_NAME/config.ini" << CONFIG
[server]
host = 127.0.0.1
port = 8000

[mining]
auto_discovery = true
polling_interval = 60

[logging]
level = INFO
CONFIG
        chown root:root "/etc/$APP_NAME/config.ini"
        chmod 644 "/etc/$APP_NAME/config.ini"
    fi
fi

# Install MIME types if available
if [ -f "$INSTALL_DIR/installer/linux/templates/bitcoin-solo-miner-monitor-mimetypes.xml" ]; then
    if command -v xdg-mime >/dev/null 2>&1; then
        xdg-mime install "$INSTALL_DIR/installer/linux/templates/bitcoin-solo-miner-monitor-mimetypes.xml" || true
    fi
fi

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi

# Update MIME database
if command -v update-mime-database >/dev/null 2>&1; then
    update-mime-database /usr/share/mime || true
fi

echo "$DISPLAY_NAME installed successfully!"
echo "Run '$APP_NAME' to start the application."
echo "Or use 'systemctl --user enable $APP_NAME@\$USER.service' to start on login."
EOF
    chmod 755 "$deb_dir/DEBIAN/postinst"
    
    # Create pre-removal script
    cat > "$deb_dir/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e

APP_NAME="bitcoin-solo-miner-monitor"

# Stop user service if running
systemctl --user stop "$APP_NAME@$USER.service" 2>/dev/null || true
systemctl --user disable "$APP_NAME@$USER.service" 2>/dev/null || true

# Stop any running instances
pkill -f "/opt/$APP_NAME/run.py" || true

echo "$DISPLAY_NAME stopped."
EOF
    chmod 755 "$deb_dir/DEBIAN/prerm"
    
    # Calculate installed size
    local deb_size=$(du -s "$deb_dir" | cut -f1)
    echo "Installed-Size: $deb_size" >> "$deb_dir/DEBIAN/control"
    
    # Build the DEB package
    local deb_file="$DIST_DIR/${APP_NAME}_${VERSION}_amd64.deb"
    dpkg-deb --build "$deb_dir" "$deb_file"
    
    # Clean up
    rm -rf "$temp_dir"
    
    log_success "DEB package created: $(basename "$deb_file")"
}

# Build RPM package
build_rpm() {
    log_info "Building RPM package..."
    
    local temp_dir=$(mktemp -d)
    local rpm_dir="$temp_dir/rpm"
    local install_dir="/opt/$APP_NAME"
    
    # Create RPM build directory structure
    mkdir -p "$rpm_dir"/{SPECS,SOURCES,BUILD,RPMS,SRPMS}
    
    # Create source directory
    local source_dir="$rpm_dir/SOURCES/$APP_NAME-$VERSION"
    mkdir -p "$source_dir$install_dir"
    mkdir -p "$source_dir/usr/bin"
    mkdir -p "$source_dir/usr/share/applications"
    mkdir -p "$source_dir/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$source_dir/usr/lib/systemd/user"
    
    # Copy application files
    cp -r "$BUILD_DIR/linux"/* "$source_dir$install_dir/"
    
    # Create launcher script
    cat > "$source_dir/usr/bin/$APP_NAME" << EOF
#!/bin/bash
cd $install_dir
exec python3 run.py "\$@"
EOF
    chmod +x "$source_dir/usr/bin/$APP_NAME"
    
    # Create desktop entry
    create_desktop_entry "$source_dir/usr/share/applications/$APP_NAME.desktop"
    
    # Copy icon
    if [ -f "$PROJECT_ROOT/installer/common/assets/app_icon_256.png" ]; then
        cp "$PROJECT_ROOT/installer/common/assets/app_icon_256.png" "$source_dir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    elif [ -f "$PROJECT_ROOT/assets/bitcoin-symbol.png" ]; then
        cp "$PROJECT_ROOT/assets/bitcoin-symbol.png" "$source_dir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    else
        log_warning "No icon found, creating placeholder"
        echo "PNG placeholder" > "$source_dir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    fi
    
    # Create systemd service
    create_systemd_service "$source_dir/usr/lib/systemd/user/$APP_NAME@.service"
    
    # Create source tarball
    cd "$rpm_dir/SOURCES"
    tar -czf "$APP_NAME-$VERSION.tar.gz" "$APP_NAME-$VERSION"
    cd - > /dev/null
    
    # Create RPM spec file
    cat > "$rpm_dir/SPECS/$APP_NAME.spec" << EOF
Name:           $APP_NAME
Version:        $VERSION
Release:        1%{?dist}
Summary:        $DESCRIPTION
License:        $LICENSE
URL:            $WEBSITE
Source0:        %{name}-%{version}.tar.gz
BuildArch:      x86_64
Requires:       python3 >= ${PYTHON_MIN_VERSION:-3.11}, python3-pip, nodejs >= ${NODEJS_MIN_VERSION:-18.0}
Recommends:     python3-virtualenv

%description
$DISPLAY_NAME is a unified monitoring and management solution
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
# Create application data directories
mkdir -p "/etc/$APP_NAME"
mkdir -p "/var/lib/$APP_NAME"

# Install Python dependencies
cd "$install_dir"
if [ -f "requirements.txt" ]; then
    python3 -m pip install --user -r requirements.txt || {
        echo "Warning: Failed to install Python dependencies automatically"
        echo "Please run: cd $install_dir && python3 -m pip install -r requirements.txt"
    }
fi

# Set permissions
chmod 755 "$install_dir/run.py"
chown -R root:root "$install_dir"
chmod -R 755 "$install_dir"

# Create default configuration if template exists
if [ -f "$install_dir/installer/linux/templates/config.ini" ]; then
    if [ ! -f "/etc/$APP_NAME/config.ini" ]; then
        cp "$install_dir/installer/linux/templates/config.ini" "/etc/$APP_NAME/config.ini"
        chown root:root "/etc/$APP_NAME/config.ini"
        chmod 644 "/etc/$APP_NAME/config.ini"
    fi
else
    # Create basic default configuration
    if [ ! -f "/etc/$APP_NAME/config.ini" ]; then
        cat > "/etc/$APP_NAME/config.ini" << CONFIG
[server]
host = 127.0.0.1
port = 8000

[mining]
auto_discovery = true
polling_interval = 60

[logging]
level = INFO
CONFIG
        chown root:root "/etc/$APP_NAME/config.ini"
        chmod 644 "/etc/$APP_NAME/config.ini"
    fi
fi

# Install MIME types if available
if [ -f "$install_dir/installer/linux/templates/bitcoin-solo-miner-monitor-mimetypes.xml" ]; then
    if command -v xdg-mime >/dev/null 2>&1; then
        xdg-mime install "$install_dir/installer/linux/templates/bitcoin-solo-miner-monitor-mimetypes.xml" || true
    fi
fi

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi

# Update MIME database
if command -v update-mime-database >/dev/null 2>&1; then
    update-mime-database /usr/share/mime || true
fi

echo "$DISPLAY_NAME installed successfully!"
echo "Run '$APP_NAME' to start the application."
echo "Or use 'systemctl --user enable $APP_NAME@\\\$USER.service' to start on login."

%preun
# Stop user service if running
systemctl --user stop "$APP_NAME@\$USER.service" 2>/dev/null || true
systemctl --user disable "$APP_NAME@\$USER.service" 2>/dev/null || true

# Stop any running instances
pkill -f "$install_dir/run.py" || true

%files
%defattr(-,root,root,-)
$install_dir
/usr/bin/$APP_NAME
/usr/share/applications/$APP_NAME.desktop
/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png
/usr/lib/systemd/user/$APP_NAME@.service

%changelog
* $(date "+%a %b %d %Y") $MAINTAINER $VERSION-1
- Initial package release
EOF
    
    # Build RPM package
    rpmbuild --define "_topdir $rpm_dir" -ba "$rpm_dir/SPECS/$APP_NAME.spec"
    
    # Copy the built RPM to the distribution directory
    local rpm_file=$(find "$rpm_dir/RPMS" -name "*.rpm" | head -1)
    if [ -n "$rpm_file" ]; then
        cp "$rpm_file" "$DIST_DIR/"
        log_success "RPM package created: $(basename "$rpm_file")"
    else
        log_error "RPM package creation failed"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Clean up
    rm -rf "$temp_dir"
}

# Build AppImage
build_appimage() {
    log_info "Building AppImage..."
    
    local temp_dir=$(mktemp -d)
    local appdir="$temp_dir/BitcoinSoloMinerMonitor.AppDir"
    
    # Create AppDir structure
    mkdir -p "$appdir/usr/bin"
    mkdir -p "$appdir/usr/share/applications"
    mkdir -p "$appdir/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$appdir/opt/$APP_NAME"
    
    # Copy application files
    cp -r "$BUILD_DIR/linux"/* "$appdir/opt/$APP_NAME/"
    
    # Create AppRun script
    cat > "$appdir/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")" 
export APPDIR="${HERE}"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"

# Set up Python path
export PYTHONPATH="${HERE}/opt/bitcoin-solo-miner-monitor:${PYTHONPATH}"

# Change to the application directory
cd "${HERE}/opt/bitcoin-solo-miner-monitor"

# Install dependencies if not already installed
if [ ! -f "${HERE}/.deps_installed" ]; then
    echo "Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        python3 -m pip install --user -r requirements.txt || {
            echo "Warning: Failed to install some dependencies"
            echo "The application may not work correctly"
        }
    fi
    touch "${HERE}/.deps_installed"
fi

# Create user config directory if it doesn't exist
CONFIG_DIR="$HOME/.config/bitcoin-solo-miner-monitor"
mkdir -p "$CONFIG_DIR"

# Copy default config if it doesn't exist
if [ ! -f "$CONFIG_DIR/config.ini" ] && [ -f "${HERE}/opt/bitcoin-solo-miner-monitor/installer/linux/templates/config.ini" ]; then
    cp "${HERE}/opt/bitcoin-solo-miner-monitor/installer/linux/templates/config.ini" "$CONFIG_DIR/config.ini"
fi

# Run the application
exec python3 run.py "$@"
EOF
    chmod +x "$appdir/AppRun"
    
    # Create desktop entry
    create_desktop_entry "$appdir/$APP_NAME.desktop"
    cp "$appdir/$APP_NAME.desktop" "$appdir/usr/share/applications/"
    
    # Copy icon
    if [ -f "$PROJECT_ROOT/installer/common/assets/app_icon_256.png" ]; then
        cp "$PROJECT_ROOT/installer/common/assets/app_icon_256.png" "$appdir/$APP_NAME.png"
        cp "$PROJECT_ROOT/installer/common/assets/app_icon_256.png" "$appdir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    elif [ -f "$PROJECT_ROOT/assets/bitcoin-symbol.png" ]; then
        cp "$PROJECT_ROOT/assets/bitcoin-symbol.png" "$appdir/$APP_NAME.png"
        cp "$PROJECT_ROOT/assets/bitcoin-symbol.png" "$appdir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    else
        log_warning "No icon found, creating placeholder"
        echo "PNG placeholder" > "$appdir/$APP_NAME.png"
        echo "PNG placeholder" > "$appdir/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    fi
    
    # Download appimagetool if not available
    local appimagetool="$temp_dir/appimagetool-x86_64.AppImage"
    if [ ! -f "$appimagetool" ]; then
        log_info "Downloading appimagetool..."
        wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" -O "$appimagetool"
        chmod +x "$appimagetool"
    fi
    
    # Build AppImage
    local appimage_file="$DIST_DIR/BitcoinSoloMinerMonitor-$VERSION-x86_64.AppImage"
    
    if [ -f "$appimagetool" ]; then
        log_info "Building AppImage with appimagetool..."
        "$appimagetool" "$appdir" "$appimage_file"
        
        if [ -f "$appimage_file" ]; then
            chmod +x "$appimage_file"
            log_success "AppImage created: $(basename "$appimage_file")"
        else
            log_error "AppImage creation failed"
            rm -rf "$temp_dir"
            return 1
        fi
    else
        log_warning "appimagetool not available, creating portable archive instead..."
        local portable_file="$DIST_DIR/BitcoinSoloMinerMonitor-$VERSION-portable.tar.gz"
        tar -czf "$portable_file" -C "$temp_dir" "BitcoinSoloMinerMonitor.AppDir"
        log_success "Portable archive created: $(basename "$portable_file")"
    fi
    
    # Clean up
    rm -rf "$temp_dir"
}

# Main build function
main() {
    log_info "Starting Linux package build system..."
    log_info "Package types: $PACKAGE_TYPES"
    
    # Load configuration
    load_config
    
    # Validate environment
    validate_environment
    
    # Prepare build
    prepare_build
    
    # Build packages based on type selection
    case "$PACKAGE_TYPES" in
        "deb")
            build_deb
            ;;
        "rpm")
            build_rpm
            ;;
        "appimage")
            build_appimage
            ;;
        "all")
            build_deb
            build_rpm
            build_appimage
            ;;
        *)
            log_error "Invalid package type: $PACKAGE_TYPES"
            log_error "Valid types: deb, rpm, appimage, all"
            exit 1
            ;;
    esac
    
    # Summary
    log_success "Linux package build completed!"
    log_info "Built packages are available in: $DIST_DIR"
    
    if [ -d "$DIST_DIR" ]; then
        log_info "Generated files:"
        ls -la "$DIST_DIR"/*.{deb,rpm,AppImage,tar.gz} 2>/dev/null | while read -r line; do
            log_info "  $(echo "$line" | awk '{print $9 " (" $5 " bytes)"}')"
        done
    fi
}

# Run main function
main "$@"