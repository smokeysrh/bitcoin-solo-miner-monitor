# Bitcoin Solo Miner Monitor - Windows Installer

## Overview

This directory contains the Windows installer system for Bitcoin Solo Miner Monitor. The installer is built using NSIS (Nullsoft Scriptable Install System) and provides a fast, offline installation experience with a pre-bundled Python runtime.

## Architecture

The installer system consists of three main components:

### 1. Bundle Preparation (`prepare-bundle.ps1`)
One-time script that downloads and prepares a complete Python runtime with all dependencies. This bundle is reused across multiple builds, making subsequent builds very fast.

### 2. Build Script (`build.ps1`)
Automated build script that compiles the frontend, stages all files, and creates the installer executable. Runs in under 60 seconds when the bundle is already prepared.

### 3. Installer Script (`installer.nsi`)
Unified NSIS script that handles installation, creates the launcher, sets up shortcuts, and manages uninstallation. All logic is contained in a single, well-documented file.

## Quick Start

### First-Time Setup

1. **Install NSIS** (if not already installed)
   - Download from: https://nsis.sourceforge.io/Download
   - Install to default location or add to PATH

2. **Prepare the Python Bundle** (one-time, ~5 minutes)
   ```powershell
   cd installer/windows
   .\prepare-bundle.ps1
   ```
   
   This downloads Python 3.11.7, installs pip, and installs all dependencies from `requirements.txt`.

### Building the Installer

Once the bundle is prepared, build the installer:

```powershell
cd installer/windows
.\build.ps1
```

The installer will be created in `distribution/BitcoinSoloMinerMonitor-{version}-Setup.exe`

Build time: ~60 seconds

## File Structure

```
installer/windows/
├── installer.nsi              # Main installer script (NSIS)
├── build.ps1                  # Build automation script
├── prepare-bundle.ps1         # Bundle preparation script
├── assets/                    # Icons, license, resources
│   ├── installer_icon.ico
│   ├── app_icon.ico
│   ├── LICENSE.txt
│   └── README.txt
├── bundle/                    # Pre-built Python runtime (gitignored)
│   └── python/                # Python 3.11.7 + dependencies
└── README.md                  # This file
```

## Detailed Documentation

### Preparing the Python Bundle

The `prepare-bundle.ps1` script performs the following steps:

1. **Download Python 3.11.7 Embeddable Package**
   - Downloads from python.org
   - Verifies download integrity
   - Extracts to `bundle/python/`

2. **Install pip**
   - Downloads get-pip.py
   - Installs pip into the embedded Python

3. **Install Dependencies**
   - Reads `../../requirements.txt`
   - Installs all packages using pip
   - Includes: FastAPI, Uvicorn, aiohttp, and all other dependencies

4. **Configure Python Path**
   - Modifies `python311._pth` for embedded use
   - Ensures site-packages are accessible

5. **Verify Installation**
   - Tests Python execution
   - Verifies all imports work correctly

**Options:**
```powershell
# Force re-download even if bundle exists
.\prepare-bundle.ps1 -Force

# Run verification tests only
.\prepare-bundle.ps1 -Verify

# Use specific Python version
.\prepare-bundle.ps1 -PythonVersion "3.11.7"
```

**Output:**
- `bundle/python/python.exe` - Python interpreter
- `bundle/python/Lib/site-packages/` - All dependencies
- Bundle size: ~150MB

### Building the Installer

The `build.ps1` script automates the complete build process:

1. **Extract Version**
   - Reads version from `src/backend/version.py`
   - Uses regex to extract `__version__` value

2. **Check Prerequisites**
   - Verifies NSIS is installed
   - Verifies Python bundle exists
   - Checks for Node.js and npm

3. **Build Frontend**
   - Runs `npm install` if needed
   - Executes `npm run build` in `src/frontend/`
   - Builds production-optimized React app

4. **Stage Files**
   - Creates temporary staging directory
   - Copies application source code
   - Copies configuration files
   - Copies Python bundle
   - Copies documentation

5. **Invoke NSIS**
   - Passes version as parameter
   - Compiles installer executable
   - Includes all staged files

6. **Generate Checksum**
   - Creates SHA256 hash of installer
   - Saves to `.sha256` file

7. **Output**
   - Moves installer to `distribution/` directory
   - Names: `BitcoinSoloMinerMonitor-{version}-Setup.exe`
   - Cleans up staging directory

