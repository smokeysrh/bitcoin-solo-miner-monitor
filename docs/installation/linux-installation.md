# Linux Installation Guide

## Overview

Bitcoin Solo Miner Monitor provides multiple installation options for Linux: DEB packages (Ubuntu/Debian), RPM packages (Fedora/CentOS), and AppImage (universal). Choose the method that best fits your distribution.

## Quick Installation by Distribution

| Distribution | Recommended Method | Package Type |
|--------------|-------------------|--------------|
| **Ubuntu/Debian** | APT package | `.deb` |
| **Fedora/CentOS/RHEL** | DNF/YUM package | `.rpm` |
| **Arch Linux** | AUR (community) | `PKGBUILD` |
| **Other/Universal** | AppImage | `.AppImage` |

## Download

1. **Go to the official releases page**: [GitHub Releases](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/latest)

2. **Download for your distribution**:
   - **Ubuntu/Debian**: `bitcoin-solo-miner-monitor_0.1.0_amd64.deb`
   - **Fedora/CentOS**: `bitcoin-solo-miner-monitor-0.1.0-1.x86_64.rpm`
   - **Universal**: `BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage`

3. **Verify the download** (recommended):
   ```bash
   # Download checksums
   wget https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v0.1.0/SHA256SUMS
   
   # Verify your download
   sha256sum -c SHA256SUMS --ignore-missing
   ```

## Installation Methods

### Ubuntu/Debian (.deb Package)

**Prerequisites**:
```bash
sudo apt update
sudo apt install python3 python3-pip curl wget
```

**Installation**:
```bash
# Download the package
wget https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v0.1.0/bitcoin-solo-miner-monitor_0.1.0_amd64.deb

# Install the package
sudo dpkg -i bitcoin-solo-miner-monitor_0.1.0_amd64.deb

# Install any missing dependencies
sudo apt-get install -f
```

**Alternative using gdebi** (handles dependencies automatically):
```bash
sudo apt install gdebi-core
sudo gdebi bitcoin-solo-miner-monitor_0.1.0_amd64.deb
```

### Fedora/CentOS/RHEL (.rpm Package)

**Prerequisites**:
```bash
# Fedora
sudo dnf install python3 python3-pip curl wget

# CentOS/RHEL (with EPEL)
sudo yum install epel-release
sudo yum install python3 python3-pip curl wget
```

**Installation**:
```bash
# Download the package
wget https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v0.1.0/bitcoin-solo-miner-monitor-0.1.0-1.x86_64.rpm

# Install the package
sudo rpm -i bitcoin-solo-miner-monitor-0.1.0-1.x86_64.rpm

# Or using dnf/yum (handles dependencies)
sudo dnf install bitcoin-solo-miner-monitor-0.1.0-1.x86_64.rpm
# or
sudo yum install bitcoin-solo-miner-monitor-0.1.0-1.x86_64.rpm
```

### Universal Linux (AppImage)

**Prerequisites**:
```bash
# Most distributions include these, but install if missing
sudo apt install fuse libfuse2  # Ubuntu/Debian
sudo dnf install fuse fuse-libs  # Fedora
sudo yum install fuse fuse-libs  # CentOS/RHEL
```

**Installation**:
```bash
# Download the AppImage
wget https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/v0.1.0/BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage

# Make it executable
chmod +x BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage

# Run the application
./BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage
```

**Optional - Integrate with desktop**:
```bash
# Move to applications directory
mkdir -p ~/.local/bin
mv BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage ~/.local/bin/bitcoin-solo-miner-monitor

# Create desktop entry
cat > ~/.local/share/applications/bitcoin-solo-miner-monitor.desktop << EOF
[Desktop Entry]
Name=Bitcoin Solo Miner Monitor
Comment=Monitor Bitcoin solo mining operations
Exec=$HOME/.local/bin/bitcoin-solo-miner-monitor
Icon=bitcoin-solo-miner-monitor
Terminal=false
Type=Application
Categories=Network;System;
EOF

# Update desktop database
update-desktop-database ~/.local/share/applications/
```

### Arch Linux (AUR)

**Using yay** (AUR helper):
```bash
yay -S bitcoin-solo-miner-monitor
```

**Manual AUR installation**:
```bash
git clone https://aur.archlinux.org/bitcoin-solo-miner-monitor.git
cd bitcoin-solo-miner-monitor
makepkg -si
```

## Post-Installation

### System Integration

After installation, the application will:
- **Create desktop entry** in applications menu
- **Install system service** (optional, for auto-start)
- **Set up file associations** for mining configuration files
- **Create command-line shortcuts**

### Starting the Application

**Desktop Environment**:
- Look for "Bitcoin Solo Miner Monitor" in your applications menu
- Or search for "bitcoin" in your application launcher

**Command Line**:
```bash
# Start the application
bitcoin-solo-miner-monitor

# Or use the full path
/opt/bitcoin-solo-miner-monitor/bin/bitcoin-solo-miner-monitor

# Start as background service
sudo systemctl start bitcoin-solo-miner-monitor
sudo systemctl enable bitcoin-solo-miner-monitor  # Auto-start at boot
```

