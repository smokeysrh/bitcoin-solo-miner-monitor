#!/usr/bin/env python3
"""
Security Audit Preparation Script

This script prepares comprehensive security scanning and audit materials
for the professional installer distribution system.
"""

import os
import sys
import json
import subprocess
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityAuditPreparator:
    """Prepares comprehensive security audit materials."""
    
    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path.cwd()
        self.audit_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'security_scans': {},
            'audit_materials': {},
            'summary': {
                'total_scans': 0,
                'passed_scans': 0,
                'security_issues': [],
                'recommendations': []
            }
        }
        
        # Create audit results directory
        self.audit_dir = self.repo_root / 'security-audit'
        self.audit_dir.mkdir(exist_ok=True)
    
    def prepare_security_audit(self) -> Dict[str, Any]:
        """Prepare comprehensive security audit materials."""
        logger.info("🔒 Starting security audit preparation")
        
        security_scans = [
            'dependency_vulnerability_scan',
            'code_security_analysis',
            'installer_integrity_check',
            'workflow_security_review',
            'documentation_security_review'
        ]
        
        for scan_type in security_scans:
            logger.info(f"🔍 Running {scan_type}...")
            result = self._run_security_scan(scan_type)
            self.audit_results['security_scans'][scan_type] = result
            self.audit_results['summary']['total_scans'] += 1
            
            if result['status'] == 'passed':
                self.audit_results['summary']['passed_scans'] += 1
            else:
                self.audit_results['summary']['security_issues'].extend(result.get('issues', []))
        
        # Generate audit materials
        logger.info("📋 Generating audit materials...")
        self._generate_audit_materials()
        
        # Determine overall status
        self._assess_security_posture()
        
        logger.info("✅ Security audit preparation completed")
        return self.audit_results
    
    def _run_security_scan(self, scan_type: str) -> Dict[str, Any]:
        """Run a specific security scan."""
        result = {'status': 'unknown', 'details': {}, 'issues': [], 'recommendations': []}
        
        try:
            if scan_type == 'dependency_vulnerability_scan':
                result = self._scan_dependencies()
            elif scan_type == 'code_security_analysis':
                result = self._analyze_code_security()
            elif scan_type == 'installer_integrity_check':
                result = self._check_installer_integrity()
            elif scan_type == 'workflow_security_review':
                result = self._review_workflow_security()
            elif scan_type == 'documentation_security_review':
                result = self._review_documentation_security()
            
        except Exception as e:
            result['status'] = 'failed'
            result['issues'] = [f"Exception in {scan_type}: {str(e)}"]
        
        return result
    
    def _scan_dependencies(self) -> Dict[str, Any]:
        """Scan dependencies for known vulnerabilities."""
        result = {'status': 'unknown', 'details': {}, 'issues': [], 'recommendations': []}
        
        # Check Python dependencies
        requirements_file = self.repo_root / 'requirements.txt'
        if requirements_file.exists():
            result['details']['python_requirements'] = 'found'
            
            # Try to run safety check if available
            try:
                safety_result = subprocess.run(
                    ['safety', 'check', '--json'],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=self.repo_root
                )
                
                if safety_result.returncode == 0:
                    result['details']['safety_scan'] = 'clean'
                else:
                    result['issues'].append("Python dependencies have known vulnerabilities")
                    result['details']['safety_output'] = safety_result.stdout
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                result['recommendations'].append("Install and run 'safety' tool for Python dependency scanning")
        
        # Check Node.js dependencies
        package_json = self.repo_root / 'package.json'
        frontend_package_json = self.repo_root / 'src' / 'frontend' / 'package.json'
        
        for pkg_file in [package_json, frontend_package_json]:
            if pkg_file.exists():
                result['details'][f'nodejs_deps_{pkg_file.parent.name}'] = 'found'
                
                try:
                    audit_result = subprocess.run(
                        ['npm', 'audit', '--audit-level=moderate', '--json'],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=pkg_file.parent
                    )
                    
                    if audit_result.returncode == 0:
                        result['details'][f'npm_audit_{pkg_file.parent.name}'] = 'clean'
                    else:
                        result['issues'].append(f"Node.js dependencies in {pkg_file.parent.name} have vulnerabilities")
                        
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    result['recommendations'].append("Run 'npm audit' for Node.js dependency scanning")
        
        # Determine status
        if not result['issues']:
            result['status'] = 'passed'
        elif len(result['issues']) <= 2:
            result['status'] = 'needs_attention'
        else:
            result['status'] = 'failed'
        
        return result
    
    def _analyze_code_security(self) -> Dict[str, Any]:
        """Analyze code for security issues."""
        result = {'status': 'unknown', 'details': {}, 'issues': [], 'recommendations': []}
        
        # Check for common security patterns
        security_patterns = [
            ('hardcoded_secrets', r'(password|secret|key|token)\s*=\s*["\'][^"\']+["\']'),
            ('sql_injection', r'(SELECT|INSERT|UPDATE|DELETE).*\+.*'),
            ('command_injection', r'(subprocess|os\.system|exec).*\+.*'),
            ('path_traversal', r'\.\./'),
        ]
        
        python_files = list(self.repo_root.rglob('*.py'))
        js_files = list(self.repo_root.rglob('*.js'))
        
        total_files = len(python_files) + len(js_files)
        result['details']['total_files_scanned'] = total_files
        
        security_issues_found = []
        
        for pattern_name, pattern in security_patterns:
            matching_files = []
            
            # Scan Python files
            for py_file in python_files:
                try:
                    content = py_file.read_text(encoding='utf-8', errors='ignore')
                    if pattern in content.lower():
                        matching_files.append(str(py_file.relative_to(self.repo_root)))
                except Exception:
                    continue
            
            # Scan JavaScript files
            for js_file in js_files:
                try:
                    content = js_file.read_text(encoding='utf-8', errors='ignore')
                    if pattern in content.lower():
                        matching_files.append(str(js_file.relative_to(self.repo_root)))
                except Exception:
                    continue
            
            if matching_files:
                security_issues_found.append({
                    'pattern': pattern_name,
                    'files': matching_files[:5]  # Limit to first 5 matches
                })
        
        result['details']['security_patterns_found'] = security_issues_found
        
        if security_issues_found:
            result['issues'].extend([f"Potential {issue['pattern']} found in code" for issue in security_issues_found])
            result['recommendations'].append("Review flagged code patterns for security issues")
        
        # Try to run bandit if available (Python security linter)
        try:
            bandit_result = subprocess.run(
                ['bandit', '-r', 'src/', '-f', 'json'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.repo_root
            )
            
            if bandit_result.returncode == 0:
                result['details']['bandit_scan'] = 'clean'
            else:
                result['issues'].append("Bandit found potential security issues in Python code")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            result['recommendations'].append("Install and run 'bandit' for Python security analysis")
        
        # Determine status
        if not result['issues']:
            result['status'] = 'passed'
        elif len(result['issues']) <= 3:
            result['status'] = 'needs_attention'
        else:
            result['status'] = 'failed'
        
        return result
    
    def _check_installer_integrity(self) -> Dict[str, Any]:
        """Check installer integrity and security."""
        result = {'status': 'unknown', 'details': {}, 'issues': [], 'recommendations': []}
        
        # Check installer directory structure
        installer_dir = self.repo_root / 'installer'
        if installer_dir.exists():
            result['details']['installer_directory'] = 'found'
            
            # Check for platform directories
            platforms = ['windows', 'macos', 'linux']
            found_platforms = []
            
            for platform in platforms:
                platform_dir = installer_dir / platform
                if platform_dir.exists():
                    found_platforms.append(platform)
                    
                    # Check for suspicious files
                    suspicious_extensions = ['.exe', '.dll', '.so', '.dylib']
                    suspicious_files = []
                    
                    for ext in suspicious_extensions:
                        suspicious_files.extend(list(platform_dir.rglob(f'*{ext}')))
                    
                    if suspicious_files:
                        result['details'][f'{platform}_binary_files'] = len(suspicious_files)
                        result['recommendations'].append(f"Verify integrity of binary files in {platform} installer")
            
            result['details']['supported_platforms'] = found_platforms
            
            if len(found_platforms) >= 2:
                result['details']['platform_coverage'] = 'good'
            else:
                result['issues'].append("Limited platform support in installers")
        else:
            result['issues'].append("Installer directory not found")
        
        # Check for checksum files
        checksum_files = list(self.repo_root.rglob('*SHA256*')) + list(self.repo_root.rglob('*checksum*'))
        if checksum_files:
            result['details']['checksum_files'] = [str(f.relative_to(self.repo_root)) for f in checksum_files]
            result['details']['integrity_verification'] = 'available'
        else:
            result['issues'].append("No checksum files found for integrity verification")
        
        # Determine status
        if not result['issues']:
            result['status'] = 'passed'
        elif len(result['issues']) <= 2:
            result['status'] = 'needs_attention'
        else:
            result['status'] = 'failed'
        
        return result
    
    def _review_workflow_security(self) -> Dict[str, Any]:
        """Review GitHub Actions workflow security."""
        result = {'status': 'unknown', 'details': {}, 'issues': [], 'recommendations': []}
        
        workflows_dir = self.repo_root / '.github' / 'workflows'
        if workflows_dir.exists():
            workflows = list(workflows_dir.glob('*.yml'))
            result['details']['workflow_count'] = len(workflows)
            
            security_issues = []
            
            for workflow in workflows:
                try:
                    content = workflow.read_text()
                    
                    # Check for security best practices
                    if 'actions/checkout@v' not in content:
                        security_issues.append(f"Workflow {workflow.name} may not pin action versions")
                    
                    if 'secrets.' in content.lower():
                        result['details'][f'{workflow.name}_uses_secrets'] = True
                    
                    if 'pull_request_target' in content:
                        security_issues.append(f"Workflow {workflow.name} uses pull_request_target (security risk)")
                    
                except Exception as e:
                    security_issues.append(f"Error reading workflow {workflow.name}: {str(e)}")
            
            result['details']['security_issues'] = security_issues
            
            if security_issues:
                result['issues'].extend(security_issues)
                result['recommendations'].append("Review and fix workflow security issues")
            
        else:
            result['issues'].append("No GitHub Actions workflows found")
        
        # Determine status
        if not result['issues']:
            result['status'] = 'passed'
        elif len(result['issues']) <= 3:
            result['status'] = 'needs_attention'
        else:
            result['status'] = 'failed'
        
        return result
    
    def _review_documentation_security(self) -> Dict[str, Any]:
        """Review documentation for security considerations."""
        result = {'status': 'unknown', 'details': {}, 'issues': [], 'recommendations': []}
        
        # Check for security documentation
        security_docs = []
        docs_dir = self.repo_root / 'docs'
        
        if docs_dir.exists():
            security_docs.extend(list(docs_dir.rglob('*security*.md')))
            security_docs.extend(list(docs_dir.rglob('*SECURITY*.md')))
        
        # Check root level security files
        root_security_files = [
            self.repo_root / 'SECURITY.md',
            self.repo_root / 'security.md'
        ]
        
        for sec_file in root_security_files:
            if sec_file.exists():
                security_docs.append(sec_file)
        
        if security_docs:
            result['details']['security_documentation'] = [str(f.relative_to(self.repo_root)) for f in security_docs]
            result['details']['security_doc_coverage'] = 'available'
        else:
            result['issues'].append("No security documentation found")
            result['recommendations'].append("Create comprehensive security documentation")
        
        # Check verification documentation for security guidance
        verification_dir = self.repo_root / 'verification'
        if verification_dir.exists():
            verification_guide = verification_dir / 'COMMUNITY_VERIFICATION_GUIDE.md'
            if verification_guide.exists():
                try:
                    content = verification_guide.read_text().lower()
                    security_terms = ['security', 'vulnerability', 'malware', 'checksum', 'signature']
                    found_terms = [term for term in security_terms if term in content]
                    
                    result['details']['verification_security_coverage'] = len(found_terms)
                    
                    if len(found_terms) >= 3:
                        result['details']['verification_security'] = 'good'
                    else:
                        result['recommendations'].append("Enhance security guidance in verification documentation")
                        
                except Exception as e:
                    result['issues'].append(f"Error reading verification guide: {str(e)}")
        
        # Determine status
        if not result['issues']:
            result['status'] = 'passed'
        elif len(result['issues']) <= 2:
            result['status'] = 'needs_attention'
        else:
            result['status'] = 'failed'
        
        return result
    
    def _generate_audit_materials(self):
        """Generate comprehensive audit materials."""
        logger.info("📋 Generating audit materials...")
        
        # Generate security summary report
        self._generate_security_summary()
        
        # Generate vulnerability assessment
        self._generate_vulnerability_assessment()
        
        # Generate compliance checklist
        self._generate_compliance_checklist()
        
        # Generate incident response plan
        self._generate_incident_response_plan()
    
    def _generate_security_summary(self):
        """Generate security summary report."""
        summary_file = self.audit_dir / 'security_summary.md'
        
        passed_scans = self.audit_results['summary']['passed_scans']
        total_scans = self.audit_results['summary']['total_scans']
        success_rate = (passed_scans / total_scans * 100) if total_scans > 0 else 0
        
        summary_content = f"""# Security Audit Summary

**Generated:** {self.audit_results['timestamp']}
**Overall Security Posture:** {self.audit_results['overall_status'].upper()}
**Security Scan Success Rate:** {success_rate:.1f}%

## Executive Summary

This document provides a comprehensive security assessment of the Bitcoin Solo Miner Monitor installer distribution system.

### Key Metrics
- **Total Security Scans:** {total_scans}
- **Passed Scans:** {passed_scans}
- **Security Issues Identified:** {len(self.audit_results['summary']['security_issues'])}

### Security Scan Results

"""
        
        for scan_name, scan_result in self.audit_results['security_scans'].items():
            status_icon = {'passed': '✅', 'needs_attention': '⚠️', 'failed': '❌'}.get(scan_result['status'], '❓')
            summary_content += f"- **{scan_name.replace('_', ' ').title()}:** {status_icon} {scan_result['status'].upper()}\n"
        
        summary_content += f"""
### Security Recommendations

"""
        
        all_recommendations = []
        for scan_result in self.audit_results['security_scans'].values():
            all_recommendations.extend(scan_result.get('recommendations', []))
        
        for i, rec in enumerate(set(all_recommendations)[:10], 1):
            summary_content += f"{i}. {rec}\n"
        
        summary_file.write_text(summary_content)
        self.audit_results['audit_materials']['security_summary'] = str(summary_file)
    
    def _generate_vulnerability_assessment(self):
        """Generate vulnerability assessment report."""
        vuln_file = self.audit_dir / 'vulnerability_assessment.json'
        
        vulnerability_data = {
            'timestamp': self.audit_results['timestamp'],
            'assessment_scope': 'installer_distribution_system',
            'vulnerabilities': [],
            'risk_assessment': {
                'high_risk': 0,
                'medium_risk': 0,
                'low_risk': 0
            }
        }
        
        # Collect vulnerabilities from scan results
        for scan_name, scan_result in self.audit_results['security_scans'].items():
            for issue in scan_result.get('issues', []):
                vulnerability = {
                    'source': scan_name,
                    'description': issue,
                    'severity': 'medium',  # Default severity
                    'status': 'open'
                }
                
                # Determine severity based on keywords
                if any(keyword in issue.lower() for keyword in ['critical', 'high', 'severe']):
                    vulnerability['severity'] = 'high'
                    vulnerability_data['risk_assessment']['high_risk'] += 1
                elif any(keyword in issue.lower() for keyword in ['low', 'minor', 'info']):
                    vulnerability['severity'] = 'low'
                    vulnerability_data['risk_assessment']['low_risk'] += 1
                else:
                    vulnerability_data['risk_assessment']['medium_risk'] += 1
                
                vulnerability_data['vulnerabilities'].append(vulnerability)
        
        with open(vuln_file, 'w') as f:
            json.dump(vulnerability_data, f, indent=2)
        
        self.audit_results['audit_materials']['vulnerability_assessment'] = str(vuln_file)
    
    def _generate_compliance_checklist(self):
        """Generate security compliance checklist."""
        checklist_file = self.audit_dir / 'compliance_checklist.md'
        
        checklist_content = """# Security Compliance Checklist

## Code Security
- [ ] No hardcoded secrets or credentials
- [ ] Input validation implemented
- [ ] SQL injection prevention measures
- [ ] Command injection prevention measures
- [ ] Path traversal protection

## Dependency Security
- [ ] All dependencies scanned for vulnerabilities
- [ ] Vulnerable dependencies updated or mitigated
- [ ] Dependency pinning implemented
- [ ] Regular dependency updates scheduled

## Build and Distribution Security
- [ ] Secure build environment
- [ ] Code signing implemented
- [ ] Checksum generation for all artifacts
- [ ] Secure distribution channels
- [ ] Integrity verification documentation

## Infrastructure Security
- [ ] GitHub Actions workflows secured
- [ ] Secrets management implemented
- [ ] Access controls configured
- [ ] Audit logging enabled

## Documentation Security
- [ ] Security documentation available
- [ ] Vulnerability disclosure process documented
- [ ] Incident response plan documented
- [ ] User security guidance provided

## Community Security
- [ ] Community verification processes documented
- [ ] Security reporting mechanisms available
- [ ] Regular security reviews scheduled
- [ ] Security awareness training materials available
"""
        
        checklist_file.write_text(checklist_content)
        self.audit_results['audit_materials']['compliance_checklist'] = str(checklist_file)
    
    def _generate_incident_response_plan(self):
        """Generate incident response plan."""
        incident_file = self.audit_dir / 'incident_response_plan.md'
        
        incident_content = """# Security Incident Response Plan

## Overview
This document outlines the procedures for responding to security incidents related to the Bitcoin Solo Miner Monitor installer distribution system.

## Incident Classification

### High Severity
- Compromised signing keys
- Malware in distributed installers
- Critical vulnerability in released software
- Unauthorized access to distribution infrastructure

### Medium Severity
- Non-critical vulnerabilities in released software
- Suspicious activity in distribution channels
- Potential security issues reported by community

### Low Severity
- Minor security improvements needed
- Documentation updates required
- Preventive security measures

## Response Procedures

### Immediate Response (0-2 hours)
1. Assess incident severity
2. Contain the threat if possible
3. Notify key stakeholders
4. Begin incident documentation

### Short-term Response (2-24 hours)
1. Investigate root cause
2. Implement temporary mitigations
3. Communicate with affected users
4. Coordinate with security team

### Long-term Response (1-7 days)
1. Implement permanent fixes
2. Update security measures
3. Conduct post-incident review
4. Update documentation and procedures

## Contact Information
- Security Team: security@project.org
- Project Maintainers: maintainers@project.org
- Community: GitHub Issues / Discussions

## Communication Templates
Templates for security advisories and user notifications should be prepared in advance.
"""
        
        incident_file.write_text(incident_content)
        self.audit_results['audit_materials']['incident_response_plan'] = str(incident_file)
    
    def _assess_security_posture(self):
        """Assess overall security posture."""
        passed_scans = self.audit_results['summary']['passed_scans']
        total_scans = self.audit_results['summary']['total_scans']
        
        if total_scans == 0:
            self.audit_results['overall_status'] = 'unknown'
        elif passed_scans == total_scans:
            self.audit_results['overall_status'] = 'strong'
        elif passed_scans >= total_scans * 0.8:
            self.audit_results['overall_status'] = 'good'
        elif passed_scans >= total_scans * 0.6:
            self.audit_results['overall_status'] = 'needs_improvement'
        else:
            self.audit_results['overall_status'] = 'weak'
    
    def save_results(self, output_file: Path = None) -> Path:
        """Save audit results to file."""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.audit_dir / f'security_audit_results_{timestamp}.json'
        
        with open(output_file, 'w') as f:
            json.dump(self.audit_results, f, indent=2)
        
        logger.info(f"📄 Security audit results saved to {output_file}")
        return output_file

def main():
    """Main entry point for security audit preparation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Security Audit Preparation for Professional Installer Distribution"
    )
    parser.add_argument('--repo-root', type=Path, help='Repository root directory')
    parser.add_argument('--output-dir', type=Path, help='Output directory for audit materials')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize preparator
    preparator = SecurityAuditPreparator(args.repo_root)
    
    if args.output_dir:
        preparator.audit_dir = args.output_dir
        preparator.audit_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run security audit preparation
        logger.info("🚀 Starting security audit preparation...")
        results = preparator.prepare_security_audit()
        
        # Save results
        results_file = preparator.save_results()
        
        # Print summary
        print("\n" + "="*80)
        print("SECURITY AUDIT PREPARATION COMPLETE")
        print("="*80)
        print(f"Security Posture: {results['overall_status'].upper()}")
        print(f"Scans Completed: {results['summary']['total_scans']}")
        print(f"Security Issues: {len(results['summary']['security_issues'])}")
        print(f"Audit Materials: {len(results['audit_materials'])}")
        print(f"Results saved to: {results_file}")
        print("="*80)
        
        # Exit with appropriate code
        if results['overall_status'] in ['strong', 'good']:
            sys.exit(0)
        elif results['overall_status'] == 'needs_improvement':
            sys.exit(1)
        else:
            sys.exit(2)
            
    except KeyboardInterrupt:
        logger.info("❌ Security audit preparation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Security audit preparation failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()