#!/usr/bin/env python3
"""
Community Security Verification Tool
Provides automated tools for community members to verify security aspects of the project
"""

import os
import sys
import json
import hashlib
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import argparse

class CommunitySecurityVerifier:
    """Tool for community security verification"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.verification_dir = Path("verification-results")
        self.verification_dir.mkdir(exist_ok=True)
        
        # GitHub repository information
        self.github_repo = "smokeysrh/bitcoin-solo-miner-monitor"
        self.github_api_base = f"https://api.github.com/repos/{self.github_repo}"
        
    def verify_release_checksums(self, version: str = "latest") -> Dict:
        """Verify checksums of official release artifacts"""
        print(f"🔐 Verifying release checksums for version: {version}")
        
        result = {
            "version": version,
            "verification_time": datetime.now().isoformat(),
            "checksum_verification": {},
            "overall_status": "unknown",
            "issues": []
        }
        
        try:
            # Get release information
            if version == "latest":
                release_url = f"{self.github_api_base}/releases/latest"
            else:
                release_url = f"{self.github_api_base}/releases/tags/v{version}"
            
            response = requests.get(release_url, timeout=30)
            if response.status_code != 200:
                result["issues"].append(f"Failed to fetch release info: {response.status_code}")
                result["overall_status"] = "error"
                return result
            
            release_data = response.json()
            actual_version = release_data["tag_name"].lstrip("v")
            result["version"] = actual_version
            
            # Find checksum file
            checksum_asset = None
            installer_assets = []
            
            for asset in release_data["assets"]:
                if asset["name"] in ["SHA256SUMS", "checksums.txt", "CHECKSUMS"]:
                    checksum_asset = asset
                elif asset["name"].endswith((".exe", ".dmg", ".deb", ".rpm", ".AppImage")):
                    installer_assets.append(asset)
            
            if not checksum_asset:
                result["issues"].append("No checksum file found in release")
                result["overall_status"] = "error"
                return result
            
            # Download checksum file
            print(f"📥 Downloading checksum file: {checksum_asset['name']}")
            checksum_response = requests.get(checksum_asset["browser_download_url"], timeout=60)
            if checksum_response.status_code != 200:
                result["issues"].append(f"Failed to download checksum file: {checksum_response.status_code}")
                result["overall_status"] = "error"
                return result
            
            # Parse checksums
            official_checksums = {}
            for line in checksum_response.text.strip().split('\n'):
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        checksum = parts[0]
                        filename = parts[1].lstrip('*')  # Remove binary mode indicator
                        official_checksums[filename] = checksum
            
            print(f"📋 Found checksums for {len(official_checksums)} files")
            
            # Verify each installer
            verification_results = {}
            
            for asset in installer_assets:
                filename = asset["name"]
                print(f"🔍 Verifying {filename}...")
                
                if filename not in official_checksums:
                    verification_results[filename] = {
                        "status": "missing_checksum",
                        "message": "No checksum found for this file"
                    }
                    continue
                
                # Download installer
                temp_file = self.verification_dir / filename
                print(f"  📥 Downloading {filename} ({asset['size']} bytes)...")
                
                installer_response = requests.get(asset["browser_download_url"], timeout=300)
                if installer_response.status_code != 200:
                    verification_results[filename] = {
                        "status": "download_failed",
                        "message": f"Download failed: {installer_response.status_code}"
                    }
                    continue
                
                # Save and calculate checksum
                with open(temp_file, 'wb') as f:
                    f.write(installer_response.content)
                
                calculated_checksum = self._calculate_sha256(temp_file)
                expected_checksum = official_checksums[filename]
                
                if calculated_checksum == expected_checksum:
                    verification_results[filename] = {
                        "status": "verified",
                        "checksum": calculated_checksum,
                        "message": "Checksum verification successful"
                    }
                    print(f"  ✅ {filename}: VERIFIED")
                else:
                    verification_results[filename] = {
                        "status": "mismatch",
                        "expected_checksum": expected_checksum,
                        "calculated_checksum": calculated_checksum,
                        "message": "Checksum mismatch detected"
                    }
                    print(f"  ❌ {filename}: CHECKSUM MISMATCH")
                    result["issues"].append(f"Checksum mismatch for {filename}")
                
                # Clean up downloaded file
                temp_file.unlink()
            
            result["checksum_verification"] = verification_results
            
            # Determine overall status
            verified_count = sum(1 for v in verification_results.values() if v["status"] == "verified")
            total_count = len(verification_results)
            
            if verified_count == total_count and total_count > 0:
                result["overall_status"] = "verified"
            elif verified_count > 0:
                result["overall_status"] = "partial"
            else:
                result["overall_status"] = "failed"
            
            print(f"\n📊 Verification Summary:")
            print(f"  Verified: {verified_count}/{total_count} files")
            print(f"  Status: {result['overall_status'].upper()}")
            
        except Exception as e:
            result["issues"].append(f"Verification error: {str(e)}")
            result["overall_status"] = "error"
            print(f"❌ Verification failed: {e}")
        
        return result
    
    def verify_reproducible_build(self, version: str = None) -> Dict:
        """Verify that builds are reproducible"""
        print("🏗️ Verifying reproducible build...")
        
        result = {
            "verification_time": datetime.now().isoformat(),
            "build_verification": {},
            "overall_status": "unknown",
            "issues": []
        }
        
        try:
            # Check if we're in the project directory
            if not (self.project_root / "tools/build/build-from-source.py").exists():
                result["issues"].append("build-from-source.py not found - not in project directory?")
                result["overall_status"] = "error"
                return result
            
            # Check for required build tools
            required_tools = ["python", "git", "npm"]
            missing_tools = []
            
            for tool in required_tools:
                try:
                    subprocess.run([tool, "--version"], capture_output=True, timeout=10)
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    missing_tools.append(tool)
            
            if missing_tools:
                result["issues"].append(f"Missing required tools: {', '.join(missing_tools)}")
                result["overall_status"] = "error"
                return result
            
            # Perform reproducible build
            print("🔨 Running reproducible build...")
            build_cmd = [sys.executable, "tools/build/build-from-source.py", "--reproducible"]
            
            if version:
                # Checkout specific version
                print(f"📌 Checking out version {version}...")
                subprocess.run(["git", "checkout", f"v{version}"], 
                             cwd=self.project_root, check=True, timeout=30)
            
            build_result = subprocess.run(
                build_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if build_result.returncode != 0:
                result["issues"].append(f"Build failed: {build_result.stderr}")
                result["overall_status"] = "failed"
                return result
            
            # Check for build artifacts
            dist_dir = self.project_root / "dist"
            if not dist_dir.exists():
                result["issues"].append("No dist directory found after build")
                result["overall_status"] = "failed"
                return result
            
            # Calculate checksums of build artifacts
            build_artifacts = {}
            for artifact in dist_dir.glob("*"):
                if artifact.is_file():
                    checksum = self._calculate_sha256(artifact)
                    build_artifacts[artifact.name] = {
                        "size": artifact.stat().st_size,
                        "checksum": checksum
                    }
            
            result["build_verification"] = {
                "build_successful": True,
                "artifacts": build_artifacts,
                "build_output": build_result.stdout
            }
            
            print(f"✅ Build completed successfully")
            print(f"📦 Generated {len(build_artifacts)} artifacts")
            
            # If version specified, compare with official release
            if version:
                print("🔍 Comparing with official release...")
                checksum_result = self.verify_release_checksums(version)
                
                if checksum_result["overall_status"] == "verified":
                    # Compare checksums
                    matches = 0
                    total = 0
                    
                    for filename, official_data in checksum_result["checksum_verification"].items():
                        if filename in build_artifacts and official_data["status"] == "verified":
                            total += 1
                            if build_artifacts[filename]["checksum"] == official_data["checksum"]:
                                matches += 1
                                print(f"  ✅ {filename}: Reproducible")
                            else:
                                print(f"  ❌ {filename}: Not reproducible")
                                result["issues"].append(f"Non-reproducible build for {filename}")
                    
                    result["build_verification"]["reproducibility"] = {
                        "matches": matches,
                        "total": total,
                        "percentage": (matches / total * 100) if total > 0 else 0
                    }
                    
                    if matches == total and total > 0:
                        result["overall_status"] = "reproducible"
                    elif matches > 0:
                        result["overall_status"] = "partially_reproducible"
                    else:
                        result["overall_status"] = "not_reproducible"
                else:
                    result["issues"].append("Could not verify official release checksums")
                    result["overall_status"] = "unknown"
            else:
                result["overall_status"] = "build_successful"
            
        except subprocess.TimeoutExpired:
            result["issues"].append("Build process timed out")
            result["overall_status"] = "timeout"
        except Exception as e:
            result["issues"].append(f"Build verification error: {str(e)}")
            result["overall_status"] = "error"
        
        return result
    
    def verify_security_scanning(self) -> Dict:
        """Verify security scanning results"""
        print("🔍 Running community security scan...")
        
        result = {
            "verification_time": datetime.now().isoformat(),
            "security_scans": {},
            "overall_status": "unknown",
            "issues": []
        }
        
        # Check if security tools are available
        security_tools = {
            "safety": ["safety", "--version"],
            "bandit": ["bandit", "--version"],
            "pip-audit": ["pip-audit", "--version"]
        }
        
        available_tools = {}
        for tool, cmd in security_tools.items():
            try:
                subprocess.run(cmd, capture_output=True, timeout=10)
                available_tools[tool] = True
                print(f"  ✅ {tool}: Available")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                available_tools[tool] = False
                print(f"  ❌ {tool}: Not available")
        
        # Run available security scans
        scan_results = {}
        
        # Safety scan (Python dependencies)
        if available_tools.get("safety"):
            print("🔍 Running Safety scan...")
            try:
                safety_result = subprocess.run(
                    ["safety", "check", "--json"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if safety_result.returncode == 0:
                    scan_results["safety"] = {
                        "status": "clean",
                        "vulnerabilities": 0,
                        "output": safety_result.stdout
                    }
                    print("  ✅ No vulnerabilities found")
                else:
                    try:
                        safety_data = json.loads(safety_result.stdout)
                        vuln_count = len(safety_data)
                        scan_results["safety"] = {
                            "status": "vulnerabilities_found",
                            "vulnerabilities": vuln_count,
                            "details": safety_data
                        }
                        print(f"  ⚠️  {vuln_count} vulnerabilities found")
                        if vuln_count > 0:
                            result["issues"].append(f"Safety found {vuln_count} vulnerabilities")
                    except json.JSONDecodeError:
                        scan_results["safety"] = {
                            "status": "error",
                            "error": "Could not parse Safety output"
                        }
            except subprocess.TimeoutExpired:
                scan_results["safety"] = {"status": "timeout"}
        
        # Bandit scan (Python code analysis)
        if available_tools.get("bandit"):
            print("🔍 Running Bandit scan...")
            try:
                bandit_result = subprocess.run(
                    ["bandit", "-r", "src/", "-f", "json"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                try:
                    bandit_data = json.loads(bandit_result.stdout)
                    issue_count = len(bandit_data.get("results", []))
                    
                    scan_results["bandit"] = {
                        "status": "completed",
                        "issues": issue_count,
                        "details": bandit_data
                    }
                    
                    if issue_count == 0:
                        print("  ✅ No security issues found")
                    else:
                        print(f"  ⚠️  {issue_count} potential security issues found")
                        high_severity = sum(1 for r in bandit_data.get("results", []) 
                                          if r.get("issue_severity") == "HIGH")
                        if high_severity > 0:
                            result["issues"].append(f"Bandit found {high_severity} high-severity issues")
                            
                except json.JSONDecodeError:
                    scan_results["bandit"] = {
                        "status": "error",
                        "error": "Could not parse Bandit output"
                    }
            except subprocess.TimeoutExpired:
                scan_results["bandit"] = {"status": "timeout"}
        
        # pip-audit scan
        if available_tools.get("pip-audit"):
            print("🔍 Running pip-audit scan...")
            try:
                pip_audit_result = subprocess.run(
                    ["pip-audit", "--format=json"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if pip_audit_result.returncode == 0:
                    scan_results["pip-audit"] = {
                        "status": "clean",
                        "vulnerabilities": 0
                    }
                    print("  ✅ No vulnerabilities found")
                else:
                    try:
                        audit_data = json.loads(pip_audit_result.stdout)
                        vuln_count = len(audit_data.get("vulnerabilities", []))
                        scan_results["pip-audit"] = {
                            "status": "vulnerabilities_found",
                            "vulnerabilities": vuln_count,
                            "details": audit_data
                        }
                        print(f"  ⚠️  {vuln_count} vulnerabilities found")
                        if vuln_count > 0:
                            result["issues"].append(f"pip-audit found {vuln_count} vulnerabilities")
                    except json.JSONDecodeError:
                        scan_results["pip-audit"] = {
                            "status": "error",
                            "error": "Could not parse pip-audit output"
                        }
            except subprocess.TimeoutExpired:
                scan_results["pip-audit"] = {"status": "timeout"}
        
        result["security_scans"] = scan_results
        
        # Determine overall status
        total_issues = len(result["issues"])
        if total_issues == 0:
            result["overall_status"] = "clean"
        elif any("high-severity" in issue.lower() for issue in result["issues"]):
            result["overall_status"] = "high_risk"
        else:
            result["overall_status"] = "low_risk"
        
        return result
    
    def generate_verification_report(self, results: Dict) -> str:
        """Generate comprehensive verification report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.verification_dir / f"community_verification_report_{timestamp}.md"
        
        lines = [
            "# Community Security Verification Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Verifier: Community Member",
            "",
            "## Executive Summary",
            ""
        ]
        
        # Overall status
        overall_statuses = []
        if "checksum_verification" in results:
            overall_statuses.append(results["checksum_verification"].get("overall_status", "unknown"))
        if "build_verification" in results:
            overall_statuses.append(results["build_verification"].get("overall_status", "unknown"))
        if "security_scans" in results:
            overall_statuses.append(results["security_scans"].get("overall_status", "unknown"))
        
        if all(status in ["verified", "clean", "reproducible", "build_successful"] for status in overall_statuses):
            overall_emoji = "✅"
            overall_status = "VERIFIED"
        elif any(status in ["failed", "error", "high_risk"] for status in overall_statuses):
            overall_emoji = "❌"
            overall_status = "FAILED"
        else:
            overall_emoji = "⚠️"
            overall_status = "PARTIAL"
        
        lines.extend([
            f"**Overall Verification Status:** {overall_emoji} {overall_status}",
            ""
        ])
        
        # Checksum verification results
        if "checksum_verification" in results:
            checksum_data = results["checksum_verification"]
            lines.extend([
                "## Release Checksum Verification",
                f"**Version:** {checksum_data.get('version', 'Unknown')}",
                f"**Status:** {checksum_data.get('overall_status', 'Unknown').upper()}",
                ""
            ])
            
            if checksum_data.get("checksum_verification"):
                lines.append("### Verified Files")
                for filename, file_data in checksum_data["checksum_verification"].items():
                    status_emoji = "✅" if file_data["status"] == "verified" else "❌"
                    lines.append(f"- {status_emoji} {filename}: {file_data['message']}")
                lines.append("")
        
        # Build verification results
        if "build_verification" in results:
            build_data = results["build_verification"]
            lines.extend([
                "## Reproducible Build Verification",
                f"**Status:** {build_data.get('overall_status', 'Unknown').upper()}",
                ""
            ])
            
            if build_data.get("build_verification", {}).get("artifacts"):
                artifacts = build_data["build_verification"]["artifacts"]
                lines.extend([
                    f"### Build Artifacts ({len(artifacts)} files)",
                    ""
                ])
                for filename, artifact_data in artifacts.items():
                    size_mb = artifact_data["size"] / (1024 * 1024)
                    lines.append(f"- **{filename}**: {size_mb:.1f} MB")
                    lines.append(f"  - SHA256: `{artifact_data['checksum']}`")
                lines.append("")
            
            if build_data.get("build_verification", {}).get("reproducibility"):
                repro = build_data["build_verification"]["reproducibility"]
                lines.extend([
                    "### Reproducibility Results",
                    f"- **Matches:** {repro['matches']}/{repro['total']} ({repro['percentage']:.1f}%)",
                    ""
                ])
        
        # Security scan results
        if "security_scans" in results:
            security_data = results["security_scans"]
            lines.extend([
                "## Security Scan Results",
                f"**Overall Status:** {security_data.get('overall_status', 'Unknown').upper()}",
                ""
            ])
            
            if security_data.get("security_scans"):
                for tool, scan_data in security_data["security_scans"].items():
                    status = scan_data.get("status", "unknown")
                    lines.extend([
                        f"### {tool.title()} Scan",
                        f"**Status:** {status.upper()}",
                    ])
                    
                    if "vulnerabilities" in scan_data:
                        lines.append(f"**Vulnerabilities:** {scan_data['vulnerabilities']}")
                    elif "issues" in scan_data:
                        lines.append(f"**Issues:** {scan_data['issues']}")
                    
                    lines.append("")
        
        # Issues and recommendations
        all_issues = []
        for result_type, result_data in results.items():
            if isinstance(result_data, dict) and "issues" in result_data:
                all_issues.extend(result_data["issues"])
        
        if all_issues:
            lines.extend([
                "## Issues Found",
                ""
            ])
            for issue in all_issues:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")
        
        # Recommendations
        lines.extend([
            "## Recommendations",
            ""
        ])
        
        if overall_status == "VERIFIED":
            lines.extend([
                "- ✅ All verification checks passed",
                "- ✅ Release artifacts are authentic and secure",
                "- ✅ Build process is reproducible",
                "- ✅ No significant security issues detected"
            ])
        else:
            lines.extend([
                "- 🔍 Review and address identified issues",
                "- 🔄 Re-run verification after fixes",
                "- 📢 Report findings to the community",
                "- 🤝 Collaborate with other community members"
            ])
        
        lines.extend([
            "",
            "## Community Participation",
            "",
            "This verification was performed by a community member as part of the",
            "Bitcoin Solo Miner Monitor community security audit process.",
            "",
            "**Community Channels:**",
            "- GitHub Issues: https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues",
            "- Discord: https://discord.gg/GzNsNnh4yT",
            "",
            "---",
            "",
            "*This report was generated by the Community Security Verification Tool*"
        ])
        
        with open(report_file, 'w') as f:
            f.write("\n".join(lines))
        
        return str(report_file)
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Community Security Verification Tool")
    parser.add_argument("--verify-checksums", action="store_true",
                       help="Verify release checksums")
    parser.add_argument("--verify-build", action="store_true",
                       help="Verify reproducible build")
    parser.add_argument("--verify-security", action="store_true",
                       help="Run security scans")
    parser.add_argument("--verify-all", action="store_true",
                       help="Run all verification checks")
    parser.add_argument("--version", help="Specific version to verify")
    parser.add_argument("--project-root", default=".", 
                       help="Path to project root directory")
    parser.add_argument("--output-dir", default="verification-results",
                       help="Output directory for results")
    
    args = parser.parse_args()
    
    verifier = CommunitySecurityVerifier(args.project_root)
    
    if args.output_dir != "verification-results":
        verifier.verification_dir = Path(args.output_dir)
        verifier.verification_dir.mkdir(exist_ok=True)
    
    results = {}
    
    if args.verify_all or args.verify_checksums:
        print("🔐 Starting checksum verification...")
        results["checksum_verification"] = verifier.verify_release_checksums(
            args.version or "latest"
        )
    
    if args.verify_all or args.verify_build:
        print("\n🏗️ Starting build verification...")
        results["build_verification"] = verifier.verify_reproducible_build(args.version)
    
    if args.verify_all or args.verify_security:
        print("\n🔍 Starting security verification...")
        results["security_scans"] = verifier.verify_security_scanning()
    
    if not any([args.verify_all, args.verify_checksums, args.verify_build, args.verify_security]):
        print("No verification type specified. Use --help for options.")
        return
    
    # Generate comprehensive report
    if results:
        report_file = verifier.generate_verification_report(results)
        print(f"\n📄 Verification report generated: {report_file}")
        
        # Print summary
        print("\n📊 Verification Summary:")
        for verification_type, result_data in results.items():
            if isinstance(result_data, dict):
                status = result_data.get("overall_status", "unknown")
                print(f"  {verification_type}: {status.upper()}")


if __name__ == "__main__":
    main()