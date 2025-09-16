# macOS Installation Guide

## Overview

The macOS installer provides a native drag-to-install experience using a professional DMG disk image. All dependencies are bundled within the application.

## Download

1. **Go to the official releases page**: [GitHub Releases](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/latest)

2. **Download the macOS installer**: Look for `BitcoinSoloMinerMonitor.dmg` (approximately 50-70 MB)

3. **Verify the download** (recommended):
   ```bash
   # In Terminal, navigate to your Downloads folder
   cd ~/Downloads
   
   # Check the file hash
   shasum -a 256 BitcoinSoloMinerMonitor.dmg
   
   # Compare with the SHA256SUMS file from the release
   ```

## Installation Steps

### Step 1: Handle Security Warnings

**macOS Gatekeeper Warning**:
When you open the DMG, macOS may show:
> "BitcoinSoloMinerMonitor.dmg can't be opened because it is from an unidentified developer"

**This is normal for open-source software.** To proceed safely:

**Method 1 - System Preferences**:
1. Go to **System Preferences** → **Security & Privacy**
2. Click **"Open Anyway"** next to the blocked application message
3. Confirm by clicking **"Open"**

**Method 2 - Right-click Override**:
1. **Right-click** the DMG file
2. Select **"Open"**
3. Click **"Open"** in the confirmation dialog

**Method 3 - Terminal (Advanced)**:
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine ~/Downloads/BitcoinSoloMinerMonitor.dmg
```

![macOS Gatekeeper Warning](../../assets/macos-gatekeeper-warning.png)

### Step 2: Mount the DMG

1. **Double-click** the DMG file (after handling security warnings)
2. The disk image will mount and open a Finder window
3. You'll see the **Bitcoin Solo Miner Monitor** application and an **Applications** folder shortcut

### Step 3: Install the Application

1. **Drag** the "Bitcoin Solo Miner Monitor" application to the "Applications" folder
2. **Wait** for the copy operation to complete
3. **Eject** the DMG by:
   - Right-clicking the mounted disk and selecting "Eject", or
   - Dragging it to the Trash, or
   - Using `⌘+E` while the disk is selected

### Step 4: First Launch

1. **Open Applications** folder (⌘+Shift+A)
2. **Find** "Bitcoin Solo Miner Monitor"
3. **Right-click** the application and select **"Open"** (first time only)
4. Click **"Open"** in the confirmation dialog

**Note**: After the first launch, you can open the app normally by double-clicking.

## Post-Installation

### Application Integration

The application will automatically:
- **Appear in Launchpad** for easy access
- **Integrate with Spotlight** search
- **Show in Applications** folder
- **Create dock icon** when running

### Network Permissions

1. **Firewall Prompt**:
   - macOS may ask for network permissions
   - Click **"Allow"** to enable miner discovery
   - This is required for local network scanning

2. **Network Access**:
   - The application needs network access to discover miners
   - No external internet access is required for core functionality

### First Launch Setup

1. **Launch the application** from Applications or Launchpad
2. **Web browser will open** automatically to `http://localhost:8000`
3. **Follow the setup wizard** to configure your mining setup
4. **Add your miners** using discovery or manual configuration

## Security Considerations

### Gatekeeper and Notarization

**Why the security warnings occur**:
- The app is not notarized by Apple (requires paid developer account)
- Open-source projects often cannot afford Apple's developer fees
- This is common in the Bitcoin ecosystem

**How to verify authenticity**:
1. **Download only from official GitHub releases**
2. **Verify SHA256 checksums** before installation
3. **Build from source** for maximum security (see [BUILD.md](../BUILD.md))

### Application Permissions

The application requests:
- **Network access**: For miner discovery and communication
- **Local file access**: For configuration and data storage
- **No camera, microphone, or location access**: Not required

### Data Storage Locations

- **Application**: `/Applications/Bitcoin Solo Miner Monitor.app`
- **User Data**: `~/Library/Application Support/Bitcoin Solo Miner Monitor/`
- **Logs**: `~/Library/Logs/Bitcoin Solo Miner Monitor/`
- **Preferences**: `~/Library/Preferences/com.bitcoinsoloapp.plist`

## Troubleshooting

### Installation Issues

**"App is damaged and can't be opened"**:
1. **Re-download** the DMG file (may be corrupted)
2. **Clear quarantine attribute**:
   ```bash
   xattr -cr "/Applications/Bitcoin Solo Miner Monitor.app"
   ```
3. **Verify download integrity** using SHA256 checksum

**"No such file or directory" when launching**:
1. **Check if Python is available**:
   ```bash
   python3 --version
   ```
2. **Install Python if missing**:
   ```bash
   # Using Homebrew (recommended)
   brew install python@3.11
   
   # Or download from python.org
   ```

**DMG won't mount**:
1. **Check disk space** (need ~200MB free)
2. **Repair disk permissions**:
   ```bash
   sudo diskutil repairPermissions /
   ```
3. **Try mounting manually**:
   ```bash
   hdiutil attach ~/Downloads/BitcoinSoloMinerMonitor.dmg
   ```

### Runtime Issues

