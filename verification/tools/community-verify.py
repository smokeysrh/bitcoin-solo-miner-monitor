#!/usr/bin/env python3
"""
Community Verification Tool for Bitcoin Solo Miner Monitor

This tool automates the verification process for community members to verify
the authenticity and integrity of releases.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class CommunityVerifier:
    def __init__(self, version: str, github_repo: str = "smokeysrh/bitcoin-solo-miner-monitor"):
        self.version = version
        self.github_repo = github_repo
        self.base_url = f"https://github.com/{github_repo}"
        self.api_url = f"https://api.github.com/repos/{github_repo}"
        self.results = {
            "version": version,
            "verification_date": None,
            "methods": {},
            "overall_status": "pending",
            "errors": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def download_file(self, url: str, local_path: Path) -> bool:
        """Download a file from URL to local path."""
        try:
            self.log(f"Downloading {url}")
            urllib.request.urlretrieve(url, local_path)
            return True
        except Exception as e:
            self.log(f"Failed to download {url}: {e}", "ERROR")
            return False
    
    def calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def verify_checksums(self, download_dir: Path) -> Dict:
        """Verify checksums of downloaded files."""
        self.log("Starting checksum verification")
        result = {
            "method": "checksum_verification",
            "status": "pending",
            "files_verified": 0,
            "files_failed": 0,
            "details": []
        }
        
        # Download SHA256SUMS file
        checksums_url = f"{self.base_url}/releases/download/{self.version}/SHA256SUMS"
        checksums_file = download_dir / "SHA256SUMS"
        
        if not self.download_file(checksums_url, checksums_file):
            result["status"] = "failed"
            result["error"] = "Could not download SHA256SUMS file"
            return result
        
        # Parse checksums file
        checksums = {}
        try:
            with open(checksums_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        hash_value, filename = line.split('  ', 1)
                        checksums[filename] = hash_value
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Failed to parse SHA256SUMS: {e}"
            return result
        
        # Download and verify each file
        for filename, expected_hash in checksums.items():
            file_url = f"{self.base_url}/releases/download/{self.version}/{filename}"
            local_file = download_dir / filename
            
            file_result = {
                "filename": filename,
                "expected_hash": expected_hash,
                "actual_hash": None,
                "status": "pending"
            }
            
            if self.download_file(file_url, local_file):
                actual_hash = self.calculate_sha256(local_file)
                file_result["actual_hash"] = actual_hash
                
                if actual_hash == expected_hash:
                    file_result["status"] = "verified"
                    result["files_verified"] += 1
                    self.log(f"✅ {filename} verified")
                else:
                    file_result["status"] = "failed"
                    result["files_failed"] += 1
                    self.log(f"❌ {filename} checksum mismatch", "ERROR")
            else:
                file_result["status"] = "download_failed"
                result["files_failed"] += 1
            
            result["details"].append(file_result)
        
        # Set overall status
        if result["files_failed"] == 0 and result["files_verified"] > 0:
            result["status"] = "verified"
        elif result["files_failed"] > 0:
            result["status"] = "failed"
        else:
            result["status"] = "no_files"
        
        return result
    
    def verify_reproducible_build(self, work_dir: Path) -> Dict:
        """Perform reproducible build verification."""
        self.log("Starting reproducible build verification")
        result = {
            "method": "reproducible_build",
            "status": "pending",
            "build_success": False,
            "checksums_match": False,
            "details": {}
        }
        
        # Clone repository
        repo_dir = work_dir / "repo"
        try:
            self.log("Cloning repository")
            subprocess.run([
                "git", "clone", f"{self.base_url}.git", str(repo_dir)
            ], check=True, capture_output=True)
            
            # Checkout specific version
            self.log(f"Checking out version {self.version}")
            subprocess.run([
                "git", "checkout", self.version
            ], cwd=repo_dir, check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            result["status"] = "failed"
            result["error"] = f"Git operations failed: {e}"
            return result
        
        # Run reproducible build
        try:
            self.log("Running reproducible build")
            build_script = repo_dir / "build-reproducible.sh"
            if build_script.exists():
                subprocess.run([
                    "bash", str(build_script), self.version.lstrip('v')
                ], cwd=repo_dir, check=True, capture_output=True)
                result["build_success"] = True
            else:
                result["status"] = "failed"
                result["error"] = "build-reproducible.sh not found"
                return result
                
        except subprocess.CalledProcessError as e:
            result["status"] = "failed"
            result["error"] = f"Build failed: {e}"
            return result
        
        # Compare checksums
        try:
            local_checksums = repo_dir / "distribution" / "SHA256SUMS"
            if local_checksums.exists():
                # Download reference checksums
                ref_checksums_url = f"{self.base_url}/releases/download/{self.version}/SHA256SUMS"
                ref_checksums_file = work_dir / "reference_SHA256SUMS"
                
                if self.download_file(ref_checksums_url, ref_checksums_file):
                    # Compare files
                    with open(local_checksums, 'r') as f1, open(ref_checksums_file, 'r') as f2:
                        local_content = f1.read().strip()
                        ref_content = f2.read().strip()
                        
                    if local_content == ref_content:
                        result["checksums_match"] = True
                        result["status"] = "verified"
                        self.log("✅ Reproducible build verified")
                    else:
                        result["status"] = "failed"
                        result["checksums_match"] = False
                        self.log("❌ Checksums do not match", "ERROR")
                else:
                    result["status"] = "failed"
                    result["error"] = "Could not download reference checksums"
            else:
                result["status"] = "failed"
                result["error"] = "Local build did not produce SHA256SUMS"
                
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Checksum comparison failed: {e}"
        
        return result
    
    def check_community_verifications(self) -> Dict:
        """Check existing community verification results."""
        self.log("Checking community verification results")
        result = {
            "method": "community_check",
            "status": "pending",
            "community_verifications": [],
            "verification_count": 0
        }
        
        try:
            # Check GitHub issues for verification reports
            issues_url = f"{self.api_url}/issues?labels=verification&state=all"
            with urllib.request.urlopen(issues_url) as response:
                issues_data = json.loads(response.read())
            
            version_verifications = []
            for issue in issues_data:
                if self.version in issue.get('title', ''):
                    verification = {
                        "issue_number": issue['number'],
                        "title": issue['title'],
                        "state": issue['state'],
                        "created_at": issue['created_at'],
                        "user": issue['user']['login']
                    }
                    version_verifications.append(verification)
            
            result["community_verifications"] = version_verifications
            result["verification_count"] = len(version_verifications)
            result["status"] = "completed"
            
            if result["verification_count"] > 0:
                self.log(f"Found {result['verification_count']} community verification(s)")
            else:
                self.log("No community verifications found")
                
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Failed to check community verifications: {e}"
        
        return result
    
    def run_verification(self, methods: List[str]) -> Dict:
        """Run verification using specified methods."""
        import datetime
        self.results["verification_date"] = datetime.datetime.now().isoformat()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            
            if "checksum" in methods:
                self.results["methods"]["checksum"] = self.verify_checksums(work_dir / "downloads")
                os.makedirs(work_dir / "downloads", exist_ok=True)
            
            if "reproducible" in methods:
                self.results["methods"]["reproducible"] = self.verify_reproducible_build(work_dir)
            
            if "community" in methods:
                self.results["methods"]["community"] = self.check_community_verifications()
        
        # Determine overall status
        verified_methods = 0
        failed_methods = 0
        
        for method_result in self.results["methods"].values():
            if method_result["status"] == "verified" or method_result["status"] == "completed":
                verified_methods += 1
            elif method_result["status"] == "failed":
                failed_methods += 1
        
        if failed_methods > 0:
            self.results["overall_status"] = "failed"
        elif verified_methods > 0:
            self.results["overall_status"] = "verified"
        else:
            self.results["overall_status"] = "no_results"
        
        return self.results
    
    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """Generate a verification report."""
        report = f"""
