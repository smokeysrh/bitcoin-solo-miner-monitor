# Building Bitcoin Solo Miner Monitor

This document provides comprehensive instructions for building Bitcoin Solo Miner Monitor from source code, including creating platform-specific installers.

## 🔒 Reproducible Builds

**For reproducible builds and community verification**, see the comprehensive documentation in [`docs/build/`](./build/):

- **[Reproducible Builds Guide](./build/REPRODUCIBLE_BUILDS.md)** - Complete guide for verifiable builds
- **[Build Environment Setup](./build/BUILD_ENVIRONMENT.md)** - Deterministic environment configuration  
- **[Build Transparency](./build/BUILD_TRANSPARENCY.md)** - Public logs and audit trails

The reproducible build system ensures that anyone can verify the authenticity of our releases by building identical binaries from the same source code - a critical security feature for Bitcoin-related software.

---

## Prerequisites

### All Platforms
- **Git**: For cloning the repository
- **Python 3.11+**: Required for the backend
- **Node.js 18+**: Required for the frontend build
- **npm**: Comes with Node.js

### Platform-Specific Tools

#### Windows
- **NSIS 3.09+**: For creating Windows installers
  ```powershell
  # Using Chocolatey
  choco install nsis
  
  # Or download from https://nsis.sourceforge.io/
  ```

#### macOS
- **Xcode Command Line Tools**: For building native components
  ```bash
  xcode-select --install
  ```

#### Linux
- **Build essentials**: For package creation
  ```bash
  # Ubuntu/Debian
  sudo apt-get install build-essential python3-dev rpm
  
  # Fedora/CentOS
  sudo dnf install @development-tools python3-devel rpm-build
  ```

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/smokeysrh/bitcoin-solo-miner-monitor.git
cd bitcoin-solo-miner-monitor
```

### 2. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Build frontend (if exists)
if [ -d "src/frontend" ]; then
  cd src/frontend
  npm ci
  npm run build
  cd ../..
fi
```

### 3. Build Installers
```bash
# Build for current platform
python scripts/create-distribution.py --version 0.1.0

# Build for specific platform
python scripts/create-distribution.py --platform windows --version 0.1.0
python scripts/create-distribution.py --platform macos --version 0.1.0
python scripts/create-distribution.py --platform linux --version 0.1.0
```

## Detailed Build Process

### Frontend Build

The frontend is a Vue.js application that needs to be compiled:

```bash
cd src/frontend
npm ci                    # Install dependencies
npm run build            # Build for production
npm run dev              # Development server (optional)
```

Built files are output to `src/frontend/dist/` and automatically included in the installer build process.

### Backend Preparation

The Python backend requires dependency installation:

```bash
pip install -r requirements.txt
```

For distribution, dependencies are bundled with the installer to ensure users don't need to install them manually.

### Platform-Specific Builds

#### Windows NSIS Installer

The Windows installer uses NSIS (Nullsoft Scriptable Install System):

**Manual Build:**
```bash
# Ensure NSIS is in PATH
makensis /DVERSION=0.1.0 installer/windows/installer.nsi
```

**Features:**
- Embedded Python runtime (no user installation required)
- Desktop and Start Menu shortcuts
- Windows Add/Remove Programs integration
- Professional installer UI with branding
- Automatic dependency installation

**Output:** `distribution/windows/BitcoinSoloMinerMonitor-0.1.0-Setup.exe`

#### macOS DMG Package

The macOS installer creates a disk image with drag-to-install interface:

**Manual Build:**
```bash
bash installer/macos/create_dmg.sh /path/to/app/bundle output.dmg 0.1.0
```

**Features:**
- Native .app bundle structure
- Drag-to-Applications installation
- Professional DMG interface with background
- Embedded Python dependencies
- macOS system integration

**Output:** `distribution/macos/BitcoinSoloMinerMonitor-0.1.0.dmg`

#### Linux Packages

Linux builds create multiple package formats:

