# macOS DMG Installer System

This directory contains the macOS DMG installer system for Bitcoin Solo Miner Monitor, implementing professional installer distribution with Python runtime bundling.

## macOS Application Bundle Integration

The macOS installer system now includes comprehensive application bundle integration for seamless user experience:

### New Features (Task 4.2 Implementation)

- **Professional App Bundle**: Complete .app bundle structure with all dependencies
- **Launchpad Integration**: Automatic appearance in Launchpad and Applications folder
- **System Integration**: Proper macOS metadata, icons, and system recognition
- **Intelligent Launcher**: Smart Python runtime detection and dependency management

### Quick Start

```bash
# Create complete app bundle
./build_macos_app_bundle.sh 1.0.0 ../../dist

# Test the integration
./test_app_bundle.sh 1.0.0

# Create DMG with integrated bundle
./create_dmg.sh ../../dist ../../dist/BitcoinSoloMinerMonitor-1.0.0.dmg 1.0.0
```

For detailed information, see [MACOS_APP_BUNDLE_INTEGRATION.md](MACOS_APP_BUNDLE_INTEGRATION.md).

## Overview

The macOS installer system creates a professional DMG (disk image) file that provides users with a familiar drag-to-install experience while bundling all necessary dependencies, including Python runtime support.

## Features

- **Professional DMG Interface**: Branded background, proper layout, and installation instructions
- **Python Runtime Bundling**: Automatic Python dependency management and runtime support
- **Drag-to-Install**: Standard macOS installation experience
- **Automatic Dependencies**: Python packages installed on first run if needed
- **Security Guidance**: Clear instructions for handling macOS security warnings
- **Checksum Generation**: SHA256 checksums for integrity verification

## Files

### Core Scripts

- **`create_dmg.sh`**: Main DMG creation script with Python runtime bundling
- **`build_macos_dmg.sh`**: Build orchestration script that prepares files and calls create_dmg.sh
- **`bundle_python_runtime.py`**: Python script for downloading and bundling Python runtime (CI/CD use)
- **`create_installer.sh`**: Legacy installer script (maintained for compatibility)

### App Bundle Integration (New)

- **`build_macos_app_bundle.sh`**: Complete app bundle creation with all integrations
- **`bundle/create_app_bundle.py`**: Professional app bundle creator with macOS integration
- **`test_app_bundle.sh`**: Comprehensive testing for app bundle functionality
- **`MACOS_APP_BUNDLE_INTEGRATION.md`**: Detailed documentation for bundle integration

### Usage

#### App Bundle Creation (Recommended)

```bash
# Create complete app bundle with all integrations
./build_macos_app_bundle.sh 1.0.0 ../../dist

# Test the app bundle integration
./test_app_bundle.sh 1.0.0

# Create app bundle only (without installers)
python3 bundle/create_app_bundle.py --output ../../dist --version 1.0.0
```

#### Basic DMG Creation

```bash
# Create DMG from prepared application directory
./create_dmg.sh /path/to/app/dir ./BitcoinSoloMinerMonitor-1.0.0.dmg 1.0.0

# Full build process (recommended)
./build_macos_dmg.sh 1.0.0
```

#### Advanced Usage with Python Bundling

```bash
# Bundle Python runtime for offline installation
python3 bundle_python_runtime.py \
    --version 3.11.7 \
    --target ./python_runtime \
    --requirements ../../requirements.txt \
    --app-bundle ./app_bundle/Contents

# Create DMG with bundled runtime
./create_dmg.sh ./prepared_app ./output.dmg 1.0.0 3.11.7
```

## DMG Structure

The created DMG contains:

```
Bitcoin Solo Miner Monitor 1.0.0/
├── Bitcoin Solo Miner Monitor.app/    # Main application bundle
│   ├── Contents/
│   │   ├── Info.plist                 # Application metadata
│   │   ├── MacOS/
│   │   │   └── BitcoinSoloMinerMonitor # Launcher script
│   │   ├── Resources/                  # Application files
│   │   │   ├── src/                    # Python source code
│   │   │   ├── config/                 # Configuration files
│   │   │   ├── assets/                 # Static assets
│   │   │   ├── run.py                  # Main application entry point
│   │   │   ├── requirements.txt        # Python dependencies
│   │   │   └── site-packages/          # Bundled Python packages
│   │   └── Frameworks/                 # Bundled frameworks
│   │       └── Python.framework/       # Python runtime (if bundled)
├── Applications@                       # Symbolic link to /Applications
├── Installation Instructions.txt       # User installation guide
└── .background/
    └── background.png                  # DMG background image
```

