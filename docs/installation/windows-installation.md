# Windows Installation Guide

## Overview

The Windows installer provides a professional installation experience with automatic dependency management. No technical knowledge or manual setup is required.

## Download

1. **Go to the official releases page**: [GitHub Releases](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/latest)

2. **Download the Windows installer**: Look for `BitcoinSoloMinerMonitor-Setup.exe` (approximately 45-60 MB)

3. **Verify the download** (recommended):
   ```powershell
   # In PowerShell, navigate to your Downloads folder
   cd $env:USERPROFILE\Downloads
   
   # Check the file hash
   Get-FileHash -Algorithm SHA256 BitcoinSoloMinerMonitor-Setup.exe
   
   # Compare with the SHA256SUMS file from the release
   ```

## Installation Steps

### Step 1: Handle Security Warnings

**Windows SmartScreen Warning**:
When you double-click the installer, Windows may show:
> "Windows protected your PC - Microsoft Defender SmartScreen prevented an unrecognized app from starting"

**This is normal for open-source software.** To proceed safely:

1. Click **"More info"**
2. Click **"Run anyway"**
3. Verify you downloaded from the official GitHub releases page

![Windows SmartScreen Warning](../../assets/windows-smartscreen-warning.png)

### Step 2: Run the Installer

1. **Right-click** the installer file
2. Select **"Run as administrator"** (recommended for proper installation)
3. If prompted by User Account Control (UAC), click **"Yes"**

### Step 3: Installation Wizard

The installer will guide you through these steps:

1. **Welcome Screen**
   - Click "Next" to continue

2. **License Agreement**
   - Review the open-source license
   - Check "I accept the agreement"
   - Click "Next"

3. **Installation Directory**
   - Default: `C:\Program Files\Bitcoin Solo Miner Monitor\`
   - Change if desired (not recommended for most users)
   - Click "Next"

4. **Component Selection**
   - **Core Application**: Required (cannot be unchecked)
   - **Desktop Shortcut**: Creates shortcut on desktop
   - **Start Menu Shortcut**: Adds to Start Menu
   - **Auto-start**: Starts with Windows (optional)
   - Click "Next"

5. **Ready to Install**
   - Review your selections
   - Click "Install"

6. **Installation Progress**
   - The installer will:
     - Extract application files
     - Install Python runtime (if needed)
     - Install dependencies
     - Create shortcuts
     - Register with Windows

7. **Completion**
   - Check "Launch Bitcoin Solo Miner Monitor" to start immediately
   - Click "Finish"

## Post-Installation

### First Launch

1. **Launch the application**:
   - Double-click the desktop shortcut, or
   - Use Start Menu → "Bitcoin Solo Miner Monitor"

2. **Windows Firewall Prompt**:
   - Windows may ask for network permissions
   - Click "Allow access" for both Private and Public networks
   - This is required for miner discovery

3. **Application Setup**:
   - The application will open in your default web browser
   - Navigate to `http://localhost:8000`
   - Follow the initial setup wizard

### Antivirus Considerations

**Common Antivirus Warnings**:
Mining software is often flagged as potentially unwanted due to similarities with malicious mining software.

**If your antivirus blocks the installation**:

1. **Temporarily disable real-time protection** during installation
2. **Add exclusions** for the installation directory:
   - Windows Defender: Settings → Virus & threat protection → Exclusions
   - Add folder: `C:\Program Files\Bitcoin Solo Miner Monitor\`

**Popular Antivirus Exclusion Instructions**:

- **Windows Defender**:
  1. Open Windows Security
  2. Go to Virus & threat protection
  3. Click "Manage settings" under Virus & threat protection settings
  4. Click "Add or remove exclusions"
  5. Add folder: `C:\Program Files\Bitcoin Solo Miner Monitor\`

- **Avast/AVG**:
  1. Open Avast/AVG
  2. Go to Settings → General → Exceptions
  3. Add file path: `C:\Program Files\Bitcoin Solo Miner Monitor\`

- **Norton**:
  1. Open Norton
  2. Go to Settings → Antivirus → Scans and Risks → Exclusions/Low Risks
  3. Add folder: `C:\Program Files\Bitcoin Solo Miner Monitor\`

- **McAfee**:
  1. Open McAfee
  2. Go to Virus and Spyware Protection → Real-Time Scanning
  3. Click "Excluded Files"
  4. Add folder: `C:\Program Files\Bitcoin Solo Miner Monitor\`

## Verification and Security

### Verify Installation Integrity

After installation, verify the application files:

```powershell
# Check if the main executable exists
Test-Path "C:\Program Files\Bitcoin Solo Miner Monitor\BitcoinSoloMinerMonitor.exe"