### First Launch Setup

1. **Launch the application** from menu or command line
2. **Web browser will open** to `http://localhost:8000`
3. **Configure firewall** if prompted (see troubleshooting section)
4. **Follow setup wizard** to configure miners

## System Service Configuration

### Systemd Service (DEB/RPM packages)

The packages install a systemd service for background operation:

**Service Management**:
```bash
# Check service status
sudo systemctl status bitcoin-solo-miner-monitor

# Start the service
sudo systemctl start bitcoin-solo-miner-monitor

# Enable auto-start at boot
sudo systemctl enable bitcoin-solo-miner-monitor

# Stop the service
sudo systemctl stop bitcoin-solo-miner-monitor

# View service logs
sudo journalctl -u bitcoin-solo-miner-monitor -f
```

**Service Configuration**:
Edit `/etc/systemd/system/bitcoin-solo-miner-monitor.service`:
```ini
[Unit]
Description=Bitcoin Solo Miner Monitor
After=network.target

[Service]
Type=simple
User=bitcoin-monitor
Group=bitcoin-monitor
WorkingDirectory=/opt/bitcoin-solo-miner-monitor
ExecStart=/opt/bitcoin-solo-miner-monitor/bin/bitcoin-solo-miner-monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Manual Service Setup (AppImage)

Create a custom systemd service:

```bash
# Create service file
sudo tee /etc/systemd/system/bitcoin-solo-miner-monitor.service > /dev/null << EOF
[Unit]
Description=Bitcoin Solo Miner Monitor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=$HOME/.local/bin/bitcoin-solo-miner-monitor --headless
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable
sudo systemctl daemon-reload
sudo systemctl enable bitcoin-solo-miner-monitor
sudo systemctl start bitcoin-solo-miner-monitor
```

## Troubleshooting

### Installation Issues

**"Package has unmet dependencies"** (Ubuntu/Debian):
```bash
# Update package lists
sudo apt update

# Install missing dependencies
sudo apt install -f

# Try installing specific dependencies
sudo apt install python3-dev python3-pip python3-venv
```

**"Package conflicts"** (Fedora/CentOS):
```bash
# Check for conflicts
rpm -q --conflicts bitcoin-solo-miner-monitor

# Force installation (use with caution)
sudo rpm -i --force bitcoin-solo-miner-monitor-0.1.0-1.x86_64.rpm
```

**AppImage won't run**:
```bash
# Check if FUSE is installed
fusermount --version

# Install FUSE if missing
sudo apt install fuse libfuse2  # Ubuntu/Debian
sudo dnf install fuse fuse-libs  # Fedora

# Check AppImage permissions
ls -la BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage
chmod +x BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage
```

### Runtime Issues

**Application won't start**:
```bash
# Check if Python is available
python3 --version

# Check system logs
sudo journalctl -u bitcoin-solo-miner-monitor -n 50

# Try running manually
/opt/bitcoin-solo-miner-monitor/bin/bitcoin-solo-miner-monitor --debug
```

**Port 8000 already in use**:
```bash
# Find what's using the port
sudo netstat -tlnp | grep :8000
# or
sudo ss -tlnp | grep :8000

# Kill the conflicting process
sudo kill -9 <PID>

# Or change application port
bitcoin-solo-miner-monitor --port 8001
```

**Permission denied errors**:
```bash
# Check file permissions
ls -la /opt/bitcoin-solo-miner-monitor/

# Fix permissions if needed
sudo chown -R bitcoin-monitor:bitcoin-monitor /opt/bitcoin-solo-miner-monitor/
sudo chmod +x /opt/bitcoin-solo-miner-monitor/bin/bitcoin-solo-miner-monitor
```

### Firewall Configuration

**UFW (Ubuntu)**:
```bash
# Allow application through firewall
sudo ufw allow 8000/tcp
sudo ufw allow from 192.168.0.0/16 to any port 8000

# Check firewall status
sudo ufw status
```

**Firewalld (Fedora/CentOS)**:
```bash
# Add firewall rule
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# Check firewall status
sudo firewall-cmd --list-all
```

**iptables (Manual)**:
```bash
# Allow incoming connections on port 8000
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT

# Save rules (varies by distribution)
sudo iptables-save > /etc/iptables/rules.v4  # Debian/Ubuntu
sudo service iptables save  # CentOS/RHEL
```

### Network Discovery Issues

**Miners not found**:
```bash
# Test network connectivity
ping 192.168.1.1  # Your router

# Check if network scanning is working
nmap -sn 192.168.1.0/24  # Scan local network

# Test specific miner connection
curl http://192.168.1.100/api/system/info  # Replace with miner IP
```

**SELinux issues** (CentOS/RHEL/Fedora):
```bash
# Check SELinux status
sestatus

# Check for SELinux denials
sudo ausearch -m AVC -ts recent

