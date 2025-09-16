#!/usr/bin/env python3
"""
GitHub Integration Tool for Community Verification

This tool integrates with GitHub Issues to automatically process
verification reports and update community verification data.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class GitHubVerificationIntegrator:
    def __init__(self, github_repo: str, github_token: Optional[str] = None):
        self.github_repo = github_repo
        self.github_token = github_token or os.environ.get('GITHUB_TOKEN')
        self.api_url = f"https://api.github.com/repos/{github_repo}"
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Bitcoin-Solo-Miner-Monitor-Verification-Bot'
        }
        if self.github_token:
            self.headers['Authorization'] = f'token {self.github_token}'
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def make_github_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
        """Make a request to the GitHub API."""
        url = f"{self.api_url}/{endpoint}"
        
        if data:
            data = json.dumps(data).encode('utf-8')
        
        request = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_data = json.loads(e.read().decode('utf-8'))
            raise Exception(f"GitHub API error: {e.code} - {error_data.get('message', 'Unknown error')}")
    
    def get_verification_issues(self, state: str = "all") -> List[Dict]:
        """Get all verification-related issues."""
        issues = self.make_github_request(f"issues?labels=verification&state={state}&per_page=100")
        return issues
    
    def parse_verification_issue(self, issue: Dict) -> Optional[Dict]:
        """Parse a verification issue to extract verification data."""
        title = issue.get('title', '')
        body = issue.get('body', '')
        
        # Extract version from title
        version_match = re.search(r'v?(\d+\.\d+\.\d+)', title)
        if not version_match:
            self.log(f"Could not extract version from issue #{issue['number']}: {title}", "WARNING")
            return None
        
        version = f"v{version_match.group(1)}"
        
        # Determine verification type
        verification_type = "unknown"
        if "SUCCESS" in title.upper():
            verification_type = "success"
        elif "FAILURE" in title.upper():
            verification_type = "failure"
        elif "SECURITY" in title.upper():
            verification_type = "security"
        
        # Parse verification details from body
        verification_data = {
            "issue_number": issue['number'],
            "version": version,
            "type": verification_type,
            "verifier": issue['user']['login'],
            "created_at": issue['created_at'],
            "updated_at": issue['updated_at'],
            "state": issue['state'],
            "title": title,
            "url": issue['html_url'],
            "details": self._parse_issue_body(body, verification_type)
        }
        
        return verification_data
    
    def _parse_issue_body(self, body: str, verification_type: str) -> Dict:
        """Parse issue body to extract verification details."""
        details = {
            "methods_used": [],
            "system_info": {},
            "verification_results": {},
            "raw_body": body
        }
        
        # Extract checkboxes for methods used
        checksum_match = re.search(r'- \[x\] Checksum verification', body, re.IGNORECASE)
        if checksum_match:
            details["methods_used"].append("checksum")
        
        reproducible_match = re.search(r'- \[x\] Reproducible build verification', body, re.IGNORECASE)
        if reproducible_match:
            details["methods_used"].append("reproducible_build")
        
        audit_match = re.search(r'- \[x\] Source code audit', body, re.IGNORECASE)
        if audit_match:
            details["methods_used"].append("source_audit")
        
        # Extract system information
        os_match = re.search(r'\*\*Operating System\*\*:\s*([^\n]+)', body)
        if os_match:
            details["system_info"]["os"] = os_match.group(1).strip()
        
        python_match = re.search(r'\*\*Python Version\*\*:\s*([^\n]+)', body)
        if python_match:
            details["system_info"]["python"] = python_match.group(1).strip()
        
        nodejs_match = re.search(r'\*\*Node\.js Version\*\*:\s*([^\n]+)', body)
        if nodejs_match:
            details["system_info"]["nodejs"] = nodejs_match.group(1).strip()
        
        # Extract verification results based on type
        if verification_type == "success":
            # Look for successful verification indicators
            files_verified_match = re.search(r'\*\*Files verified\*\*:\s*(\d+)', body)
            if files_verified_match:
                details["verification_results"]["files_verified"] = int(files_verified_match.group(1))
            
            checksums_matched = re.search(r'\*\*All checksums matched\*\*:\s*(Yes|No)', body, re.IGNORECASE)
            if checksums_matched:
                details["verification_results"]["checksums_matched"] = checksums_matched.group(1).lower() == "yes"
        
        elif verification_type == "failure":
            # Look for failure details
            expected_checksum = re.search(r'\*\*Expected checksum\*\*:\s*`([^`]+)`', body)
            if expected_checksum:
                details["verification_results"]["expected_checksum"] = expected_checksum.group(1)
            
            actual_checksum = re.search(r'\*\*Actual checksum\*\*:\s*`([^`]+)`', body)
            if actual_checksum:
                details["verification_results"]["actual_checksum"] = actual_checksum.group(1)
        
        return details
    
    def update_community_verification_data(self, verification_reports: List[Dict]) -> Dict:
        """Update community verification data based on reports."""
        # Group reports by version
        version_reports = {}
        for report in verification_reports:
            version = report['version']
            if version not in version_reports:
                version_reports[version] = []
            version_reports[version].append(report)
        
        updated_versions = {}
        
        for version, reports in version_reports.items():
            self.log(f"Processing {len(reports)} reports for version {version}")
            
            # Load existing verification data or create new
            verification_data_path = Path(f"verification/community-builds/{version}/verification-data.json")
            
            if verification_data_path.exists():
                with open(verification_data_path, 'r') as f:
                    verification_data = json.load(f)
            else:
                # Create from template
                template_path = Path("verification/community-builds/template/verification-data.json")
                with open(template_path, 'r') as f:
                    verification_data = json.load(f)
                verification_data['version'] = version
                verification_data['maintainer_notes']['created_date'] = datetime.now().isoformat()
            
            # Process each report
            success_count = 0
            failure_count = 0
            
            for report in reports:
                if report['type'] == 'success':
                    success_count += 1
                    self._add_successful_verification(verification_data, report)
                elif report['type'] == 'failure':
                    failure_count += 1
                    self._add_failed_verification(verification_data, report)
                elif report['type'] == 'security':
                    self._add_security_report(verification_data, report)
            
            # Update verification status
            total_verifications = len([v for v in verification_data['verifications'] if v.get('status') == 'success'])
            
            if failure_count > 0:
                verification_data['verification_status'] = 'failed'
            elif total_verifications >= 3:
                verification_data['verification_status'] = 'verified'
                if not verification_data['consensus_reached']:
                    verification_data['consensus_reached'] = datetime.now().isoformat()
            elif total_verifications > 0:
                verification_data['verification_status'] = 'pending'
            
            verification_data['verification_count'] = total_verifications
            verification_data['maintainer_notes']['last_updated'] = datetime.now().isoformat()
            
            # Save updated data
            os.makedirs(verification_data_path.parent, exist_ok=True)
            with open(verification_data_path, 'w') as f:
                json.dump(verification_data, f, indent=2)
            
            updated_versions[version] = verification_data
        
        return updated_versions
    
    def _add_successful_verification(self, verification_data: Dict, report: Dict):
        """Add a successful verification report to the data."""
        verification_entry = {
            "verifier": report['verifier'],
            "date": report['created_at'],
            "issue_number": report['issue_number'],
            "status": "success",
            "methods": report['details']['methods_used'],
            "system_info": report['details']['system_info'],
            "verification_results": report['details']['verification_results']
        }
        
        # Check if this verifier already has an entry
        existing_index = None
        for i, existing in enumerate(verification_data['verifications']):
            if existing['verifier'] == report['verifier']:
                existing_index = i
                break
        
        if existing_index is not None:
            # Update existing entry
            verification_data['verifications'][existing_index] = verification_entry
        else:
            # Add new entry
            verification_data['verifications'].append(verification_entry)
        
        # Update method statistics
        for method in report['details']['methods_used']:
            if method in verification_data['verification_methods']:
                verification_data['verification_methods'][method]['successes'] += 1
    
    def _add_failed_verification(self, verification_data: Dict, report: Dict):
        """Add a failed verification report to the data."""
        failure_entry = {
            "verifier": report['verifier'],
            "date": report['created_at'],
            "issue_number": report['issue_number'],
            "status": "failure",
            "details": report['details']['verification_results'],
            "system_info": report['details']['system_info']
        }
        
        verification_data['verifications'].append(failure_entry)
        verification_data['community_feedback']['negative_reports'] += 1
        verification_data['community_feedback']['issues_reported'].append({
            "issue_number": report['issue_number'],
            "type": "verification_failure",
            "date": report['created_at'],
            "verifier": report['verifier']
        })
    
    def _add_security_report(self, verification_data: Dict, report: Dict):
        """Add a security report to the data."""
        security_entry = {
            "issue_number": report['issue_number'],
            "reporter": report['verifier'],
            "date": report['created_at'],
            "type": "security_issue",
            "status": "reported"
        }
        
        verification_data['security_notes'].append(security_entry)
        verification_data['community_feedback']['issues_reported'].append({
            "issue_number": report['issue_number'],
            "type": "security_issue",
            "date": report['created_at'],
            "reporter": report['verifier']
        })
    
    def generate_verification_summary(self, updated_versions: Dict) -> str:
        """Generate a summary of verification updates."""
        summary = "# Community Verification Update Summary\n\n"
        summary += f"**Update Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        
        for version, data in updated_versions.items():
            status_emoji = {
                'verified': '🟢',
                'pending': '🟡', 
                'failed': '🔴',
                'unverified': '⚫'
            }.get(data['verification_status'], '❓')
            
            summary += f"## {version} {status_emoji}\n\n"
            summary += f"- **Status**: {data['verification_status'].title()}\n"
            summary += f"- **Verifications**: {data['verification_count']}\n"
            
            if data['consensus_reached']:
                summary += f"- **Consensus Reached**: {data['consensus_reached'][:10]}\n"
            
            if data['security_notes']:
                summary += f"- **Security Notes**: {len(data['security_notes'])} reported\n"
            
            summary += "\n"
        
        return summary
    
    def sync_verification_data(self) -> Dict:
        """Sync verification data from GitHub issues."""
        self.log("Starting verification data sync from GitHub issues")
        
        # Get all verification issues
        issues = self.get_verification_issues()
        self.log(f"Found {len(issues)} verification-related issues")
        
        # Parse verification reports
        verification_reports = []
        for issue in issues:
            parsed = self.parse_verification_issue(issue)
            if parsed:
                verification_reports.append(parsed)
        
        self.log(f"Parsed {len(verification_reports)} valid verification reports")
        
        # Update community verification data
        updated_versions = self.update_community_verification_data(verification_reports)
        
        # Generate summary
        summary = self.generate_verification_summary(updated_versions)
        
        return {
            "updated_versions": updated_versions,
            "summary": summary,
            "total_reports": len(verification_reports),
            "total_issues": len(issues)
        }


def main():
    parser = argparse.ArgumentParser(
        description="GitHub integration tool for community verification"
    )
    parser.add_argument(
        "--repo",
        default="smokeysrh/bitcoin-solo-miner-monitor",
        help="GitHub repository (owner/repo)"
    )
    parser.add_argument(
        "--token",
        help="GitHub API token (or set GITHUB_TOKEN environment variable)"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync verification data from GitHub issues"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for sync summary"
    )
    
    args = parser.parse_args()
    
    try:
        integrator = GitHubVerificationIntegrator(args.repo, args.token)
        
        if args.sync:
            result = integrator.sync_verification_data()
            
            print(result['summary'])
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(result['summary'])
                print(f"\nSummary saved to {args.output}")
            
            print(f"\nSync completed:")
            print(f"- Total issues processed: {result['total_issues']}")
            print(f"- Valid reports parsed: {result['total_reports']}")
            print(f"- Versions updated: {len(result['updated_versions'])}")
        
        else:
            print("No action specified. Use --sync to sync verification data.")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()