---
name: Security Issue Report
about: Report a security vulnerability or concern
title: '[SECURITY] Brief description of security issue'
labels: security, needs-triage
assignees: ''

---

## 🔒 Security Issue Report

**⚠️ IMPORTANT**: For critical security vulnerabilities, consider reporting privately first through GitHub Security Advisories or by contacting maintainers directly.

### Issue Classification

**Severity**: (Critical/High/Medium/Low/Informational)
**Type**: 
- [ ] Code vulnerability
- [ ] Build process security issue
- [ ] Dependency vulnerability
- [ ] Infrastructure security concern
- [ ] Social engineering/phishing attempt
- [ ] Other (specify)

### Vulnerability Details

**Component Affected**: (e.g., backend API, frontend, build system, installer)
**File(s) Involved**: (path/to/affected/files)
**Function/Method**: (specific function if applicable)

**Description**: 
(Clear description of the security issue)

**Attack Vector**: 
(How could this vulnerability be exploited?)

**Impact Assessment**:
- **Confidentiality**: (None/Low/Medium/High)
- **Integrity**: (None/Low/Medium/High)  
- **Availability**: (None/Low/Medium/High)
- **Scope**: (Local/Network/Remote)

### Technical Details

**Affected Versions**: (e.g., v0.1.0 - v1.2.0, or "all versions")

**Code Snippet** (if applicable):
```python
# Paste relevant code showing the issue
```

**Proof of Concept** (if safe to share):
```bash
# Steps to demonstrate the vulnerability
```

**Environment Information**:
- **Operating System**: 
- **Python Version**: 
- **Dependencies**: (relevant package versions)
- **Network Configuration**: (if relevant)

### Discovery Information

**Discovery Method**: 
- [ ] Code review
- [ ] Automated security scanning
- [ ] Penetration testing
- [ ] User report
- [ ] Third-party security research
- [ ] Other (specify)

**Discovery Date**: (YYYY-MM-DD)
**Reporter**: (Your name/organization if comfortable sharing)

### Potential Solutions

**Suggested Fix**: 
(If you have ideas for how to fix this issue)

**Workarounds**: 
(Temporary measures users can take to mitigate the risk)

**References**: 
(Links to relevant security advisories, CVEs, documentation)

### Disclosure Timeline

**Preferred Disclosure**: 
- [ ] Immediate public disclosure
- [ ] Coordinated disclosure (30 days)
- [ ] Extended coordinated disclosure (90 days)
- [ ] Private disclosure only

**Reason for Timeline**: 
(Why you chose this disclosure approach)

### Additional Context

**Related Issues**: (Links to related GitHub issues or security reports)

**External References**: 
- CVE IDs (if applicable)
- Security advisories
- Research papers
- Blog posts

### Impact on Bitcoin Operations

**Mining Impact**: 
- [ ] Could affect mining operations
- [ ] Could compromise mining rewards
- [ ] Could expose mining credentials
- [ ] No direct mining impact

**Wallet/Key Security**: 
- [ ] Could expose private keys
- [ ] Could affect wallet operations
- [ ] No wallet/key impact

**Network Security**: 
- [ ] Could affect network communications
- [ ] Could enable man-in-the-middle attacks
- [ ] Could compromise mining pool connections
- [ ] No network security impact

### Verification and Testing

**Tested On**: 
- [ ] Windows
- [ ] macOS  
- [ ] Linux
- [ ] Multiple versions
- [ ] Different configurations

**Verification Steps**: 
1. (Steps others can use to verify this issue)
2. 
3. 

### Responsible Disclosure

- [ ] I have not publicly disclosed this vulnerability
- [ ] I have not shared this with unauthorized parties
- [ ] I understand the potential impact of this issue
- [ ] I am willing to work with maintainers on a fix
- [ ] I would like to be credited in security advisories (optional)

---

## For Maintainers

**Triage Information**:
- **Severity Assessment**: (Critical/High/Medium/Low)
- **Affected Components**: 
- **Fix Priority**: (Immediate/Next Release/Future Release)
- **Security Advisory Needed**: (Yes/No)
- **CVE Request Needed**: (Yes/No)

**Response Checklist**:
- [ ] Acknowledge receipt within 24 hours
- [ ] Verify and reproduce the issue
- [ ] Assess impact and severity
- [ ] Develop and test fix
- [ ] Coordinate disclosure timeline
- [ ] Prepare security advisory
- [ ] Release patched version
- [ ] Update security documentation

**Assigned Security Lead**: (GitHub username)
**Investigation Status**: (Not Started/In Progress/Completed)
**Target Fix Date**: (YYYY-MM-DD)

---

**Thank you for helping keep Bitcoin Solo Miner Monitor secure!** Responsible security reporting helps protect the entire community.