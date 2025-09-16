#!/usr/bin/env python3
"""
Community Security Audit Coordinator
Coordinates community security audits and manages the audit process
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class CommunityAuditCoordinator:
    """Coordinates community security audits"""
    
    def __init__(self, config_file: str = "config/security-config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.github_repo = self.config.get("github_repo", "smokeysrh/bitcoin-solo-miner-monitor")
        self.github_api_base = f"https://api.github.com/repos/{self.github_repo}"
        
    def _load_config(self) -> Dict:
        """Load security configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
        
        return {
            "github_repo": "smokeysrh/bitcoin-solo-miner-monitor",
            "audit_coordination": {
                "enabled": True,
                "audit_labels": ["security-audit", "audit-report"],
                "coordinator_role": "community"
            }
        }
    
    def get_active_audits(self) -> List[Dict]:
        """Get list of active security audits from GitHub issues"""
        print("🔍 Fetching active security audits...")
        
        try:
            # Get issues with security-audit label
            params = {
                "labels": "security-audit",
                "state": "open",
                "sort": "created",
                "direction": "desc"
            }
            
            response = requests.get(f"{self.github_api_base}/issues", params=params, timeout=30)
            if response.status_code != 200:
                print(f"API request failed with status {response.status_code}: {response.text}")
                return []
            
            issues = response.json()
            
            if len(issues) == 0:
                print("📊 No security audit issues found (this is normal for new projects)")
            else:
                print(f"📊 Found {len(issues)} active security audits")
            
            audits = []
            for issue in issues:
                audit_info = {
                    "number": issue["number"],
                    "title": issue["title"],
                    "created_at": issue["created_at"],
                    "updated_at": issue["updated_at"],
                    "author": issue["user"]["login"],
                    "labels": [label["name"] for label in issue["labels"]],
                    "url": issue["html_url"],
                    "state": issue["state"]
                }
                
                # Determine audit type from labels and title
                if "audit-report" in audit_info["labels"]:
                    audit_info["type"] = "comprehensive_report"
                elif "security-audit" in audit_info["labels"]:
                    audit_info["type"] = "individual_finding"
                else:
                    audit_info["type"] = "unknown"
                
                audits.append(audit_info)
            
            return audits
            
        except Exception as e:
            print(f"Error fetching active audits: {e}")
            return []
    
    def analyze_audit_coverage(self, audits: List[Dict]) -> Dict:
        """Analyze audit coverage and identify gaps"""
        print("📈 Analyzing audit coverage...")
        
        coverage = {
            "total_audits": len(audits),
            "audit_types": {},
            "recent_activity": 0,
            "coverage_gaps": [],
            "recommendations": []
        }
        
        # Analyze audit types
        for audit in audits:
            audit_type = audit.get("type", "unknown")
            if audit_type not in coverage["audit_types"]:
                coverage["audit_types"][audit_type] = 0
            coverage["audit_types"][audit_type] += 1
        
        # Check for recent activity (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        for audit in audits:
            updated_date = datetime.fromisoformat(audit["updated_at"].replace("Z", "+00:00"))
            if updated_date.replace(tzinfo=None) > thirty_days_ago:
                coverage["recent_activity"] += 1
        
        # Identify coverage gaps
        expected_audit_areas = [
            "source_code_review",
            "dependency_scanning",
            "build_verification",
            "installer_security",
            "network_security",
            "configuration_review"
        ]
        
        # Check for missing audit areas (simplified analysis)
        audit_titles = " ".join([audit["title"].lower() for audit in audits])
        
        for area in expected_audit_areas:
            area_keywords = {
                "source_code_review": ["code", "source", "review"],
                "dependency_scanning": ["dependency", "dependencies", "vulnerability", "cve"],
                "build_verification": ["build", "reproducible", "compilation"],
                "installer_security": ["installer", "package", "distribution"],
                "network_security": ["network", "communication", "protocol"],
                "configuration_review": ["config", "configuration", "settings"]
            }
            
            keywords = area_keywords.get(area, [area.replace("_", " ")])
            if not any(keyword in audit_titles for keyword in keywords):
                coverage["coverage_gaps"].append(area)
        
        # Generate recommendations
        if coverage["recent_activity"] == 0:
            coverage["recommendations"].append("No recent audit activity - consider organizing community audit")
        
        if coverage["total_audits"] < 5:
            coverage["recommendations"].append("Limited audit coverage - encourage more community participation")
        
        if coverage["coverage_gaps"]:
            coverage["recommendations"].append(f"Missing audit coverage for: {', '.join(coverage['coverage_gaps'])}")
        
        if coverage["audit_types"].get("comprehensive_report", 0) == 0:
            coverage["recommendations"].append("No comprehensive audit reports - consider coordinating full audit")
        
        return coverage
    
    def generate_audit_status_report(self, audits: List[Dict], coverage: Dict) -> str:
        """Generate audit status report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(f"security-reports/audit_status_report_{timestamp}.md")
        report_file.parent.mkdir(exist_ok=True)
        
        lines = [
            "# Community Security Audit Status Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Executive Summary",
            "",
            f"**Total Active Audits:** {coverage['total_audits']}",
            f"**Recent Activity (30 days):** {coverage['recent_activity']}",
            f"**Coverage Gaps:** {len(coverage['coverage_gaps'])}",
            ""
        ]
        
        # Audit activity overview
        if coverage["total_audits"] > 0:
            lines.extend([
                "## Audit Activity Overview",
                ""
            ])
            
            for audit_type, count in coverage["audit_types"].items():
                lines.append(f"- **{audit_type.replace('_', ' ').title()}:** {count}")
            
            lines.append("")
        
        # Active audits
        if audits:
            lines.extend([
                "## Active Security Audits",
                ""
            ])
            
            for audit in audits[:10]:  # Show top 10 most recent
                created_date = datetime.fromisoformat(audit["created_at"].replace("Z", "+00:00"))
                days_ago = (datetime.now().replace(tzinfo=None) - created_date.replace(tzinfo=None)).days
                
                lines.extend([
                    f"### [{audit['title']}]({audit['url']})",
                    f"- **Author:** {audit['author']}",
                    f"- **Created:** {days_ago} days ago",
                    f"- **Type:** {audit['type'].replace('_', ' ').title()}",
                    f"- **Labels:** {', '.join(audit['labels'])}",
                    ""
                ])
        
        # Coverage analysis
        lines.extend([
            "## Coverage Analysis",
            ""
        ])
        
        if coverage["coverage_gaps"]:
            lines.extend([
                "### Coverage Gaps",
                ""
            ])
            for gap in coverage["coverage_gaps"]:
                lines.append(f"- ⚠️ {gap.replace('_', ' ').title()}")
            lines.append("")
        else:
            lines.extend([
                "✅ No significant coverage gaps identified",
                ""
            ])
        
        # Recommendations
        if coverage["recommendations"]:
            lines.extend([
                "## Recommendations",
                ""
            ])
            for rec in coverage["recommendations"]:
                lines.append(f"- 📋 {rec}")
            lines.append("")
        
        # Community participation
        lines.extend([
            "## Community Participation Opportunities",
            "",
            "### How to Participate",
            "1. **Review Active Audits**: Comment on existing audit issues",
            "2. **Verify Findings**: Reproduce and validate reported issues",
            "3. **Contribute New Audits**: Start new security audits in uncovered areas",
            "4. **Share Expertise**: Provide security expertise and guidance",
            "",
            "### Getting Started",
            "- Use the Community Audit Participation Guide: `python verification/community-audit/audit-participation-guide.py --interactive`",
            "- Join Discord for real-time coordination: https://discord.gg/GzNsNnh4yT",
            "- Review security documentation: `docs/security/`",
            "",
            "### Priority Areas",
        ])
        
        # Add priority areas based on gaps
        if coverage["coverage_gaps"]:
            for gap in coverage["coverage_gaps"][:3]:  # Top 3 priority gaps
                lines.append(f"- 🎯 {gap.replace('_', ' ').title()}")
        else:
            lines.extend([
                "- 🔄 Ongoing verification of existing findings",
                "- 📊 Comprehensive audit report compilation",
                "- 🔍 Deep-dive security analysis"
            ])
        
        lines.extend([
            "",
            "## Resources",
            "",
            "### Documentation",
            "- [Community Security Audit Guide](docs/security/COMMUNITY_SECURITY_AUDIT_GUIDE.md)",
            "- [Security Issue Reporting](docs/security/SECURITY_ISSUE_REPORTING.md)",
            "- [Verification Tools](verification/community-audit/)",
            "",
            "### Tools",
            "- Audit Participation Guide: `verification/community-audit/audit-participation-guide.py`",
            "- Security Verifier: `verification/community-audit/community-security-verifier.py`",
            "- Security Integration: `scripts/security/security-integration.py`",
            "",
            "### Community Channels",
            "- **GitHub Issues**: https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues",
            "- **Discord**: https://discord.gg/GzNsNnh4yT",
            "",
            "---",
            "",
            "*This report was generated by the Community Audit Coordinator*",
            "*Next update: Automated weekly or on-demand*"
        ])
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        return str(report_file)
    
    def suggest_audit_activities(self, coverage: Dict) -> List[Dict]:
        """Suggest specific audit activities based on coverage analysis"""
        suggestions = []
        
        # Based on coverage gaps
        gap_activities = {
            "source_code_review": {
                "title": "Source Code Security Review",
                "description": "Comprehensive review of application source code for security vulnerabilities",
                "priority": "high",
                "estimated_effort": "8-16 hours",
                "skills_needed": ["Python", "JavaScript", "Security Analysis"]
            },
            "dependency_scanning": {
                "title": "Dependency Vulnerability Assessment",
                "description": "Scan and analyze all project dependencies for known vulnerabilities",
                "priority": "high",
                "estimated_effort": "2-4 hours",
                "skills_needed": ["Command Line", "Security Tools"]
            },
            "build_verification": {
                "title": "Reproducible Build Verification",
                "description": "Verify that builds are reproducible and secure",
                "priority": "medium",
                "estimated_effort": "4-8 hours",
                "skills_needed": ["Build Systems", "Docker", "Cryptography"]
            },
            "installer_security": {
                "title": "Installer Security Analysis",
                "description": "Security analysis of generated installer packages",
                "priority": "medium",
                "estimated_effort": "6-10 hours",
                "skills_needed": ["Reverse Engineering", "Malware Analysis"]
            },
            "network_security": {
                "title": "Network Security Assessment",
                "description": "Analysis of network communications and protocols",
                "priority": "medium",
                "estimated_effort": "8-12 hours",
                "skills_needed": ["Network Security", "Protocol Analysis"]
            },
            "configuration_review": {
                "title": "Configuration Security Review",
                "description": "Review of application and system configurations",
                "priority": "low",
                "estimated_effort": "3-6 hours",
                "skills_needed": ["System Administration", "Security Configuration"]
            }
        }
        
        for gap in coverage.get("coverage_gaps", []):
            if gap in gap_activities:
                suggestions.append(gap_activities[gap])
        
        # General suggestions based on audit status
        if coverage["total_audits"] == 0:
            suggestions.append({
                "title": "Initial Security Assessment",
                "description": "Comprehensive initial security assessment of the entire project",
                "priority": "critical",
                "estimated_effort": "20-40 hours",
                "skills_needed": ["Security Analysis", "Code Review", "Testing"]
            })
        
        if coverage["recent_activity"] == 0:
            suggestions.append({
                "title": "Security Audit Refresh",
                "description": "Update and refresh existing security audits with latest code changes",
                "priority": "high",
                "estimated_effort": "10-20 hours",
                "skills_needed": ["Security Analysis", "Change Analysis"]
            })
        
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 4))
        
        return suggestions
    
    def create_audit_coordination_issue(self, suggestions: List[Dict]) -> Optional[str]:
        """Create a GitHub issue for audit coordination"""
        if not suggestions:
            return None
        
        # Create issue content
        title = f"[AUDIT COORDINATION] Community Security Audit - {datetime.now().strftime('%Y-%m')}"
        
        body_lines = [
            "## Community Security Audit Coordination",
            "",
            f"This issue coordinates community security audit activities for {datetime.now().strftime('%B %Y')}.",
            "",
            "## Suggested Audit Activities",
            ""
        ]
        
        for i, suggestion in enumerate(suggestions[:5], 1):  # Top 5 suggestions
            priority_emoji = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "📋",
                "low": "💡"
            }.get(suggestion["priority"], "📋")
            
            body_lines.extend([
                f"### {i}. {suggestion['title']} {priority_emoji}",
                f"**Priority:** {suggestion['priority'].title()}",
                f"**Estimated Effort:** {suggestion['estimated_effort']}",
                f"**Skills Needed:** {', '.join(suggestion['skills_needed'])}",
                "",
                suggestion['description'],
                "",
                "**Volunteers:**",
                "- [ ] _Add your name here to volunteer_",
                "",
                "---",
                ""
            ])
        
        body_lines.extend([
            "## How to Participate",
            "",
            "1. **Choose an Activity**: Comment on this issue to volunteer for specific activities",
            "2. **Get Started**: Use the audit participation guide: `python verification/community-audit/audit-participation-guide.py --interactive`",
            "3. **Coordinate**: Join Discord for real-time coordination: https://discord.gg/GzNsNnh4yT",
            "4. **Report Findings**: Create individual issues for findings using the security audit templates",
            "",
            "## Resources",
            "",
            "- [Community Security Audit Guide](docs/security/COMMUNITY_SECURITY_AUDIT_GUIDE.md)",
            "- [Security Issue Reporting Process](docs/security/SECURITY_ISSUE_REPORTING.md)",
            "- [Verification Tools](verification/community-audit/)",
            "",
            "## Timeline",
            "",
            f"- **Coordination Period:** {datetime.now().strftime('%Y-%m-%d')} - {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}",
            f"- **Audit Period:** {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')} - {(datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')}",
            f"- **Reporting Period:** {(datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')} - {(datetime.now() + timedelta(days=35)).strftime('%Y-%m-%d')}",
            "",
            "---",
            "",
            "*This coordination issue was automatically generated by the Community Audit Coordinator*"
        ])
        
        issue_content = {
            "title": title,
            "body": "\n".join(body_lines),
            "labels": ["security-audit", "coordination", "community"]
        }
        
        # Save to file for manual creation (since we don't have GitHub API token)
        coordination_file = Path("security-reports/audit-coordination-issue.json")
        coordination_file.parent.mkdir(exist_ok=True)
        
        with open(coordination_file, 'w', encoding='utf-8') as f:
            json.dump(issue_content, f, indent=2)
        
        print(f"📝 Audit coordination issue content saved to: {coordination_file}")
        print("To create the issue, copy the content and create it manually on GitHub")
        
        return str(coordination_file)


def main():
    parser = argparse.ArgumentParser(description="Community Security Audit Coordinator")
    parser.add_argument("--status-report", action="store_true",
                       help="Generate audit status report")
    parser.add_argument("--suggest-activities", action="store_true",
                       help="Suggest audit activities based on coverage")
    parser.add_argument("--coordinate", action="store_true",
                       help="Create audit coordination issue")
    parser.add_argument("--config", help="Path to security configuration file")
    
    args = parser.parse_args()
    
    config_file = args.config if args.config else "config/security-config.json"
    coordinator = CommunityAuditCoordinator(config_file)
    
    # Get active audits
    audits = coordinator.get_active_audits()
    coverage = coordinator.analyze_audit_coverage(audits)
    
    if args.status_report or not any(vars(args).values()):
        # Generate status report
        report_file = coordinator.generate_audit_status_report(audits, coverage)
        print(f"📊 Audit status report generated: {report_file}")
    
    if args.suggest_activities:
        # Generate activity suggestions
        suggestions = coordinator.suggest_audit_activities(coverage)
        
        print("\n🎯 Suggested Audit Activities:")
        print("=" * 50)
        
        for i, suggestion in enumerate(suggestions, 1):
            priority_emoji = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "📋",
                "low": "💡"
            }.get(suggestion["priority"], "📋")
            
            print(f"{i}. {suggestion['title']} {priority_emoji}")
            print(f"   Priority: {suggestion['priority'].title()}")
            print(f"   Effort: {suggestion['estimated_effort']}")
            print(f"   Skills: {', '.join(suggestion['skills_needed'])}")
            print(f"   {suggestion['description']}")
            print()
    
    if args.coordinate:
        # Create coordination issue
        suggestions = coordinator.suggest_audit_activities(coverage)
        coordination_file = coordinator.create_audit_coordination_issue(suggestions)
        
        if coordination_file:
            print(f"🤝 Audit coordination issue prepared: {coordination_file}")
        else:
            print("No coordination issue needed at this time")


if __name__ == "__main__":
    main()