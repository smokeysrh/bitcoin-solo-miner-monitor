#!/usr/bin/env python3
"""
Build Comparison Tool for Bitcoin Solo Miner Monitor

This tool compares local build results with community-verified builds
to help detect inconsistencies or potential security issues.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

class BuildComparator:
    def __init__(self, github_repo: str = "smokeysrh/bitcoin-solo-miner-monitor"):
        self.github_repo = github_repo
        self.base_url = f"https://github.com/{github_repo}"
        self.api_url = f"https://api.github.com/repos/{github_repo}"
        self.community_builds_url = f"https://raw.githubusercontent.com/{github_repo}/main/verification/community-builds"
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def parse_checksums_file(self, file_path: Path) -> Dict[str, str]:
        """Parse a SHA256SUMS file into a dictionary."""
        checksums = {}
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            hash_value, filename = line.split('  ', 1)
                            checksums[filename] = hash_value
                        except ValueError:
                            self.log(f"Invalid format on line {line_num}: {line}", "WARNING")
        except Exception as e:
            self.log(f"Error parsing {file_path}: {e}", "ERROR")
        return checksums
    
    def download_community_checksums(self, version: str) -> Optional[Dict[str, str]]:
        """Download community-verified checksums for a version."""
        try:
            # Try to download from community builds directory
            community_file_url = f"{self.community_builds_url}/{version}/SHA256SUMS"
            self.log(f"Downloading community checksums from {community_file_url}")
            
            with urllib.request.urlopen(community_file_url) as response:
                content = response.read().decode('utf-8')
            
            # Parse the content
            checksums = {}
            for line in content.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        hash_value, filename = line.split('  ', 1)
                        checksums[filename] = hash_value
                    except ValueError:
                        continue
            
            return checksums
            
        except Exception as e:
            self.log(f"Could not download community checksums: {e}", "WARNING")
            
            # Fallback: try to download from releases
            try:
                release_url = f"{self.base_url}/releases/download/{version}/SHA256SUMS"
                self.log(f"Trying fallback from releases: {release_url}")
                
                with urllib.request.urlopen(release_url) as response:
                    content = response.read().decode('utf-8')
                
                checksums = {}
                for line in content.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            hash_value, filename = line.split('  ', 1)
                            checksums[filename] = hash_value
                        except ValueError:
                            continue
                
                return checksums
                
            except Exception as e2:
                self.log(f"Fallback also failed: {e2}", "ERROR")
                return None
    
    def get_community_verification_data(self, version: str) -> Dict:
        """Get community verification data for a version."""
        try:
            community_data_url = f"{self.community_builds_url}/{version}/verification-data.json"
            with urllib.request.urlopen(community_data_url) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            self.log(f"Could not load community verification data: {e}", "WARNING")
            return {}
    
    def compare_checksums(self, local_checksums: Dict[str, str], 
                         community_checksums: Dict[str, str]) -> Dict:
        """Compare local checksums with community checksums."""
        result = {
            "total_files": 0,
            "matching_files": 0,
            "mismatched_files": 0,
            "local_only_files": 0,
            "community_only_files": 0,
            "details": [],
            "status": "unknown"
        }
        
        all_files = set(local_checksums.keys()) | set(community_checksums.keys())
        result["total_files"] = len(all_files)
        
        for filename in sorted(all_files):
            local_hash = local_checksums.get(filename)
            community_hash = community_checksums.get(filename)
            
            file_result = {
                "filename": filename,
                "local_hash": local_hash,
                "community_hash": community_hash,
                "status": "unknown"
            }
            
            if local_hash and community_hash:
                if local_hash == community_hash:
                    file_result["status"] = "match"
                    result["matching_files"] += 1
                else:
                    file_result["status"] = "mismatch"
                    result["mismatched_files"] += 1
            elif local_hash and not community_hash:
                file_result["status"] = "local_only"
                result["local_only_files"] += 1
            elif community_hash and not local_hash:
                file_result["status"] = "community_only"
                result["community_only_files"] += 1
            
            result["details"].append(file_result)
        
        # Determine overall status
        if result["mismatched_files"] > 0 or result["local_only_files"] > 0 or result["community_only_files"] > 0:
            result["status"] = "differences_found"
        elif result["matching_files"] > 0:
            result["status"] = "all_match"
        else:
            result["status"] = "no_files"
        
        return result
    
    def analyze_differences(self, comparison_result: Dict) -> Dict:
        """Analyze the differences and provide recommendations."""
        analysis = {
            "risk_level": "unknown",
            "recommendations": [],
            "potential_issues": []
        }
        
        mismatched = comparison_result["mismatched_files"]
        local_only = comparison_result["local_only_files"]
        community_only = comparison_result["community_only_files"]
        
        # Determine risk level
        if mismatched > 0:
            analysis["risk_level"] = "high"
            analysis["potential_issues"].append("Checksum mismatches detected - possible tampering or build inconsistency")
            analysis["recommendations"].append("Do not use these builds until discrepancies are resolved")
            analysis["recommendations"].append("Report the issue to the development team immediately")
        elif local_only > 0 or community_only > 0:
            analysis["risk_level"] = "medium"
            analysis["potential_issues"].append("Different files present in local vs community builds")
            analysis["recommendations"].append("Investigate why file sets differ")
            analysis["recommendations"].append("Verify build process and dependencies")
        else:
            analysis["risk_level"] = "low"
            analysis["recommendations"].append("Builds appear consistent with community verification")
        
        # Add specific recommendations based on file types
        for detail in comparison_result["details"]:
            if detail["status"] == "mismatch":
                filename = detail["filename"]
                if filename.endswith(('.exe', '.msi')):
                    analysis["potential_issues"].append(f"Windows installer {filename} has different checksum")
                elif filename.endswith('.dmg'):
                    analysis["potential_issues"].append(f"macOS installer {filename} has different checksum")
                elif filename.endswith(('.deb', '.rpm', '.AppImage')):
                    analysis["potential_issues"].append(f"Linux package {filename} has different checksum")
        
        return analysis
    
    def generate_report(self, local_file: Path, version: str, 
                       comparison_result: Dict, analysis: Dict, 
                       community_data: Dict) -> str:
        """Generate a detailed comparison report."""
        
        report = f"""# Build Comparison Report

