# Security Guide

## Overview

Security is paramount when installing Bitcoin-related software. This guide explains how to safely install and verify Bitcoin Solo Miner Monitor, understand security warnings, and protect your mining operations.

## 🔒 Security Philosophy

**Open Source Security**: We believe in transparency and community verification rather than relying on expensive certificates or centralized authorities. This approach aligns with Bitcoin's decentralized principles.

**Community Trust**: Our security model is based on:
- **Open source code** - Anyone can audit the software
- **Reproducible builds** - Anyone can verify our releases
- **Community verification** - Multiple people check our work
- **Transparent processes** - All builds happen in public

## Understanding Security Warnings

### Why You See Security Warnings

**Common warnings you'll encounter**:
- "Unknown Publisher" (Windows)
- "Unidentified Developer" (macOS)
- "Unsigned Package" (Linux)
- Antivirus false positives

**Why these warnings appear**:

1. **Code Signing Certificates Cost $300-500/year**
   - Individual developers often can't afford these
   - Many legitimate open-source projects show similar warnings
   - Certificate authorities don't validate software quality, only identity

2. **Mining Software Triggers Antivirus**
   - Mining software shares characteristics with malicious miners
   - Antivirus software uses heuristics that flag legitimate mining tools
   - This is a known issue across the entire mining ecosystem

3. **New Software Lacks "Reputation"**
   - Operating systems track download frequency
   - New or infrequently downloaded software triggers warnings
   - This is normal for specialized tools like mining software

### This is Normal in Bitcoin Ecosystem

**Popular Bitcoin software with similar warnings**:
- Bitcoin Core (official Bitcoin client)
- Electrum wallet
- BTCPay Server
- Most mining software (CGMiner, BFGMiner, etc.)
- Hardware wallet software

**The Bitcoin community has established practices** for safely installing software without relying on centralized certificate authorities.

## Safe Installation Practices

### 1. Verify Download Source

**✅ Safe Sources**:
- Official GitHub releases: `https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases`
- Direct links from project documentation

**❌ Unsafe Sources**:
- Third-party download sites
- Torrents or file sharing
- Email attachments
- Social media links

**Verification Steps**:
```bash
# Check the URL carefully
# Correct: https://github.com/smokeysrh/bitcoin-solo-miner-monitor
# Incorrect: https://github.com/smokeysrh/bitcoin-solo-miner-monitr (missing 'o')
# Incorrect: https://githab.com/smokeysrh/bitcoin-solo-miner-monitor (wrong domain)
```

### 2. Checksum Verification

**Why checksums matter**:
- Detect corrupted downloads
- Verify file integrity
- Ensure you have the exact file we built

**How to verify checksums**:

**Windows (PowerShell)**:
```powershell
# Download the checksums file
Invoke-WebRequest -Uri "https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v1.0.0/SHA256SUMS" -OutFile "SHA256SUMS"

# Calculate checksum of your download
Get-FileHash -Algorithm SHA256 BitcoinSoloMinerMonitor-Setup.exe

# Compare with the value in SHA256SUMS file
Get-Content SHA256SUMS | Select-String "BitcoinSoloMinerMonitor-Setup.exe"
```

**macOS**:
```bash
# Download checksums
curl -O https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v1.0.0/SHA256SUMS

# Verify your download
shasum -a 256 BitcoinSoloMinerMonitor.dmg

# Compare with checksums file
grep "BitcoinSoloMinerMonitor.dmg" SHA256SUMS
```

**Linux**:
```bash
# Download checksums
wget https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v1.0.0/SHA256SUMS

# Verify all downloads at once
sha256sum -c SHA256SUMS --ignore-missing

# Or verify specific file
sha256sum bitcoin-solo-miner-monitor_1.0.0_amd64.deb
grep "bitcoin-solo-miner-monitor_1.0.0_amd64.deb" SHA256SUMS
```

### 3. Reproducible Build Verification

**For maximum security**, build from source and compare checksums:

```bash
# Clone the repository
git clone https://github.com/smokeysrh/bitcoin-solo-miner-monitor.git
cd bitcoin-solo-miner-monitor

# Checkout the exact release tag
git checkout v1.0.0

# Build the installer
python scripts/create-distribution.py --version 1.0.0

# Compare your build checksum with official release
sha256sum distribution/windows/BitcoinSoloMinerMonitor-Setup.exe
```

**If checksums match**, you can be confident the official release is authentic.

## Handling Security Warnings Safely

### Windows SmartScreen

