# Bitcoin Solo Miner Monitor - Installation Guide

## Overview

Bitcoin Solo Miner Monitor provides professional installers for Windows, macOS, and Linux platforms. This guide covers installation methods, security considerations, and troubleshooting for each platform.

## Quick Installation

### Windows
1. Download `BitcoinSoloMinerMonitor-Setup.exe` from [GitHub Releases](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases)
2. Right-click the installer and select "Run as administrator"
3. Follow the installation wizard
4. **Security Note**: Windows may show an "Unknown Publisher" warning - this is normal for open-source software

### macOS
1. Download `BitcoinSoloMinerMonitor.dmg` from [GitHub Releases](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases)
2. Open the DMG file
3. Drag the application to your Applications folder
4. **Security Note**: macOS may require you to allow the app in System Preferences > Security & Privacy

### Linux

#### Ubuntu/Debian (.deb)
```bash
# Download the .deb package
wget https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v1.0.0/bitcoin-solo-miner-monitor_1.0.0_amd64.deb

# Install the package
sudo dpkg -i bitcoin-solo-miner-monitor_1.0.0_amd64.deb

# Install dependencies if needed
sudo apt-get install -f
```

#### Fedora/CentOS (.rpm)
```bash
# Download the .rpm package
wget https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v1.0.0/bitcoin-solo-miner-monitor-1.0.0-1.x86_64.rpm

# Install the package
sudo rpm -i bitcoin-solo-miner-monitor-1.0.0-1.x86_64.rpm
```

#### Universal Linux (AppImage)
```bash
# Download the AppImage
wget https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v1.0.0/BitcoinSoloMinerMonitor-1.0.0-x86_64.AppImage

# Make it executable
chmod +x BitcoinSoloMinerMonitor-1.0.0-x86_64.AppImage

# Run the application
./BitcoinSoloMinerMonitor-1.0.0-x86_64.AppImage
```

## Security Verification

### Checksum Verification

All releases include SHA256 checksums for verification:

1. Download the `SHA256SUMS` file from the release
2. Verify your download:

**Windows (PowerShell):**
```powershell
Get-FileHash -Algorithm SHA256 BitcoinSoloMinerMonitor-Setup.exe
```

**macOS/Linux:**
```bash
shasum -a 256 BitcoinSoloMinerMonitor.dmg
# or
sha256sum bitcoin-solo-miner-monitor_1.0.0_amd64.deb
```

3. Compare the output with the corresponding entry in `SHA256SUMS`

### Reproducible Builds

You can verify the authenticity by building from source:

```bash
git clone https://github.com/your-repo/bitcoin-solo-miner-monitor.git
cd bitcoin-solo-miner-monitor
python scripts/create-distribution.py --version 1.0.0
```

The generated installer should have the same SHA256 checksum as the official release.

## Security Warnings and Solutions

### Windows "Unknown Publisher" Warning

**Why this happens:** Open-source software often doesn't have expensive code signing certificates.

**How to proceed safely:**
1. Verify the SHA256 checksum (see above)
2. Download only from official GitHub releases
3. Click "More info" → "Run anyway" in the Windows warning dialog

### Antivirus False Positives

**Why this happens:** Mining software is often flagged by antivirus programs due to similarities with malicious mining software.

**Solutions:**
1. **Verify authenticity** using checksums before whitelisting
2. **Add exclusions** for the installation directory:
   - Windows Defender: Settings → Virus & threat protection → Exclusions
   - Other antivirus: Consult your antivirus documentation

**Common directories to whitelist:**
- Windows: `C:\Program Files\Bitcoin Solo Miner Monitor\`
- macOS: `/Applications/Bitcoin Solo Miner Monitor.app`
- Linux: `/opt/bitcoin-solo-miner-monitor/`

### macOS Gatekeeper Warnings

**Why this happens:** The app is not notarized by Apple (requires paid developer account).

**How to proceed safely:**
1. Verify the SHA256 checksum
2. Right-click the app → "Open" → "Open" in the dialog
3. Or disable Gatekeeper temporarily: `sudo spctl --master-disable`

## System Requirements

### Minimum Requirements
- **Windows**: Windows 10 or later, Python 3.11+
- **macOS**: macOS 10.15 (Catalina) or later, Python 3.11+
- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+, or equivalent

### Recommended Requirements
- 4GB RAM
- 1GB free disk space
- Network access for miner discovery
- Modern web browser for the dashboard

## Troubleshooting

### Installation Issues

**Windows: "Installation failed" or "Access denied"**
- Run the installer as administrator
- Temporarily disable antivirus during installation
- Check Windows Event Viewer for detailed error messages

**macOS: "App is damaged and can't be opened"**
- Re-download the DMG file (may be corrupted)
- Clear quarantine attribute: `xattr -cr "/Applications/Bitcoin Solo Miner Monitor.app"`

**Linux: "Dependency issues"**
- Update package lists: `sudo apt update` (Ubuntu/Debian)
- Install missing dependencies manually
- Use the AppImage version for universal compatibility

### Runtime Issues

**Application won't start**
1. Check if Python 3.11+ is installed
2. Verify all dependencies are installed
3. Check application logs:
   - Windows: `%APPDATA%\Bitcoin Solo Miner Monitor\logs\`
   - macOS: `~/Library/Application Support/Bitcoin Solo Miner Monitor/logs/`
   - Linux: `~/.local/share/bitcoin-solo-miner-monitor/logs/`

**Network discovery not working**
1. Check firewall settings
2. Ensure the application has network permissions
3. Verify your miners are on the same network segment

## Uninstallation

### Windows
- Use "Add or Remove Programs" in Windows Settings
- Or run the uninstaller: `C:\Program Files\Bitcoin Solo Miner Monitor\Uninstall.exe`

### macOS
- Drag the application from Applications to Trash
- Remove application data: `~/Library/Application Support/Bitcoin Solo Miner Monitor/`

### Linux
```bash
# For .deb packages
sudo apt remove bitcoin-solo-miner-monitor

# For .rpm packages
sudo rpm -e bitcoin-solo-miner-monitor

# For AppImage
# Simply delete the AppImage file
```

## Getting Help

- **GitHub Issues**: [Report bugs and request features](https://github.com/your-repo/issues)
- **Documentation**: [Full documentation](https://github.com/your-repo/docs)
- **Community**: [Discussions and support](https://github.com/your-repo/discussions)

## Building from Source

See [BUILD.md](../BUILD.md) for detailed instructions on building the application and installers from source code.