# Security Scanning Integration

This directory contains the automated security scanning integration for Bitcoin Solo Miner Monitor. The system provides comprehensive security scanning of dependencies, code, and generated installers, along with automated vulnerability detection and security patch distribution.

## Components

### 1. Installer Security Scanner (`installer-security-scanner.py`)

Scans generated installer files for security issues including:
- File integrity verification
- Size and type validation
- Malware scanning (when ClamAV is available)
- Platform-specific security checks
- Checksum verification

**Usage:**
```bash
python scripts/security/installer-security-scanner.py installer1.exe installer2.dmg --format markdown
```

### 2. Vulnerability Detector (`vulnerability-detector.py`)

Detects vulnerabilities in project dependencies:
- Python dependencies (using Safety and pip-audit)
- Node.js dependencies (using npm audit and yarn audit)
- System-level vulnerability checks
- Comprehensive reporting with severity levels

**Usage:**
```bash
# Scan all dependency types
python scripts/security/vulnerability-detector.py --all

# Scan specific types
python scripts/security/vulnerability-detector.py --python --nodejs
```

### 3. Security Patch Distributor (`security-patch-distributor.py`)

Manages security patch distribution and updates:
- Checks for security updates from GitHub releases
- Downloads and verifies security patches
- Generates security advisories
- Integrates with application update system

**Usage:**
```bash
# Check for security updates
python scripts/security/security-patch-distributor.py --check-updates --current-version 1.0.0

# Download available patches
python scripts/security/security-patch-distributor.py --check-updates --download-patches --current-version 1.0.0
```

### 4. Security Integration (`security-integration.py`)

Main integration script that coordinates all security components:
- Runs complete security scans
- Generates consolidated reports
- Sets up security monitoring
- Provides unified interface for CI/CD integration

**Usage:**
```bash
# Run complete security scan
python scripts/security/security-integration.py --scan-all --current-version 1.0.0 --installer-files dist/*.exe

# Setup security monitoring
python scripts/security/security-integration.py --setup-monitoring
```

## Configuration

### Security Configuration (`config/security-config.json`)

Main configuration file for all security components:

```json
{
  "vulnerability_scanning": {
    "enabled": true,
    "fail_on_critical": true,
    "tools": {
      "safety": {"enabled": true},
      "bandit": {"enabled": true},
      "npm_audit": {"enabled": true}
    }
  },
  "installer_security": {
    "max_file_size_mb": 500,
    "verify_file_types": true,
    "scan_for_malware": true
  },
  "patch_verification": {
    "require_checksum": true,
    "require_community_review": true
  }
}
```

## CI/CD Integration

### GitHub Actions Integration

The security scanning is integrated into the GitHub Actions workflows:

1. **Dependency Scanning** (`.github/workflows/security-scan.yml`)
   - Runs on every push and pull request
   - Scans Python and Node.js dependencies
   - Generates vulnerability reports

2. **Installer Scanning** (`.github/workflows/build-installers.yml`)
   - Runs after installer builds complete
   - Scans all generated installer files
   - Verifies checksums and file integrity

### Workflow Integration

```yaml
- name: Run comprehensive security scan
  run: |
    python scripts/security/security-integration.py \
      --scan-all \
      --current-version ${{ github.ref_name }} \
      --installer-files artifacts/*/*.exe artifacts/*/*.dmg \
      --verbose
```

## Security Features

### 1. Vulnerability Detection

- **Python Dependencies**: Uses Safety and pip-audit to check for known CVEs
- **Node.js Dependencies**: Uses npm audit and yarn audit for vulnerability detection
- **System Dependencies**: Checks for known system-level vulnerabilities
- **Real-time Updates**: Integrates with vulnerability databases for up-to-date information

### 2. Installer Security

- **File Integrity**: Verifies installer file structure and format
- **Malware Scanning**: Optional ClamAV integration for malware detection
- **Size Validation**: Checks for suspiciously small or large files
- **Type Verification**: Ensures file types match extensions
- **Checksum Validation**: Verifies SHA256 checksums for integrity

### 3. Patch Management

- **Automated Detection**: Monitors GitHub releases for security updates
- **Severity Classification**: Categorizes updates by security impact
- **Community Verification**: Supports community review processes
- **Transparent Distribution**: Maintains open-source transparency principles

