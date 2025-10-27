# Building the Windows Installer for Release

## Overview

This guide explains how to build the Windows installer for Bitcoin Solo Miner Monitor. The installer system has been completely refactored for simplicity, speed, and reliability.

**Key Features:**
- Fast offline installation (<60 seconds)
- Pre-bundled Python runtime (no internet required)
- Single unified installer script
- Automated build process

## Prerequisites

### Required Software

1. **NSIS (Nullsoft Scriptable Install System)**
   - Download from: https://nsis.sourceforge.io/Download
   - Version 3.08 or later
   - Install to default location or add to PATH

2. **Node.js and npm**
   - Required for building the frontend
   - Version 16.x or later

3. **PowerShell**
   - Version 5.1 or later (included in Windows 10+)

### System Requirements

- Windows 10 or later
- 500MB free disk space
- Internet connection (for initial bundle preparation only)

## Quick Start

### First-Time Setup (One-Time)

Before building your first installer, prepare the Python bundle:

```powershell
cd installer\windows
.\prepare-bundle.ps1
```

This downloads Python 3.11.7 and all dependencies (~5 minutes, one-time only).

### Building the Installer

Once the bundle is prepared, build the installer:

```powershell
cd installer\windows
.\build.ps1
```

**Output:** `distribution\BitcoinSoloMinerMonitor-{version}-Setup.exe`

**Build Time:** ~60 seconds

## Detailed Build Process

### Step 1: Prepare Python Bundle (First Time Only)

The bundle preparation script downloads and configures a complete Python runtime:

```powershell
cd installer\windows
.\prepare-bundle.ps1
```

**What it does:**
1. Downloads Python 3.11.7 embeddable package
2. Installs pip into the embedded Python
3. Installs all dependencies from `requirements.txt`
4. Configures Python path for embedded use
5. Verifies the bundle works correctly

**Output:** `installer\windows\bundle\python\` (~150MB)

**Note:** This bundle is reused for all future builds, so you only need to do this once.

### Step 2: Build the Installer

The build script automates the complete build process:

```powershell
cd installer\windows
.\build.ps1
```

**What it does:**
1. Extracts version from `src\backend\version.py`
2. Checks prerequisites (NSIS, bundle, Node.js)
3. Builds the frontend (`npm run build`)
4. Stages all application files
5. Copies the Python bundle
6. Invokes NSIS to create installer
7. Generates SHA256 checksum
8. Outputs to `distribution\` directory

**Build Options:**

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

### Step 3: Test the Installer

Before releasing, test the installer locally:

```powershell
cd distribution
.\BitcoinSoloMinerMonitor-{version}-Setup.exe
```

**Test Checklist:**
- ✅ Installer runs without errors
- ✅ Installation completes in <60 seconds
- ✅ Application launches successfully
- ✅ Browser opens to http://localhost:8000
- ✅ Application functions correctly
- ✅ Uninstaller works properly

**Recommended:** Test on a clean Windows VM for thorough validation.

## Version Management

Version is managed in a single location: `src\backend\version.py`

```python
__version__ = "0.9.1"
__version_info__ = (0, 9, 1)
```

**To release a new version:**
1. Update `src\backend\version.py`
2. Run `.\build.ps1`
3. Installer automatically uses the new version

The version is used for:
- Installer filename
- Installer metadata
- Add/Remove Programs display
- Registry entries

## Creating a GitHub Release

### Option A: Via GitHub Web Interface

1. **Go to Releases:**
   ```
   https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases
   ```

2. **Click "Draft a new release"**

3. **Fill in details:**
   - **Tag:** `v{version}` (e.g., `v0.9.1`)
   - **Release title:** `v{version} - Description`
   - **Description:** Copy from `CHANGELOG.md`

4. **Upload files:**
   - Drag and drop: `BitcoinSoloMinerMonitor-{version}-Setup.exe`
   - Also upload: `BitcoinSoloMinerMonitor-{version}-Setup.exe.sha256`

5. **Click "Publish release"**

### Option B: Via GitHub CLI

```powershell
gh release create v0.9.1 ^
  --title "v0.9.1 - Installer Refactoring" ^
  --notes-file CHANGELOG.md ^
  distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe ^
  distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe.sha256
