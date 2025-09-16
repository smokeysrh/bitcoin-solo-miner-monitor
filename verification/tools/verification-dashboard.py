#!/usr/bin/env python3
"""
Verification Dashboard for Bitcoin Solo Miner Monitor

This tool generates a comprehensive dashboard showing the current
status of community verification across all releases.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class VerificationDashboard:
    def __init__(self, verification_dir: Path = None):
        self.verification_dir = verification_dir or Path("verification/community-builds")
    
    def load_verification_data(self) -> Dict[str, Dict]:
        """Load verification data for all versions."""
        verification_data = {}
        
        if not self.verification_dir.exists():
            return verification_data
        
        for version_dir in self.verification_dir.iterdir():
            if version_dir.is_dir() and version_dir.name != "template":
                data_file = version_dir / "verification-data.json"
                if data_file.exists():
                    try:
                        with open(data_file, 'r') as f:
                            data = json.load(f)
                        verification_data[version_dir.name] = data
                    except Exception as e:
                        print(f"Warning: Could not load data for {version_dir.name}: {e}")
        
        return verification_data
    
    def calculate_statistics(self, verification_data: Dict[str, Dict]) -> Dict:
        """Calculate overall verification statistics."""
        stats = {
            "total_versions": len(verification_data),
            "verified_versions": 0,
            "pending_versions": 0,
            "failed_versions": 0,
            "unverified_versions": 0,
            "total_verifications": 0,
            "total_verifiers": set(),
            "verification_methods": {
                "checksum": {"attempts": 0, "successes": 0},
                "reproducible_build": {"attempts": 0, "successes": 0},
                "source_audit": {"attempts": 0, "successes": 0}
            },
            "platform_coverage": {
                "windows": 0,
                "macos": 0,
                "linux": 0
            },
            "security_issues": 0,
            "latest_version": None,
            "oldest_verification": None,
            "newest_verification": None
        }
        
        verification_dates = []
        
        for version, data in verification_data.items():
            status = data.get('verification_status', 'unverified')
            
            if status == 'verified':
                stats["verified_versions"] += 1
            elif status == 'pending':
                stats["pending_versions"] += 1
            elif status == 'failed':
                stats["failed_versions"] += 1
            else:
                stats["unverified_versions"] += 1
            
            # Count verifications and verifiers
            verifications = data.get('verifications', [])
            stats["total_verifications"] += len(verifications)
            
            for verification in verifications:
                stats["total_verifiers"].add(verification.get('verifier', 'unknown'))
                if verification.get('date'):
                    verification_dates.append(verification['date'])
            
            # Count verification methods
            methods = data.get('verification_methods', {})
            for method, method_data in methods.items():
                if method in stats["verification_methods"]:
                    stats["verification_methods"][method]["attempts"] += method_data.get('attempts', 0)
                    stats["verification_methods"][method]["successes"] += method_data.get('successes', 0)
            
            # Count platform coverage
            platforms = data.get('platforms', {})
            for platform, platform_data in platforms.items():
                if platform in stats["platform_coverage"] and platform_data.get('verified', False):
                    stats["platform_coverage"][platform] += 1
            
            # Count security issues
            stats["security_issues"] += len(data.get('security_notes', []))
        
        # Convert verifiers set to count
        stats["total_verifiers"] = len(stats["total_verifiers"])
        
        # Find latest version (simple string comparison, assumes semantic versioning)
        if verification_data:
            versions = list(verification_data.keys())
            versions.sort(reverse=True)
            stats["latest_version"] = versions[0]
        
        # Find oldest and newest verifications
        if verification_dates:
            verification_dates.sort()
            stats["oldest_verification"] = verification_dates[0]
            stats["newest_verification"] = verification_dates[-1]
        
        return stats
    
    def generate_html_dashboard(self, verification_data: Dict[str, Dict], stats: Dict) -> str:
        """Generate an HTML dashboard."""
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bitcoin Solo Miner Monitor - Community Verification Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f7931a;
        }}
        .header h1 {{
            color: #f7931a;
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            color: #666;
            margin: 10px 0 0 0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #f7931a;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #f7931a;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .versions-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }}
        .versions-table th,
        .versions-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .versions-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .status-badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .status-verified {{ background: #d4edda; color: #155724; }}
        .status-pending {{ background: #fff3cd; color: #856404; }}
        .status-failed {{ background: #f8d7da; color: #721c24; }}
        .status-unverified {{ background: #e2e3e5; color: #383d41; }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background-color: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background-color: #f7931a;
            transition: width 0.3s ease;
        }}
        .method-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .method-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 0.9em;
        }}
        .security-alert {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Community Verification Dashboard</h1>
            <p>Bitcoin Solo Miner Monitor - Decentralized Trust Through Transparency</p>
            <p><strong>Last Updated:</strong> {update_time}</p>
        </div>
"""
        
        # Add security alerts if any
        if stats["security_issues"] > 0:
            html += f"""
        <div class="security-alert">
            <strong>⚠️ Security Notice:</strong> {stats["security_issues"]} security issue(s) have been reported. 
            Please review the version details below and follow security recommendations.
        </div>
"""
        
        # Statistics cards
        html += f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{stats["total_versions"]}</div>
                <div class="stat-label">Total Versions</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats["verified_versions"]}</div>
                <div class="stat-label">Verified Versions</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats["total_verifications"]}</div>
                <div class="stat-label">Community Verifications</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats["total_verifiers"]}</div>
                <div class="stat-label">Active Verifiers</div>
            </div>
        </div>
