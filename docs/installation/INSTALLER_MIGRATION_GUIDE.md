# Installer Migration Guide

## Overview

This guide explains the changes made to the Windows installer system in version 0.9.1. The installer has been completely refactored from a complex, multi-file architecture to a streamlined, single-script solution.

**Target Audience:** Developers maintaining the installer or building releases

## What Changed

### High-Level Summary

| Aspect | Old System | New System |
|--------|-----------|------------|
| **Installer Scripts** | 3 files (installer.nsi, installer_enhanced.nsi, installer_final.nsi) | 1 file (installer.nsi) |
| **Configuration Files** | 6 .nsh files in config/ directory | 0 (all inline) |
| **Build Scripts** | 2 batch files + 1 PowerShell script | 1 PowerShell script (build.ps1) |
| **Python Runtime** | Downloaded during installation | Pre-bundled (offline install) |
| **Installation Time** | 5-10 minutes | <60 seconds |
| **Build Time** | Variable | ~60 seconds (with bundle) |
| **Launcher Creation** | External macro (easy to forget) | Inline (can't forget) |
| **Version Management** | Multiple locations | Single source (version.py) |
| **Maintenance** | Complex, error-prone | Simple, maintainable |

### Detailed Changes

#### 1. Installer Scripts Consolidated

**Old System:**
```
installer/windows/
├── installer.nsi              # Basic version (unused)
├── installer_enhanced.nsi     # Current default (had bugs)
├── installer_final.nsi        # "Final" version (different features)
```

**New System:**
```
installer/windows/
├── installer.nsi              # Single unified installer
```

**Why:** Having three installer scripts created confusion about which one to use and made maintenance difficult. The new system consolidates all features into one well-documented script.

#### 2. Configuration Files Eliminated

**Old System:**
```
installer/windows/config/
├── branding.nsh               # UI branding
├── dependencies.nsh           # Python download logic
├── runtime_config.nsh         # Launcher creation (macros)
├── shortcuts.nsh              # Shortcut creation
├── uninstaller.nsh            # Uninstall logic
└── version.nsh                # Version metadata
```

**New System:**
```
(All logic is inline in installer.nsi)
```

**Why:** External configuration files with macro dependencies made it easy to forget critical steps (like calling the launcher creation macro). Inline code is more maintainable and prevents bugs.

#### 3. Build Process Simplified

**Old System:**
```
installer/windows/
├── build_installer.bat        # Old batch script
├── build_final_installer.bat  # Another batch script
└── (root)/build-and-release.ps1  # PowerShell script
```

**New System:**
```
installer/windows/
├── build.ps1                  # Single build script
└── prepare-bundle.ps1         # One-time bundle prep
```

**Why:** Multiple build scripts created confusion. The new system has one clear build script with automated steps.

#### 4. Python Runtime Pre-Bundled

**Old System:**
- Python downloaded during installation
- Required internet connection
- Slow installation (5-10 minutes)
- Could fail if download failed

**New System:**
- Python pre-bundled in installer
- No internet required
- Fast installation (<60 seconds)
- Reliable offline installation

**Why:** Pre-bundling Python makes installation faster, more reliable, and works offline.

#### 5. Launcher Creation Inline

**Old System:**
```nsis
; In installer_enhanced.nsi
!include "config\runtime_config.nsh"

Section "Install"
  ; ... file copying ...
  !insertmacro ConfigureRuntimeEnvironment  ; Easy to forget!
SectionEnd
```

**New System:**
```nsis
Section "!Core Application (required)" SecCore
  ; ... file copying ...
  
  ; Create launcher inline (can't forget it!)
  DetailPrint "Creating application launcher..."
  FileOpen $0 "$INSTDIR\BitcoinSoloMinerMonitor.bat" w
  FileWrite $0 "@echo off$\r$\n"
  ; ... (complete launcher code inline) ...
  FileClose $0
  
  ; Verify it was created
  ${If} ${FileExists} "$INSTDIR\BitcoinSoloMinerMonitor.bat"
    DetailPrint "✓ Launcher created successfully"
  ${Else}
    MessageBox MB_OK|MB_ICONSTOP "Failed to create launcher!"
    Abort
  ${EndIf}
SectionEnd
```

**Why:** The old system used a macro that had to be explicitly called. Forgetting to call it caused the "app won't launch" bug. Inline creation with verification prevents this.

#### 6. Version Management Centralized

**Old System:**
- Version hardcoded in multiple files
- Had to update manually in each location
- Easy to have version mismatches

**New System:**
- Single source: `src/backend/version.py`
- Build script extracts version automatically
- Consistent across all components

**Why:** Single source of truth prevents version inconsistencies and reduces manual work.

## Migration Steps (Already Complete)

These steps have already been completed in version 0.9.1:

1. ✅ Created `prepare-bundle.ps1` for Python bundle preparation
2. ✅ Created unified `build.ps1` build script
3. ✅ Created new unified `installer.nsi` with inline launcher creation
4. ✅ Updated `.gitignore` for bundle and staging directories
5. ✅ Tested bundle preparation, build process, and installation
6. ✅ Deleted old installer files:
   - `installer_enhanced.nsi`
   - `installer_final.nsi`
   - `config/` directory (all .nsh files)
   - `build_installer.bat`
   - `build_final_installer.bat`
   - `scripts/prepare_python_runtime.py`
   - Test installer executables
7. ✅ Created comprehensive documentation
8. ✅ Updated root documentation

## How to Use the New System

### First-Time Setup

1. **Prepare the Python bundle** (one-time, ~5 minutes):
   ```powershell
   cd installer\windows
   .\prepare-bundle.ps1
   ```

2. **Build the installer** (~60 seconds):
   ```powershell
   .\build.ps1
   ```

3. **Test the installer**:
   ```powershell
   cd ..\..\distribution
   .\BitcoinSoloMinerMonitor-{version}-Setup.exe
   ```

### Subsequent Builds

Once the bundle is prepared, just run:
```powershell
cd installer\windows
.\build.ps1
```

### Updating Version

1. Edit `src\backend\version.py`:
   ```python
   __version__ = "0.9.2"
   ```

2. Build:
   ```powershell
   cd installer\windows
   .\build.ps1
   ```

Version is automatically extracted and used everywhere.

## Key Differences for Developers

### Building Installers

**Old Way:**
```powershell
# Which script do I use?
cd installer\windows
build_installer.bat  # or build_final_installer.bat?

# Or maybe:
cd ..\..
.\build-and-release.ps1
```

**New Way:**
```powershell
# Clear and simple
cd installer\windows
.\build.ps1
```

### Modifying Installer Behavior

**Old Way:**
- Find the right .nsh file in config/
- Edit the macro
- Remember to include it in the main script
- Hope you didn't break anything

**New Way:**
- Open `installer.nsi`
- Find the relevant section (clearly commented)
- Edit inline code
- All logic is visible in one place

### Debugging Installation Issues

**Old Way:**
- Check multiple files
- Trace macro calls
- Guess which version is being used
- Hard to see complete flow

**New Way:**
- Open `installer.nsi`
- Read through the installation section
- All logic is visible and documented
- Easy to understand complete flow

## Benefits of New System

### For Developers

1. **Easier Maintenance**
   - One file to edit instead of nine
   - Clear, documented code
   - No hidden macro dependencies

2. **Faster Iteration**
   - Build in ~60 seconds
   - No re-downloading Python
   - Quick test cycles

3. **Fewer Bugs**
   - Can't forget launcher creation
   - Verification steps catch errors
   - Consistent version management

4. **Better Documentation**
   - Comprehensive README
   - Inline comments
   - Clear architecture

### For Users

1. **Faster Installation**
   - <60 seconds vs 5-10 minutes
   - No waiting for downloads
   - Immediate gratification

2. **More Reliable**
   - Works offline
   - No download failures
   - Consistent experience

3. **Better Experience**
   - Professional installer wizard
   - Clear progress indicators
   - Helpful error messages

## Backward Compatibility

### Installation Directory

**Same:** `C:\Program Files\Bitcoin Solo Miner Monitor\`

The new installer uses the same installation directory, so upgrades work smoothly.

### Registry Keys

**Same:** Registry keys are in the same locations

The new installer uses the same registry structure for compatibility.

### User Data

**Same:** `%APPDATA%\Bitcoin Solo Miner Monitor\`

User data location is unchanged, so settings and data are preserved during upgrades.

### Upgrade Path

Users can upgrade from old versions (0.9.0 and earlier) to new versions (0.9.1+):

1. Run new installer
2. Installer detects old version
3. Prompts to uninstall old version
4. Uninstalls old version (preserves user data)
5. Installs new version
6. User data is preserved

## Troubleshooting

### "I can't find installer_enhanced.nsi"

**Answer:** It's been removed. Use `installer.nsi` instead.

### "Where are the config files?"

**Answer:** They've been eliminated. All logic is inline in `installer.nsi`.

### "How do I modify the launcher?"

**Answer:** Edit the launcher creation section in `installer.nsi` (around line 200-250, clearly commented).

### "The build script can't find the bundle"

**Answer:** Run `prepare-bundle.ps1` first to create the Python bundle.

### "I need to update the version"

**Answer:** Edit `src\backend\version.py` only. The build script extracts it automatically.

## File Location Reference

### Old Locations (Removed)

```
installer/windows/
├── installer_enhanced.nsi     ❌ REMOVED
├── installer_final.nsi        ❌ REMOVED
├── config/                    ❌ REMOVED (entire directory)
│   ├── branding.nsh
│   ├── dependencies.nsh
│   ├── runtime_config.nsh
│   ├── shortcuts.nsh
│   ├── uninstaller.nsh
│   └── version.nsh
├── scripts/                   ❌ REMOVED (entire directory)
│   └── prepare_python_runtime.py
├── build_installer.bat        ❌ REMOVED
└── build_final_installer.bat  ❌ REMOVED
```

### New Locations

```
installer/windows/
├── installer.nsi              ✅ Main installer script
├── build.ps1                  ✅ Build automation
├── prepare-bundle.ps1         ✅ Bundle preparation
├── assets/                    ✅ Icons, license, etc.
├── bundle/                    ✅ Python runtime (gitignored)
└── README.md                  ✅ Comprehensive docs
```

## Additional Resources

- **Installer Documentation:** `installer/windows/README.md`
- **Build Instructions:** `BUILD_INSTALLER_FOR_RELEASE.md`
- **Changelog:** `CHANGELOG.md`
- **Cleanup Summary:** `installer/windows/CLEANUP_SUMMARY.md`

## Questions?

If you have questions about the new installer system:

1. Check `installer/windows/README.md` for detailed documentation
2. Review the inline comments in `installer.nsi`
3. Look at the build script output for debugging
4. Open a GitHub issue if you need help

---

**Migration Date:** October 25, 2025  
**Version:** 0.9.1  
**Status:** Complete and Production-Ready