**Version**: {version}
**Local Checksums File**: {local_file}
**Comparison Date**: {comparison_result.get('comparison_date', 'Unknown')}

## Summary

- **Total Files**: {comparison_result['total_files']}
- **Matching Files**: {comparison_result['matching_files']} ✅
- **Mismatched Files**: {comparison_result['mismatched_files']} ❌
- **Local Only Files**: {comparison_result['local_only_files']} ⚠️
- **Community Only Files**: {comparison_result['community_only_files']} ⚠️

**Overall Status**: {comparison_result['status'].upper()}
**Risk Level**: {analysis['risk_level'].upper()}

## Detailed File Comparison

"""
        
        for detail in comparison_result['details']:
            status_emoji = {
                'match': '✅',
                'mismatch': '❌',
                'local_only': '⚠️ (Local Only)',
                'community_only': '⚠️ (Community Only)'
            }.get(detail['status'], '❓')
            
            report += f"### {detail['filename']} {status_emoji}\n\n"
            
            if detail['local_hash']:
                report += f"**Local Hash**: `{detail['local_hash']}`\n"
            if detail['community_hash']:
                report += f"**Community Hash**: `{detail['community_hash']}`\n"
            
            report += f"**Status**: {detail['status']}\n\n"
        
        # Add analysis section
        report += "## Analysis\n\n"
        
        if analysis['potential_issues']:
            report += "### Potential Issues\n\n"
            for issue in analysis['potential_issues']:
                report += f"- ⚠️ {issue}\n"
            report += "\n"
        
        if analysis['recommendations']:
            report += "### Recommendations\n\n"
            for rec in analysis['recommendations']:
                report += f"- 📋 {rec}\n"
            report += "\n"
        
        # Add community verification info
        if community_data:
            report += "## Community Verification Data\n\n"
            if 'verifications' in community_data:
                report += f"**Community Verifications**: {len(community_data['verifications'])}\n"
                for verification in community_data['verifications'][:5]:  # Show first 5
                    report += f"- {verification.get('date', 'Unknown')}: {verification.get('verifier', 'Anonymous')} ({verification.get('method', 'Unknown method')})\n"
                if len(community_data['verifications']) > 5:
                    report += f"- ... and {len(community_data['verifications']) - 5} more\n"
                report += "\n"
        
        # Add next steps
        report += "## Next Steps\n\n"
        
        if analysis['risk_level'] == 'high':
            report += """❌ **HIGH RISK**: Significant differences detected!