```

## User Installation Experience

When users download and run the installer:

1. **Download:** Single `.exe` file (~55MB)
2. **Run:** Double-click the installer
3. **Install:** Follow the wizard (<60 seconds)
4. **Launch:** Application opens automatically
5. **Use:** Browser opens to http://localhost:8000

**No additional software required!** Python and all dependencies are bundled.

## Installer Features

The installer provides:

### Installation Options
- Installation directory selection
- Desktop shortcut (optional)
- Start Menu shortcuts (optional)
- Start with Windows (optional)

### What Gets Installed
- Complete application source code
- Pre-configured Python 3.11.7 runtime
- All Python dependencies
- Application launcher
- Configuration files
- Documentation

### Installation Locations
- **Application:** `C:\Program Files\Bitcoin Solo Miner Monitor\`
- **User Data:** `%APPDATA%\Bitcoin Solo Miner Monitor\`
- **Logs:** `C:\Program Files\Bitcoin Solo Miner Monitor\logs\`

### Uninstallation
- Available from Add/Remove Programs
- Stops running application
- Removes all files and shortcuts
- Prompts about user data removal
- Clean uninstallation

## Troubleshooting

### "NSIS not found"

**Problem:** Build script can't find NSIS

**Solution:**
```powershell
# Check if NSIS is installed
where makensis

# If not found, install NSIS from:
# https://nsis.sourceforge.io/Download
```

### "Python bundle not found"

**Problem:** Build script can't find the Python bundle

**Solution:**
```powershell
cd installer\windows
.\prepare-bundle.ps1
```

### "Frontend build failed"

**Problem:** npm build errors

**Solution:**
```powershell
cd src\frontend
npm install
npm run build
```

### "Installer won't run"

**Problem:** Windows SmartScreen blocks installer

**Solution:**
- Click "More info" → "Run anyway"
- Or: Code sign the installer (requires certificate)

### Build is slow

**Problem:** Build takes longer than expected

**Check:**
- Is the Python bundle already prepared?
- Is the frontend already built?
- Use `-SkipFrontend` if frontend is current

## Advanced Topics

### Code Signing

To eliminate SmartScreen warnings:

1. Obtain code signing certificate
2. Install certificate on build machine
3. Sign installer after build:
   ```powershell
   signtool sign /f certificate.pfx /p password installer.exe
   ```

### Rebuilding the Bundle

If you need to update Python or dependencies:

```powershell
cd installer\windows
.\prepare-bundle.ps1 -Force
```

This re-downloads everything and rebuilds the bundle.

### Custom Build Configuration

Edit `installer\windows\installer.nsi` to customize:
- Installation directory
- Component options
- UI text and branding
- Registry keys
- Shortcuts

All customization is in one file with clear comments.

## File Structure

```
installer/windows/
├── installer.nsi              # Main installer script
├── build.ps1                  # Build automation
├── prepare-bundle.ps1         # Bundle preparation
├── assets/                    # Icons, license, etc.
├── bundle/                    # Python runtime (gitignored)
└── README.md                  # Detailed documentation
```

## Performance Metrics

- **Bundle Preparation:** ~5 minutes (one-time)
- **Build Time:** ~60 seconds (with bundle)
- **Installation Time:** <60 seconds
- **Installer Size:** ~55MB
- **Installed Size:** ~200MB

## Documentation

For more detailed information, see:
- `installer\windows\README.md` - Comprehensive installer documentation
- `INSTALLER_MIGRATION_GUIDE.md` - Changes from old system
- `CHANGELOG.md` - Version history

## Platform Support

**Current:** Windows 10 and Windows 11 (x64)

**Future:** macOS and Linux installers are planned but not yet implemented. This refactoring focused on Windows to establish a solid foundation.

## Support

If you encounter issues:
1. Check `installer\windows\README.md` for troubleshooting
2. Review build script output for errors
3. Test on a clean Windows VM
4. Report issues on GitHub

---

**Last Updated:** October 25, 2025  
**Installer Version:** 0.9.1  
**Python Version:** 3.11.7  
**NSIS Version:** 3.08+
