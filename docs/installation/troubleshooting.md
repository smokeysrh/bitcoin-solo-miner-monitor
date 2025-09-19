# Installation Troubleshooting Guide

## Overview

This guide covers common installation issues and their solutions for Bitcoin Solo Miner Monitor across all platforms. Issues are organized by category for quick resolution.

## Quick Diagnosis

### Step 1: Identify Your Issue Category

| Symptom | Category | Quick Fix |
|---------|----------|-----------|
| **Can't download installer** | [Download Issues](#download-issues) | Check internet, verify URL |
| **Security warnings during download/install** | [Security Warnings](#security-warnings) | Normal for open-source, verify checksums |
| **Installation fails or crashes** | [Installation Failures](#installation-failures) | Run as admin, check logs |
| **App won't start after install** | [Runtime Issues](#runtime-issues) | Check dependencies, ports |
| **Can't find miners** | [Network Discovery](#network-discovery-issues) | Check firewall, network settings |
| **Performance problems** | [Performance Issues](#performance-issues) | Check resources, close other apps |

### Step 2: Gather System Information

Before troubleshooting, collect this information:

**Windows**:
```powershell
# System info
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory
Get-NetAdapter | Where-Object Status -eq "Up"
python --version
```

**macOS**:
```bash
# System info
sw_vers
system_profiler SPHardwareDataType | grep "Memory:"
python3 --version
```

**Linux**:
```bash
# System info
uname -a
lsb_release -a
free -h
python3 --version
```

## Download Issues

### Cannot Access GitHub Releases

**Symptoms**:
- "Site can't be reached" error
- Download links don't work
- Slow or failed downloads

**Solutions**:

1. **Check GitHub Status**:
   - Visit [GitHub Status](https://www.githubstatus.com/)
   - Try again if GitHub is experiencing issues

2. **Network Connectivity**:
   ```bash
   # Test connectivity
   ping github.com
   nslookup github.com
   ```

3. **Corporate Firewall/Proxy**:
   ```bash
   # Configure git proxy if needed
   git config --global http.proxy http://proxy.company.com:8080
   git config --global https.proxy https://proxy.company.com:8080
   ```

4. **Alternative Download Methods**:
   ```bash
   # Using curl
   curl -L -O https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v0.1.0/BitcoinSoloMinerMonitor-Setup.exe
   
   # Using wget
   wget https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v0.1.0/BitcoinSoloMinerMonitor-Setup.exe
   ```

### Corrupted Downloads

**Symptoms**:
- Installer won't run
- "File is corrupted" errors
- Checksum verification fails

**Solutions**:

1. **Verify Download Integrity**:
   ```bash
   # Windows (PowerShell)
   Get-FileHash -Algorithm SHA256 BitcoinSoloMinerMonitor-Setup.exe
   
   # macOS/Linux
   shasum -a 256 BitcoinSoloMinerMonitor.dmg
   sha256sum bitcoin-solo-miner-monitor_0.1.0_amd64.deb
   ```

2. **Re-download from Different Location**:
   - Try different browser
   - Use command-line tools
   - Download from different network

3. **Clear Browser Cache**:
   - Clear downloads cache
   - Disable browser extensions
   - Try incognito/private mode

## Security Warnings

### Windows SmartScreen

**Warning Message**:
> "Windows protected your PC - Microsoft Defender SmartScreen prevented an unrecognized app from starting"

**Why This Happens**:
- Open-source software lacks expensive code signing certificates
- New or infrequently downloaded applications trigger warnings
- This is normal and expected for community-developed software

**Safe Resolution**:
1. **Verify Download Source**: Ensure you downloaded from official GitHub releases
2. **Check Checksum**: Verify SHA256 hash matches official release
3. **Proceed Safely**: Click "More info" → "Run anyway"

**Alternative Solutions**:
```powershell
# Temporarily disable SmartScreen (not recommended)
Set-MpPreference -EnableNetworkProtection Disabled

# Re-enable after installation
Set-MpPreference -EnableNetworkProtection Enabled
```

### macOS Gatekeeper

**Warning Message**:
> "App can't be opened because it is from an unidentified developer"

**Safe Resolution**:
1. **System Preferences Method**:
   - System Preferences → Security & Privacy
   - Click "Open Anyway" next to the blocked app message

2. **Right-click Method**:
   - Right-click the app → "Open"
   - Click "Open" in confirmation dialog

3. **Terminal Method** (Advanced):
   ```bash
   # Remove quarantine attribute
   xattr -d com.apple.quarantine /path/to/app
   
   # Or for the entire application bundle
   xattr -cr "/Applications/Bitcoin Solo Miner Monitor.app"
   ```

### Linux Package Warnings

**Warning Message**:
> "Package is not signed" or "Untrusted package"

**Safe Resolution**:
```bash
# Ubuntu/Debian - install anyway
sudo dpkg -i --force-depends bitcoin-solo-miner-monitor_0.1.0_amd64.deb

# Fedora/CentOS - skip signature check
sudo rpm -i --nosignature bitcoin-solo-miner-monitor-0.1.0-1.x86_64.rpm

# Or verify checksums manually first
sha256sum -c SHA256SUMS --ignore-missing
```

## Installation Failures

### Windows Installation Issues

**"Installation failed" or "Access denied"**:

1. **Run as Administrator**:
   - Right-click installer → "Run as administrator"
   - Confirm UAC prompt

2. **Disable Antivirus Temporarily**:
   - Disable real-time protection during installation
   - Re-enable immediately after installation

3. **Check Windows Event Viewer**:
   ```powershell
   # Open Event Viewer
   eventvwr.msc
   
   # Look for errors in:
   # Windows Logs → Application
   # Applications and Services Logs → MsiInstaller
   ```

4. **Clear Windows Installer Cache**:
   ```cmd
   # Stop Windows Installer service
   net stop msiserver
   
   # Clear cache
   del /q "%WINDIR%\Installer\*.msi"
   
   # Restart service
   net start msiserver
   ```

**"Python installation failed"**:

1. **Manual Python Installation**:
   ```powershell
   # Download and install Python 3.11+
   Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe" -OutFile "python-installer.exe"
   .\python-installer.exe /quiet InstallAllUsers=1 PrependPath=1
   ```

2. **Verify Python Installation**:
   ```cmd
   python --version
   pip --version
   ```

### macOS Installation Issues

**"App is damaged and can't be opened"**:

1. **Re-download the DMG**:
   - Download may be corrupted
   - Try different browser or network

2. **Clear Quarantine Attributes**:
   ```bash
   # For DMG file
   xattr -d com.apple.quarantine ~/Downloads/BitcoinSoloMinerMonitor.dmg
   
   # For installed app
   xattr -cr "/Applications/Bitcoin Solo Miner Monitor.app"
   ```

3. **Check Disk Space**:
   ```bash
   df -h /Applications
   # Ensure at least 500MB free space
   ```

**DMG Won't Mount**:

1. **Manual Mount**:
   ```bash
   hdiutil attach ~/Downloads/BitcoinSoloMinerMonitor.dmg
   ```

2. **Repair Disk Permissions**:
   ```bash
   sudo diskutil repairPermissions /
   ```

3. **Check Console for Errors**:
   - Applications → Utilities → Console
   - Look for mount-related errors

### Linux Installation Issues

**"Package has unmet dependencies"**:

1. **Update Package Lists**:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install -f
   
   # Fedora
   sudo dnf update
   sudo dnf install --best --allowerasing bitcoin-solo-miner-monitor
   ```

2. **Install Dependencies Manually**:
   ```bash
   # Common dependencies
   sudo apt install python3 python3-pip python3-dev build-essential
   sudo dnf install python3 python3-pip python3-devel gcc
   ```

**AppImage Won't Execute**:

1. **Check FUSE Installation**:
   ```bash
   # Install FUSE
   sudo apt install fuse libfuse2  # Ubuntu/Debian
   sudo dnf install fuse fuse-libs  # Fedora
   ```

2. **Verify Permissions**:
   ```bash
   chmod +x BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage
   ls -la BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage
   ```

3. **Run with Debug Output**:
   ```bash
   ./BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage --appimage-debug
   ```

## Runtime Issues

### Application Won't Start

**Common Causes and Solutions**:

1. **Port Already in Use**:
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # macOS/Linux
   lsof -i :8000
   netstat -tlnp | grep :8000
   
   # Kill conflicting process
   kill -9 <PID>
   ```

2. **Missing Dependencies**:
   ```bash
   # Check Python installation
   python3 --version
   pip3 --version
   
   # Install missing packages
   pip3 install -r requirements.txt
   ```

3. **Permission Issues**:
   ```bash
   # Linux - fix permissions
   sudo chown -R $USER:$USER ~/.local/share/bitcoin-solo-miner-monitor/
   chmod +x /opt/bitcoin-solo-miner-monitor/bin/bitcoin-solo-miner-monitor
   ```

### Dashboard Not Accessible

**Symptoms**:
- Browser shows "This site can't be reached"
- Connection timeout errors
- Blank page loads

**Solutions**:

1. **Check Application Status**:
   ```bash
   # Windows
   tasklist | findstr python
   
   # macOS/Linux
   ps aux | grep bitcoin-solo-miner-monitor
   ```

2. **Try Alternative URLs**:
   - `http://localhost:8000`
   - `http://127.0.0.1:8000`
   - `http://[your-ip]:8000`

3. **Check Firewall Settings**:
   ```bash
   # Windows - allow through firewall
   netsh advfirewall firewall add rule name="Bitcoin Solo Miner Monitor" dir=in action=allow protocol=TCP localport=8000
   
   # Linux - UFW
   sudo ufw allow 8000/tcp
   
   # Linux - Firewalld
   sudo firewall-cmd --permanent --add-port=8000/tcp
   sudo firewall-cmd --reload
   ```

4. **Check Application Logs**:
   - **Windows**: `%APPDATA%\Bitcoin Solo Miner Monitor\logs\`
   - **macOS**: `~/Library/Logs/Bitcoin Solo Miner Monitor/`
   - **Linux**: `~/.local/share/bitcoin-solo-miner-monitor/logs/`

## Network Discovery Issues

### Miners Not Found

**Symptoms**:
- No miners appear in discovery
- "Network scan completed - 0 miners found"
- Specific miners not detected

**Diagnostic Steps**:

1. **Verify Network Connectivity**:
   ```bash
   # Test basic connectivity
   ping 192.168.1.1  # Your router IP
   ping 192.168.1.100  # Known miner IP
   
   # Test miner API directly
   curl http://192.168.1.100/api/system/info
   ```

2. **Check Network Configuration**:
   ```bash
   # Windows
   ipconfig /all
   
   # macOS/Linux
   ifconfig
   ip addr show
   ```

3. **Verify Miner Accessibility**:
   ```bash
   # Scan network for active devices
   nmap -sn 192.168.1.0/24
   
   # Test specific miner ports
   nmap -p 80,4028 192.168.1.100
   ```

**Common Solutions**:

1. **Firewall Configuration**:
   ```bash
   # Allow network discovery
   # Windows
   netsh advfirewall firewall set rule group="Network Discovery" new enable=Yes
   
   # Linux
   sudo ufw allow from 192.168.0.0/16
   ```

2. **Network Range Configuration**:
   - Ensure application scans correct IP range
   - Check if miners are on different subnet
   - Configure custom IP ranges in settings

3. **Miner-Specific Issues**:
   - **Bitaxe**: Ensure HTTP API is enabled
   - **Avalon Nano**: Check CGMiner API port (4028)
   - **Magic Miner**: Verify web interface accessibility

### Network Performance Issues

**Symptoms**:
- Slow miner discovery
- Frequent connection timeouts
- Intermittent data updates

**Solutions**:

1. **Adjust Scan Settings**:
   - Increase timeout values
   - Reduce concurrent connections
   - Limit scan range

2. **Network Optimization**:
   ```bash
   # Check network latency
   ping -c 10 192.168.1.100
   
   # Monitor network usage
   # Windows
   netstat -e
   
   # Linux
   iftop
   nethogs
   ```

3. **Router Configuration**:
   - Enable UPnP if needed
   - Check for bandwidth limitations
   - Verify QoS settings

## Performance Issues

### High CPU/Memory Usage

**Symptoms**:
- System becomes slow
- High resource usage in Task Manager
- Application becomes unresponsive

**Solutions**:

1. **Check Resource Usage**:
   ```bash
   # Windows
   tasklist /fi "imagename eq python.exe"
   
   # macOS/Linux
   top -p $(pgrep -f bitcoin-solo-miner-monitor)
   htop
   ```

2. **Optimize Settings**:
   - Reduce update frequency
   - Limit number of monitored miners
   - Disable unnecessary features

3. **System Optimization**:
   ```bash
   # Close unnecessary applications
   # Increase virtual memory (Windows)
   # Check for system updates
   ```

### Slow Dashboard Loading

**Symptoms**:
- Dashboard takes long to load
- Charts don't update
- Slow page transitions

**Solutions**:

1. **Browser Optimization**:
   - Clear browser cache
   - Disable browser extensions
   - Try different browser

2. **Network Optimization**:
   - Check local network speed
   - Reduce chart data retention
   - Optimize database queries

## Advanced Troubleshooting

### Debug Mode

Enable debug logging for detailed troubleshooting:

**Windows**:
```cmd
cd "C:\Program Files\Bitcoin Solo Miner Monitor"
python main.py --debug --log-level DEBUG
```

**macOS**:
```bash
"/Applications/Bitcoin Solo Miner Monitor.app/Contents/MacOS/Bitcoin Solo Miner Monitor" --debug
```

**Linux**:
```bash
bitcoin-solo-miner-monitor --debug --verbose
```

### Log Analysis

**Log Locations**:
- **Windows**: `%APPDATA%\Bitcoin Solo Miner Monitor\logs\app.log`
- **macOS**: `~/Library/Logs/Bitcoin Solo Miner Monitor/app.log`
- **Linux**: `~/.local/share/bitcoin-solo-miner-monitor/logs/app.log`

**Common Log Patterns**:
```bash
# Search for errors
grep -i error app.log

# Search for network issues
grep -i "connection\|timeout\|network" app.log

# Search for miner-specific issues
grep -i "bitaxe\|avalon\|magic" app.log
```

### Database Issues

**Symptoms**:
- Data not saving
- Configuration resets
- Performance degradation

**Solutions**:

1. **Check Database File**:
   ```bash
   # Verify database exists and is accessible
   ls -la ~/.local/share/bitcoin-solo-miner-monitor/data/
   
   # Check database integrity
   sqlite3 config.db "PRAGMA integrity_check;"
   ```

2. **Reset Database**:
   ```bash
   # Backup current database
   cp config.db config.db.backup
   
   # Delete corrupted database (will be recreated)
   rm config.db
   ```

### Network Debugging

**Packet Capture**:
```bash
# Linux - capture network traffic
sudo tcpdump -i any -w bitcoin-monitor.pcap port 8000 or port 4028

# Analyze with Wireshark
wireshark bitcoin-monitor.pcap
```

**API Testing**:
```bash
# Test miner APIs directly
curl -v http://192.168.1.100/api/system/info
curl -v http://192.168.1.100:4028 -d '{"command":"summary"}'
```

## Getting Help

### Before Requesting Support

1. **Check existing issues**: [GitHub Issues](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues)
2. **Search documentation**: [Project Wiki](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/wiki)
3. **Gather system information** (see Quick Diagnosis section)
4. **Collect relevant logs** with debug mode enabled

### Creating Support Requests

**Include this information**:
- Operating system and version
- Installation method used
- Complete error messages
- Steps to reproduce the issue
- Relevant log excerpts
- Network configuration details

**Use appropriate templates**:
- [Bug Report](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues/new?template=bug_report.md)
- [Installation Issue](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues/new?template=installation-issue.md)
- [Feature Request](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues/new?template=feature_request.md)

### Community Resources

- **[Discord Server](https://discord.gg/GzNsNnh4yT)** - Real-time community support and discussions
- **[GitHub Discussions](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions)** - Community support
- **[Project Documentation](../../README.md)** - Complete project information
- **[Build Guide](../BUILD.md)** - Building from source
- **[Security Guide](security-guide.md)** - Security-related questions

---

**Still having issues?** Don't hesitate to reach out to the community - we're here to help fellow solo miners succeed! 🚀⚡