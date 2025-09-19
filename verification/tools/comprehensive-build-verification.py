#!/usr/bin/env python3
"""
Comprehensive Build Verification Tool for Bitcoin Solo Miner Monitor

This tool provides automated verification of Bitcoin Solo Miner Monitor releases
through multiple verification methods including checksum verification, reproducible
builds, and security scanning.

Usage:
    python3 comprehensive-build-verification.py --version v0.1.0 --method all
    python3 comprehensive-build-verification.py --version v0.1.0 --method checksum
    python3 comprehensive-build-verification.py --version v0.1.0 --method reproducible
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class VerificationResult:
    """Container for verification results"""
    def __init__(self, method: str, success: bool, details: Dict, duration: float):
        self.method = method
        self.success = success
        self.details = details
        self.duration = duration
        self.timestamp = datetime.utcnow().isoformat()

class BuildVerifier:
    """Main verification class"""
    
    def __init__(self, version: str, work_dir: Optional[str] = None):
        self.version = version
        self.work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="bitcoin-miner-verify-"))
        self.repo_url = "https://github.com/smokeysrh/bitcoin-solo-miner-monitor"
        self.results: List[VerificationResult] = []
        
        # Create work directory structure
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir = self.work_dir / "downloads"
        self.build_dir = self.work_dir / "build"
        self.reports_dir = self.work_dir / "reports"
        
        for dir_path in [self.downloads_dir, self.build_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str, color: str = Colors.WHITE, bold: bool = False):
        """Print colored log message"""
        prefix = f"{Colors.BOLD}" if bold else ""
        print(f"{prefix}{color}{message}{Colors.END}")
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, 
                   capture_output: bool = True, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run shell command and return success, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd or self.work_dir,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)
    
    def download_file(self, url: str, filename: str) -> bool:
        """Download file with progress indication"""
        try:
            self.log(f"Downloading {filename}...", Colors.BLUE)
            file_path = self.downloads_dir / filename
            
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r  Progress: {progress:.1f}%", end='', flush=True)
                
                print()  # New line after progress
                self.log(f"✅ Downloaded {filename}", Colors.GREEN)
                return True
                
        except Exception as e:
            self.log(f"❌ Failed to download {filename}: {e}", Colors.RED)
            return False
    
    def verify_checksums(self) -> VerificationResult:
        """Verify file checksums against official release"""
        start_time = time.time()
        self.log("🔍 Starting checksum verification...", Colors.CYAN, bold=True)
        
        details = {
            "files_verified": [],
            "files_failed": [],
            "missing_files": [],
            "checksum_source": "official_release"
        }
        
        try:
            # Download checksums file
            checksums_url = f"{self.repo_url}/releases/download/{self.version}/SHA256SUMS"
            if not self.download_file(checksums_url, "SHA256SUMS"):
                return VerificationResult("checksum", False, 
                                        {"error": "Failed to download checksums"}, 
                                        time.time() - start_time)
            
            # Parse checksums file
            checksums_file = self.downloads_dir / "SHA256SUMS"
            expected_checksums = {}
            
            with open(checksums_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '  ' in line:
                        checksum, filename = line.split('  ', 1)
                        expected_checksums[filename] = checksum.lower()
            
            self.log(f"Found {len(expected_checksums)} files in checksums", Colors.BLUE)
            
            # Download and verify each file
            for filename, expected_checksum in expected_checksums.items():
                file_url = f"{self.repo_url}/releases/download/{self.version}/{filename}"
                
                if not self.download_file(file_url, filename):
                    details["missing_files"].append(filename)
                    continue
                
                # Calculate actual checksum
                file_path = self.downloads_dir / filename
                actual_checksum = self.calculate_sha256(file_path)
                
                if actual_checksum == expected_checksum:
                    self.log(f"✅ {filename}: VERIFIED", Colors.GREEN)
                    details["files_verified"].append({
                        "filename": filename,
                        "checksum": actual_checksum,
                        "size": file_path.stat().st_size
                    })
                else:
                    self.log(f"❌ {filename}: CHECKSUM MISMATCH", Colors.RED)
                    details["files_failed"].append({
                        "filename": filename,
                        "expected": expected_checksum,
                        "actual": actual_checksum
                    })
            
            success = len(details["files_failed"]) == 0 and len(details["missing_files"]) == 0
            
            if success:
                self.log("🎉 All checksums verified successfully!", Colors.GREEN, bold=True)
            else:
                self.log("❌ Checksum verification failed!", Colors.RED, bold=True)
            
            return VerificationResult("checksum", success, details, time.time() - start_time)
            
        except Exception as e:
            return VerificationResult("checksum", False, 
                                    {"error": str(e)}, 
                                    time.time() - start_time)
    
    def verify_reproducible_build(self) -> VerificationResult:
        """Perform full reproducible build verification"""
        start_time = time.time()
        self.log("🏗️ Starting reproducible build verification...", Colors.CYAN, bold=True)
        
        details = {
            "environment": {},
            "build_results": {},
            "checksum_comparison": {},
            "build_logs": []
        }
        
        try:
            # Check prerequisites
            if not self.check_build_prerequisites():
                return VerificationResult("reproducible", False,
                                        {"error": "Build prerequisites not met"},
                                        time.time() - start_time)
            
            # Record environment
            details["environment"] = self.get_build_environment()
            
            # Clone repository
            repo_dir = self.build_dir / "bitcoin-solo-miner-monitor"
            if repo_dir.exists():
                shutil.rmtree(repo_dir)
            
            self.log("Cloning repository...", Colors.BLUE)
            success, stdout, stderr = self.run_command([
                "git", "clone", self.repo_url, str(repo_dir)
            ])
            
            if not success:
                return VerificationResult("reproducible", False,
                                        {"error": f"Git clone failed: {stderr}"},
                                        time.time() - start_time)
            
            # Checkout specific version
            self.log(f"Checking out version {self.version}...", Colors.BLUE)
            success, stdout, stderr = self.run_command([
                "git", "checkout", self.version
            ], cwd=repo_dir)
            
            if not success:
                return VerificationResult("reproducible", False,
                                        {"error": f"Git checkout failed: {stderr}"},
                                        time.time() - start_time)
            
            # Set reproducible build environment
            env = os.environ.copy()
            env.update({
                "PYTHONHASHSEED": "0",
                "SOURCE_DATE_EPOCH": "1704067200",
                "LC_ALL": "C.UTF-8",
                "LANG": "C.UTF-8",
                "TZ": "UTC"
            })
            
            # Install dependencies
            self.log("Installing Python dependencies...", Colors.BLUE)
            success, stdout, stderr = self.run_command([
                "python3", "-m", "pip", "install", "-r", "requirements.txt"
            ], cwd=repo_dir)
            
            if not success:
                details["build_logs"].append(f"Pip install failed: {stderr}")
            
            # Build frontend if exists
            frontend_dir = repo_dir / "src" / "frontend"
            if frontend_dir.exists():
                self.log("Building frontend...", Colors.BLUE)
                
                # Install npm dependencies
                success, stdout, stderr = self.run_command([
                    "npm", "ci"
                ], cwd=frontend_dir)
                
                if success:
                    # Build frontend
                    success, stdout, stderr = self.run_command([
                        "npm", "run", "build"
                    ], cwd=frontend_dir)
                
                if not success:
                    details["build_logs"].append(f"Frontend build failed: {stderr}")
            
            # Build installers for current platform
            current_platform = self.get_current_platform()
            self.log(f"Building installer for {current_platform}...", Colors.BLUE)
            
            success, stdout, stderr = self.run_command([
                "python3", "scripts/create-distribution.py",
                "--platform", current_platform,
                "--version", self.version.lstrip('v')
            ], cwd=repo_dir, timeout=1800)  # 30 minute timeout
            
            if not success:
                details["build_logs"].append(f"Build failed: {stderr}")
                return VerificationResult("reproducible", False, details, time.time() - start_time)
            
            # Generate checksums for built files
            dist_dir = repo_dir / "distribution"
            if dist_dir.exists():
                local_checksums = {}
                for file_path in dist_dir.rglob("*"):
                    if file_path.is_file() and file_path.suffix in ['.exe', '.dmg', '.deb', '.rpm', '.AppImage']:
                        checksum = self.calculate_sha256(file_path)
                        local_checksums[file_path.name] = checksum
                
                details["build_results"]["local_checksums"] = local_checksums
                
                # Compare with official checksums
                official_checksums_file = self.downloads_dir / "SHA256SUMS"
                if official_checksums_file.exists():
                    with open(official_checksums_file, 'r') as f:
                        official_checksums = {}
                        for line in f:
                            line = line.strip()
                            if line and '  ' in line:
                                checksum, filename = line.split('  ', 1)
                                official_checksums[filename] = checksum.lower()
                    
                    # Compare checksums
                    matches = 0
                    total = 0
                    for filename, local_checksum in local_checksums.items():
                        if filename in official_checksums:
                            total += 1
                            if local_checksum == official_checksums[filename]:
                                matches += 1
                                self.log(f"✅ {filename}: BUILD MATCHES", Colors.GREEN)
                            else:
                                self.log(f"❌ {filename}: BUILD DIFFERS", Colors.RED)
                                details["checksum_comparison"][filename] = {
                                    "local": local_checksum,
                                    "official": official_checksums[filename]
                                }
                    
                    success = matches == total and total > 0
                    details["build_results"]["matches"] = matches
                    details["build_results"]["total"] = total
                else:
                    success = False
                    details["error"] = "No official checksums available for comparison"
            else:
                success = False
                details["error"] = "No build artifacts generated"
            
            if success:
                self.log("🎉 Reproducible build verification successful!", Colors.GREEN, bold=True)
            else:
                self.log("❌ Reproducible build verification failed!", Colors.RED, bold=True)
            
            return VerificationResult("reproducible", success, details, time.time() - start_time)
            
        except Exception as e:
            return VerificationResult("reproducible", False,
                                    {"error": str(e)},
                                    time.time() - start_time)
    
    def verify_source_audit(self) -> VerificationResult:
        """Perform basic source code security audit"""
        start_time = time.time()
        self.log("🔒 Starting source code security audit...", Colors.CYAN, bold=True)
        
        details = {
            "security_tools": [],
            "vulnerabilities": [],
            "code_quality": {},
            "dependency_audit": {}
        }
        
        try:
            repo_dir = self.build_dir / "bitcoin-solo-miner-monitor"
            
            # Python security analysis with bandit
            if shutil.which("bandit"):
                self.log("Running bandit security analysis...", Colors.BLUE)
                success, stdout, stderr = self.run_command([
                    "bandit", "-r", "src/", "-f", "json", "-o", "bandit-report.json"
                ], cwd=repo_dir)
                
                details["security_tools"].append("bandit")
                
                if success:
                    bandit_report_file = repo_dir / "bandit-report.json"
                    if bandit_report_file.exists():
                        with open(bandit_report_file, 'r') as f:
                            bandit_data = json.load(f)
                            details["vulnerabilities"].extend(bandit_data.get("results", []))
            
            # Python dependency security check with safety
            if shutil.which("safety"):
                self.log("Running safety dependency check...", Colors.BLUE)
                success, stdout, stderr = self.run_command([
                    "safety", "check", "-r", "requirements.txt", "--json"
                ], cwd=repo_dir)
                
                details["security_tools"].append("safety")
                
                if success and stdout:
                    try:
                        safety_data = json.loads(stdout)
                        details["dependency_audit"]["vulnerabilities"] = safety_data
                    except json.JSONDecodeError:
                        pass
            
            # Node.js dependency audit
            frontend_dir = repo_dir / "src" / "frontend"
            if frontend_dir.exists() and shutil.which("npm"):
                self.log("Running npm audit...", Colors.BLUE)
                success, stdout, stderr = self.run_command([
                    "npm", "audit", "--json"
                ], cwd=frontend_dir)
                
                details["security_tools"].append("npm-audit")
                
                if stdout:
                    try:
                        npm_audit_data = json.loads(stdout)
                        details["dependency_audit"]["npm"] = npm_audit_data
                    except json.JSONDecodeError:
                        pass
            
            # Basic code quality checks
            python_files = list((repo_dir / "src").rglob("*.py"))
            details["code_quality"]["python_files"] = len(python_files)
            
            # Count lines of code
            total_lines = 0
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        total_lines += len(f.readlines())
                except:
                    pass
            
            details["code_quality"]["total_lines"] = total_lines
            
            # Check for common security patterns
            security_patterns = [
                "eval(",
                "exec(",
                "subprocess.call",
                "os.system",
                "shell=True"
            ]
            
            pattern_matches = {}
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in security_patterns:
                            if pattern in content:
                                if pattern not in pattern_matches:
                                    pattern_matches[pattern] = []
                                pattern_matches[pattern].append(str(py_file.relative_to(repo_dir)))
                except:
                    pass
            
            details["code_quality"]["security_patterns"] = pattern_matches
            
            # Determine overall security status
            high_risk_vulns = len([v for v in details["vulnerabilities"] if v.get("issue_severity") == "HIGH"])
            medium_risk_vulns = len([v for v in details["vulnerabilities"] if v.get("issue_severity") == "MEDIUM"])
            
            success = high_risk_vulns == 0 and medium_risk_vulns < 5
            
            if success:
                self.log("🎉 Source code audit passed!", Colors.GREEN, bold=True)
            else:
                self.log("⚠️ Source code audit found issues!", Colors.YELLOW, bold=True)
            
            return VerificationResult("audit", success, details, time.time() - start_time)
            
        except Exception as e:
            return VerificationResult("audit", False,
                                    {"error": str(e)},
                                    time.time() - start_time)
    
    def calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest().lower()
    
    def check_build_prerequisites(self) -> bool:
        """Check if build prerequisites are available"""
        required_tools = ["git", "python3", "pip"]
        
        for tool in required_tools:
            if not shutil.which(tool):
                self.log(f"❌ Required tool not found: {tool}", Colors.RED)
                return False
        
        # Check Python version
        success, stdout, stderr = self.run_command(["python3", "--version"])
        if success and "3.11" in stdout:
            self.log("✅ Python 3.11 found", Colors.GREEN)
        else:
            self.log("⚠️ Python 3.11 not found, build may not be reproducible", Colors.YELLOW)
        
        # Check Node.js if needed
        if shutil.which("node"):
            success, stdout, stderr = self.run_command(["node", "--version"])
            if success and "v18" in stdout:
                self.log("✅ Node.js 18 found", Colors.GREEN)
            else:
                self.log("⚠️ Node.js 18 not found, frontend build may fail", Colors.YELLOW)
        
        return True
    
    def get_build_environment(self) -> Dict:
        """Get current build environment information"""
        env_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
        
        # Get tool versions
        tools = ["git", "python3", "node", "npm"]
        for tool in tools:
            if shutil.which(tool):
                success, stdout, stderr = self.run_command([tool, "--version"])
                if success:
                    env_info[f"{tool}_version"] = stdout.strip().split('\n')[0]
        
        return env_info
    
    def get_current_platform(self) -> str:
        """Get current platform for building"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        else:
            return "linux"
    
    def generate_report(self) -> str:
        """Generate comprehensive verification report"""
        report_lines = [
            "# Bitcoin Solo Miner Monitor - Verification Report",
            f"**Generated**: {datetime.utcnow().isoformat()}Z",
            f"**Version**: {self.version}",
            f"**Platform**: {platform.platform()}",
            "",
            "## Summary",
            ""
        ]
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        
        report_lines.extend([
            f"- **Total Tests**: {total_tests}",
            f"- **Passed**: {passed_tests}",
            f"- **Failed**: {total_tests - passed_tests}",
            f"- **Overall Status**: {'✅ PASSED' if passed_tests == total_tests else '❌ FAILED'}",
            ""
        ])
        
        # Detailed results
        for result in self.results:
            status = "✅ PASSED" if result.success else "❌ FAILED"
            duration = f"{result.duration:.2f}s"
            
            report_lines.extend([
                f"## {result.method.title()} Verification",
                f"- **Status**: {status}",
                f"- **Duration**: {duration}",
                f"- **Timestamp**: {result.timestamp}",
                ""
            ])
            
            if result.details:
                report_lines.append("### Details")
                report_lines.append("```json")
                report_lines.append(json.dumps(result.details, indent=2))
                report_lines.append("```")
                report_lines.append("")
        
        # Recommendations
        report_lines.extend([
            "## Recommendations",
            ""
        ])
        
        if passed_tests == total_tests:
            report_lines.append("✅ All verifications passed. The release appears to be authentic and secure.")
        else:
            report_lines.append("❌ Some verifications failed. DO NOT use this release until issues are resolved.")
            report_lines.append("")
            report_lines.append("**Next Steps:**")
            report_lines.append("1. Report verification failure to the development team")
            report_lines.append("2. Do not install or use the software")
            report_lines.append("3. Wait for official response and resolution")
        
        return "\n".join(report_lines)
    
    def run_verification(self, methods: List[str]) -> bool:
        """Run specified verification methods"""
        self.log(f"🚀 Starting verification of {self.version}", Colors.MAGENTA, bold=True)
        self.log(f"Working directory: {self.work_dir}", Colors.BLUE)
        
        method_map = {
            "checksum": self.verify_checksums,
            "reproducible": self.verify_reproducible_build,
            "audit": self.verify_source_audit
        }
        
        for method in methods:
            if method in method_map:
                self.log(f"\n{'='*60}", Colors.CYAN)
                result = method_map[method]()
                self.results.append(result)
            else:
                self.log(f"❌ Unknown verification method: {method}", Colors.RED)
        
        # Generate and save report
        report_content = self.generate_report()
        report_file = self.reports_dir / f"verification-report-{self.version}-{int(time.time())}.md"
        
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        self.log(f"\n{'='*60}", Colors.CYAN)
        self.log(f"📄 Report saved to: {report_file}", Colors.BLUE)
        
        # Print summary
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        
        if passed == total:
            self.log(f"🎉 All {total} verifications PASSED!", Colors.GREEN, bold=True)
            return True
        else:
            self.log(f"❌ {total - passed} of {total} verifications FAILED!", Colors.RED, bold=True)
            return False

