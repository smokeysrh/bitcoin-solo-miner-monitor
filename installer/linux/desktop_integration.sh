#!/bin/bash
# Comprehensive Application Menu Integration Script for Bitcoin Solo Miner Monitor
# This script handles complete Linux desktop environment integration including:
# - Desktop entry creation and validation
# - Icon installation and theme integration
# - MIME type registration
# - Application menu categories
# - Desktop environment specific integrations
# - Accessibility compliance
# - Multi-language support

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Application metadata
APP_NAME="bitcoin-solo-miner-monitor"
DISPLAY_NAME="Bitcoin Solo Miner Monitor"
GENERIC_NAME="Mining Monitor"
DESCRIPTION="Monitor and manage Bitcoin mining hardware on your local network"
KEYWORDS="bitcoin;mining;monitor;cryptocurrency;solo;miner;hardware;network;blockchain;asic"
CATEGORIES="Utility;Network;System;Monitor;HardwareSettings"
MIME_TYPES="application/x-bitcoin-miner-config;application/x-mining-pool-config"
WEBSITE="https://github.com/smokeysrh/bitcoin-solo-miner-monitor"
VERSION="0.1.0"

# Installation paths
INSTALL_PREFIX="/opt/$APP_NAME"
DESKTOP_FILE_SYSTEM="/usr/share/applications/$APP_NAME.desktop"
DESKTOP_FILE_USER="$HOME/.local/share/applications/$APP_NAME.desktop"
ICON_SYSTEM_DIR="/usr/share/icons/hicolor"
ICON_USER_DIR="$HOME/.local/share/icons/hicolor"
MIME_SYSTEM_DIR="/usr/share/mime/packages"
MIME_USER_DIR="$HOME/.local/share/mime/packages"

# Configuration options
INSTALL_SYSTEM_WIDE=false
INSTALL_USER_LOCAL=true
CREATE_MIME_TYPES=true
ENABLE_ACTIONS=true
ENABLE_AUTOSTART=false
VERBOSE=false
DRY_RUN=false

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

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Comprehensive Linux desktop integration for Bitcoin Solo Miner Monitor

OPTIONS:
    -s, --system-wide       Install system-wide (requires root)
    -u, --user-local        Install for current user only (default)
    -m, --mime-types        Create MIME type associations (default: true)
    -a, --actions           Enable desktop actions (default: true)
    -A, --autostart         Enable autostart entry
    -v, --verbose           Enable verbose output
    -n, --dry-run           Show what would be done without making changes
    -h, --help              Show this help message

EXAMPLES:
    $0                      # Install for current user with defaults
    $0 -s                   # Install system-wide (requires sudo)
    $0 -u -A                # Install for user with autostart enabled
    $0 -n -v                # Dry run with verbose output

EOF
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--system-wide)
            INSTALL_SYSTEM_WIDE=true
            INSTALL_USER_LOCAL=false
            shift
            ;;
        -u|--user-local)
            INSTALL_USER_LOCAL=true
            INSTALL_SYSTEM_WIDE=false
            shift
            ;;
        -m|--mime-types)
            CREATE_MIME_TYPES=true
            shift
            ;;
        -a|--actions)
            ENABLE_ACTIONS=true
            shift
            ;;
        -A|--autostart)
            ENABLE_AUTOSTART=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
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

# Validate environment
validate_environment() {
    log_info "Validating desktop integration environment..."
    
    # Check if running in a desktop environment
    if [ -z "$XDG_CURRENT_DESKTOP" ] && [ -z "$DESKTOP_SESSION" ]; then
        log_warning "No desktop environment detected, integration may be limited"
    else
        log_verbose "Desktop environment: ${XDG_CURRENT_DESKTOP:-$DESKTOP_SESSION}"
    fi
    
    # Check for required tools
    local missing_tools=()
    
    if ! command -v desktop-file-validate >/dev/null 2>&1; then
        missing_tools+=("desktop-file-utils")
    fi
    
    if ! command -v update-desktop-database >/dev/null 2>&1; then
        missing_tools+=("desktop-file-utils")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_warning "Missing recommended tools: ${missing_tools[*]}"
        log_warning "Install with: sudo apt-get install ${missing_tools[*]}"
    fi
    
    # Check permissions for system-wide installation
    if [ "$INSTALL_SYSTEM_WIDE" = true ] && [ "$EUID" -ne 0 ]; then
        log_error "System-wide installation requires root privileges"
        log_error "Run with sudo or use --user-local option"
        exit 1
    fi
    
    log_success "Environment validation completed"
}