**Options:**
```powershell
# Skip frontend build (if already built)
.\build.ps1 -SkipFrontend

# Override version
.\build.ps1 -Version "0.9.2"

# Custom output directory
.\build.ps1 -OutputDir "C:\Releases"

# Verbose output
.\build.ps1 -Verbose
```

**Build Time:**
- With existing bundle: ~60 seconds
- Without bundle: Run `prepare-bundle.ps1` first

### Installer Features

The `installer.nsi` script provides:

#### Installation Features
- **Fast Installation**: Completes in under 60 seconds
- **Offline Installation**: No internet required
- **Pre-bundled Python**: Includes Python 3.11.7 + all dependencies
- **Automatic Launcher Creation**: Creates batch file to start application
- **Optional Components**:
  - Desktop shortcut
  - Start Menu shortcuts
  - Start with Windows (auto-start)

#### Launcher Behavior
The installer creates `BitcoinSoloMinerMonitor.bat` which:
1. Checks if application is already running
2. Starts Python backend in minimized window
3. Waits 3 seconds for server initialization
4. Opens browser to http://localhost:8000
5. Backend serves the built frontend automatically

#### Installation Verification
The installer verifies:
- Python runtime exists and is executable
- Application files are present
- Launcher was created successfully
- All critical components are in place

#### Registry Configuration
Creates entries in:
- `HKLM\Software\Bitcoin Solo Miner Monitor` - Application settings
- `HKLM\...\Uninstall\Bitcoin Solo Miner Monitor` - Add/Remove Programs

#### Uninstallation
The uninstaller:
- Stops any running Python processes
- Removes all application files
- Removes shortcuts (Desktop, Start Menu)
- Removes registry entries
- Prompts about removing user data in `%APPDATA%`
- Verifies complete removal

## Testing the Installer

### Manual Testing

1. **Build the installer**
   ```powershell
   .\build.ps1
   ```

2. **Run the installer**
   ```powershell
   cd ..\..\distribution
   .\BitcoinSoloMinerMonitor-{version}-Setup.exe
   ```

3. **Verify installation**
   - Check files in `C:\Program Files\Bitcoin Solo Miner Monitor\`
   - Verify launcher exists: `BitcoinSoloMinerMonitor.bat`
   - Check shortcuts (if selected)
   - Verify Add/Remove Programs entry

4. **Test application**
   - Launch from Desktop shortcut or Start Menu
   - Verify browser opens to http://localhost:8000
   - Verify application loads and functions

5. **Test uninstallation**
   - Uninstall from Add/Remove Programs
   - Verify all files removed
   - Verify shortcuts removed
   - Check user data prompt

### Automated Testing

Use the provided test scripts:

```powershell
# Validate installer structure
.\validate_installer.bat