1. **Do not use these builds** until issues are resolved
2. **Report immediately** to the development team
3. **Verify your build environment** for potential compromise
4. **Re-download** from official sources and compare again

"""
        elif analysis['risk_level'] == 'medium':
            report += """⚠️ **MEDIUM RISK**: Some differences detected.

1. **Investigate** the differences before using
2. **Verify** your build process matches the official process
3. **Check** for any local modifications or different dependencies
4. **Consider** reporting to the community for clarification

"""
        else:
            report += """✅ **LOW RISK**: Builds appear consistent.

1. **Proceed** with confidence in using the builds
2. **Consider** contributing your verification results to the community
3. **Help others** by sharing your successful verification

"""
        
        report += f"""
## Reporting

- **Report Issues**: [{self.base_url}/issues/new]({self.base_url}/issues/new)
- **Community Discussion**: [{self.base_url}/discussions]({self.base_url}/discussions)
- **Security Issues**: Follow responsible disclosure process

---
*Generated by Bitcoin Solo Miner Monitor Build Comparison Tool*
"""
        
        return report
    
    def compare_builds(self, local_file: Path, version: str, output_file: Optional[Path] = None) -> Dict:
        """Main comparison function."""
        import datetime
        
        self.log(f"Starting build comparison for version {version}")
        
        # Parse local checksums
        if not local_file.exists():
            raise FileNotFoundError(f"Local checksums file not found: {local_file}")
        
        local_checksums = self.parse_checksums_file(local_file)
        self.log(f"Loaded {len(local_checksums)} local checksums")
        
        # Download community checksums
        community_checksums = self.download_community_checksums(version)
        if not community_checksums:
            raise RuntimeError(f"Could not download community checksums for version {version}")
        
        self.log(f"Loaded {len(community_checksums)} community checksums")
        
        # Perform comparison
        comparison_result = self.compare_checksums(local_checksums, community_checksums)
        comparison_result["comparison_date"] = datetime.datetime.now().isoformat()
        
        # Analyze results
        analysis = self.analyze_differences(comparison_result)
        
        # Get community verification data
        community_data = self.get_community_verification_data(version)
        
        # Generate report
        report = self.generate_report(local_file, version, comparison_result, analysis, community_data)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            self.log(f"Report saved to {output_file}")
        
        # Combine all results
        full_result = {
            "version": version,
            "local_file": str(local_file),
            "comparison": comparison_result,
            "analysis": analysis,
            "community_data": community_data,
            "report": report
        }
        
        return full_result


def main():
    parser = argparse.ArgumentParser(
        description="Compare local build checksums with community-verified builds"
    )
    parser.add_argument(
        "--local", "-l",
        type=Path,
        required=True,
        help="Path to local SHA256SUMS file"
    )
    parser.add_argument(
        "--version", "-v",
        required=True,
        help="Version to compare against (e.g., v1.0.0)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file for comparison report"
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
    
    try:
        comparator = BuildComparator(args.repo)
        result = comparator.compare_builds(args.local, args.version, args.output)
        
        if args.json:
            # Remove the report from JSON output to avoid duplication
            json_result = {k: v for k, v in result.items() if k != 'report'}
            print(json.dumps(json_result, indent=2))
        else:
            if not args.output:
                print(result['report'])
        
        # Exit with appropriate code based on risk level
        risk_level = result['analysis']['risk_level']
        if risk_level == 'high':
            sys.exit(1)
        elif risk_level == 'medium':
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()