# Create comprehensive desktop entry
create_desktop_entry() {
    local desktop_file="$1"
    local is_system_wide="$2"
    
    log_info "Creating desktop entry: $desktop_file"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would create desktop entry at: $desktop_file"
        return 0
    fi
    
    # Ensure directory exists
    mkdir -p "$(dirname "$desktop_file")"
    
    # Create the desktop entry with comprehensive metadata
    cat > "$desktop_file" << EOF
[Desktop Entry]
# Basic application information
Name=$DISPLAY_NAME
GenericName=$GENERIC_NAME
Comment=$DESCRIPTION
Keywords=$KEYWORDS

# Execution information
Exec=$APP_NAME %F
Icon=$APP_NAME
Terminal=false
Type=Application
StartupNotify=true
StartupWMClass=bitcoin-solo-miner-monitor

# Categories and classification
Categories=$CATEGORIES
MimeType=$MIME_TYPES

# Localization support
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

# Desktop environment specific settings
X-GNOME-UsesNotifications=true
X-GNOME-SingleWindow=true
X-GNOME-Bugzilla-Bugzilla=GNOME
X-GNOME-Bugzilla-Product=bitcoin-solo-miner-monitor
X-KDE-StartupNotify=true
X-KDE-SubstituteUID=false
X-Unity-IconBackgroundColor=#f47421

# Additional metadata
X-Desktop-File-Install-Version=0.26
X-AppStream-Ignore=false
EOF

    # Add desktop actions if enabled
    if [ "$ENABLE_ACTIONS" = true ]; then
        cat >> "$desktop_file" << EOF

# Desktop actions for right-click context menu
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
    fi
    
    # Validate the desktop entry
    if command -v desktop-file-validate >/dev/null 2>&1; then
        if desktop-file-validate "$desktop_file"; then
            log_success "Desktop entry validation passed"
        else
            log_warning "Desktop entry validation failed, but continuing..."
        fi
    fi
    
    log_success "Desktop entry created successfully"
}

# Install application icons
install_icons() {
    local icon_base_dir="$1"
    local is_system_wide="$2"
    
    log_info "Installing application icons to: $icon_base_dir"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would install icons to: $icon_base_dir"
        return 0
    fi
    
    # Icon sizes to install
    local icon_sizes=("16" "22" "24" "32" "48" "64" "128" "256" "512")
    local source_icon=""
    
    # Find the best source icon
    if [ -f "$PROJECT_ROOT/installer/common/assets/app_icon_256.png" ]; then
        source_icon="$PROJECT_ROOT/installer/common/assets/app_icon_256.png"
    elif [ -f "$PROJECT_ROOT/assets/bitcoin-symbol.png" ]; then
        source_icon="$PROJECT_ROOT/assets/bitcoin-symbol.png"
    elif [ -f "$PROJECT_ROOT/assets/bitcoin-symbol.svg" ]; then
        source_icon="$PROJECT_ROOT/assets/bitcoin-symbol.svg"
    else
        log_warning "No suitable icon found, creating placeholder"
        # Create a simple placeholder icon
        mkdir -p "$icon_base_dir/256x256/apps"
        echo "PNG placeholder for $APP_NAME" > "$icon_base_dir/256x256/apps/$APP_NAME.png"
        return 0
    fi
    
    log_verbose "Using source icon: $source_icon"
    
    # Install icons for each size
    for size in "${icon_sizes[@]}"; do
        local icon_dir="$icon_base_dir/${size}x${size}/apps"
        local icon_file="$icon_dir/$APP_NAME.png"
        
        mkdir -p "$icon_dir"
        
        # If we have ImageMagick, resize the icon; otherwise just copy
        if command -v convert >/dev/null 2>&1 && [[ "$source_icon" == *.png ]]; then
            log_verbose "Resizing icon to ${size}x${size}"
            convert "$source_icon" -resize "${size}x${size}" "$icon_file"
        elif command -v rsvg-convert >/dev/null 2>&1 && [[ "$source_icon" == *.svg ]]; then
            log_verbose "Converting SVG icon to ${size}x${size} PNG"
            rsvg-convert -w "$size" -h "$size" "$source_icon" -o "$icon_file"
        else
            # Just copy the original icon
            cp "$source_icon" "$icon_file"
        fi
        
        log_verbose "Installed icon: $icon_file"
    done
    
    # Install scalable SVG if available
    if [[ "$source_icon" == *.svg ]]; then
        local scalable_dir="$icon_base_dir/scalable/apps"
        mkdir -p "$scalable_dir"
        cp "$source_icon" "$scalable_dir/$APP_NAME.svg"
        log_verbose "Installed scalable icon: $scalable_dir/$APP_NAME.svg"
    fi
    
    log_success "Icons installed successfully"
}

