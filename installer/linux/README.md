# Linux Package Generation System

This directory contains the comprehensive Linux package generation system for Bitcoin Solo Miner Monitor. The system creates professional-grade DEB, RPM, and AppImage packages with full desktop integration, systemd service support, and comprehensive dependency management.

## Overview

The Linux package system provides:

- **DEB packages** for Debian/Ubuntu distributions
- **RPM packages** for Red Hat/Fedora/CentOS distributions  
- **AppImage packages** for universal Linux compatibility
- **Comprehensive desktop integration** with multi-language support
- **Systemd service integration** for background operation
- **MIME type associations** for mining configuration files
- **Professional branding** and user experience

## Quick Start

### Build All Package Types

```bash
# Build all package types (DEB, RPM, AppImage)
./create_all_packages.sh

# Build with custom version
./create_all_packages.sh --version 2.0.0

# Build with verbose output and clean build
./create_all_packages.sh --verbose --clean
```

### Build Specific Package Types

```bash
# Build only DEB package
./create_all_packages.sh --type deb

# Build only RPM package  
./create_all_packages.sh --type rpm

# Build only AppImage
./create_all_packages.sh --type appimage
```

### Build Individual Packages

```bash
# Build DEB package directly
./build_deb.sh /path/to/app /path/to/dist 1.0.0

# Build RPM package directly
./build_rpm.sh /path/to/app /path/to/dist 1.0.0

# Build AppImage directly
./build_appimage.sh /path/to/app /path/to/dist 1.0.0
```

## File Structure

```
installer/linux/
├── README.md                           # This documentation
├── build_packages.sh                   # Comprehensive build system
├── create_all_packages.sh              # Main package creation script
├── build_deb.sh                        # DEB package builder
├── build_rpm.sh                        # RPM package builder
├── build_appimage.sh                   # AppImage builder
├── create_packages.sh                  # Legacy package creator
├── dependency_resolver.py              # Dependency resolution system
├── desktop_integration.sh              # Desktop integration script
├── test_desktop_integration.sh         # Desktop integration tests
└── templates/                          # Package templates
    ├── bitcoin-solo-miner-monitor.desktop      # Desktop entry
    ├── bitcoin-solo-miner-monitor@.service     # Systemd service
    ├── bitcoin-solo-miner-monitor-mimetypes.xml # MIME types
    └── config.ini                              # Default configuration
```

## Package Features

### DEB Package Features

- **Professional packaging** following Debian policy
- **Automatic dependency resolution** for Python and Node.js
- **Desktop integration** with application menu entries
- **Systemd user service** for background operation
- **MIME type associations** for configuration files
- **Multi-language desktop entries** (English, Spanish, French, German, Chinese)
- **Desktop actions** for service management
- **Proper uninstallation** with cleanup

### RPM Package Features

- **Red Hat packaging standards** compliance
- **Automatic dependency management** for RHEL/Fedora/CentOS
- **Desktop environment integration** across distributions
- **Systemd service integration** with security hardening
- **Icon cache updates** for proper desktop appearance
- **Configuration file management** with user preservation
- **Professional metadata** and documentation

### AppImage Features

- **Universal Linux compatibility** - runs on any distribution
- **Portable execution** - no installation required
- **Embedded dependencies** - includes Python runtime
- **User configuration management** in ~/.config
- **Automatic dependency installation** on first run
- **Professional desktop integration** when installed
- **Fallback portable archive** if AppImage tools unavailable

## Desktop Integration

### Desktop Entry Features

- **Multi-language support** for international users
- **Professional categorization** in application menus
- **MIME type associations** for mining configuration files
- **Desktop actions** for right-click context menus:
  - Start/Stop mining monitor service
  - View application logs
  - Open configuration
  - Check service status
- **Accessibility compliance** with proper metadata
- **Desktop environment specific** optimizations

### Systemd Service Features

- **User-level service** for per-user operation
- **Security hardening** with restricted permissions
- **Automatic restart** on failure
- **Proper logging** to systemd journal
- **Resource limits** for system protection
- **Network dependency** management

## Build Requirements

### System Requirements

- **Linux distribution** with package building tools
- **Python 3.11+** for application runtime
- **Node.js 18+** for frontend building
- **Git** for version control

### DEB Building Requirements