# Community Verification Report

**Version**: {self.results['version']}
**Verification Date**: {self.results['verification_date']}
**Overall Status**: {self.results['overall_status'].upper()}

## Verification Methods

"""
        
        for method_name, method_result in self.results["methods"].items():
            status_emoji = "✅" if method_result["status"] in ["verified", "completed"] else "❌"
            report += f"### {method_name.title()} Verification {status_emoji}\n\n"
            report += f"**Status**: {method_result['status']}\n\n"
            
            if method_name == "checksum":
                report += f"**Files Verified**: {method_result.get('files_verified', 0)}\n"
                report += f"**Files Failed**: {method_result.get('files_failed', 0)}\n\n"
                
                if method_result.get("details"):
                    report += "**File Details**:\n"
                    for file_detail in method_result["details"]:
                        status_emoji = "✅" if file_detail["status"] == "verified" else "❌"
                        report += f"- {status_emoji} {file_detail['filename']}\n"
                    report += "\n"
            
            elif method_name == "reproducible":
                report += f"**Build Success**: {method_result.get('build_success', False)}\n"
                report += f"**Checksums Match**: {method_result.get('checksums_match', False)}\n\n"
            
            elif method_name == "community":
                report += f"**Community Verifications Found**: {method_result.get('verification_count', 0)}\n\n"
                
                if method_result.get("community_verifications"):
                    report += "**Community Reports**:\n"
                    for verification in method_result["community_verifications"]:
                        report += f"- Issue #{verification['issue_number']}: {verification['title']}\n"
                    report += "\n"
            
            if method_result.get("error"):
                report += f"**Error**: {method_result['error']}\n\n"
        
        report += """