**DEB Package (Ubuntu/Debian):**
```bash
bash installer/linux/build_deb.sh /path/to/app/files /output/dir 0.1.0
```

**RPM Package (Fedora/CentOS):**
```bash
bash installer/linux/build_rpm.sh /path/to/app/files /output/dir 0.1.0
```

**AppImage (Universal):**
```bash
bash installer/linux/build_appimage.sh /path/to/app/files /output/dir 0.1.0
```

**Features:**
- Native package manager integration
- Desktop environment integration
- Systemd service support (optional)
- Dependency resolution through package managers

**Outputs:**
- `distribution/linux/bitcoin-solo-miner-monitor_0.1.0_amd64.deb`
- `distribution/linux/bitcoin-solo-miner-monitor-0.1.0-1.x86_64.rpm`
- `distribution/linux/BitcoinSoloMinerMonitor-0.1.0-x86_64.AppImage`

## Automated Builds with GitHub Actions

The project includes GitHub Actions workflows for automated building:

### Triggering Builds

**Release Build (creates GitHub release):**
```bash
git tag v0.1.0
git push origin v0.1.0
```

**Development Build:**
```bash
# Push to main or develop branch
git push origin main
```

**Manual Build:**
- Go to GitHub Actions tab
- Select "Build Installers" workflow
- Click "Run workflow"
- Enter version number

### Workflow Features

- **Multi-platform builds**: Windows, macOS, and Linux
- **Automated testing**: Installation verification on clean VMs
- **Security scanning**: Dependency and code security checks
- **Checksum generation**: SHA256 hashes for all artifacts
- **Release automation**: Automatic GitHub release creation
- **Artifact storage**: 30-day retention for development builds

## Reproducible Builds

To ensure build reproducibility:

### 1. Use Exact Versions
```bash
# Pin Python dependencies
pip freeze > requirements-lock.txt

# Pin Node.js dependencies (package-lock.json is committed)
npm ci  # Uses exact versions from package-lock.json
```

### 2. Consistent Build Environment
```bash
# Use the same Python version
python --version  # Should be 3.11.x

# Use the same Node.js version
node --version    # Should be 18.x.x
```

### 3. Verify Reproducibility
```bash
# Build twice and compare checksums
python scripts/create-distribution.py --version 0.1.0
sha256sum distribution/windows/*.exe > checksums1.txt

# Clean and rebuild
rm -rf distribution/
python scripts/create-distribution.py --version 0.1.0
sha256sum distribution/windows/*.exe > checksums2.txt

# Compare
diff checksums1.txt checksums2.txt  # Should be identical
```

## Development Builds

For development and testing:

### Quick Development Package
```bash
# Create a simple ZIP package for testing
python scripts/create-distribution.py --version dev-$(git rev-parse --short HEAD)
```

### Local Testing
```bash
# Run the application directly
python run.py

# Or use the development server
cd src/frontend
npm run dev  # Frontend development server
```

## Troubleshooting Build Issues

### Common Issues

**NSIS not found (Windows):**
```bash
# Add NSIS to PATH or install via Chocolatey
choco install nsis
```

**Permission denied (macOS/Linux):**
```bash
# Make scripts executable
chmod +x installer/macos/create_dmg.sh
chmod +x installer/linux/*.sh
```

**Missing dependencies:**
```bash
# Install all build dependencies
pip install -r requirements.txt
npm ci
cd src/frontend && npm ci
```

**Frontend build fails:**
```bash
# Clear npm cache and reinstall
cd src/frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Build Logs

Check build logs for detailed error information:

- **Local builds**: Console output
- **GitHub Actions**: Actions tab → Build logs
- **Installer logs**: Platform-specific installer logs

### Getting Help

- **Build Issues**: [Open a GitHub issue](../../issues)
- **Documentation**: [Project documentation](../README.md)
- **Community**: [GitHub Discussions](../../discussions)

## Contributing

When contributing build system improvements:

1. Test on all target platforms
2. Update documentation
3. Ensure reproducible builds
4. Add appropriate tests
5. Update CI/CD workflows if needed

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.