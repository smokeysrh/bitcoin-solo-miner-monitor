# Bitcoin Solo Miner Monitor - Installation Guide

## Overview

Bitcoin Solo Miner Monitor provides professional installers for Windows, macOS, and Linux platforms. This comprehensive guide covers installation methods, security considerations, and troubleshooting for each platform.

**🔒 Security First**: As Bitcoin-related software, we prioritize transparency and security. All installers are built from open source code with reproducible builds and community verification.

## 📋 Installation Quick Links

### Platform-Specific Guides
- **[Windows Installation Guide](windows-installation.md)** - Professional .exe installer with automatic dependencies
- **[macOS Installation Guide](macos-installation.md)** - Native .dmg disk image with drag-to-install
- **[Linux Installation Guide](linux-installation.md)** - DEB, RPM, and AppImage packages for all distributions

### Support Documentation
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions
- **[Security Guide](security-guide.md)** - Understanding and handling security warnings
- **[User Guide](../user-guide.md)** - Getting started after installation

## 🔒 Security and Trust

### Understanding Security Warnings

**Why you see warnings with open-source Bitcoin software:**
- No expensive code signing certificates ($300-500/year for individual developers)
- Mining software commonly flagged by antivirus (false positives)
- "Unknown Publisher" warnings are normal for community-developed software
- **This is standard in the Bitcoin ecosystem** - Bitcoin Core, Electrum, and most mining tools show similar warnings

### Safe Installation Process

**✅ Step 1: Verify Download Source**
- **Official source only**: [GitHub Releases](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases)
- **Check URL carefully**: Ensure exact match to avoid phishing

**✅ Step 2: Verify File Integrity**
- Download `SHA256SUMS` file from the same release
- Compare checksums before installation (detailed instructions in platform guides)
- **This proves file authenticity** without relying on certificates

**✅ Step 3: Handle Security Warnings Safely**
- Follow platform-specific instructions in our guides
- Understand why warnings appear (see [Security Guide](security-guide.md))
- Proceed confidently after verification

**🔧 Maximum Security: Build from Source**
- Complete instructions: [BUILD.md](../BUILD.md)
- Compare your build checksums with official releases
- **If checksums match, official releases are authentic**

### Community Verification System

- **🔍 Reproducible builds**: Anyone can verify our releases
- **📊 Public build logs**: All builds performed in public GitHub Actions
- **👥 Community checksums**: Independent verification by multiple users
- **📖 Open source**: Complete source code available for audit
- **🛡️ Transparent process**: No hidden steps or proprietary components

## System Requirements

### Minimum Requirements
- **Windows**: Windows 10 or later (64-bit)
- **macOS**: macOS 10.15 (Catalina) or later
- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+, or equivalent

### Recommended Requirements
- **RAM**: 4GB or more
- **Storage**: 1GB free disk space
- **Network**: Internet connection for miner discovery
- **Browser**: Modern web browser for dashboard access

### Hardware Compatibility
- **Supported Miners**: Bitaxe, Avalon Nano, Magic Miner
- **Network**: Ethernet or Wi-Fi connection
- **Ports**: Application uses port 8000 by default

## Installation Methods Comparison

| Method | Windows | macOS | Linux | Notes |
|--------|---------|-------|-------|-------|
| **Professional Installer** | ✅ .exe | ✅ .dmg | ✅ .deb/.rpm | Recommended for most users |
| **Portable/Universal** | ❌ | ❌ | ✅ AppImage | No installation required |
| **Package Manager** | ❌ | 🔄 Homebrew (planned) | 🔄 Community repos | Future enhancement |
| **Build from Source** | ✅ | ✅ | ✅ | Maximum security |

## Post-Installation

### First Launch
1. **Launch the application** using desktop shortcut or Start menu
2. **Configure network settings** for your mining setup
3. **Add your miners** using the discovery or manual configuration
4. **Access the dashboard** at `http://localhost:8000`

### Default Locations
- **Windows**: `C:\Program Files\Bitcoin Solo Miner Monitor\`
- **macOS**: `/Applications/Bitcoin Solo Miner Monitor.app`
- **Linux**: `/opt/bitcoin-solo-miner-monitor/` or `/usr/local/bin/`

### Data Storage
- **Windows**: `%APPDATA%\Bitcoin Solo Miner Monitor\`
- **macOS**: `~/Library/Application Support/Bitcoin Solo Miner Monitor/`
- **Linux**: `~/.local/share/bitcoin-solo-miner-monitor/`

## Getting Help

### Documentation
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions
- **[Security Guide](security-guide.md)** - Detailed security information
- **[Build Guide](../BUILD.md)** - Building from source

### Community Support
- **[Discord Server](https://discord.gg/GzNsNnh4yT)** - Real-time community support and discussions
- **[GitHub Issues](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions)** - Community support
- **[Project Documentation](../../README.md)** - Full project information

### Quick Links
- [Download Latest Release](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/latest)
- [Verify Checksums](security-guide.md#checksum-verification)
- [Report Installation Issues](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues/new?template=installation-issue.md)

---

**Built by solo miners, for solo miners** 🚀⚡

This application is developed entirely by the Bitcoin solo mining community. Your feedback and contributions help make it better for everyone!