## Next Steps

"""
        
        if self.results["overall_status"] == "verified":
            report += "✅ **Verification successful!** The release appears to be authentic and safe to use.\n\n"
            report += "Consider reporting your successful verification to help the community:\n"
            report += f"- [Create verification success report]({self.base_url}/issues/new?template=verification-success.md)\n\n"
        elif self.results["overall_status"] == "failed":
            report += "❌ **Verification failed!** Do not use this release until issues are resolved.\n\n"
            report += "Please report verification failures:\n"
            report += f"- [Report verification failure]({self.base_url}/issues/new?template=verification-failure.md)\n\n"
        else:
            report += "⚠️ **Verification incomplete.** Some methods could not be completed.\n\n"
        
        report += f"""
## System Information

- **Python Version**: {sys.version}
- **Platform**: {sys.platform}
- **Working Directory**: {os.getcwd()}

---
*Generated by Bitcoin Solo Miner Monitor Community Verification Tool*
"""
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            self.log(f"Report saved to {output_file}")
        
        return report


def main():
    parser = argparse.ArgumentParser(
        description="Community verification tool for Bitcoin Solo Miner Monitor releases"
    )
    parser.add_argument(
        "--version", "-v",
        required=True,
        help="Version to verify (e.g., v1.0.0)"
    )
    parser.add_argument(
        "--method", "-m",
        choices=["checksum", "reproducible", "community", "all"],
        default="all",
        help="Verification method to use"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file for verification report"
    )
    parser.add_argument(
        "--repo",
        default="smokeysrh/bitcoin-solo-miner-monitor",
        help="GitHub repository (owner/repo)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    
    args = parser.parse_args()
    
    # Determine methods to run
    if args.method == "all":
        methods = ["checksum", "community"]
        # Only include reproducible build if we have git and build tools
        if subprocess.run(["which", "git"], capture_output=True).returncode == 0:
            methods.append("reproducible")
    else:
        methods = [args.method]
    
    # Run verification
    verifier = CommunityVerifier(args.version, args.repo)
    results = verifier.run_verification(methods)
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        report = verifier.generate_report(args.output)
        if not args.output:
            print(report)
    
    # Exit with appropriate code
    if results["overall_status"] == "verified":
        sys.exit(0)
    elif results["overall_status"] == "failed":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()