"""
        
        # Verification progress
        if stats["total_versions"] > 0:
            verification_rate = (stats["verified_versions"] / stats["total_versions"]) * 100
            html += f"""
        <h2>📊 Verification Progress</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {verification_rate:.1f}%"></div>
        </div>
        <p><strong>{verification_rate:.1f}%</strong> of releases have been community verified</p>
"""
        
        # Verification methods statistics
        html += """
        <h2>🔧 Verification Methods</h2>
        <div class="method-stats">
"""
        
        for method, data in stats["verification_methods"].items():
            success_rate = (data["successes"] / data["attempts"] * 100) if data["attempts"] > 0 else 0
            html += f"""
            <div class="method-card">
                <h4>{method.replace('_', ' ').title()}</h4>
                <p><strong>Attempts:</strong> {data["attempts"]}</p>
                <p><strong>Successes:</strong> {data["successes"]}</p>
                <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
            </div>
"""
        
        html += """
        </div>
"""
        
        # Platform coverage
        html += """
        <h2>💻 Platform Coverage</h2>
        <div class="method-stats">
"""
        
        for platform, count in stats["platform_coverage"].items():
            html += f"""
            <div class="method-card">
                <h4>{platform.title()}</h4>
                <p><strong>Verified Versions:</strong> {count}</p>
            </div>
"""
        
        html += """
        </div>
"""
        
        # Versions table
        html += """
        <h2>📋 Version Details</h2>
        <table class="versions-table">
            <thead>
                <tr>
                    <th>Version</th>
                    <th>Status</th>
                    <th>Verifications</th>
                    <th>Methods</th>
                    <th>Security Notes</th>
                    <th>Last Updated</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Sort versions (newest first)
        sorted_versions = sorted(verification_data.items(), reverse=True)
        
        for version, data in sorted_versions:
            status = data.get('verification_status', 'unverified')
            verification_count = data.get('verification_count', 0)
            security_notes_count = len(data.get('security_notes', []))
            
            # Get methods used
            methods = []
            for verification in data.get('verifications', []):
                methods.extend(verification.get('methods', []))
            unique_methods = list(set(methods))
            methods_str = ', '.join(unique_methods) if unique_methods else 'None'
            
            # Format last updated
            last_updated = data.get('maintainer_notes', {}).get('last_updated', 'Unknown')
            if last_updated != 'Unknown':
                try:
                    last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                except:
                    pass
            
            status_class = f"status-{status}"
            security_indicator = f"⚠️ {security_notes_count}" if security_notes_count > 0 else "✅ None"
            
            html += f"""
                <tr>
                    <td><strong>{version}</strong></td>
                    <td><span class="status-badge {status_class}">{status.title()}</span></td>
                    <td>{verification_count}</td>
                    <td>{methods_str}</td>
                    <td>{security_indicator}</td>
                    <td>{last_updated}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
"""
        
        # Footer
        html += """
        <div class="footer">
            <p>
                <strong>How to Contribute:</strong> 
                <a href="https://github.com/smokeysrh/bitcoin-solo-miner-monitor/blob/main/verification/COMMUNITY_VERIFICATION_GUIDE.md">
                    Community Verification Guide
                </a> | 
                <a href="https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues/new?template=verification-success.md">
                    Report Verification
                </a>
            </p>
            <p>
                This dashboard is automatically generated from community verification reports. 
                Data is updated when new verification reports are submitted through GitHub issues.
            </p>
            <p>
                <em>Bitcoin Solo Miner Monitor - Empowering decentralized Bitcoin mining through open-source transparency</em>
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_markdown_dashboard(self, verification_data: Dict[str, Dict], stats: Dict) -> str:
        """Generate a markdown dashboard."""
        md = f"""# Community Verification Dashboard

**Last Updated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}

## 📊 Overview Statistics