## Application Bundle Details

### Info.plist Configuration

The application bundle includes a comprehensive Info.plist with:

- Proper bundle identification (`com.bitcoinsolominormonitor.app`)
- Version information and metadata
- System requirements (macOS 10.15+)
- High-resolution display support
- Network security permissions for mining hardware communication
- Application category and copyright information

### Launcher Script Features

The launcher script (`BitcoinSoloMinerMonitor`) provides:

- **Python Runtime Detection**: Tries bundled Python first, falls back to system Python
- **Version Verification**: Ensures Python 3.11+ is available
- **Dependency Management**: Installs missing packages on first run
- **Error Handling**: User-friendly error dialogs for common issues
- **Environment Setup**: Proper PYTHONPATH configuration for bundled packages

### Python Runtime Bundling

The system supports two modes:

1. **System Python Mode**: Relies on user's Python installation with automatic dependency installation
2. **Bundled Python Mode**: Includes complete Python runtime for offline installation

## Security and Trust

### Code Signing Preparation

The installer is prepared for future code signing:

- Proper bundle structure for signing
- Info.plist configured for notarization
- Framework structure compatible with signing requirements

### Security Warnings

Users will encounter macOS security warnings because the application is not code-signed. The installer includes:

- Clear documentation explaining why warnings appear
- Step-by-step instructions for safely opening the application
- Alternative verification methods using SHA256 checksums

### Integrity Verification

Each DMG includes:

- SHA256 checksum file (`.sha256`)
- Installation instructions with verification guidance
- Links to community verification resources

## Build Process Integration

### Local Development

```bash
# Build and test locally
cd installer/macos
./build_macos_dmg.sh 1.0.0

# Test the created DMG
open ../../dist/BitcoinSoloMinerMonitor-1.0.0.dmg
```

### CI/CD Integration

The scripts are designed for GitHub Actions integration:

```yaml
- name: Build macOS DMG
  run: |
    cd installer/macos
    ./build_macos_dmg.sh ${{ github.ref_name }}
    
- name: Upload DMG Artifact
  uses: actions/upload-artifact@v3
  with:
    name: macos-dmg
    path: dist/*.dmg*
```

## System Requirements

### Build Environment

- macOS 10.15+ (for building)
- Xcode Command Line Tools
- Python 3.11+
- Node.js 18+ (for frontend building)

### Runtime Requirements

- macOS 10.15 (Catalina) or later
- 2 GB RAM minimum
- 5 GB free disk space
- Python 3.11+ (installed automatically if needed)

## Troubleshooting

### Common Build Issues

1. **Permission Denied**: Ensure scripts are executable
   ```bash
   chmod +x *.sh
   ```

2. **DMG Mount Failures**: Clean up any existing mounts
   ```bash
   hdiutil detach /Volumes/Bitcoin\ Solo\ Miner\ Monitor*
   ```

3. **AppleScript Errors**: Normal in headless environments (CI/CD)
   - The script continues without GUI customization
   - DMG functionality is not affected

### User Installation Issues

1. **"Unidentified Developer" Warning**:
   - Right-click the app and select "Open"
   - Or use System Preferences > Security & Privacy

2. **Python Not Found**:
   - Install Python 3.11+ from python.org
   - Or use Homebrew: `brew install python@3.11`

3. **Dependencies Installation Fails**:
   - Check internet connection
   - Manually install: `pip3 install -r requirements.txt`

## Future Enhancements

### Planned Features

- **Code Signing**: When budget allows for Apple Developer Program
- **Notarization**: Automatic notarization for enhanced security
- **Universal Binaries**: Native Apple Silicon support
- **Automatic Updates**: In-app update checking and installation

### Community Contributions

The installer system is designed to accept community contributions:

- Package maintainer support
- Alternative distribution channels
- Enhanced security verification
- Localization support

## Testing

### Manual Testing

1. Build DMG using `build_macos_dmg.sh`
2. Mount DMG and verify appearance
3. Drag app to Applications
4. Launch app and verify functionality
5. Test uninstallation (drag to Trash)

### Automated Testing

The system supports automated testing in CI/CD:

- DMG creation verification
- Bundle structure validation
- Checksum generation testing
- Installation simulation

## Support

For issues with the macOS installer system:

1. Check the troubleshooting section above
2. Review build logs for specific error messages
3. Open an issue on the project repository
4. Consult the community forums for user-reported solutions

The macOS installer system is designed to provide a professional, secure, and user-friendly installation experience while maintaining the open-source principles of transparency and community verification.