# Debug installation issues
.\debug-installation.ps1
```

### Testing on Clean System

For thorough testing, use a clean Windows VM:

1. **Set up VM** (see `VM-SETUP-GUIDE.md`)
   - Windows 10 or Windows 11
   - No Python installed
   - No development tools

2. **Copy installer to VM**
   - Transfer the `.exe` file
   - No other files needed

3. **Run installer**
   - Double-click to install
   - Test all features
   - Verify offline installation works

4. **Test upgrade scenario**
   - Install old version first
   - Run new installer
   - Verify upgrade works smoothly

## Troubleshooting

### Common Issues

#### "NSIS not found"
**Problem:** Build script can't find NSIS
**Solution:** 
- Install NSIS from https://nsis.sourceforge.io/Download
- Add NSIS to PATH, or
- Install to default location: `C:\Program Files (x86)\NSIS\`

#### "Python bundle not found"
**Problem:** Build script can't find the Python bundle
**Solution:**
```powershell
cd installer/windows
.\prepare-bundle.ps1
```

#### "Frontend build failed"
**Problem:** npm build errors
**Solution:**
```powershell
cd src/frontend
npm install
npm run build
```

#### "Installer won't run"
**Problem:** Windows SmartScreen blocks installer
**Solution:**
- Click "More info" → "Run anyway"
- Or: Code sign the installer (requires certificate)

#### "Application won't start after installation"
**Problem:** Launcher fails or Python errors
**Solution:**
- Check `C:\Program Files\Bitcoin Solo Miner Monitor\logs\`
- Verify Python bundle is complete
- Rebuild with fresh bundle: `.\prepare-bundle.ps1 -Force`

#### "Port 8000 already in use"
**Problem:** Another application is using port 8000
**Solution:**
- Close other applications using port 8000
- Or modify `config/config.json` to use different port

### Debug Mode

Enable verbose output in build script:
```powershell
.\build.ps1 -Verbose
```

Check NSIS compilation output for errors:
```powershell
# NSIS output is displayed during build
# Look for "Error:" or "Warning:" messages
```

### Log Files

After installation, check logs:
- Application logs: `C:\Program Files\Bitcoin Solo Miner Monitor\logs\`
- User data: `%APPDATA%\Bitcoin Solo Miner Monitor\`

## Version Management

Version is managed in a single location: `src/backend/version.py`

```python
__version__ = "0.9.1"
__version_info__ = (0, 9, 1)
```

The build script automatically extracts this version and uses it for:
- Installer filename
- Installer metadata
- Add/Remove Programs display
- Registry entries

To release a new version:
1. Update `src/backend/version.py`
2. Run `.\build.ps1`
3. Installer will automatically use new version

## Advanced Topics

### Customizing the Installer

Edit `installer.nsi` to customize:
- Installation directory
- Component options
- UI text and branding
- Registry keys
- Shortcuts

All customization is in one file with clear comments.

### Code Signing

To eliminate SmartScreen warnings:

1. Obtain code signing certificate
2. Install certificate on build machine
3. Sign installer after build:
   ```powershell
   signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com installer.exe
   ```

### Silent Installation

For enterprise deployment:
```cmd
BitcoinSoloMinerMonitor-Setup.exe /S
```

Options:
- `/S` - Silent installation
- `/D=C:\Custom\Path` - Custom installation directory

### Creating Portable Version

To create a portable (non-installed) version:
1. Copy `bundle/python/` directory
2. Copy `src/` directory
3. Copy `config/` directory
4. Copy `run.py`
5. Create launcher batch file
6. Package as ZIP

## Build Requirements

### Software Requirements
- **NSIS**: 3.08 or later
- **PowerShell**: 5.1 or later (included in Windows 10+)
- **Node.js**: 16.x or later (for frontend build)
- **npm**: 8.x or later

### System Requirements
- **OS**: Windows 10 or later
- **Disk Space**: 500MB free (for bundle and build artifacts)
- **Internet**: Required for initial bundle preparation only

### Build Machine Setup
1. Install NSIS
2. Install Node.js and npm
3. Clone repository
4. Run `prepare-bundle.ps1` once
5. Ready to build!

## Performance Metrics

### Bundle Preparation
- **Time**: ~5 minutes (one-time)
- **Download Size**: ~30MB
- **Extracted Size**: ~150MB

### Build Process
- **Time**: ~60 seconds (with existing bundle)
- **Output Size**: ~55MB installer
- **Installed Size**: ~200MB

### Installation
- **Time**: <60 seconds
- **Internet**: Not required
- **User Interaction**: Minimal (click through wizard)

## Support and Contribution

### Getting Help
- Check this README first
- Review `VM-SETUP-GUIDE.md` for testing
- Check `CLEANUP_SUMMARY.md` for recent changes
- Review NSIS documentation: https://nsis.sourceforge.io/Docs/

### Contributing
When modifying the installer:
1. Test on clean Windows VM
2. Verify upgrade scenario works
3. Test uninstallation
4. Update this README if needed
5. Add comments to `installer.nsi`

### Best Practices
- Keep all logic in `installer.nsi` (no external macros)
- Add comments for complex logic
- Test on both Windows 10 and 11
- Verify offline installation works
- Check Add/Remove Programs entry
- Test with and without admin rights

## Migration from Old System

If you're familiar with the old installer system:

### What Changed
- **3 installer scripts → 1**: All logic in `installer.nsi`
- **6 config files → 0**: No external config files
- **Multiple build scripts → 1**: Single `build.ps1`
- **Runtime download → Pre-bundled**: Python included in installer
- **5-10 minute install → <60 seconds**: Much faster

### What Stayed the Same
- NSIS as the installer framework
- Same installation directory
- Same shortcuts and registry keys
- Same application functionality
- Same uninstaller behavior

### Migration Guide
See `CLEANUP_SUMMARY.md` for details on what was removed.

## License

This installer system is part of Bitcoin Solo Miner Monitor.
See `../../LICENSE` for license information.

## Changelog

### Version 0.9.1 (October 2025)
- Complete installer refactoring
- Single unified installer script
- Pre-bundled Python runtime
- Fast offline installation (<60 seconds)
- Improved error handling and verification
- Comprehensive documentation

---

**Last Updated**: October 25, 2025
**Installer Version**: 0.9.1
**Python Version**: 3.11.7
**NSIS Version**: 3.08+