**When you see**:
> "Windows protected your PC - Microsoft Defender SmartScreen prevented an unrecognized app from starting"

**Safe procedure**:
1. ✅ **Verify you downloaded from official GitHub releases**
2. ✅ **Confirm checksum matches** (see above)
3. ✅ **Click "More info"** → **"Run anyway"**

**Why this is safe**:
- You've verified the file integrity with checksums
- You downloaded from the official source
- The warning is about publisher identity, not malicious content

### macOS Gatekeeper

**When you see**:
> "App can't be opened because it is from an unidentified developer"

**Safe procedure**:
1. ✅ **Verify checksum first** (see above)
2. ✅ **Right-click the app** → **"Open"**
3. ✅ **Click "Open"** in the confirmation dialog

**Alternative method**:
- System Preferences → Security & Privacy → Click "Open Anyway"

### Linux Package Warnings

**When you see**:
> "Package is not signed" or "Untrusted package"

**Safe procedure**:
1. ✅ **Verify checksum first** (see above)
2. ✅ **Install with appropriate flags**:
   ```bash
   # Ubuntu/Debian
   sudo dpkg -i bitcoin-solo-miner-monitor_1.0.0_amd64.deb
   
   # Fedora/CentOS
   sudo rpm -i bitcoin-solo-miner-monitor-1.0.0-1.x86_64.rpm
   ```

## Antivirus Considerations

### Why Mining Software Gets Flagged

**Common reasons**:
- **Network scanning behavior** (looking for miners)
- **System resource monitoring** (CPU, memory usage)
- **Background processes** (continuous monitoring)
- **Cryptocurrency-related keywords** in code

**This affects all mining software**, not just ours.

### Safe Antivirus Handling