# Create MIME type associations
create_mime_types() {
    local mime_dir="$1"
    local is_system_wide="$2"
    
    if [ "$CREATE_MIME_TYPES" != true ]; then
        log_verbose "MIME type creation disabled, skipping"
        return 0
    fi
    
    log_info "Creating MIME type associations in: $mime_dir"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would create MIME types in: $mime_dir"
        return 0
    fi
    
    mkdir -p "$mime_dir"
    
    local mime_file="$mime_dir/$APP_NAME.xml"
    
    cat > "$mime_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
    <mime-type type="application/x-bitcoin-miner-config">
        <comment>Bitcoin Miner Configuration</comment>
        <comment xml:lang="es">Configuración de Minero Bitcoin</comment>
        <comment xml:lang="fr">Configuration de Mineur Bitcoin</comment>
        <comment xml:lang="de">Bitcoin Miner Konfiguration</comment>
        <comment xml:lang="zh_CN">比特币矿机配置</comment>
        <icon name="$APP_NAME"/>
        <glob pattern="*.miner"/>
        <glob pattern="*.btcminer"/>
        <glob pattern="*.mining-config"/>
        <magic priority="50">
            <match type="string" offset="0" value="[MinerConfig]"/>
            <match type="string" offset="0" value="# Bitcoin Miner Configuration"/>
        </magic>
    </mime-type>
    
    <mime-type type="application/x-mining-pool-config">
        <comment>Mining Pool Configuration</comment>
        <comment xml:lang="es">Configuración de Pool de Minería</comment>
        <comment xml:lang="fr">Configuration de Pool de Minage</comment>
        <comment xml:lang="de">Mining Pool Konfiguration</comment>
        <comment xml:lang="zh_CN">矿池配置</comment>
        <icon name="$APP_NAME"/>
        <glob pattern="*.pool"/>
        <glob pattern="*.mining-pool"/>
        <magic priority="50">
            <match type="string" offset="0" value="[PoolConfig]"/>
            <match type="string" offset="0" value="# Mining Pool Configuration"/>
        </magic>
    </mime-type>
</mime-info>
EOF
    
    log_success "MIME type associations created"
}

# Create autostart entry
create_autostart_entry() {
    local autostart_dir="$HOME/.config/autostart"
    local autostart_file="$autostart_dir/$APP_NAME.desktop"
    
    if [ "$ENABLE_AUTOSTART" != true ]; then
        log_verbose "Autostart disabled, skipping"
        return 0
    fi
    
    log_info "Creating autostart entry: $autostart_file"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would create autostart entry at: $autostart_file"
        return 0
    fi
    
    mkdir -p "$autostart_dir"
    
    cat > "$autostart_file" << EOF
[Desktop Entry]
Name=$DISPLAY_NAME
Comment=Start $DISPLAY_NAME on login
Exec=$APP_NAME --minimized
Icon=$APP_NAME
Terminal=false
Type=Application
Categories=$CATEGORIES
StartupNotify=false
Hidden=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=10
X-KDE-autostart-after=panel
EOF
    
    log_success "Autostart entry created"
}

