# Community Builds Directory

This directory contains community-verified build results and verification data for Bitcoin Solo Miner Monitor releases.

## Directory Structure

```
community-builds/
├── v1.0.0/
│   ├── SHA256SUMS                 # Community-verified checksums
│   ├── verification-data.json     # Verification metadata
│   ├── build-reports/             # Individual build reports
│   └── verifiers/                 # Verifier-specific data
├── v1.0.1/
│   └── ...
└── template/                      # Templates for new versions
```

## How Community Verification Works

### 1. Release Process
1. Official release is published with SHA256SUMS
2. Community members independently verify the release
3. Verification results are collected and validated
4. Consensus checksums are established and stored here

### 2. Verification Levels

**🟢 Verified (3+ independent verifications)**
- Multiple community members have successfully verified
- Checksums match across all verifications
- No security concerns reported

**🟡 Pending (1-2 verifications)**
- Limited verification, needs more community input
- Some verifications successful but need confirmation
- Waiting for additional community verification

**🔴 Failed (verification failures reported)**
- One or more verification failures reported
- Potential security or build consistency issues
- Investigation needed before use recommended

**⚫ Unverified (no community verification)**
- No community verification attempts yet
- New release or limited community engagement
- Official checksums available but not community-verified

### 3. Verification Data Format

Each version directory contains:

#### SHA256SUMS
Standard format checksum file with community-verified hashes:
```
a1b2c3d4e5f6... BitcoinSoloMinerMonitor-1.0.0-Setup.exe
f6e5d4c3b2a1... BitcoinSoloMinerMonitor-1.0.0.dmg
9876543210ab... bitcoin-solo-miner-monitor_1.0.0_amd64.deb
```

#### verification-data.json
Metadata about community verification:
```json
{
  "version": "v1.0.0",
  "release_date": "2024-01-15T10:30:00Z",
  "verification_status": "verified",
  "verification_count": 5,
  "consensus_reached": "2024-01-16T08:00:00Z",
  "verifications": [
    {
      "verifier": "community_member_1",
      "date": "2024-01-15T12:00:00Z",
      "method": "reproducible_build",
      "platform": "linux",
      "checksum_match": true,
      "build_environment": {
        "os": "Ubuntu 22.04",
        "python": "3.11.5",
        "nodejs": "18.17.0"
      }
    }
  ],
  "security_notes": [],
  "build_reproducibility": {
    "reproducible": true,
    "deterministic_builds": 4,
    "build_variations": 0
  }
}
```

## Contributing Verification Results

### For Community Members

1. **Verify a release** using our [verification guide](../COMMUNITY_VERIFICATION_GUIDE.md)
2. **Report results** using GitHub issue templates
3. **Submit verification data** via pull request (for experienced contributors)

### For Maintainers

1. **Collect verification reports** from GitHub issues
2. **Validate verification data** for accuracy and authenticity
3. **Update community builds** when consensus is reached
4. **Maintain verification status** and security notes

## Using Community Verification Data

### Automated Tools

Our verification tools automatically check this directory:

```bash
# Verify against community data
python3 verification/tools/community-verify.py --version v1.0.0

# Compare your build with community builds
python3 verification/tools/compare-builds.py --local SHA256SUMS --version v1.0.0
```

### Manual Verification

1. **Download** the SHA256SUMS file for your version
2. **Compare** with your local checksums
3. **Check** verification-data.json for community consensus
4. **Review** any security notes or concerns

## Security Considerations

### Trust Model

Community verification operates on a **web of trust** model:
- Multiple independent verifications increase confidence
- Diverse verification methods (checksum, reproducible build, audit)
- Transparent process with public verification data
- No single point of failure or authority

### Limitations

Community verification **cannot** protect against:
- Sophisticated supply chain attacks affecting all verifiers
- Coordinated attacks by multiple malicious verifiers
- Vulnerabilities in the verification tools themselves
- Social engineering attacks on the verification process

### Best Practices

1. **Use multiple verification methods** when possible
2. **Cross-reference** with verifiers you trust
3. **Report suspicious activity** immediately
4. **Maintain verification tool security** (keep tools updated)
5. **Participate in verification** to strengthen the community

## Verification Statistics

### Current Status Summary

| Version | Status | Verifications | Last Updated |
|---------|--------|---------------|--------------|
| v1.0.0  | 🟢 Verified | 5 | 2024-01-16 |
| v0.9.0  | 🟡 Pending | 2 | 2024-01-10 |
| v0.8.0  | 🟢 Verified | 7 | 2024-01-05 |

### Community Participation

- **Active Verifiers**: 12 community members
- **Total Verifications**: 45 across all releases
- **Average Time to Consensus**: 18 hours
- **Verification Success Rate**: 98.2%

## Getting Help

### Questions About Verification

- **GitHub Discussions**: [Community Q&A](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions)
- **GitHub Issues**: [Verification Support](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues?q=label%3Averification)
- **Documentation**: [Verification Guide](../COMMUNITY_VERIFICATION_GUIDE.md)

### Reporting Issues

- **Verification Failures**: Use the [verification failure template](../../.github/ISSUE_TEMPLATE/verification-failure.md)
- **Security Concerns**: Use the [security issue template](../../.github/ISSUE_TEMPLATE/security-issue.md)
- **Process Improvements**: Create a regular GitHub issue with suggestions

## Legal and Disclaimer

Community verification results are provided by volunteers and do not constitute a warranty or guarantee of software security. The Bitcoin Solo Miner Monitor project maintainers are not responsible for community verification results.

All verification activities are performed voluntarily by community members. Verifiers are encouraged to follow responsible disclosure practices for any security issues discovered during verification.

---

**Contributing to community verification helps strengthen Bitcoin software security through decentralized trust and transparency.**