**Before installation**:
1. ✅ **Verify checksums** (proves file integrity)
2. ✅ **Scan with multiple antivirus engines** at [VirusTotal](https://www.virustotal.com/)
3. ✅ **Check community reports** on GitHub issues

**During installation**:
1. **Temporarily disable real-time protection**
2. **Install the software**
3. **Re-enable protection immediately**
4. **Add exclusions for installation directory**

**Exclusion directories**:
- **Windows**: `C:\Program Files\Bitcoin Solo Miner Monitor\`
- **macOS**: `/Applications/Bitcoin Solo Miner Monitor.app`
- **Linux**: `/opt/bitcoin-solo-miner-monitor/`

### Popular Antivirus Exclusion Instructions

**Windows Defender**:
1. Windows Security → Virus & threat protection
2. Manage settings → Add or remove exclusions
3. Add folder → Browse to installation directory

**Avast/AVG**:
1. Settings → General → Exceptions
2. Add exception → File path
3. Browse to installation directory

**Norton**:
1. Settings → Antivirus → Scans and Risks
2. Exclusions/Low Risks → Configure
3. Add folder exclusion

**McAfee**:
1. Virus and Spyware Protection → Real-Time Scanning
2. Excluded Files → Add file
3. Browse to installation directory

## Network Security

### Application Network Behavior

**What the application does**:
- ✅ **Scans local network** for miners (192.168.x.x range)
- ✅ **Connects to miners** via HTTP/TCP (ports 80, 4028)
- ✅ **Serves web dashboard** on localhost:8000
- ✅ **Checks for updates** from GitHub (optional)

**What the application does NOT do**:
- ❌ **Send mining data externally**
- ❌ **Connect to mining pools** (miners do this directly)
- ❌ **Access personal files** outside its data directory
- ❌ **Install additional software** without permission

### Firewall Configuration

**Recommended firewall rules**:

**Windows**:
```cmd
# Allow application through Windows Firewall
netsh advfirewall firewall add rule name="Bitcoin Solo Miner Monitor" dir=in action=allow protocol=TCP localport=8000
```

**macOS**:
```bash
# Allow through macOS firewall (if enabled)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add "/Applications/Bitcoin Solo Miner Monitor.app"
```

**Linux (UFW)**:
```bash
# Allow local dashboard access
sudo ufw allow 8000/tcp

# Allow from local network only
sudo ufw allow from 192.168.0.0/16 to any port 8000
```

### Network Isolation

**For maximum security**:
1. **Dedicated mining network** - Separate VLAN for mining equipment
2. **Firewall rules** - Block internet access for mining devices
3. **VPN access** - Remote monitoring through VPN only
4. **Network monitoring** - Log all network traffic

## Data Security

### What Data is Stored

**Configuration data**:
- Miner IP addresses and connection settings
- Dashboard preferences and user settings
- Historical performance data (local only)

**What is NOT stored**:
- Private keys or wallet information
- Mining pool credentials
- Personal identification information
- External account information

### Data Storage Locations

**Windows**: `%APPDATA%\Bitcoin Solo Miner Monitor\`
**macOS**: `~/Library/Application Support/Bitcoin Solo Miner Monitor/`
**Linux**: `~/.local/share/bitcoin-solo-miner-monitor/`

### Data Protection

**Backup recommendations**:
```bash
# Create backup of configuration
# Windows
xcopy "%APPDATA%\Bitcoin Solo Miner Monitor" "C:\Backup\BitcoinMonitor" /E /I

# macOS
cp -R "~/Library/Application Support/Bitcoin Solo Miner Monitor" ~/Backup/

# Linux
cp -R ~/.local/share/bitcoin-solo-miner-monitor ~/backup/
```

**Secure deletion** (when uninstalling):
```bash
# Windows
sdelete -p 3 -s -z "C:\Program Files\Bitcoin Solo Miner Monitor"

# macOS/Linux
shred -vfz -n 3 ~/.local/share/bitcoin-solo-miner-monitor/*
```

## Community Verification

### How to Verify Our Claims

**Check our build process**:
1. **GitHub Actions logs** are public - see exactly how we build
2. **Source code** is open - audit any part of the application
3. **Build scripts** are included - reproduce builds yourself
4. **Community reports** - other users share their verification results

**Participate in verification**:
1. **Build from source** and compare checksums
2. **Report your results** in GitHub discussions
3. **Share verification scripts** with the community
4. **Audit source code** and report findings

### Community Resources

**Verification discussions**:
- [GitHub Discussions - Security](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions/categories/security)
- [Community Build Verification](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions/categories/build-verification)

**Security reporting**:
- [Security Issues](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/security/advisories)
- [Bug Bounty Program](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/security/policy) (if available)

## Incident Response

### If You Suspect Compromise

**Immediate steps**:
1. **Disconnect from network** - Isolate the system
2. **Stop the application** - Terminate all processes
3. **Scan with multiple antivirus** engines
4. **Check network logs** for unusual activity
5. **Report to community** - Help others stay safe

**Investigation steps**:
1. **Verify file checksums** - Compare with known good values
2. **Check file timestamps** - Look for unexpected modifications
3. **Review network connections** - Ensure only expected traffic
4. **Examine system logs** - Look for suspicious activity

### Reporting Security Issues

**For security vulnerabilities**:
- **Email**: security@bitcoinsoloapp.com (if available)
- **GitHub Security**: Use private security advisory
- **PGP encryption**: Use our public key for sensitive reports

**For general security questions**:
- **GitHub Discussions**: Public security discussions
- **GitHub Issues**: Non-sensitive security topics

## Security Best Practices

### System Hardening

**Operating system security**:
- ✅ **Keep OS updated** - Install security patches promptly
- ✅ **Use standard user accounts** - Don't run as administrator/root
- ✅ **Enable automatic updates** - For critical security fixes
- ✅ **Use strong passwords** - For system accounts

**Network security**:
- ✅ **Secure your router** - Change default passwords
- ✅ **Use WPA3 encryption** - For wireless networks
- ✅ **Disable unnecessary services** - Reduce attack surface
- ✅ **Monitor network traffic** - Watch for unusual activity

### Mining Security

**Miner protection**:
- ✅ **Change default passwords** - On all mining devices
- ✅ **Update firmware regularly** - Install security patches
- ✅ **Use dedicated network** - Isolate mining equipment
- ✅ **Monitor for unauthorized access** - Check logs regularly

**Pool security**:
- ✅ **Use reputable pools** - Research pool operators
- ✅ **Monitor payouts** - Verify expected payments
- ✅ **Use separate wallets** - Don't reuse addresses
- ✅ **Enable 2FA** - Where supported by pools

## Conclusion

**Security in the Bitcoin ecosystem** requires understanding that:
- Open source software often shows security warnings
- Community verification is more trustworthy than certificates
- Transparency and reproducibility provide real security
- The Bitcoin community has established practices for safe installation

**By following this guide**, you can safely install and use Bitcoin Solo Miner Monitor while maintaining the security principles that make Bitcoin valuable.

**Remember**: When in doubt, build from source and verify checksums. The Bitcoin community is here to help you stay secure! 🔒⚡

---

**Questions about security?** Join the discussion in our [Security Forum](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions/categories/security) or review our [Security Policy](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/security/policy).