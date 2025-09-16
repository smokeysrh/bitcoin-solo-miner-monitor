# GitHub Actions CI/CD System

This directory contains the automated build and deployment workflows for Bitcoin Solo Miner Monitor.

## Workflows Overview

### 1. Build Installers (`build-installers.yml`)

**Purpose**: Creates platform-specific installers for Windows, macOS, and Linux.

**Triggers**:
- Git tags starting with `v*` (e.g., `v1.0.0`)
- Pull requests to `main` or `develop` branches
- Manual workflow dispatch

**Outputs**:
- Windows: `.exe` installer with embedded Python runtime
- macOS: `.dmg` disk image with drag-to-install interface
- Linux: `.deb`, `.rpm`, and `.AppImage` packages

**Features**:
- Multi-platform matrix builds
- Automatic dependency installation
- SHA256 checksum generation
- Artifact upload with 30-day retention
- Automatic GitHub release creation for tags

### 2. Test Installers (`test-installers.yml`)

**Purpose**: Validates installer functionality across platforms.

**Triggers**:
- After successful completion of "Build Installers" workflow
- Manual workflow dispatch

**Tests**:
- Installation success verification
- Application launch testing
- Uninstaller functionality (Windows)
- Package integrity checks

### 3. Security Scan (`security-scan.yml`)

**Purpose**: Performs security analysis on code and dependencies.

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main`
- Daily scheduled scan at 2 AM UTC
- Manual workflow dispatch

**Scans**:
- Python dependency vulnerabilities (Safety)
- Python code security issues (Bandit)
- Node.js dependency vulnerabilities (npm audit)
- Installer artifact security checks

## Usage Guide

### Creating a Release

1. **Prepare the release**:
   ```bash
   # Update version in relevant files
   # Update CHANGELOG.md
   # Commit changes
   git add .
   git commit -m "Prepare release v1.0.0"
   ```

2. **Create and push tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **Monitor the build**:
   - Go to GitHub Actions tab
   - Watch the "Build Installers" workflow
   - Check for any failures and address them

4. **Verify the release**:
   - Check the automatically created GitHub release
   - Verify all platform installers are present
   - Confirm SHA256SUMS file is included

### Manual Builds

For testing or development builds:

1. Go to GitHub Actions tab
2. Select "Build Installers" workflow
3. Click "Run workflow"
4. Enter a version string (e.g., "dev-test")
5. Click "Run workflow"

### Monitoring Security

The security scan workflow runs automatically and:
- Comments on pull requests with security findings
- Uploads detailed security reports as artifacts
- Fails the build if critical vulnerabilities are found

## Build Environment Details

### Windows Runner
- **OS**: Windows Server 2022
- **Python**: 3.11
- **Node.js**: 18
- **Tools**: NSIS, PowerShell, Git

### macOS Runner
- **OS**: macOS 12 (Monterey)
- **Python**: 3.11
- **Node.js**: 18
- **Tools**: Xcode Command Line Tools, Homebrew

### Linux Runner
- **OS**: Ubuntu 22.04 LTS
- **Python**: 3.11
- **Node.js**: 18
- **Tools**: build-essential, rpm, dpkg

## Artifact Structure

### Release Artifacts
```
BitcoinSoloMinerMonitor-1.0.0-Setup.exe          # Windows installer
BitcoinSoloMinerMonitor-1.0.0.dmg                # macOS disk image
bitcoin-solo-miner-monitor_1.0.0_amd64.deb       # Debian package
bitcoin-solo-miner-monitor-1.0.0-1.x86_64.rpm    # RPM package
BitcoinSoloMinerMonitor-1.0.0-x86_64.AppImage     # Universal Linux
SHA256SUMS                                        # Checksums file
```

### Development Artifacts
- Stored for 30 days
- Named with commit SHA or custom version
- Include build logs and test results

## Customization

### Adding New Platforms

To add support for a new platform:

1. **Create installer scripts**:
   ```bash
   mkdir installer/newplatform
   # Add build scripts following existing patterns
   ```

2. **Update distribution script**:
   ```python
   # Add new platform support in scripts/create-distribution.py
   def build_newplatform(self, version):
       # Implementation
   ```

3. **Add to CI workflow**:
   ```yaml
   # Add new job in .github/workflows/build-installers.yml
   build-newplatform:
     runs-on: newplatform-latest
     # Job configuration
   ```

### Modifying Build Process

Common customizations:

**Change Python/Node.js versions**:
```yaml
env:
  NODE_VERSION: '20'      # Update Node.js version
  PYTHON_VERSION: '3.12'  # Update Python version
```

**Add build steps**:
```yaml
- name: Custom build step
  run: |
    # Your custom commands here
```

**Modify artifact retention**:
```yaml
- name: Upload artifacts
  uses: actions/upload-artifact@v4
  with:
    retention-days: 90  # Change from default 30 days
```

## Troubleshooting

### Common Build Failures

**NSIS compilation fails (Windows)**:
- Check NSIS script syntax
- Verify all referenced files exist
- Check file paths and permissions

**DMG creation fails (macOS)**:
- Verify AppleScript syntax
- Check background image paths
- Ensure proper file permissions

**Package creation fails (Linux)**:
- Check package metadata
- Verify dependency specifications
- Ensure proper file structure

### Debugging Workflows

1. **Check workflow logs**:
   - Go to Actions tab
   - Click on failed workflow
   - Expand failed steps to see detailed logs

2. **Test locally**:
   ```bash
   # Run the same commands locally
   python scripts/create-distribution.py --version test
   ```

3. **Enable debug logging**:
   ```yaml
   - name: Debug step
     run: |
       set -x  # Enable bash debugging
       # Your commands here
   ```

### Getting Help

- **Workflow Issues**: Check GitHub Actions documentation
- **Build Problems**: See [BUILD.md](../docs/BUILD.md)
- **Security Concerns**: Review security scan reports
- **General Support**: Open a GitHub issue

## Security Considerations

### Secrets Management
- No secrets are currently required
- Future code signing will require certificate secrets
- Use GitHub encrypted secrets for sensitive data

### Supply Chain Security
- All dependencies are pinned to specific versions
- Security scanning runs on every build
- Reproducible builds ensure integrity

### Artifact Security
- SHA256 checksums for all releases
- Public build logs for transparency
- Automated security scanning of outputs

## Future Enhancements

Planned improvements:
- Code signing for Windows and macOS
- Notarization for macOS apps
- Package repository submissions
- Performance optimization
- Enhanced security scanning