```bash
# Ubuntu/Debian
sudo apt-get install dpkg-dev build-essential

# Required tools
dpkg-deb          # DEB package creation
update-desktop-database  # Desktop integration
gtk-update-icon-cache   # Icon cache management
```

### RPM Building Requirements

```bash
# RHEL/Fedora/CentOS
sudo yum install rpm-build rpmdevtools
# or
sudo dnf install rpm-build rpmdevtools

# Required tools
rpmbuild          # RPM package creation
update-desktop-database  # Desktop integration
gtk-update-icon-cache   # Icon cache management
```

### AppImage Building Requirements

```bash
# Universal requirements
wget              # Download appimagetool
python3-pip       # Python package management

# Optional but recommended
fuse              # AppImage execution support
```

## Configuration

### Build Configuration

The build system uses configuration from:

1. **installer/common/installer_config.json** - Main configuration
2. **Environment variables** - Runtime overrides
3. **Command line arguments** - Build-time options

### Template Customization

Templates in `templates/` directory can be customized:

- **Desktop entry** - Modify application metadata
- **Systemd service** - Adjust service configuration
- **MIME types** - Add file associations
- **Default config** - Set application defaults

## Testing

### Package Testing

```bash
# Test desktop integration
./test_desktop_integration.sh

# Test DEB package installation
sudo dpkg -i distribution/bitcoin-solo-miner-monitor_1.0.0_amd64.deb

# Test RPM package installation
sudo rpm -i distribution/bitcoin-solo-miner-monitor-1.0.0-1.x86_64.rpm

# Test AppImage execution
chmod +x distribution/BitcoinSoloMinerMonitor-1.0.0-x86_64.AppImage
./distribution/BitcoinSoloMinerMonitor-1.0.0-x86_64.AppImage
```

### Validation

The build system includes validation for:

- **Package integrity** - Checksums and signatures
- **Dependency resolution** - Required packages available
- **Desktop integration** - Menu entries and icons
- **Service functionality** - Systemd service operation
- **File permissions** - Proper security settings

## Troubleshooting

### Common Issues

**Build fails with missing dependencies:**
```bash
# Install build dependencies
sudo apt-get install dpkg-dev rpm-build wget python3-pip

# Or use the dependency resolver
python3 dependency_resolver.py --install
```

**Desktop integration not working:**
```bash
# Update desktop databases manually
update-desktop-database ~/.local/share/applications
gtk-update-icon-cache ~/.local/share/icons/hicolor
```

**AppImage won't run:**
```bash
# Install FUSE support
sudo apt-get install fuse

# Make executable
chmod +x *.AppImage
```

**Service won't start:**
```bash
# Check service status
systemctl --user status bitcoin-solo-miner-monitor@$USER.service

# View service logs
journalctl --user -u bitcoin-solo-miner-monitor@$USER.service
```

### Debug Mode

Enable verbose output for debugging:

```bash
# Verbose build output
./create_all_packages.sh --verbose

# Debug individual package builds
./build_deb.sh /path/to/app /path/to/dist 1.0.0 --verbose
```

## Distribution

### Package Distribution

Generated packages are suitable for:

- **Direct distribution** via GitHub releases
- **Community repositories** (AUR, PPA, COPR)
- **Enterprise deployment** via configuration management
- **User installation** via package managers

### Community Integration

The packages are designed for easy community adoption:

- **Standard packaging practices** for each distribution
- **Comprehensive documentation** for maintainers
- **Reproducible builds** for verification
- **Professional quality** for repository inclusion

## Support

For issues with the Linux packaging system:

1. **Check the logs** - Build output contains detailed information
2. **Validate environment** - Ensure all build dependencies are installed
3. **Test templates** - Verify template files are correct
4. **Review configuration** - Check installer_config.json settings
5. **Community support** - Use GitHub issues for assistance

## Contributing

To contribute to the Linux packaging system:

1. **Test on multiple distributions** - Ensure compatibility
2. **Follow packaging standards** - Maintain professional quality
3. **Update documentation** - Keep README current
4. **Add test cases** - Verify functionality
5. **Submit pull requests** - Include comprehensive testing

The Linux package system is designed to provide professional-grade installation experiences while maintaining the open-source values of transparency, reproducibility, and community collaboration.