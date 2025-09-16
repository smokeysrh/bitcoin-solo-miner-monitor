---
name: Installation Issue
about: Report problems with installing Bitcoin Solo Miner Monitor
title: '[INSTALL] '
labels: ['installation', 'bug']
assignees: ''
---

## Installation Issue Report

**Before submitting**, please check:
- [ ] I downloaded from the official [GitHub Releases](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases) page
- [ ] I verified the SHA256 checksum of my download
- [ ] I checked the [Troubleshooting Guide](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/blob/main/docs/installation/troubleshooting.md)
- [ ] I searched existing issues for similar problems

## System Information

**Operating System:**
- [ ] Windows (version: _____)
- [ ] macOS (version: _____)
- [ ] Linux (distribution: _____, version: _____)

**Installation Method:**
- [ ] Windows .exe installer
- [ ] macOS .dmg package
- [ ] Linux .deb package
- [ ] Linux .rpm package
- [ ] Linux AppImage
- [ ] Built from source

**System Specifications:**
- RAM: _____ GB
- Available disk space: _____ GB
- Python version (if applicable): _____
- Antivirus software: _____

## Problem Description

**What happened:**
<!-- Describe the installation issue in detail -->

**What you expected:**
<!-- Describe what you expected to happen -->

**When it occurs:**
- [ ] During download
- [ ] During installation
- [ ] After installation (first launch)
- [ ] During uninstallation

## Error Details

**Error messages:**
```
Paste any error messages here
```

**Screenshots:**
<!-- If applicable, add screenshots to help explain the problem -->

**Installation logs:**
<!-- 
Windows: Check Windows Event Viewer (eventvwr.msc) → Windows Logs → Application
macOS: Check Console.app for installation-related errors
Linux: Check system logs with journalctl or /var/log/
-->

```
Paste relevant log entries here
```

## Steps to Reproduce

1. 
2. 
3. 
4. 

## Security Warnings

**Did you encounter security warnings?**
- [ ] Windows SmartScreen warning
- [ ] macOS Gatekeeper warning
- [ ] Antivirus detection/blocking
- [ ] Linux package signature warning
- [ ] Other: _____

**How did you handle them:**
<!-- Describe what you did when you saw security warnings -->

## Troubleshooting Attempted

**What you've already tried:**
- [ ] Ran installer as administrator/sudo
- [ ] Temporarily disabled antivirus
- [ ] Downloaded file again
- [ ] Verified checksum
- [ ] Tried different browser
- [ ] Cleared browser cache
- [ ] Restarted computer
- [ ] Other: _____

## Network Environment

**Network configuration:**
- [ ] Home network
- [ ] Corporate/enterprise network
- [ ] Public WiFi
- [ ] VPN connection
- [ ] Proxy server

**Firewall/Security:**
- [ ] Windows Firewall enabled
- [ ] Third-party firewall: _____
- [ ] Corporate security policies
- [ ] Parental controls

## Additional Context

**Anything else that might be relevant:**
<!-- 
- Previous installations of similar software
- Recent system changes
- Other mining software installed
- Hardware-specific issues
-->

## Verification Information

**Download verification:**
- Download URL: _____
- File size: _____ bytes
- SHA256 checksum: _____
- Checksum verified: [ ] Yes [ ] No

**File information:**
```bash
# Windows (PowerShell)
Get-FileHash -Algorithm SHA256 filename.exe
Get-ItemProperty filename.exe | Select-Object Name, Length, CreationTime

# macOS/Linux
shasum -a 256 filename.dmg
ls -la filename.deb
```

---

**For the development team:**
- Installation method: _____
- Error category: _____
- Priority: [ ] Low [ ] Medium [ ] High [ ] Critical
- Affects: [ ] Single user [ ] Multiple users [ ] All users

---

## Community Support

Need immediate help? Join our community:

- **[Discord Server](https://discord.gg/GzNsNnh4yT)** - Real-time community support and discussions
- **[GitHub Discussions](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions)** - Community support
- **[Troubleshooting Guide](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/blob/main/docs/installation/troubleshooting.md)** - Common solutions