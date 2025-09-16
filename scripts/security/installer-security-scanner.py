#!/usr/bin/env python3
"""
Installer Security Scanner
Automated security scanning of generated installers for Bitcoin Solo Miner Monitor
"""

import os
import sys
import json
import hashlib
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import tempfile
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityScanner:
    """Main security scanner for installer files"""
    
    def __init__(self, output_dir: str = "security-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.scan_results = {}
        
    def scan_installer_file(self, file_path: str) -> Dict:
        """Scan a single installer file for security issues"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Installer file not found: {file_path}")
            
        logger.info(f"[SCAN] Scanning installer: {file_path.name}")
        
        scan_result = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "scan_timestamp": datetime.now().isoformat(),
            "file_info": self._get_file_info(file_path),
            "security_checks": {},
            "vulnerabilities": [],
            "recommendations": [],
            "overall_status": "unknown"
        }
        
        # Perform various security checks
        scan_result["security_checks"]["file_integrity"] = self._check_file_integrity(file_path)
        scan_result["security_checks"]["file_size"] = self._check_file_size(file_path)
        scan_result["security_checks"]["file_type"] = self._check_file_type(file_path)
        scan_result["security_checks"]["malware_scan"] = self._scan_for_malware(file_path)
        scan_result["security_checks"]["dependency_scan"] = self._scan_dependencies(file_path)
        
        # Platform-specific checks
        if file_path.suffix.lower() == '.exe':
            scan_result["security_checks"]["windows_specific"] = self._scan_windows_exe(file_path)
        elif file_path.suffix.lower() == '.dmg':
            scan_result["security_checks"]["macos_specific"] = self._scan_macos_dmg(file_path)
        elif file_path.suffix.lower() in ['.deb', '.rpm', '.appimage']:
            scan_result["security_checks"]["linux_specific"] = self._scan_linux_package(file_path)
            
        # Determine overall status
        scan_result["overall_status"] = self._determine_overall_status(scan_result)
        
        return scan_result
        
    def _get_file_info(self, file_path: Path) -> Dict:
        """Get basic file information"""
        stat = file_path.stat()
        
        # Calculate checksums
        sha256_hash = hashlib.sha256()
        md5_hash = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
                md5_hash.update(chunk)
                
        return {
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "sha256": sha256_hash.hexdigest(),
            "md5": md5_hash.hexdigest(),
            "permissions": oct(stat.st_mode)[-3:]
        }
        
    def _check_file_integrity(self, file_path: Path) -> Dict:
        """Check file integrity and basic properties"""
        result = {"status": "pass", "issues": [], "details": {}}
        
        try:
            # Check if file is readable
            with open(file_path, 'rb') as f:
                f.read(1024)  # Try to read first 1KB
                
            result["details"]["readable"] = True
            
            # Check file size reasonableness
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb < 1:
                result["issues"].append("File size unusually small (< 1MB)")
                result["status"] = "warning"
            elif size_mb > 500:
                result["issues"].append("File size unusually large (> 500MB)")
                result["status"] = "warning"
                
        except Exception as e:
            result["status"] = "fail"
            result["issues"].append(f"File integrity check failed: {str(e)}")
            
        return result
        
    def _check_file_size(self, file_path: Path) -> Dict:
        """Check if file size is within expected ranges"""
        result = {"status": "pass", "issues": [], "details": {}}
        
        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        
        result["details"]["size_bytes"] = size_bytes
        result["details"]["size_mb"] = round(size_mb, 2)
        
        # Define expected size ranges by file type
        expected_ranges = {
            '.exe': (5, 200),    # 5MB to 200MB for Windows installer
            '.dmg': (10, 300),   # 10MB to 300MB for macOS DMG
            '.deb': (1, 100),    # 1MB to 100MB for DEB package
            '.rpm': (1, 100),    # 1MB to 100MB for RPM package
            '.appimage': (5, 150) # 5MB to 150MB for AppImage
        }
        
        suffix = file_path.suffix.lower()
        if suffix in expected_ranges:
            min_size, max_size = expected_ranges[suffix]
            
            if size_mb < min_size:
                result["status"] = "warning"
                result["issues"].append(f"File size ({size_mb:.1f}MB) below expected minimum ({min_size}MB)")
            elif size_mb > max_size:
                result["status"] = "warning"
                result["issues"].append(f"File size ({size_mb:.1f}MB) above expected maximum ({max_size}MB)")
                
        return result
        
    def _check_file_type(self, file_path: Path) -> Dict:
        """Verify file type matches extension"""
        result = {"status": "pass", "issues": [], "details": {}}
        
        try:
            # Use file command if available (Unix-like systems)
            if shutil.which('file'):
                cmd_result = subprocess.run(
                    ['file', str(file_path)], 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                
                if cmd_result.returncode == 0:
                    file_type = cmd_result.stdout.strip()
                    result["details"]["detected_type"] = file_type
                    
                    # Verify file type matches extension
                    suffix = file_path.suffix.lower()
                    expected_types = {
                        '.exe': ['PE32', 'executable', 'Windows'],
                        '.dmg': ['disk image', 'Apple', 'DMG'],
                        '.deb': ['Debian', 'package', 'archive'],
                        '.rpm': ['RPM', 'package'],
                        '.appimage': ['ELF', 'executable', 'AppImage']
                    }
                    
                    if suffix in expected_types:
                        expected = expected_types[suffix]
                        if not any(exp.lower() in file_type.lower() for exp in expected):
                            result["status"] = "warning"
                            result["issues"].append(f"File type '{file_type}' doesn't match extension '{suffix}'")
                            
        except subprocess.TimeoutExpired:
            result["status"] = "warning"
            result["issues"].append("File type check timed out")
        except Exception as e:
            result["status"] = "warning"
            result["issues"].append(f"Could not determine file type: {str(e)}")
            
        return result
        
    def _scan_for_malware(self, file_path: Path) -> Dict:
        """Basic malware scanning using available tools"""
        result = {"status": "pass", "issues": [], "details": {}}
        
        # Note: This is a basic implementation
        # In production, you might integrate with ClamAV or other scanners
        
        try:
            # Check for ClamAV
            if shutil.which('clamscan'):
                logger.info("Running ClamAV scan...")
                cmd_result = subprocess.run(
                    ['clamscan', '--no-summary', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                result["details"]["clamav_output"] = cmd_result.stdout
                
                if cmd_result.returncode != 0:
                    if "FOUND" in cmd_result.stdout:
                        result["status"] = "fail"
                        result["issues"].append("Malware detected by ClamAV")
                    else:
                        result["status"] = "warning"
                        result["issues"].append("ClamAV scan completed with warnings")
                else:
                    result["details"]["clamav_clean"] = True
                    
            else:
                result["status"] = "info"
                result["issues"].append("ClamAV not available - malware scan skipped")
                
        except subprocess.TimeoutExpired:
            result["status"] = "warning"
            result["issues"].append("Malware scan timed out")
        except Exception as e:
            result["status"] = "warning"
            result["issues"].append(f"Malware scan failed: {str(e)}")
            
        return result
        
    def _scan_dependencies(self, file_path: Path) -> Dict:
        """Scan for known vulnerable dependencies"""
        result = {"status": "pass", "issues": [], "details": {}}
        
        # This would integrate with vulnerability databases
        # For now, we'll do basic checks
        
        result["details"]["scan_method"] = "basic_heuristics"
        result["status"] = "info"
        result["issues"].append("Dependency vulnerability scanning requires integration with CVE databases")
        
        return result
        
    def _scan_windows_exe(self, file_path: Path) -> Dict:
        """Windows-specific security checks"""
        result = {"status": "pass", "issues": [], "details": {}}
        
        try:
            # Check if it's a valid PE file
            with open(file_path, 'rb') as f:
                # Read DOS header
                dos_header = f.read(64)
                if len(dos_header) >= 2 and dos_header[:2] == b'MZ':
                    result["details"]["valid_pe"] = True
                else:
                    result["status"] = "fail"
                    result["issues"].append("Invalid PE file format")
                    
        except Exception as e:
            result["status"] = "warning"
            result["issues"].append(f"PE analysis failed: {str(e)}")
            
        return result
        
    def _scan_macos_dmg(self, file_path: Path) -> Dict:
        """macOS-specific security checks"""
        result = {"status": "pass", "issues": [], "details": {}}
        
        # Check if hdiutil is available (macOS only)
        if shutil.which('hdiutil'):
            try:
                # Verify DMG integrity
                cmd_result = subprocess.run(
                    ['hdiutil', 'verify', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if cmd_result.returncode == 0:
                    result["details"]["dmg_integrity"] = "valid"
                else:
                    result["status"] = "fail"
                    result["issues"].append("DMG integrity verification failed")
                    
            except subprocess.TimeoutExpired:
                result["status"] = "warning"
                result["issues"].append("DMG verification timed out")
            except Exception as e:
                result["status"] = "warning"
                result["issues"].append(f"DMG verification failed: {str(e)}")
        else:
            result["status"] = "info"
            result["issues"].append("hdiutil not available - DMG verification skipped")
            
        return result
        
    def _scan_linux_package(self, file_path: Path) -> Dict:
        """Linux package-specific security checks"""
        result = {"status": "pass", "issues": [], "details": {}}
        
        suffix = file_path.suffix.lower()
        
        if suffix == '.deb':
            # Check DEB package integrity
            if shutil.which('dpkg'):
                try:
                    cmd_result = subprocess.run(
                        ['dpkg', '--info', str(file_path)],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if cmd_result.returncode == 0:
                        result["details"]["deb_info"] = cmd_result.stdout
                    else:
                        result["status"] = "fail"
                        result["issues"].append("Invalid DEB package format")
                        
                except Exception as e:
                    result["status"] = "warning"
                    result["issues"].append(f"DEB analysis failed: {str(e)}")
            else:
                result["status"] = "info"
                result["issues"].append("dpkg not available - DEB verification skipped")
                
        elif suffix == '.rpm':
            # Check RPM package integrity
            if shutil.which('rpm'):
                try:
                    cmd_result = subprocess.run(
                        ['rpm', '-qip', str(file_path)],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if cmd_result.returncode == 0:
                        result["details"]["rpm_info"] = cmd_result.stdout
                    else:
                        result["status"] = "fail"
                        result["issues"].append("Invalid RPM package format")
                        
                except Exception as e:
                    result["status"] = "warning"
                    result["issues"].append(f"RPM analysis failed: {str(e)}")
            else:
                result["status"] = "info"
                result["issues"].append("rpm not available - RPM verification skipped")
                
        elif suffix == '.appimage':
            # Check AppImage executable permissions
            if not os.access(file_path, os.X_OK):
                result["status"] = "warning"
                result["issues"].append("AppImage is not executable")
                
        return result
        
    def _determine_overall_status(self, scan_result: Dict) -> str:
        """Determine overall security status based on all checks"""
        statuses = []
        
        for check_name, check_result in scan_result["security_checks"].items():
            if isinstance(check_result, dict) and "status" in check_result:
                statuses.append(check_result["status"])
                
        # Priority: fail > warning > info > pass
        if "fail" in statuses:
            return "fail"
        elif "warning" in statuses:
            return "warning"
        elif "info" in statuses:
            return "info"
        else:
            return "pass"
            
    def generate_report(self, scan_results: List[Dict], output_format: str = "json") -> str:
        """Generate security scan report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == "json":
            report_file = self.output_dir / f"security_report_{timestamp}.json"
            
            report_data = {
                "scan_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "scanner_version": "1.0.0",
                    "total_files_scanned": len(scan_results)
                },
                "scan_results": scan_results,
                "summary": self._generate_summary(scan_results)
            }
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
                
        elif output_format == "markdown":
            report_file = self.output_dir / f"security_report_{timestamp}.md"
            
            with open(report_file, 'w') as f:
                f.write(self._generate_markdown_report(scan_results))
                
        logger.info(f"[REPORT] Security report generated: {report_file}")
        return str(report_file)
        
    def _generate_summary(self, scan_results: List[Dict]) -> Dict:
        """Generate summary statistics"""
        summary = {
            "total_files": len(scan_results),
            "status_counts": {"pass": 0, "warning": 0, "fail": 0, "info": 0},
            "critical_issues": [],
            "recommendations": []
        }
        
        for result in scan_results:
            status = result.get("overall_status", "unknown")
            if status in summary["status_counts"]:
                summary["status_counts"][status] += 1
                
            # Collect critical issues
            if status == "fail":
                summary["critical_issues"].append({
                    "file": result["file_name"],
                    "issues": self._extract_issues(result)
                })
                
        # Generate recommendations
        if summary["status_counts"]["fail"] > 0:
            summary["recommendations"].append("Address critical security issues before distribution")
        if summary["status_counts"]["warning"] > 0:
            summary["recommendations"].append("Review and resolve security warnings")
            
        return summary
        
    def _extract_issues(self, scan_result: Dict) -> List[str]:
        """Extract all issues from a scan result"""
        issues = []
        
        for check_name, check_result in scan_result.get("security_checks", {}).items():
            if isinstance(check_result, dict) and "issues" in check_result:
                issues.extend(check_result["issues"])
                
        return issues
        
    def _generate_markdown_report(self, scan_results: List[Dict]) -> str:
        """Generate markdown format report"""
        lines = [
            "# Security Scan Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            ""
        ]
        
        summary = self._generate_summary(scan_results)
        
        lines.extend([
            f"- **Total Files Scanned:** {summary['total_files']}",
            f"- **Passed:** {summary['status_counts']['pass']}",
            f"- **Warnings:** {summary['status_counts']['warning']}",
            f"- **Failed:** {summary['status_counts']['fail']}",
            f"- **Info:** {summary['status_counts']['info']}",
            ""
        ])
        
        if summary["critical_issues"]:
            lines.extend([
                "## Critical Issues",
                ""
            ])
            
            for issue in summary["critical_issues"]:
                lines.append(f"### {issue['file']}")
                for item in issue["issues"]:
                    lines.append(f"- ❌ {item}")
                lines.append("")
                
        lines.extend([
            "## Detailed Results",
            ""
        ])
        
        for result in scan_results:
            status_emoji = {
                "pass": "✅",
                "warning": "⚠️",
                "fail": "❌",
                "info": "ℹ️"
            }.get(result["overall_status"], "❓")
            
            lines.extend([
                f"### {status_emoji} {result['file_name']}",
                f"**Status:** {result['overall_status']}",
                f"**Size:** {result['file_info']['size_mb']} MB",
                f"**SHA256:** `{result['file_info']['sha256']}`",
                ""
            ])
            
            # Add issues if any
            all_issues = self._extract_issues(result)
            if all_issues:
                lines.append("**Issues:**")
                for issue in all_issues:
                    lines.append(f"- {issue}")
                lines.append("")
                
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Security scanner for installer files")
    parser.add_argument("files", nargs="+", help="Installer files to scan")
    parser.add_argument("--output-dir", default="security-reports", help="Output directory for reports")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Report format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    scanner = SecurityScanner(args.output_dir)
    scan_results = []
    
    for file_path in args.files:
        try:
            result = scanner.scan_installer_file(file_path)
            scan_results.append(result)
            
            status_emoji = {
                "pass": "✅",
                "warning": "⚠️", 
                "fail": "❌",
                "info": "ℹ️"
            }.get(result["overall_status"], "❓")
            
            status_text = {
                "pass": "[PASS]",
                "warning": "[WARN]", 
                "fail": "[FAIL]",
                "info": "[INFO]"
            }.get(result["overall_status"], "[UNKNOWN]")
            
            print(f"{status_text} {result['file_name']}: {result['overall_status']}")
            
        except Exception as e:
            logger.error(f"Failed to scan {file_path}: {str(e)}")
            
    if scan_results:
        report_file = scanner.generate_report(scan_results, args.format)
        print(f"\n[REPORT] Report generated: {report_file}")
        
        # Print summary
        summary = scanner._generate_summary(scan_results)
        if summary["status_counts"]["fail"] > 0:
            print(f"[FAIL] {summary['status_counts']['fail']} files failed security checks")
            sys.exit(1)
        elif summary["status_counts"]["warning"] > 0:
            print(f"[WARN] {summary['status_counts']['warning']} files have security warnings")
        else:
            print("[PASS] All files passed security checks")


if __name__ == "__main__":
    main()