# Create custom SELinux policy if needed
sudo setsebool -P httpd_can_network_connect 1
```

## Advanced Configuration

### Custom Installation Paths

**DEB/RPM packages** install to standard locations:
- **Binaries**: `/opt/bitcoin-solo-miner-monitor/`
- **Configuration**: `/etc/bitcoin-solo-miner-monitor/`
- **Data**: `/var/lib/bitcoin-solo-miner-monitor/`
- **Logs**: `/var/log/bitcoin-solo-miner-monitor/`

**AppImage** can be placed anywhere:
```bash
# Recommended locations
~/.local/bin/bitcoin-solo-miner-monitor  # User-specific
/usr/local/bin/bitcoin-solo-miner-monitor  # System-wide
```

### Environment Configuration

Create environment file for custom settings:

```bash
# Create environment file
sudo tee /etc/bitcoin-solo-miner-monitor/environment << EOF
# Application settings
BITCOIN_MONITOR_PORT=8000
BITCOIN_MONITOR_HOST=0.0.0.0
BITCOIN_MONITOR_DEBUG=false

# Data directories
BITCOIN_MONITOR_DATA_DIR=/var/lib/bitcoin-solo-miner-monitor
BITCOIN_MONITOR_LOG_DIR=/var/log/bitcoin-solo-miner-monitor

# Network settings
BITCOIN_MONITOR_NETWORK_RANGE=192.168.1.0/24
BITCOIN_MONITOR_DISCOVERY_TIMEOUT=30
EOF

# Update systemd service to use environment file
sudo systemctl edit bitcoin-solo-miner-monitor
```

Add to the override file:
```ini
[Service]
EnvironmentFile=/etc/bitcoin-solo-miner-monitor/environment
```

### Building from Source

For the latest features or custom builds:

```bash
# Install build dependencies
sudo apt install build-essential python3-dev nodejs npm  # Ubuntu/Debian
sudo dnf install @development-tools python3-devel nodejs npm  # Fedora

# Clone repository
git clone https://github.com/smokeysrh/bitcoin-solo-miner-monitor.git
cd bitcoin-solo-miner-monitor

# Install Python dependencies
pip3 install -r requirements.txt

# Build frontend (if exists)
cd src/frontend
npm ci
npm run build
cd ../..

# Run from source
python3 run.py
```

## Uninstallation

### DEB Package (Ubuntu/Debian)
```bash
# Remove package
sudo apt remove bitcoin-solo-miner-monitor

# Remove configuration files too
sudo apt purge bitcoin-solo-miner-monitor

# Remove user data (optional)
rm -rf ~/.local/share/bitcoin-solo-miner-monitor/
```

### RPM Package (Fedora/CentOS)
```bash
# Remove package
sudo dnf remove bitcoin-solo-miner-monitor
# or
sudo yum remove bitcoin-solo-miner-monitor

# Remove user data (optional)
rm -rf ~/.local/share/bitcoin-solo-miner-monitor/
```

### AppImage
```bash
# Simply delete the AppImage file
rm ~/.local/bin/bitcoin-solo-miner-monitor

# Remove desktop integration
rm ~/.local/share/applications/bitcoin-solo-miner-monitor.desktop
update-desktop-database ~/.local/share/applications/

# Remove user data (optional)
rm -rf ~/.local/share/bitcoin-solo-miner-monitor/
```

### Complete System Cleanup
```bash
# Stop and disable service
sudo systemctl stop bitcoin-solo-miner-monitor
sudo systemctl disable bitcoin-solo-miner-monitor

# Remove service file
sudo rm /etc/systemd/system/bitcoin-solo-miner-monitor.service
sudo systemctl daemon-reload

# Remove firewall rules
sudo ufw delete allow 8000/tcp  # UFW
sudo firewall-cmd --permanent --remove-port=8000/tcp && sudo firewall-cmd --reload  # Firewalld

# Remove system user (if created)
sudo userdel bitcoin-monitor
sudo groupdel bitcoin-monitor
```

## Distribution-Specific Notes

### Ubuntu/Debian
- **LTS versions** are fully supported and tested
- **Snap package** may be available in the future
- **PPA repository** is planned for easier updates

### Fedora
- **Latest stable** versions are supported
- **Silverblue/Kinoite** users should use AppImage or Flatpak
- **COPR repository** may be available for easier installation

### CentOS/RHEL
- **EPEL repository** required for some dependencies
- **Enterprise support** available through community
- **Podman/Docker** containers available as alternative

### Arch Linux
- **AUR package** maintained by community
- **Rolling release** compatibility maintained
- **Manjaro** and derivatives supported

## Getting Help

- **Installation Issues**: [Report on GitHub](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues/new?template=installation-issue.md)
- **Distribution-specific**: [Community Wiki](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/wiki)
- **General Troubleshooting**: [Troubleshooting Guide](troubleshooting.md)
- **Security Questions**: [Security Guide](security-guide.md)
- **Community Support**: [GitHub Discussions](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions)

---

**Next Steps**: After successful installation, see the [User Guide](../user-guide.md) to configure your miners and start monitoring!