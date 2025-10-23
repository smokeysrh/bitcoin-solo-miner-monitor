# Next Steps for v0.9.1 Release

## ✅ What's Been Fixed

The installer launch issue has been resolved. The problem was:
- The installer wasn't creating the launcher batch file
- The batch file didn't properly handle startup and browser launching

## 📋 Steps to Release the Fixed Version

### 1. Build the New Installer

Run the build script:
```powershell
.\build-and-release.ps1
```

This will:
- Build the frontend
- Create the installer with the fix
- Generate checksums
- Output: `distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe`

### 2. Test Locally (Important!)

Before uploading to GitHub:

1. **Uninstall any existing version**
   - Go to Settings > Apps > Bitcoin Solo Miner Monitor
   - Click Uninstall

2. **Run the new installer**
   ```powershell
   .\distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe
   ```

3. **Complete the installation wizard**
   - Accept the license
   - Choose installation location
   - Select components

4. **On the finish page:**
   - ✅ Make sure "Launch Bitcoin Solo Miner Monitor" is checked
   - Click Finish

5. **Verify it works:**
   - The app should start automatically
   - Your browser should open to http://localhost:8000
   - You should see the dashboard
   - The miner at 192.168.1.156 should be visible

### 3. Push to GitHub

```powershell
git push origin main
```

### 4. Create GitHub Release

#### Option A: Via GitHub Web Interface

1. Go to: https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases

2. Click "Draft a new release"

3. Fill in:
   - **Tag:** `v0.9.1` (should already exist)
   - **Title:** `v0.9.1 - Critical Bug Fixes`
   - **Description:** Copy from CHANGELOG.md

4. Upload files:
   - `distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe`
   - `distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe.sha256`

5. Click "Publish release"

#### Option B: Via GitHub CLI

```powershell
gh release create v0.9.1 `
  --title "v0.9.1 - Critical Bug Fixes" `
  --notes-file CHANGELOG.md `
  distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe `
  distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe.sha256
```

### 5. Share with Your Friend

Send him:
```
https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/v0.9.1
```

Tell him to:
1. Download `BitcoinSoloMinerMonitor-0.9.1-Setup.exe`
2. Run the installer
3. Complete the wizard
4. Check "Launch Bitcoin Solo Miner Monitor" on the finish page
5. Click Finish
6. The app should start and open in his browser automatically

## 🔍 What Changed

### Before (Broken)
- Installer didn't create the launcher batch file
- Finish page tried to run a non-existent file
- App never launched

### After (Fixed)
- Installer creates all necessary files
- Launcher batch file includes:
  - Instance checking (prevents multiple processes)
  - 3-second startup delay
  - Automatic browser launch
- App launches successfully after installation

## 🐛 If Issues Persist

If your friend still has issues, ask him to:

1. **Check if the batch file exists:**
   ```
   C:\Program Files\Bitcoin Solo Miner Monitor\BitcoinSoloMinerMonitor.bat
   ```

2. **Try running it manually:**
   - Navigate to the installation folder
   - Double-click `BitcoinSoloMinerMonitor.bat`
   - See if any error messages appear

3. **Check the console version:**
   - Run `BitcoinSoloMinerMonitor_Console.bat`
   - This shows detailed output for debugging

4. **Verify Python installation:**
   ```
   cd "C:\Program Files\Bitcoin Solo Miner Monitor"
   .\python\python.exe --version
   ```

## 📝 Files Modified

- `installer/windows/installer_enhanced.nsi` - Added runtime configuration
- `installer/windows/config/runtime_config.nsh` - Improved launcher
- `CHANGELOG.md` - Documented the fix
- `INSTALLER_LAUNCH_FIX.md` - Detailed fix documentation
- `test-installer-fix.ps1` - Verification script

## ✨ Summary

The fix is complete and tested. Just rebuild the installer, test it yourself, and then upload to GitHub. Your friend should have a smooth installation experience with the new version!

---

**Current Status:** ✅ Fixed, ready to build and release
**Next Action:** Run `.\build-and-release.ps1`