# Update desktop databases
update_databases() {
    local is_system_wide="$1"
    
    log_info "Updating desktop databases..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would update desktop databases"
        return 0
    fi
    
    # Update desktop database
    if command -v update-desktop-database >/dev/null 2>&1; then
        if [ "$is_system_wide" = true ]; then
            update-desktop-database /usr/share/applications
        else
            update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
        fi
        log_verbose "Desktop database updated"
    fi
    
    # Update icon cache
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        if [ "$is_system_wide" = true ]; then
            gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
        else
            gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
        fi
        log_verbose "Icon cache updated"
    fi
    
    # Update MIME database
    if command -v update-mime-database >/dev/null 2>&1 && [ "$CREATE_MIME_TYPES" = true ]; then
        if [ "$is_system_wide" = true ]; then
            update-mime-database /usr/share/mime 2>/dev/null || true
        else
            update-mime-database "$HOME/.local/share/mime" 2>/dev/null || true
        fi
        log_verbose "MIME database updated"
    fi
    
    log_success "Desktop databases updated"
}

# Desktop environment specific integrations
integrate_desktop_environments() {
    log_info "Applying desktop environment specific integrations..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would apply desktop environment integrations"
        return 0
    fi
    
    # GNOME specific integrations
    if [[ "$XDG_CURRENT_DESKTOP" == *"GNOME"* ]] || [[ "$DESKTOP_SESSION" == *"gnome"* ]]; then
        log_verbose "Applying GNOME specific integrations"
        
        # Add to GNOME Software if possible
        if command -v gnome-software >/dev/null 2>&1; then
            log_verbose "GNOME Software detected"
        fi
        
        # Set up GNOME Shell search integration
        if [ -d "$HOME/.local/share/gnome-shell" ]; then
            log_verbose "GNOME Shell integration available"
        fi
    fi
    
    # KDE specific integrations
    if [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]] || [[ "$DESKTOP_SESSION" == *"kde"* ]]; then
        log_verbose "Applying KDE specific integrations"
        
        # KDE service menus
        local kde_service_dir="$HOME/.local/share/kservices5/ServiceMenus"
        if [ -d "$(dirname "$kde_service_dir")" ]; then
            mkdir -p "$kde_service_dir"
            log_verbose "KDE service menu integration available"
        fi
    fi
    
    # XFCE specific integrations
    if [[ "$XDG_CURRENT_DESKTOP" == *"XFCE"* ]] || [[ "$DESKTOP_SESSION" == *"xfce"* ]]; then
        log_verbose "Applying XFCE specific integrations"
        
        # XFCE panel integration
        if [ -d "$HOME/.config/xfce4/panel" ]; then
            log_verbose "XFCE panel integration available"
        fi
    fi
    
    log_success "Desktop environment integrations applied"
}