**Application won't start**:
1. **Check Console.app** for error messages:
   - Applications → Utilities → Console
   - Look for "Bitcoin Solo Miner Monitor" entries

2. **Try launching from Terminal**:
   ```bash
   "/Applications/Bitcoin Solo Miner Monitor.app/Contents/MacOS/Bitcoin Solo Miner Monitor"
   ```

3. **Check dependencies**:
   ```bash
   # Verify Python installation
   python3 --version
   
   # Check if required modules are available
   python3 -c "import sqlite3, json, asyncio"
   ```

**Port 8000 already in use**:
1. **Find what's using the port**:
   ```bash
   lsof -i :8000
   ```
2. **Kill the conflicting process** or change application port

**Dashboard not accessible**:
1. **Check if application is running**:
   ```bash
   ps aux | grep "Bitcoin Solo Miner Monitor"
   ```
2. **Try alternative URLs**:
   - `http://127.0.0.1:8000`
   - `http://localhost:8000`

### Network Discovery Issues

**Miners not found**:
1. **Check network connectivity**:
   ```bash
   ping 192.168.1.1  # Your router IP
   ```
2. **Verify firewall settings**:
   - System Preferences → Security & Privacy → Firewall
   - Ensure "Bitcoin Solo Miner Monitor" is allowed

3. **Test manual miner connection**:
   ```bash
   # Test if miner is reachable
   curl http://192.168.1.100/api/system/info  # Replace with miner IP
   ```

## Advanced Configuration

### Custom Installation Location

While not recommended, you can install to a custom location:

1. **Create custom directory**:
   ```bash
   mkdir -p ~/Applications
   ```

2. **Copy application**:
   ```bash
   cp -R "/Volumes/Bitcoin Solo Miner Monitor/Bitcoin Solo Miner Monitor.app" ~/Applications/
   ```

3. **Create alias in main Applications** (optional):
   ```bash
   ln -s ~/Applications/Bitcoin\ Solo\ Miner\ Monitor.app /Applications/
   ```

### Launch Agent Setup

To start automatically at login:

1. **Create launch agent**:
   ```bash
   cat > ~/Library/LaunchAgents/com.bitcoinsoloapp.plist << EOF
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.bitcoinsoloapp</string>
       <key>ProgramArguments</key>
       <array>
           <string>/Applications/Bitcoin Solo Miner Monitor.app/Contents/MacOS/Bitcoin Solo Miner Monitor</string>
       </array>
       <key>RunAtLoad</key>
       <true/>
       <key>KeepAlive</key>
       <true/>
   </dict>
   </plist>
   EOF
   ```

2. **Load the launch agent**:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.bitcoinsoloapp.plist
   ```

3. **Remove launch agent**:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.bitcoinsoloapp.plist
   rm ~/Library/LaunchAgents/com.bitcoinsoloapp.plist
   ```

### Command Line Usage

Access the application from Terminal:

```bash
# Create alias for easy access
echo 'alias bitcoin-monitor="/Applications/Bitcoin\ Solo\ Miner\ Monitor.app/Contents/MacOS/Bitcoin\ Solo\ Miner\ Monitor"' >> ~/.zshrc
source ~/.zshrc

# Now you can run
bitcoin-monitor --help
```

## Uninstallation

### Standard Uninstall

1. **Quit the application** if running
2. **Drag to Trash**:
   - Open Applications folder
   - Drag "Bitcoin Solo Miner Monitor" to Trash
   - Empty Trash

### Complete Removal

To remove all traces:

1. **Remove application** (above)

2. **Remove user data**:
   ```bash
   rm -rf ~/Library/Application\ Support/Bitcoin\ Solo\ Miner\ Monitor/
   rm -rf ~/Library/Logs/Bitcoin\ Solo\ Miner\ Monitor/
   rm ~/Library/Preferences/com.bitcoinsoloapp.plist
   ```

3. **Remove launch agent** (if created):
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.bitcoinsoloapp.plist
   rm ~/Library/LaunchAgents/com.bitcoinsoloapp.plist
   ```

4. **Clear Spotlight index**:
   ```bash
   sudo mdutil -E /
   ```

## Version Management

### Updating

1. **Download new version** from GitHub releases
2. **Quit current application**
3. **Replace in Applications folder**:
   - Drag new version to Applications
   - Choose "Replace" when prompted
4. **Launch new version**

### Downgrading

1. **Download older version** from GitHub releases
2. **Remove current version** completely
3. **Install older version** following standard steps
4. **Restore data backup** if needed

## Getting Help

- **Installation Issues**: [Report on GitHub](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues/new?template=installation-issue.md)
- **General Troubleshooting**: [Troubleshooting Guide](troubleshooting.md)
- **Security Questions**: [Security Guide](security-guide.md)
- **Community Support**: [GitHub Discussions](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions)

## macOS-Specific Resources

- **Apple Developer Documentation**: [Distributing Apps Outside the App Store](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- **Homebrew**: [Package Manager for macOS](https://brew.sh)
- **macOS Security**: [System Integrity Protection](https://support.apple.com/en-us/HT204899)

---

**Next Steps**: After successful installation, see the [User Guide](../user-guide.md) to configure your miners and start monitoring!