| Metric | Value |
|--------|-------|
| Total Versions | {stats["total_versions"]} |
| Verified Versions | {stats["verified_versions"]} 🟢 |
| Pending Versions | {stats["pending_versions"]} 🟡 |
| Failed Versions | {stats["failed_versions"]} 🔴 |
| Unverified Versions | {stats["unverified_versions"]} ⚫ |
| Total Verifications | {stats["total_verifications"]} |
| Active Verifiers | {stats["total_verifiers"]} |
| Security Issues | {stats["security_issues"]} |

"""
        
        if stats["total_versions"] > 0:
            verification_rate = (stats["verified_versions"] / stats["total_versions"]) * 100
            md += f"**Verification Rate**: {verification_rate:.1f}% of releases verified\n\n"
        
        # Security alerts
        if stats["security_issues"] > 0:
            md += f"""## ⚠️ Security Alerts

{stats["security_issues"]} security issue(s) have been reported. Please review version details below.

"""
        
        # Verification methods
        md += """## 🔧 Verification Methods

| Method | Attempts | Successes | Success Rate |
|--------|----------|-----------|--------------|
"""
        
        for method, data in stats["verification_methods"].items():
            success_rate = (data["successes"] / data["attempts"] * 100) if data["attempts"] > 0 else 0
            md += f"| {method.replace('_', ' ').title()} | {data['attempts']} | {data['successes']} | {success_rate:.1f}% |\n"
        
        # Platform coverage
        md += """
## 💻 Platform Coverage

| Platform | Verified Versions |
|----------|-------------------|
"""
        
        for platform, count in stats["platform_coverage"].items():
            md += f"| {platform.title()} | {count} |\n"
        
        # Version details
        md += """
## 📋 Version Details

| Version | Status | Verifications | Methods | Security | Last Updated |
|---------|--------|---------------|---------|----------|--------------|
"""
        
        # Sort versions (newest first)
        sorted_versions = sorted(verification_data.items(), reverse=True)
        
        for version, data in sorted_versions:
            status = data.get('verification_status', 'unverified')
            verification_count = data.get('verification_count', 0)
            security_notes_count = len(data.get('security_notes', []))
            
            # Status emoji
            status_emoji = {
                'verified': '🟢',
                'pending': '🟡',
                'failed': '🔴',
                'unverified': '⚫'
            }.get(status, '❓')
            
            # Get methods used
            methods = []
            for verification in data.get('verifications', []):
                methods.extend(verification.get('methods', []))
            unique_methods = list(set(methods))
            methods_str = ', '.join(unique_methods) if unique_methods else 'None'
            
            # Format last updated
            last_updated = data.get('maintainer_notes', {}).get('last_updated', 'Unknown')
            if last_updated != 'Unknown':
                try:
                    last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                except:
                    pass
            
            security_indicator = f"⚠️ {security_notes_count}" if security_notes_count > 0 else "✅"
            
            md += f"| **{version}** | {status_emoji} {status.title()} | {verification_count} | {methods_str} | {security_indicator} | {last_updated} |\n"
        
        # Footer
        md += f"""
## 🤝 How to Contribute

- **Verify a Release**: Follow our [Community Verification Guide](COMMUNITY_VERIFICATION_GUIDE.md)
- **Report Success**: Use the [Verification Success template](../.github/ISSUE_TEMPLATE/verification-success.md)
- **Report Issues**: Use the [Verification Failure template](../.github/ISSUE_TEMPLATE/verification-failure.md)
- **Security Issues**: Use the [Security Issue template](../.github/ISSUE_TEMPLATE/security-issue.md)

## 📈 Verification Trends

- **Latest Version**: {stats.get("latest_version", "Unknown")}
- **Oldest Verification**: {stats.get("oldest_verification", "Unknown")[:10] if stats.get("oldest_verification") else "Unknown"}
- **Newest Verification**: {stats.get("newest_verification", "Unknown")[:10] if stats.get("newest_verification") else "Unknown"}

---

*This dashboard is automatically generated from community verification data. Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}*
"""
        
        return md
    
    def generate_dashboard(self, format_type: str = "markdown", output_file: Path = None) -> str:
        """Generate the verification dashboard."""
        verification_data = self.load_verification_data()
        stats = self.calculate_statistics(verification_data)
        
        if format_type == "html":
            dashboard = self.generate_html_dashboard(verification_data, stats)
        else:
            dashboard = self.generate_markdown_dashboard(verification_data, stats)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(dashboard)
            print(f"Dashboard saved to {output_file}")
        
        return dashboard


def main():
    parser = argparse.ArgumentParser(
        description="Generate community verification dashboard"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "html"],
        default="markdown",
        help="Output format"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path"
    )
    parser.add_argument(
        "--verification-dir",
        type=Path,
        help="Path to verification directory"
    )
    
    args = parser.parse_args()
    
    try:
        dashboard = VerificationDashboard(args.verification_dir)
        result = dashboard.generate_dashboard(args.format, args.output)
        
        if not args.output:
            print(result)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()