### 4. Reporting and Monitoring

- **Comprehensive Reports**: Generates detailed security reports in multiple formats
- **Executive Summaries**: Provides high-level security status overviews
- **Actionable Recommendations**: Suggests specific remediation steps
- **Historical Tracking**: Maintains security scan history for trend analysis

## Security Principles

### Open Source Security

The security system follows Bitcoin and open-source security principles:

1. **Transparency**: All security processes are open and auditable
2. **Community Verification**: Security measures can be independently verified
3. **Reproducible Builds**: Security scans produce consistent results
4. **No Central Authority**: Doesn't rely on centralized certificate authorities

### Defense in Depth

Multiple layers of security scanning:

1. **Source Code Analysis**: Static analysis of application code
2. **Dependency Scanning**: Vulnerability detection in third-party libraries
3. **Build Artifact Scanning**: Security validation of generated installers
4. **Runtime Monitoring**: Ongoing security monitoring and alerting

### Community Trust

- **Public Processes**: All security scanning processes are publicly documented
- **Community Review**: Security findings can be independently verified
- **Transparent Reporting**: Security reports are available to the community
- **Open Remediation**: Security fixes follow open development processes

## Usage Examples

### Basic Security Scan

```bash
# Scan current project for vulnerabilities
python scripts/security/vulnerability-detector.py --all --verbose
```

### Installer Security Check

```bash
# Scan installer files
python scripts/security/installer-security-scanner.py \
  dist/BitcoinSoloMinerMonitor-1.0.0.exe \
  dist/BitcoinSoloMinerMonitor-1.0.0.dmg \
  --format markdown \
  --output-dir security-reports
```

### Complete Security Assessment

```bash
# Run comprehensive security assessment
python scripts/security/security-integration.py \
  --scan-all \
  --current-version 1.0.0 \
  --installer-files dist/*.exe dist/*.dmg \
  --verbose
```

### Security Update Check

```bash
# Check for available security updates
python scripts/security/security-patch-distributor.py \
  --check-updates \
  --current-version 1.0.0 \
  --generate-advisory
```

## Requirements

### Python Dependencies

```bash
pip install requests packaging safety bandit pip-audit
```

### System Dependencies

- **ClamAV** (optional): For malware scanning
- **Node.js/npm**: For Node.js dependency scanning
- **Platform tools**: dpkg (Linux), rpm (Linux), hdiutil (macOS)

### Environment Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install security scanning tools:
   ```bash
   pip install safety bandit pip-audit
   ```

3. Configure security settings:
   ```bash
   cp config/security-config.json.example config/security-config.json
   # Edit configuration as needed
   ```

## Troubleshooting

### Common Issues

1. **Tool Not Found**: Install missing security scanning tools
2. **Permission Denied**: Ensure scripts have execute permissions
3. **Network Timeouts**: Check internet connection for vulnerability database updates
4. **Large Files**: Adjust file size limits in configuration

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python scripts/security/security-integration.py --scan-all --verbose
```

### Log Files

Security scan logs are stored in:
- `security-reports/`: Scan reports and logs
- `logs/security.log`: Detailed security operation logs

## Contributing

### Adding New Security Checks

1. Create new scanner class inheriting from base scanner
2. Implement required scanning methods
3. Add configuration options to `security-config.json`
4. Update integration script to include new scanner
5. Add tests and documentation

### Improving Vulnerability Detection

1. Add new vulnerability data sources
2. Implement additional scanning tools
3. Enhance severity classification
4. Improve false positive filtering

### Security Tool Integration

1. Add new security tool wrappers
2. Implement tool-specific result parsing
3. Add configuration options
4. Update CI/CD workflows

## Security Considerations

### Data Privacy

- No sensitive data is transmitted to external services
- Vulnerability databases are accessed read-only
- Local scanning preserves privacy

### Network Security

- All external communications use HTTPS
- Vulnerability database updates are verified
- No automatic code execution from external sources

### Access Control

- Security configuration requires appropriate file permissions
- Sensitive operations require explicit user confirmation
- Audit trails are maintained for security operations

## License

This security scanning system is part of the Bitcoin Solo Miner Monitor project and is licensed under the same terms as the main project.