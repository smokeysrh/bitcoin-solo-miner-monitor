#!/usr/bin/env python3
"""
Community Audit Participation Guide Tool
Provides interactive guidance for community members to participate in security audits
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class CommunityAuditGuide:
    """Interactive guide for community audit participation"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.audit_dir = Path("community-audit-workspace")
        self.audit_dir.mkdir(exist_ok=True)
        
    def display_welcome(self):
        """Display welcome message and audit overview"""
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    Bitcoin Solo Miner Monitor                               ║
║                   Community Security Audit Guide                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Welcome to the community security audit participation guide!

This tool will help you:
• Set up your audit environment
• Choose appropriate audit activities based on your skill level
• Execute security audits with proper tools and procedures
• Document and report your findings
• Participate in the community audit process

Let's get started with your security audit journey!
""")
    
    def assess_skill_level(self) -> str:
        """Assess user's skill level for appropriate audit tasks"""
        print("\n🎯 Skill Level Assessment")
        print("=" * 50)
        
        questions = [
            {
                "question": "How familiar are you with Git version control?",
                "options": ["Beginner", "Intermediate", "Advanced"],
                "weights": {"Beginner": 1, "Intermediate": 2, "Advanced": 3}
            },
            {
                "question": "What's your experience with Python programming?",
                "options": ["None", "Basic", "Intermediate", "Advanced"],
                "weights": {"None": 0, "Basic": 1, "Intermediate": 2, "Advanced": 3}
            },
            {
                "question": "How familiar are you with web security concepts?",
                "options": ["None", "Basic", "Intermediate", "Advanced"],
                "weights": {"None": 0, "Basic": 1, "Intermediate": 2, "Advanced": 3}
            },
            {
                "question": "Have you used security scanning tools before?",
                "options": ["Never", "Occasionally", "Regularly", "Expert"],
                "weights": {"Never": 0, "Occasionally": 1, "Regularly": 2, "Expert": 3}
            },
            {
                "question": "What's your experience with build systems and CI/CD?",
                "options": ["None", "Basic", "Intermediate", "Advanced"],
                "weights": {"None": 0, "Basic": 1, "Intermediate": 2, "Advanced": 3}
            }
        ]
        
        total_score = 0
        max_score = 0
        
        for i, q in enumerate(questions, 1):
            print(f"\n{i}. {q['question']}")
            for j, option in enumerate(q['options'], 1):
                print(f"   {j}. {option}")
            
            while True:
                try:
                    choice = int(input(f"Enter your choice (1-{len(q['options'])}): "))
                    if 1 <= choice <= len(q['options']):
                        selected = q['options'][choice - 1]
                        total_score += q['weights'][selected]
                        max_score += max(q['weights'].values())
                        break
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
        
        # Determine skill level based on score
        percentage = (total_score / max_score) * 100
        
        if percentage >= 80:
            skill_level = "Advanced"
        elif percentage >= 60:
            skill_level = "Intermediate"
        elif percentage >= 30:
            skill_level = "Basic"
        else:
            skill_level = "Beginner"
        
        print(f"\n📊 Assessment Results:")
        print(f"Score: {total_score}/{max_score} ({percentage:.1f}%)")
        print(f"Skill Level: {skill_level}")
        
        return skill_level
    
    def recommend_audit_activities(self, skill_level: str) -> List[Dict]:
        """Recommend appropriate audit activities based on skill level"""
        activities = {
            "Beginner": [
                {
                    "name": "Documentation Review",
                    "description": "Review security documentation for accuracy and completeness",
                    "time_estimate": "2-4 hours",
                    "tools_needed": ["Web browser", "Text editor"],
                    "difficulty": "Easy"
                },
                {
                    "name": "Basic Checksum Verification",
                    "description": "Verify checksums of released installers",
                    "time_estimate": "1-2 hours",
                    "tools_needed": ["Command line", "sha256sum"],
                    "difficulty": "Easy"
                },
                {
                    "name": "User Interface Security Review",
                    "description": "Review user interface for security-related usability issues",
                    "time_estimate": "3-5 hours",
                    "tools_needed": ["Web browser", "Application"],
                    "difficulty": "Easy"
                }
            ],
            "Basic": [
                {
                    "name": "Configuration Security Review",
                    "description": "Review configuration files for security issues",
                    "time_estimate": "4-6 hours",
                    "tools_needed": ["Text editor", "JSON/YAML knowledge"],
                    "difficulty": "Medium"
                },
                {
                    "name": "Dependency Vulnerability Scanning",
                    "description": "Run automated dependency vulnerability scans",
                    "time_estimate": "2-3 hours",
                    "tools_needed": ["Python", "npm", "safety", "npm audit"],
                    "difficulty": "Medium"
                },
                {
                    "name": "Basic Code Review",
                    "description": "Review code for obvious security issues",
                    "time_estimate": "6-8 hours",
                    "tools_needed": ["Git", "Code editor", "Basic Python knowledge"],
                    "difficulty": "Medium"
                }
            ],
            "Intermediate": [
                {
                    "name": "Static Code Analysis",
                    "description": "Perform comprehensive static code analysis",
                    "time_estimate": "8-12 hours",
                    "tools_needed": ["bandit", "eslint", "sonarqube"],
                    "difficulty": "Medium-Hard"
                },
                {
                    "name": "Build Process Verification",
                    "description": "Verify reproducible builds and build security",
                    "time_estimate": "6-10 hours",
                    "tools_needed": ["Docker", "Build tools", "Checksum utilities"],
                    "difficulty": "Medium-Hard"
                },
                {
                    "name": "Network Security Analysis",
                    "description": "Analyze network communications and security",
                    "time_estimate": "8-12 hours",
                    "tools_needed": ["Wireshark", "netstat", "curl"],
                    "difficulty": "Hard"
                }
            ],
            "Advanced": [
                {
                    "name": "Dynamic Security Testing",
                    "description": "Perform runtime security testing and analysis",
                    "time_estimate": "12-20 hours",
                    "tools_needed": ["OWASP ZAP", "Burp Suite", "Custom scripts"],
                    "difficulty": "Hard"
                },
                {
                    "name": "Cryptographic Analysis",
                    "description": "Review cryptographic implementations and protocols",
                    "time_estimate": "10-16 hours",
                    "tools_needed": ["Cryptographic knowledge", "Analysis tools"],
                    "difficulty": "Hard"
                },
                {
                    "name": "Penetration Testing",
                    "description": "Comprehensive penetration testing of the application",
                    "time_estimate": "20-40 hours",
                    "tools_needed": ["Kali Linux", "Metasploit", "Custom exploits"],
                    "difficulty": "Expert"
                }
            ]
        }
        
        return activities.get(skill_level, activities["Beginner"])
    
    def setup_audit_environment(self, activities: List[Dict]) -> bool:
        """Set up audit environment based on selected activities"""
        print("\n🔧 Setting Up Audit Environment")
        print("=" * 50)
        
        # Determine required tools
        all_tools = set()
        for activity in activities:
            all_tools.update(activity.get("tools_needed", []))
        
        print("Required tools for your selected activities:")
        for tool in sorted(all_tools):
            print(f"  • {tool}")
        
        # Check for existing tools
        tool_checks = {
            "git": "git --version",
            "python": "python --version",
            "pip": "pip --version",
            "node": "node --version",
            "npm": "npm --version",
            "docker": "docker --version"
        }
        
        print("\n🔍 Checking for installed tools...")
        available_tools = {}
        
        for tool, command in tool_checks.items():
            try:
                result = subprocess.run(command.split(), 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    available_tools[tool] = result.stdout.strip()
                    print(f"  ✅ {tool}: {result.stdout.strip()}")
                else:
                    print(f"  ❌ {tool}: Not found")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print(f"  ❌ {tool}: Not found")
        
        # Install Python security tools if Python is available
        if "python" in available_tools and "pip" in available_tools:
            print("\n📦 Installing Python security tools...")
            security_tools = ["safety", "bandit", "pip-audit"]
            
            for tool in security_tools:
                try:
                    print(f"  Installing {tool}...")
                    result = subprocess.run([sys.executable, "-m", "pip", "install", tool],
                                          capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        print(f"  ✅ {tool} installed successfully")
                    else:
                        print(f"  ⚠️  {tool} installation failed: {result.stderr}")
                except subprocess.TimeoutExpired:
                    print(f"  ⚠️  {tool} installation timed out")
        
        # Clone project repository
        print("\n📥 Setting up project repository...")
        repo_dir = self.audit_dir / "bitcoin-solo-miner-monitor"
        
        if not repo_dir.exists():
            try:
                print("  Cloning repository...")
                result = subprocess.run([
                    "git", "clone", 
                    "https://github.com/smokeysrh/bitcoin-solo-miner-monitor.git",
                    str(repo_dir)
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    print("  ✅ Repository cloned successfully")
                else:
                    print(f"  ❌ Repository clone failed: {result.stderr}")
                    return False
            except subprocess.TimeoutExpired:
                print("  ❌ Repository clone timed out")
                return False
        else:
            print("  ✅ Repository already exists")
        
        # Create audit workspace
        workspace_dirs = [
            "reports",
            "tools",
            "evidence",
            "scripts"
        ]
        
        for dir_name in workspace_dirs:
            (self.audit_dir / dir_name).mkdir(exist_ok=True)
        
        print(f"\n✅ Audit environment set up in: {self.audit_dir.absolute()}")
        return True
    
    def generate_audit_checklist(self, activities: List[Dict]) -> str:
        """Generate personalized audit checklist"""
        checklist_file = self.audit_dir / "audit-checklist.md"
        
        lines = [
            "# Personal Security Audit Checklist",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Pre-Audit Setup",
            "",
            "- [ ] Environment setup completed",
            "- [ ] Required tools installed",
            "- [ ] Project repository cloned",
            "- [ ] Audit workspace organized",
            "",
            "## Audit Activities",
            ""
        ]
        
        for i, activity in enumerate(activities, 1):
            lines.extend([
                f"### {i}. {activity['name']}",
                f"**Difficulty:** {activity['difficulty']}",
                f"**Time Estimate:** {activity['time_estimate']}",
                f"**Description:** {activity['description']}",
                "",
                "**Tools Needed:**"
            ])
            
            for tool in activity.get("tools_needed", []):
                lines.append(f"- {tool}")
            
            lines.extend([
                "",
                "**Checklist:**",
                "- [ ] Activity started",
                "- [ ] Tools and environment prepared",
                "- [ ] Audit procedures executed",
                "- [ ] Findings documented",
                "- [ ] Evidence collected",
                "- [ ] Report generated",
                "- [ ] Activity completed",
                "",
                "**Notes:**",
                "_Add your notes and findings here_",
                "",
                "---",
                ""
            ])
        
        lines.extend([
            "## Post-Audit Activities",
            "",
            "- [ ] All findings documented",
            "- [ ] Evidence organized",
            "- [ ] Reports generated",
            "- [ ] Community submission prepared",
            "- [ ] Feedback provided to community",
            "",
            "## Community Participation",
            "",
            "- [ ] Findings shared with community",
            "- [ ] GitHub issues created (if applicable)",
            "- [ ] Discord discussions participated",
            "- [ ] Peer review conducted",
            "- [ ] Follow-up actions completed",
            "",
            "---",
            "",
            "*This checklist was generated by the Bitcoin Solo Miner Monitor*",
            "*Community Audit Participation Guide*"
        ])
        
        with open(checklist_file, 'w') as f:
            f.write("\n".join(lines))
        
        return str(checklist_file)
    
    def provide_activity_guidance(self, activity: Dict):
        """Provide detailed guidance for a specific audit activity"""
        print(f"\n📋 Activity Guidance: {activity['name']}")
        print("=" * 60)
        print(f"Description: {activity['description']}")
        print(f"Difficulty: {activity['difficulty']}")
        print(f"Time Estimate: {activity['time_estimate']}")
        
        # Activity-specific guidance
        guidance = {
            "Documentation Review": self._guide_documentation_review,
            "Basic Checksum Verification": self._guide_checksum_verification,
            "Dependency Vulnerability Scanning": self._guide_dependency_scanning,
            "Static Code Analysis": self._guide_static_analysis,
            "Build Process Verification": self._guide_build_verification
        }
        
        guide_func = guidance.get(activity['name'])
        if guide_func:
            guide_func()
        else:
            print("\nGeneral guidance:")
            print("1. Read relevant documentation")
            print("2. Set up required tools")
            print("3. Execute audit procedures")
            print("4. Document findings")
            print("5. Report results to community")
    
    def _guide_documentation_review(self):
        """Provide guidance for documentation review"""
        print("\n📚 Documentation Review Guidance:")
        print("""
1. **Security Documentation Review:**
   - Review docs/security/ directory
   - Check for accuracy and completeness
   - Verify links and references work
   - Look for missing information

2. **Installation Documentation:**
   - Review installation guides
   - Check for security warnings
   - Verify instructions are clear
   - Test instructions if possible

3. **API Documentation:**
   - Review API security documentation
   - Check for authentication details
   - Verify security best practices
   - Look for missing security considerations

4. **What to Look For:**
   - Outdated information
   - Missing security warnings
   - Unclear instructions
   - Broken links or references
   - Inconsistent information

5. **How to Report:**
   - Create GitHub issue with 'documentation' label
   - Provide specific page/section references
   - Suggest improvements
   - Offer to help with corrections
""")
    
    def _guide_checksum_verification(self):
        """Provide guidance for checksum verification"""
        print("\n🔐 Checksum Verification Guidance:")
        print("""
1. **Download Official Checksums:**
   ```bash
   curl -L https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/latest/download/SHA256SUMS -o SHA256SUMS
   ```

2. **Download Installers:**
   ```bash
   # Download all platform installers
   curl -L [installer-url] -o installer-file
   ```

3. **Verify Checksums:**
   ```bash
   # On Linux/macOS
   sha256sum -c SHA256SUMS
   
   # On Windows
   certutil -hashfile installer-file SHA256
   ```

4. **What to Check:**
   - All checksums match official values
   - No missing or extra files
   - Checksum file is properly formatted
   - All platforms are represented

5. **Report Issues:**
   - Mismatched checksums (CRITICAL)
   - Missing checksum files
   - Formatting issues
   - Missing platform support
""")
    
    def _guide_dependency_scanning(self):
        """Provide guidance for dependency vulnerability scanning"""
        print("\n🔍 Dependency Vulnerability Scanning Guidance:")
        print("""
1. **Python Dependencies:**
   ```bash
   cd bitcoin-solo-miner-monitor
   safety check --json --output reports/safety-report.json
   pip-audit --format=json --output=reports/pip-audit-report.json
   ```

2. **Node.js Dependencies:**
   ```bash
   cd src/frontend
   npm audit --json > ../../reports/npm-audit-report.json
   ```

3. **Analyze Results:**
   - Review vulnerability reports
   - Check severity levels
   - Identify outdated packages
   - Research false positives

4. **What to Report:**
   - High/Critical vulnerabilities
   - Outdated dependencies
   - Missing security updates
   - Dependency conflicts

5. **Create Reports:**
   - Summarize findings
   - Provide remediation suggestions
   - Include tool outputs
   - Prioritize by severity
""")
    
    def _guide_static_analysis(self):
        """Provide guidance for static code analysis"""
        print("\n🔬 Static Code Analysis Guidance:")
        print("""
1. **Python Code Analysis:**
   ```bash
   cd bitcoin-solo-miner-monitor
   bandit -r src/ -f json -o reports/bandit-report.json
   ```

2. **JavaScript Code Analysis:**
   ```bash
   cd src/frontend
   npm run lint -- --format json > ../../reports/eslint-report.json
   ```

3. **Manual Code Review:**
   - Focus on security-sensitive areas
   - Check input validation
   - Review authentication/authorization
   - Examine error handling

4. **Areas to Focus:**
   - User input handling
   - File operations
   - Network communications
   - Cryptographic operations
   - Configuration handling

5. **Document Findings:**
   - Specific file and line numbers
   - Vulnerability description
   - Potential impact
   - Suggested remediation
""")
    
    def _guide_build_verification(self):
        """Provide guidance for build process verification"""
        print("\n🏗️ Build Process Verification Guidance:")
        print("""
1. **Reproducible Build:**
   ```bash
   cd bitcoin-solo-miner-monitor
   python tools/build/build-from-source.py --reproducible
   ```

2. **Compare Artifacts:**
   ```bash
   # Generate checksums of your build
   sha256sum dist/* > community-checksums.txt
   
   # Compare with official checksums
   diff community-checksums.txt official-checksums.txt
   ```

3. **Verify Build Environment:**
   - Check build dependencies
   - Verify build scripts
   - Test on clean environment
   - Document build process

4. **What to Verify:**
   - Build reproducibility
   - Checksum consistency
   - Dependency integrity
   - Build script security

5. **Report Issues:**
   - Non-reproducible builds
   - Checksum mismatches
   - Build failures
   - Security concerns in build process
""")
    
    def run_interactive_guide(self):
        """Run the interactive audit participation guide"""
        self.display_welcome()
        
        # Assess skill level
        skill_level = self.assess_skill_level()
        
        # Recommend activities
        activities = self.recommend_audit_activities(skill_level)
        
        print(f"\n🎯 Recommended Audit Activities for {skill_level} Level:")
        print("=" * 60)
        
        for i, activity in enumerate(activities, 1):
            print(f"{i}. {activity['name']} ({activity['difficulty']})")
            print(f"   {activity['description']}")
            print(f"   Time: {activity['time_estimate']}")
            print()
        
        # Activity selection
        print("Select activities you'd like to participate in:")
        print("Enter activity numbers separated by commas (e.g., 1,3,4) or 'all' for all activities:")
        
        while True:
            selection = input("Your selection: ").strip().lower()
            
            if selection == 'all':
                selected_activities = activities
                break
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(',')]
                    if all(0 <= i < len(activities) for i in indices):
                        selected_activities = [activities[i] for i in indices]
                        break
                    else:
                        print("Invalid selection. Please try again.")
                except ValueError:
                    print("Invalid format. Please enter numbers separated by commas.")
        
        print(f"\n✅ Selected {len(selected_activities)} activities")
        
        # Set up environment
        if self.setup_audit_environment(selected_activities):
            # Generate checklist
            checklist_file = self.generate_audit_checklist(selected_activities)
            print(f"\n📋 Audit checklist generated: {checklist_file}")
            
            # Provide activity guidance
            print("\n🎓 Would you like detailed guidance for any activity? (y/n)")
            if input().lower().startswith('y'):
                for i, activity in enumerate(selected_activities, 1):
                    print(f"\n{i}. {activity['name']}")
                
                while True:
                    try:
                        choice = int(input(f"Select activity for guidance (1-{len(selected_activities)}, 0 to skip): "))
                        if choice == 0:
                            break
                        elif 1 <= choice <= len(selected_activities):
                            self.provide_activity_guidance(selected_activities[choice - 1])
                            break
                        else:
                            print("Invalid choice.")
                    except ValueError:
                        print("Please enter a valid number.")
            
            print(f"""
🎉 Audit setup complete!

Your audit workspace: {self.audit_dir.absolute()}

Next steps:
1. Review your personalized checklist: {checklist_file}
2. Start with your selected activities
3. Document findings in the reports/ directory
4. Share results with the community

Community channels:
• GitHub: https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues
• Discord: https://discord.gg/GzNsNnh4yT

Happy auditing! 🔒
""")
        else:
            print("\n❌ Environment setup failed. Please check the errors above and try again.")


def main():
    parser = argparse.ArgumentParser(description="Community Security Audit Participation Guide")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Run interactive audit guide")
    parser.add_argument("--skill-level", choices=["Beginner", "Basic", "Intermediate", "Advanced"],
                       help="Specify skill level directly")
    parser.add_argument("--list-activities", action="store_true",
                       help="List available audit activities")
    
    args = parser.parse_args()
    
    guide = CommunityAuditGuide()
    
    if args.list_activities:
        print("Available Audit Activities by Skill Level:")
        print("=" * 50)
        
        for level in ["Beginner", "Basic", "Intermediate", "Advanced"]:
            activities = guide.recommend_audit_activities(level)
            print(f"\n{level} Level:")
            for activity in activities:
                print(f"  • {activity['name']} ({activity['difficulty']})")
                print(f"    {activity['description']}")
                print(f"    Time: {activity['time_estimate']}")
    
    elif args.interactive or not any(vars(args).values()):
        guide.run_interactive_guide()
    
    elif args.skill_level:
        activities = guide.recommend_audit_activities(args.skill_level)
        print(f"Recommended activities for {args.skill_level} level:")
        for i, activity in enumerate(activities, 1):
            print(f"{i}. {activity['name']} ({activity['time_estimate']})")
            print(f"   {activity['description']}")


if __name__ == "__main__":
    main()