# Check the installation registry entry
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object {$_.DisplayName -like "*Bitcoin Solo Miner Monitor*"}
```

### Network Security

The application:
- **Listens on localhost:8000** (web dashboard)
- **Scans local network** for miners (configurable)
- **Does not send data externally** (except for optional updates)
- **Uses standard HTTP/WebSocket protocols**

## Troubleshooting

### Installation Issues

**"Installation failed" or "Access denied"**:
1. Run installer as administrator
2. Temporarily disable antivirus
3. Check Windows Event Viewer for detailed errors:
   - Windows Logs → Application
   - Look for errors from "MsiInstaller"

**"Python installation failed"**:
1. Manually install Python 3.11+ from python.org
2. Restart the installer
3. Or use the portable version (if available)

**"Cannot create shortcuts"**:
1. Run installer as administrator
2. Check if Desktop/Start Menu folders are accessible
3. Manually create shortcuts after installation

### Runtime Issues

**Application won't start**:
1. Check if Python is installed: `python --version`
2. Check Windows Event Viewer for application errors
3. Try running from command line:
   ```cmd
   cd "C:\Program Files\Bitcoin Solo Miner Monitor"
   python main.py
   ```

**Port 8000 already in use**:
1. Check what's using port 8000:
   ```cmd
   netstat -ano | findstr :8000
   ```
2. Stop the conflicting service or change the application port

**Dashboard not accessible**:
1. Check Windows Firewall settings
2. Try accessing `http://127.0.0.1:8000` instead
3. Check if the application service is running:
   ```cmd
   tasklist | findstr python
   ```

### Network Discovery Issues

**Miners not found**:
1. Ensure miners and PC are on the same network
2. Check Windows Firewall isn't blocking network discovery
3. Verify miner IP addresses are in the correct range
4. Try manual miner configuration instead of auto-discovery

## Uninstallation

### Standard Uninstall

1. **Windows Settings Method**:
   - Settings → Apps → Apps & features
   - Search for "Bitcoin Solo Miner Monitor"
   - Click → Uninstall

2. **Control Panel Method**:
   - Control Panel → Programs → Programs and Features
   - Find "Bitcoin Solo Miner Monitor"
   - Right-click → Uninstall

3. **Start Menu Method**:
   - Start Menu → Bitcoin Solo Miner Monitor folder
   - Click "Uninstall Bitcoin Solo Miner Monitor"

### Complete Removal

To remove all traces:

1. **Run the standard uninstaller** (above)

2. **Remove user data** (optional):
   ```cmd
   rmdir /s "%APPDATA%\Bitcoin Solo Miner Monitor"
   ```

3. **Remove registry entries** (advanced users):
   ```cmd
   reg delete "HKCU\Software\Bitcoin Solo Miner Monitor" /f
   ```

4. **Clear Windows Firewall rules**:
   - Windows Security → Firewall & network protection
   - Advanced settings → Inbound Rules
   - Remove any "Bitcoin Solo Miner Monitor" rules

## Advanced Configuration

### Custom Installation Directory

If you installed to a custom directory:

1. **Update PATH environment variable** (if needed):
   ```cmd
   setx PATH "%PATH%;C:\Your\Custom\Path\Bitcoin Solo Miner Monitor"
   ```

2. **Create custom shortcuts**:
   ```cmd
   # Desktop shortcut
   powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('$Home\Desktop\Bitcoin Solo Miner Monitor.lnk'); $Shortcut.TargetPath = 'C:\Your\Custom\Path\BitcoinSoloMinerMonitor.exe'; $Shortcut.Save()"
   ```

### Service Installation

To run as a Windows service:

1. **Install using sc command**:
   ```cmd
   sc create "BitcoinSoloMinerMonitor" binPath= "C:\Program Files\Bitcoin Solo Miner Monitor\BitcoinSoloMinerMonitor.exe --service"
   sc config "BitcoinSoloMinerMonitor" start= auto
   sc start "BitcoinSoloMinerMonitor"
   ```

2. **Remove service**:
   ```cmd
   sc stop "BitcoinSoloMinerMonitor"
   sc delete "BitcoinSoloMinerMonitor"
   ```

## Getting Help

- **Installation Issues**: [Report on GitHub](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues/new?template=installation-issue.md)
- **General Troubleshooting**: [Troubleshooting Guide](troubleshooting.md)
- **Security Questions**: [Security Guide](security-guide.md)
- **Community Support**: [GitHub Discussions](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions)

---

**Next Steps**: After successful installation, see the [User Guide](../user-guide.md) to configure your miners and start monitoring!