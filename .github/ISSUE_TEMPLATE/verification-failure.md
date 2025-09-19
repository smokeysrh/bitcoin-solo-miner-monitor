---
name: Verification Failure Report
about: Report failed verification of a release - SECURITY CRITICAL
title: '[VERIFICATION FAILURE] Version X.X.X verification failed'
labels: verification, security, urgent
assignees: ''

---

## ⚠️ VERIFICATION FAILURE REPORT ⚠️

**🚨 SECURITY NOTICE**: This report indicates a potential security issue. Do not use the software until this is resolved.

**Version**: (e.g., v0.1.0)
**Verification Date**: (YYYY-MM-DD)
**Reporter**: (Your GitHub username or identifier)

### Failure Summary

**Verification Method**: (Checksum/Reproducible Build/Source Audit)
**Failure Type**: (Checksum mismatch/Build inconsistency/Security issue)
**Severity**: (Critical/High/Medium/Low)

### Detailed Failure Information

#### Checksum Verification Failure
- **Expected checksum**: `(paste expected SHA256)`
- **Actual checksum**: `(paste actual SHA256)`
- **File(s) affected**: (filename(s))
- **Download source**: (where you downloaded the file)
- **Download date/time**: (when you downloaded)

#### Reproducible Build Failure
- **Build environment**: (OS, versions, tools)
- **Build command used**: `(exact command)`
- **Build output**: 
```
(paste relevant build output/errors)
```
- **Generated checksums**:
```
(paste your SHA256SUMS content)
```
- **Reference checksums**:
```
(paste official SHA256SUMS content)
```

#### Source Code Issues (if applicable)
- **File(s) with issues**: (path/to/file.py)
- **Issue description**: (detailed description)
- **Security impact**: (potential impact assessment)
- **Code snippet**:
```python
# Paste relevant code snippet
```

### System Information

- **Operating System**: (e.g., Ubuntu 22.04, Windows 11, macOS 13.0)
- **Architecture**: (e.g., x86_64, arm64)
- **Python Version**: (e.g., 3.11.5)
- **Node.js Version**: (e.g., 18.17.0)
- **Git Version**: (e.g., 2.40.1)
- **Build Tools**: (NSIS version, compiler versions, etc.)

### Network and Download Information

- **Internet Connection**: (Direct/VPN/Proxy)
- **Download Method**: (Browser/wget/curl/git clone)
- **Geographic Location**: (Country/Region - helps identify regional attacks)
- **ISP**: (if comfortable sharing)

### Reproduction Steps

1. (Step-by-step instructions to reproduce the failure)
2. 
3. 

### Verification Attempts

- [ ] Re-downloaded files and verified again
- [ ] Tried different download source/mirror
- [ ] Verified on different system/network
- [ ] Checked with different verification tools
- [ ] Compared with other community members

**Results of additional attempts**: (describe what happened)

### Evidence and Logs

Please attach or provide links to:
- [ ] Complete verification logs
- [ ] Build logs (if applicable)
- [ ] Screenshots of error messages
- [ ] Network traffic logs (if relevant)
- [ ] System security scan results

### Immediate Actions Taken

- [ ] Stopped using the software
- [ ] Isolated potentially compromised files
- [ ] Scanned system for malware
- [ ] Notified other users in my network
- [ ] Preserved evidence for investigation

### Community Impact Assessment

**Potential Impact**: 
- [ ] Individual user only
- [ ] Multiple users potentially affected
- [ ] Widespread distribution issue
- [ ] Possible supply chain attack

**Urgency Level**:
- [ ] Critical - Immediate action required
- [ ] High - Action needed within 24 hours
- [ ] Medium - Action needed within 1 week
- [ ] Low - Can be addressed in next release cycle

### Additional Context

(Any other information that might be relevant to understanding or reproducing this issue)

---

## For Maintainers

**Investigation Checklist**:
- [ ] Verify reporter's findings
- [ ] Check build infrastructure
- [ ] Review recent commits/changes
- [ ] Scan for compromise indicators
- [ ] Coordinate with other maintainers
- [ ] Prepare security advisory if needed
- [ ] Update community on status

**Response Priority**: (Critical/High/Medium/Low)
**Assigned Investigator**: (GitHub username)
**Investigation Status**: (Not Started/In Progress/Completed)

---

**Security Reminder**: If this appears to be a critical security issue, consider also reporting through private security channels if available.