def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive verification tool for Bitcoin Solo Miner Monitor releases"
    )
    parser.add_argument(
        "--version", 
        required=True,
        help="Version to verify (e.g., v0.1.0)"
    )
    parser.add_argument(
        "--method",
        choices=["checksum", "reproducible", "audit", "all"],
        default="checksum",
        help="Verification method to use"
    )
    parser.add_argument(
        "--work-dir",
        help="Working directory for verification (default: temporary directory)"
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep downloaded files and build artifacts"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Determine methods to run
    if args.method == "all":
        methods = ["checksum", "reproducible", "audit"]
    else:
        methods = [args.method]
    
    # Create verifier
    verifier = BuildVerifier(args.version, args.work_dir)
    
    try:
        # Run verification
        success = verifier.run_verification(methods)
        
        # Cleanup if requested
        if not args.keep_files and not args.work_dir:
            shutil.rmtree(verifier.work_dir)
            verifier.log(f"🧹 Cleaned up temporary files", Colors.BLUE)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        verifier.log("\n⚠️ Verification interrupted by user", Colors.YELLOW)
        sys.exit(130)
    except Exception as e:
        verifier.log(f"\n❌ Verification failed with error: {e}", Colors.RED)
        sys.exit(1)

if __name__ == "__main__":
    main()