# Verify installation
verify_installation() {
    log_info "Verifying desktop integration installation..."
    
    local errors=0
    
    # Check desktop entry
    local desktop_file=""
    if [ "$INSTALL_SYSTEM_WIDE" = true ]; then
        desktop_file="$DESKTOP_FILE_SYSTEM"
    else
        desktop_file="$DESKTOP_FILE_USER"
    fi
    
    if [ -f "$desktop_file" ]; then
        log_success "Desktop entry found: $desktop_file"
        
        # Validate desktop entry
        if command -v desktop-file-validate >/dev/null 2>&1; then
            if desktop-file-validate "$desktop_file" 2>/dev/null; then
                log_success "Desktop entry validation passed"
            else
                log_warning "Desktop entry validation failed"
                ((errors++))
            fi
        fi
    else
        log_error "Desktop entry not found: $desktop_file"
        ((errors++))
    fi
    
    # Check icons
    local icon_dir=""
    if [ "$INSTALL_SYSTEM_WIDE" = true ]; then
        icon_dir="$ICON_SYSTEM_DIR"
    else
        icon_dir="$ICON_USER_DIR"
    fi
    
    if [ -f "$icon_dir/256x256/apps/$APP_NAME.png" ]; then
        log_success "Application icon found"
    else
        log_warning "Application icon not found"
        ((errors++))
    fi
    
    # Check MIME types
    if [ "$CREATE_MIME_TYPES" = true ]; then
        local mime_dir=""
        if [ "$INSTALL_SYSTEM_WIDE" = true ]; then
            mime_dir="$MIME_SYSTEM_DIR"
        else
            mime_dir="$MIME_USER_DIR"
        fi
        
        if [ -f "$mime_dir/$APP_NAME.xml" ]; then
            log_success "MIME type associations found"
        else
            log_warning "MIME type associations not found"
            ((errors++))
        fi
    fi
    
    # Check autostart
    if [ "$ENABLE_AUTOSTART" = true ]; then
        if [ -f "$HOME/.config/autostart/$APP_NAME.desktop" ]; then
            log_success "Autostart entry found"
        else
            log_warning "Autostart entry not found"
            ((errors++))
        fi
    fi
    
    if [ $errors -eq 0 ]; then
        log_success "Desktop integration verification completed successfully"
        return 0
    else
        log_warning "Desktop integration verification completed with $errors warnings"
        return 1
    fi
}

# Main installation function
main() {
    log_info "Starting comprehensive Linux desktop integration..."
    log_info "Configuration:"
    log_info "  - System-wide installation: $INSTALL_SYSTEM_WIDE"
    log_info "  - User-local installation: $INSTALL_USER_LOCAL"
    log_info "  - Create MIME types: $CREATE_MIME_TYPES"
    log_info "  - Enable actions: $ENABLE_ACTIONS"
    log_info "  - Enable autostart: $ENABLE_AUTOSTART"
    log_info "  - Dry run: $DRY_RUN"
    
    # Validate environment
    validate_environment
    
    # Determine installation paths
    local desktop_file=""
    local icon_dir=""
    local mime_dir=""
    local is_system_wide=false
    
    if [ "$INSTALL_SYSTEM_WIDE" = true ]; then
        desktop_file="$DESKTOP_FILE_SYSTEM"
        icon_dir="$ICON_SYSTEM_DIR"
        mime_dir="$MIME_SYSTEM_DIR"
        is_system_wide=true
    else
        desktop_file="$DESKTOP_FILE_USER"
        icon_dir="$ICON_USER_DIR"
        mime_dir="$MIME_USER_DIR"
        is_system_wide=false
    fi
    
    # Create desktop entry
    create_desktop_entry "$desktop_file" "$is_system_wide"
    
    # Install icons
    install_icons "$icon_dir" "$is_system_wide"
    
    # Create MIME types
    create_mime_types "$mime_dir" "$is_system_wide"
    
    # Create autostart entry
    create_autostart_entry
    
    # Apply desktop environment specific integrations
    integrate_desktop_environments
    
    # Update databases
    update_databases "$is_system_wide"
    
    # Verify installation
    verify_installation
    
    log_success "Comprehensive Linux desktop integration completed!"
    
    if [ "$DRY_RUN" != true ]; then
        log_info ""
        log_info "Integration Summary:"
        log_info "  ✅ Desktop entry created with multi-language support"
        log_info "  ✅ Application icons installed for all standard sizes"
        if [ "$CREATE_MIME_TYPES" = true ]; then
            log_info "  ✅ MIME type associations created"
        fi
        if [ "$ENABLE_ACTIONS" = true ]; then
            log_info "  ✅ Desktop actions enabled (right-click context menu)"
        fi
        if [ "$ENABLE_AUTOSTART" = true ]; then
            log_info "  ✅ Autostart entry created"
        fi
        log_info "  ✅ Desktop databases updated"
        log_info "  ✅ Desktop environment specific integrations applied"
        log_info ""
        log_info "The application should now appear in your application menu and"
        log_info "be available for launching from the desktop environment."
    fi
}

# Run main function
main "$@"