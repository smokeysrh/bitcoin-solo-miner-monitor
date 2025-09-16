#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bitcoin Solo Miner Monitor - Documentation Updater
Updates download links and version information in documentation
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Ensure proper encoding for Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

class DocumentationUpdater:
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent.parent).resolve()
        self.docs_dir = self.project_root / "docs"
        
    def update_installation_readme(self, version: str, tag_name: str):
        """Update the main installation README with new download links"""
        readme_path = self.docs_dir / "installation" / "README.md"
        
        if not readme_path.exists():
            print(f"Warning: {readme_path} not found")
            return
        
        print(f"Updating {readme_path}...")
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update the quick links section with latest release
        latest_release_pattern = r'\[Download Latest Release\]\([^)]+\)'
        latest_release_replacement = f'[Download Latest Release](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/{tag_name})'
        content = re.sub(latest_release_pattern, latest_release_replacement, content)
        
        # Update any version-specific references
        version_pattern = r'v\d+\.\d+\.\d+'
        content = re.sub(version_pattern, f'v{version}', content)
        
        # Update the last modified date if there's a comment for it
        date_pattern = r'<!-- Last updated: [^>]+ -->'
        date_replacement = f'<!-- Last updated: {datetime.now().strftime("%Y-%m-%d")} -->'
        if re.search(date_pattern, content):
            content = re.sub(date_pattern, date_replacement, content)
        else:
            # Add date comment at the end
            content += f'\n\n<!-- Last updated: {datetime.now().strftime("%Y-%m-%d")} -->\n'
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Updated {readme_path}")
    
    def update_platform_installation_guides(self, version: str, tag_name: str):
        """Update platform-specific installation guides with new download links"""
        
        # Define platform-specific files and their download patterns
        platform_configs = {
            'windows-installation.md': {
                'download_pattern': r'BitcoinSoloMinerMonitor-[^-]+-Setup\.exe',
                'download_replacement': f'BitcoinSoloMinerMonitor-{version}-Setup.exe',
                'platform_name': 'Windows'
            },
            'macos-installation.md': {
                'download_pattern': r'BitcoinSoloMinerMonitor-[^.]+\.dmg',
                'download_replacement': f'BitcoinSoloMinerMonitor-{version}.dmg',
                'platform_name': 'macOS'
            },
            'linux-installation.md': {
                'download_pattern': r'BitcoinSoloMinerMonitor-[^-]+-[^.]+\.(deb|rpm|AppImage)',
                'download_replacement': f'BitcoinSoloMinerMonitor-{version}',
                'platform_name': 'Linux'
            }
        }
        
        for filename, config in platform_configs.items():
            file_path = self.docs_dir / "installation" / filename
            
            if not file_path.exists():
                print(f"Warning: {file_path} not found")
                continue
            
            print(f"Updating {file_path}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update download links with new version
            base_url = f"https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/{tag_name}"
            
            if filename == 'linux-installation.md':
                # Handle multiple Linux package formats
                patterns = [
                    (r'BitcoinSoloMinerMonitor-[^-]+-Ubuntu-20\.04\.deb', f'BitcoinSoloMinerMonitor-{version}-Ubuntu-20.04.deb'),
                    (r'BitcoinSoloMinerMonitor-[^-]+-Ubuntu-22\.04\.deb', f'BitcoinSoloMinerMonitor-{version}-Ubuntu-22.04.deb'),
                    (r'BitcoinSoloMinerMonitor-[^-]+-Fedora-38\.rpm', f'BitcoinSoloMinerMonitor-{version}-Fedora-38.rpm'),
                    (r'BitcoinSoloMinerMonitor-[^.]+\.AppImage', f'BitcoinSoloMinerMonitor-{version}.AppImage')
                ]
                
                for pattern, replacement in patterns:
                    content = re.sub(pattern, replacement, content)
            else:
                # Handle Windows and macOS
                content = re.sub(config['download_pattern'], config['download_replacement'], content)
            
            # Update any GitHub release URLs
            release_url_pattern = r'https://github\.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v[^/]+/'
            release_url_replacement = f'{base_url}/'
            content = re.sub(release_url_pattern, release_url_replacement, content)
            
            # Update version references in text
            version_pattern = r'version \d+\.\d+\.\d+'
            version_replacement = f'version {version}'
            content = re.sub(version_pattern, version_replacement, content, flags=re.IGNORECASE)
            
            # Update last modified date
            date_pattern = r'<!-- Last updated: [^>]+ -->'
            date_replacement = f'<!-- Last updated: {datetime.now().strftime("%Y-%m-%d")} -->'
            if re.search(date_pattern, content):
                content = re.sub(date_pattern, date_replacement, content)
            else:
                content += f'\n\n<!-- Last updated: {datetime.now().strftime("%Y-%m-%d")} -->\n'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Updated {file_path}")
    
    def update_main_readme(self, version: str, tag_name: str):
        """Update the main project README with new version information"""
        readme_path = self.project_root / "README.md"
        
        if not readme_path.exists():
            print(f"Warning: {readme_path} not found")
            return
        
        print(f"Updating {readme_path}...")
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update version badges if they exist
        version_badge_pattern = r'!\[Version\]\([^)]*badge[^)]*v[^)]*\)'
        if re.search(version_badge_pattern, content):
            version_badge_replacement = f'![Version](https://img.shields.io/badge/version-v{version}-blue)'
            content = re.sub(version_badge_pattern, version_badge_replacement, content)
        
        # Update download links
        download_pattern = r'\[Download Latest Release\]\([^)]+\)'
        download_replacement = f'[Download Latest Release](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/{tag_name})'
        content = re.sub(download_pattern, download_replacement, content)
        
        # Update any version references in installation sections
        version_pattern = r'v\d+\.\d+\.\d+'
        content = re.sub(version_pattern, f'v{version}', content)
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Updated {readme_path}")
    
    def create_download_page(self, version: str, tag_name: str):
        """Create or update a dedicated download page"""
        download_page_path = self.docs_dir / "DOWNLOADS.md"
        
        print(f"Creating/updating {download_page_path}...")
        
        base_url = f"https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/{tag_name}"
        
        content = f"""# Bitcoin Solo Miner Monitor - Downloads

## Latest Release: v{version}

**Release Date:** {datetime.now().strftime("%Y-%m-%d")}

### Quick Download Links

| Platform | Download | Size | Checksum |
|----------|----------|------|----------|
| **Windows** | [BitcoinSoloMinerMonitor-{version}-Setup.exe]({base_url}/BitcoinSoloMinerMonitor-{version}-Setup.exe) | ~45MB | [SHA256]({base_url}/SHA256SUMS) |
| **macOS** | [BitcoinSoloMinerMonitor-{version}.dmg]({base_url}/BitcoinSoloMinerMonitor-{version}.dmg) | ~50MB | [SHA256]({base_url}/SHA256SUMS) |
| **Linux (Ubuntu 20.04)** | [BitcoinSoloMinerMonitor-{version}-Ubuntu-20.04.deb]({base_url}/BitcoinSoloMinerMonitor-{version}-Ubuntu-20.04.deb) | ~35MB | [SHA256]({base_url}/SHA256SUMS) |
| **Linux (Ubuntu 22.04)** | [BitcoinSoloMinerMonitor-{version}-Ubuntu-22.04.deb]({base_url}/BitcoinSoloMinerMonitor-{version}-Ubuntu-22.04.deb) | ~35MB | [SHA256]({base_url}/SHA256SUMS) |
| **Linux (Fedora 38)** | [BitcoinSoloMinerMonitor-{version}-Fedora-38.rpm]({base_url}/BitcoinSoloMinerMonitor-{version}-Fedora-38.rpm) | ~35MB | [SHA256]({base_url}/SHA256SUMS) |
| **Linux (Universal)** | [BitcoinSoloMinerMonitor-{version}.AppImage]({base_url}/BitcoinSoloMinerMonitor-{version}.AppImage) | ~40MB | [SHA256]({base_url}/SHA256SUMS) |

### Verification Files

- **[SHA256SUMS]({base_url}/SHA256SUMS)** - Master checksum file for all downloads
- **[Release Notes](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/{tag_name})** - Full release information

## Installation Instructions

### Windows
1. Download `BitcoinSoloMinerMonitor-{version}-Setup.exe`
2. Right-click and select "Run as administrator"
3. Windows may show "Unknown Publisher" warning - click "More info" then "Run anyway"
4. Follow the installation wizard
5. Launch from desktop shortcut or Start menu

### macOS
1. Download `BitcoinSoloMinerMonitor-{version}.dmg`
2. Double-click to mount the disk image
3. Drag "Bitcoin Solo Miner Monitor" to Applications folder
4. Launch from Applications or Launchpad
5. macOS may show security warning - go to System Preferences > Security & Privacy to allow

### Linux

#### Ubuntu/Debian (.deb)
```bash
# Download the appropriate .deb file for your Ubuntu version
wget {base_url}/BitcoinSoloMinerMonitor-{version}-Ubuntu-22.04.deb

# Install the package
sudo dpkg -i BitcoinSoloMinerMonitor-{version}-Ubuntu-22.04.deb

# Fix any dependency issues
sudo apt-get install -f
```

#### Fedora/CentOS (.rpm)
```bash
# Download the RPM package
wget {base_url}/BitcoinSoloMinerMonitor-{version}-Fedora-38.rpm

# Install the package
sudo rpm -i BitcoinSoloMinerMonitor-{version}-Fedora-38.rpm
```

#### Universal Linux (AppImage)
```bash
# Download the AppImage
wget {base_url}/BitcoinSoloMinerMonitor-{version}.AppImage

# Make it executable
chmod +x BitcoinSoloMinerMonitor-{version}.AppImage

# Run the application
./BitcoinSoloMinerMonitor-{version}.AppImage
```

## Verification

### Why Verify Downloads?
- Ensures file integrity during download
- Confirms authenticity of the software
- Protects against malicious modifications

### How to Verify

1. **Download the checksum file:**
   ```bash
   wget {base_url}/SHA256SUMS
   ```

2. **Verify your download:**
   
   **Windows (PowerShell):**
   ```powershell
   Get-FileHash -Algorithm SHA256 BitcoinSoloMinerMonitor-{version}-Setup.exe
   ```
   
   **macOS/Linux:**
   ```bash
   shasum -a 256 BitcoinSoloMinerMonitor-{version}.dmg
   # or
   sha256sum BitcoinSoloMinerMonitor-{version}-Ubuntu-22.04.deb
   ```

3. **Compare the output** with the corresponding entry in `SHA256SUMS`

## Security Information

### Understanding Security Warnings

**Why you see warnings:**
- Open-source software without expensive code signing certificates
- Mining software commonly flagged by antivirus (false positives)
- "Unknown Publisher" warnings are normal for community-developed software

**This is standard in the Bitcoin ecosystem** - Bitcoin Core, Electrum, and most mining tools show similar warnings.

### Safe Installation Process

1. **Download only from official sources** (GitHub releases)
2. **Verify checksums** before installation
3. **Understand security warnings** are expected
4. **Use community verification** - all builds are reproducible

### Maximum Security: Build from Source

For maximum security, you can build from source and compare checksums:
- [Build Instructions](BUILD.md)
- [Reproducible Build Guide](docs/community/reproducible-builds.md)

## System Requirements

### Minimum Requirements
- **Windows**: Windows 10 or later (64-bit)
- **macOS**: macOS 10.15 (Catalina) or later
- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+, or equivalent
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 1GB free disk space
- **Network**: Internet connection for miner discovery

### Supported Hardware
- **Miners**: Bitaxe, Avalon Nano, Magic Miner, and other solo mining devices
- **Network**: Ethernet or Wi-Fi connection
- **Ports**: Application uses port 8000 by default (configurable)

## Previous Releases

For older versions, visit the [GitHub Releases page](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases).

## Support

### Getting Help
- **[Discord Community](https://discord.gg/GzNsNnh4yT)** - Real-time support and discussions
- **[Installation Guide](installation/README.md)** - Comprehensive installation instructions
- **[Troubleshooting Guide](installation/troubleshooting.md)** - Common issues and solutions
- **[GitHub Issues](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues)** - Bug reports and feature requests

### Quick Links
- [User Guide](user-guide.md) - Getting started after installation
- [Security Guide](installation/security-guide.md) - Detailed security information
- [Build Guide](BUILD.md) - Building from source

---

**Built by solo miners, for solo miners** 🚀⚡

<!-- Last updated: {datetime.now().strftime("%Y-%m-%d")} -->
"""
        
        with open(download_page_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Created/updated {download_page_path}")
    
    def update_user_guide(self, version: str, tag_name: str):
        """Update user guide with new version references"""
        user_guide_path = self.docs_dir / "user-guide.md"
        
        if not user_guide_path.exists():
            print(f"Warning: {user_guide_path} not found")
            return
        
        print(f"Updating {user_guide_path}...")
        
        with open(user_guide_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update installation guide links
        installation_link_pattern = r'\[Installation Guide\]\([^)]+\)'
        installation_link_replacement = '[Installation Guide](installation/README.md)'
        content = re.sub(installation_link_pattern, installation_link_replacement, content)
        
        # Update download links
        download_pattern = r'\[Download Latest Release\]\([^)]+\)'
        download_replacement = f'[Download Latest Release](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/{tag_name})'
        content = re.sub(download_pattern, download_replacement, content)
        
        # Update version references
        version_pattern = r'v\d+\.\d+\.\d+'
        content = re.sub(version_pattern, f'v{version}', content)
        
        with open(user_guide_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Updated {user_guide_path}")
    
    def update_all_documentation(self, version: str, tag_name: str):
        """Update all documentation files with new version information"""
        print(f"Updating all documentation for version {version}...")
        
        # Update main documentation files
        self.update_main_readme(version, tag_name)
        self.update_installation_readme(version, tag_name)
        self.update_platform_installation_guides(version, tag_name)
        self.update_user_guide(version, tag_name)
        
        # Create/update download page
        self.create_download_page(version, tag_name)
        
        print(f"All documentation updated for version {version}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Update documentation for Bitcoin Solo Miner Monitor release")
    parser.add_argument("version", help="Version string (e.g., 1.0.0)")
    parser.add_argument("--tag-name", help="Git tag name (defaults to v{version})")
    parser.add_argument("--project-root", help="Project root directory")
    
    args = parser.parse_args()
    
    tag_name = args.tag_name or f"v{args.version}"
    
    updater = DocumentationUpdater(args.project_root)
    updater.update_all_documentation(args.version, tag_name)

if __name__ == "__main__":
    main()