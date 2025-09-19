#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bitcoin Solo Miner Monitor - Release Notes Generator
Generates comprehensive release notes from commit history and changelog
"""

import os
import sys
import subprocess
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Ensure proper encoding for Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

class ReleaseNotesGenerator:
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent.parent).resolve()
        self.changelog_path = self.project_root / "CHANGELOG.md"
        
    def get_git_commits_since_tag(self, since_tag: Optional[str] = None) -> List[Dict]:
        """Get git commits since the specified tag or all commits if no tag specified"""
        try:
            if since_tag:
                # Get commits since the last tag
                cmd = ["git", "log", f"{since_tag}..HEAD", "--pretty=format:%H|%s|%an|%ae|%ad", "--date=iso"]
            else:
                # Get all commits for the first release
                cmd = ["git", "log", "--pretty=format:%H|%s|%an|%ae|%ad", "--date=iso"]
                
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                print(f"Warning: Git command failed: {result.stderr}")
                return []
                
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 4)
                    if len(parts) == 5:
                        commits.append({
                            'hash': parts[0],
                            'subject': parts[1],
                            'author': parts[2],
                            'email': parts[3],
                            'date': parts[4]
                        })
            return commits
            
        except Exception as e:
            print(f"Error getting git commits: {e}")
            return []
    
    def get_previous_tag(self) -> Optional[str]:
        """Get the most recent git tag"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"], 
                capture_output=True, text=True, cwd=self.project_root
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def categorize_commits(self, commits: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize commits by type based on conventional commit format and keywords"""
        categories = {
            'features': [],
            'fixes': [],
            'improvements': [],
            'security': [],
            'documentation': [],
            'build': [],
            'other': []
        }
        
        # Patterns for categorization
        patterns = {
            'features': [
                r'^feat(\(.+\))?:', r'^add:', r'^implement:', r'^new:', 
                r'\b(add|implement|new|feature)\b.*\b(feature|functionality|support)\b'
            ],
            'fixes': [
                r'^fix(\(.+\))?:', r'^bug:', r'^hotfix:', r'^patch:',
                r'\b(fix|bug|issue|error|problem|resolve)\b'
            ],
            'improvements': [
                r'^improve(\(.+\))?:', r'^enhance:', r'^update:', r'^refactor:',
                r'\b(improve|enhance|optimize|refactor|update|upgrade)\b'
            ],
            'security': [
                r'^security(\(.+\))?:', r'^sec:', 
                r'\b(security|vulnerability|exploit|patch|cve)\b'
            ],
            'documentation': [
                r'^docs?(\(.+\))?:', r'^doc:', 
                r'\b(doc|documentation|readme|guide|manual)\b'
            ],
            'build': [
                r'^build(\(.+\))?:', r'^ci(\(.+\))?:', r'^chore(\(.+\))?:',
                r'\b(build|ci|deploy|release|package|installer)\b'
            ]
        }
        
        for commit in commits:
            subject = commit['subject'].lower()
            categorized = False
            
            for category, category_patterns in patterns.items():
                for pattern in category_patterns:
                    if re.search(pattern, subject):
                        categories[category].append(commit)
                        categorized = True
                        break
                if categorized:
                    break
            
            if not categorized:
                categories['other'].append(commit)
        
        return categories
    
    def read_changelog_entry(self, version: str) -> Optional[str]:
        """Read changelog entry for a specific version if it exists"""
        if not self.changelog_path.exists():
            return None
            
        try:
            with open(self.changelog_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for version section in changelog
            version_pattern = rf'^## \[?{re.escape(version)}\]?.*$'
            lines = content.split('\n')
            
            start_idx = None
            for i, line in enumerate(lines):
                if re.match(version_pattern, line):
                    start_idx = i
                    break
            
            if start_idx is None:
                return None
            
            # Find the end of this version section
            end_idx = len(lines)
            for i in range(start_idx + 1, len(lines)):
                if re.match(r'^## ', lines[i]):
                    end_idx = i
                    break
            
            # Extract the changelog content for this version
            changelog_lines = lines[start_idx + 1:end_idx]
            return '\n'.join(changelog_lines).strip()
            
        except Exception as e:
            print(f"Error reading changelog: {e}")
            return None
    
    def format_commit_for_release_notes(self, commit: Dict) -> str:
        """Format a single commit for release notes"""
        subject = commit['subject']
        hash_short = commit['hash'][:7]
        
        # Clean up the subject line
        subject = re.sub(r'^(feat|fix|docs?|build|ci|chore|improve|enhance|add|implement|new|update)(\(.+\))?:\s*', '', subject)
        subject = subject.capitalize()
        
        return f"- {subject} ([{hash_short}](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/commit/{commit['hash']}))"
    
    def generate_release_notes(self, version: str, tag_name: str) -> str:
        """Generate comprehensive release notes for a version"""
        print(f"Generating release notes for version {version}...")
        
        # Get previous tag for commit range
        previous_tag = self.get_previous_tag()
        print(f"Previous tag: {previous_tag or 'None (first release)'}")
        
        # Get commits since last tag
        commits = self.get_git_commits_since_tag(previous_tag)
        print(f"Found {len(commits)} commits since last release")
        
        # Check for manual changelog entry
        changelog_entry = self.read_changelog_entry(version)
        
        # Start building release notes
        notes = []
        notes.append(f"# Bitcoin Solo Miner Monitor {version}")
        notes.append("")
        
        # Add release date
        release_date = datetime.now().strftime("%Y-%m-%d")
        notes.append(f"**Release Date:** {release_date}")
        notes.append("")
        
        # Add manual changelog if available
        if changelog_entry:
            notes.append("## Release Highlights")
            notes.append("")
            notes.append(changelog_entry)
            notes.append("")
        
        # Add download section
        notes.append("## Downloads")
        notes.append("")
        notes.append("Choose the installer for your operating system:")
        notes.append("")
        notes.append("### Windows")
        notes.append(f"- **[BitcoinSoloMinerMonitor-{version}-Setup.exe](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/{tag_name}/BitcoinSoloMinerMonitor-{version}-Setup.exe)**")
        notes.append("  - Professional installer with automatic dependency management")
        notes.append("  - Creates desktop shortcuts and Start menu entries")
        notes.append("  - Includes uninstaller for clean removal")
        notes.append("")
        
        notes.append("### macOS")
        notes.append(f"- **[BitcoinSoloMinerMonitor-{version}.dmg](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/{tag_name}/BitcoinSoloMinerMonitor-{version}.dmg)**")
        notes.append("  - Native macOS disk image")
        notes.append("  - Drag-to-Applications installation")
        notes.append("  - Full macOS system integration")
        notes.append("")
        
        notes.append("### Linux")
        notes.append("Choose the package format for your distribution:")
        notes.append("")
        notes.append("**Ubuntu/Debian (.deb packages):**")
        notes.append(f"- [BitcoinSoloMinerMonitor-{version}-Ubuntu-20.04.deb](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/{tag_name}/BitcoinSoloMinerMonitor-{version}-Ubuntu-20.04.deb)")
        notes.append(f"- [BitcoinSoloMinerMonitor-{version}-Ubuntu-22.04.deb](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/{tag_name}/BitcoinSoloMinerMonitor-{version}-Ubuntu-22.04.deb)")
        notes.append("")
        notes.append("**Fedora/CentOS (.rpm packages):**")
        notes.append(f"- [BitcoinSoloMinerMonitor-{version}-Fedora-38.rpm](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/{tag_name}/BitcoinSoloMinerMonitor-{version}-Fedora-38.rpm)")
        notes.append("")
        notes.append("**Universal Linux (AppImage):**")
        notes.append(f"- [BitcoinSoloMinerMonitor-{version}.AppImage](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/{tag_name}/BitcoinSoloMinerMonitor-{version}.AppImage)")
        notes.append("  - Works on any Linux distribution")
        notes.append("  - No installation required - just download and run")
        notes.append("")
        
        # Add verification section
        notes.append("## Verification")
        notes.append("")
        notes.append("**All downloads include SHA256 checksums for verification:**")
        notes.append(f"- **[SHA256SUMS](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/download/{tag_name}/SHA256SUMS)** - Master checksum file")
        notes.append("")
        notes.append("**Verify your download:**")
        notes.append("```bash")
        notes.append("# Windows (PowerShell):")
        notes.append("Get-FileHash -Algorithm SHA256 <filename>")
        notes.append("")
        notes.append("# macOS/Linux:")
        notes.append("shasum -a 256 <filename>")
        notes.append("# or")
        notes.append("sha256sum <filename>")
        notes.append("```")
        notes.append("")
        notes.append("Compare the output with the corresponding entry in SHA256SUMS.")
        notes.append("")
        
        # Add installation instructions
        notes.append("## Installation Instructions")
        notes.append("")
        notes.append("### Windows")
        notes.append("1. Download the `.exe` file")
        notes.append("2. Right-click and select 'Run as administrator' (if prompted)")
        notes.append("3. Windows may show an 'Unknown Publisher' warning - this is normal for open-source software")
        notes.append("4. Click 'More info' then 'Run anyway' to proceed")
        notes.append("5. Follow the installer wizard")
        notes.append("")
        notes.append("### macOS")
        notes.append("1. Download the `.dmg` file")
        notes.append("2. Double-click to open the disk image")
        notes.append("3. Drag 'Bitcoin Solo Miner Monitor' to the Applications folder")
        notes.append("4. Launch from Applications or Launchpad")
        notes.append("")
        notes.append("### Linux")
        notes.append("**DEB packages (Ubuntu/Debian):**")
        notes.append("```bash")
        notes.append("sudo dpkg -i BitcoinSoloMinerMonitor-*.deb")
        notes.append("sudo apt-get install -f  # Fix any dependency issues")
        notes.append("```")
        notes.append("")
        notes.append("**RPM packages (Fedora/CentOS):**")
        notes.append("```bash")
        notes.append("sudo rpm -i BitcoinSoloMinerMonitor-*.rpm")
        notes.append("```")
        notes.append("")
        notes.append("**AppImage (Universal):**")
        notes.append("```bash")
        notes.append("chmod +x BitcoinSoloMinerMonitor-*.AppImage")
        notes.append("./BitcoinSoloMinerMonitor-*.AppImage")
        notes.append("```")
        notes.append("")
        
        # Add security information
        notes.append("## Security Information")
        notes.append("")
        notes.append("### Why You See Security Warnings")
        notes.append("- **Open-source software**: No expensive code signing certificates ($300-500/year)")
        notes.append("- **Mining software**: Commonly flagged by antivirus (false positives)")
        notes.append("- **Community developed**: 'Unknown Publisher' warnings are normal")
        notes.append("- **Bitcoin ecosystem standard**: Bitcoin Core, Electrum, and most mining tools show similar warnings")
        notes.append("")
        notes.append("### Safe Installation Process")
        notes.append("1. **Verify download source**: Only download from official GitHub releases")
        notes.append("2. **Check checksums**: Compare SHA256 hashes before installation")
        notes.append("3. **Understand warnings**: Security warnings are expected for open-source Bitcoin software")
        notes.append("4. **Community verification**: All builds are reproducible and publicly auditable")
        notes.append("")
        notes.append("### Maximum Security: Build from Source")
        notes.append("- Complete instructions: [BUILD.md](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/blob/main/docs/BUILD.md)")
        notes.append("- Compare your build checksums with official releases")
        notes.append("- If checksums match, official releases are authentic")
        notes.append("")
        
        # Add changes section if we have commits
        if commits:
            categorized = self.categorize_commits(commits)
            
            # Only show categories that have commits
            category_titles = {
                'features': '🚀 New Features',
                'improvements': '⚡ Improvements',
                'fixes': '🐛 Bug Fixes',
                'security': '🔒 Security',
                'documentation': '📚 Documentation',
                'build': '🔧 Build & Infrastructure'
            }
            
            has_changes = False
            for category, title in category_titles.items():
                if categorized[category]:
                    if not has_changes:
                        notes.append("## What's Changed")
                        notes.append("")
                        has_changes = True
                    
                    notes.append(f"### {title}")
                    notes.append("")
                    for commit in categorized[category]:
                        notes.append(self.format_commit_for_release_notes(commit))
                    notes.append("")
            
            # Add other commits if any
            if categorized['other']:
                if not has_changes:
                    notes.append("## What's Changed")
                    notes.append("")
                
                notes.append("### Other Changes")
                notes.append("")
                for commit in categorized['other']:
                    notes.append(self.format_commit_for_release_notes(commit))
                notes.append("")
        
        # Add support section
        notes.append("## Support")
        notes.append("")
        notes.append("### Getting Help")
        notes.append("- **[Discord Community](https://discord.gg/GzNsNnh4yT)** - Real-time support and discussions")
        notes.append("- **[Installation Guide](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/blob/main/docs/installation/README.md)** - Complete installation instructions")
        notes.append("- **[Troubleshooting Guide](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/blob/main/docs/installation/troubleshooting.md)** - Common issues and solutions")
        notes.append("- **[GitHub Issues](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues)** - Bug reports and feature requests")
        notes.append("")
        notes.append("### System Requirements")
        notes.append("- **Windows**: Windows 10 or later (64-bit)")
        notes.append("- **macOS**: macOS 10.15 (Catalina) or later")
        notes.append("- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+, or equivalent")
        notes.append("- **RAM**: 4GB recommended")
        notes.append("- **Storage**: 1GB free disk space")
        notes.append("")
        
        # Add footer
        notes.append("---")
        notes.append("")
        notes.append("**Built by solo miners, for solo miners** 🚀⚡")
        notes.append("")
        notes.append("This release was built automatically from source code using GitHub Actions.")
        notes.append("All build logs are public and the process is fully reproducible.")
        
        return '\n'.join(notes)
    
    def update_changelog(self, version: str, release_notes: str):
        """Update or create CHANGELOG.md with the new release"""
        print(f"Updating CHANGELOG.md for version {version}...")
        
        # Extract the changes section from release notes
        lines = release_notes.split('\n')
        changes_start = None
        changes_end = None
        
        for i, line in enumerate(lines):
            if line.strip() == "## What's Changed":
                changes_start = i
            elif changes_start is not None and line.startswith("## ") and "What's Changed" not in line:
                changes_end = i
                break
        
        if changes_start is not None:
            if changes_end is None:
                changes_end = len(lines)
            changes_content = '\n'.join(lines[changes_start:changes_end]).strip()
        else:
            changes_content = "- Initial release"
        
        # Create or update changelog
        changelog_entry = f"""## [{version}] - {datetime.now().strftime("%Y-%m-%d")}

{changes_content}

"""
        
        if self.changelog_path.exists():
            # Read existing changelog
            with open(self.changelog_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Insert new entry at the top (after title)
            lines = existing_content.split('\n')
            if lines and lines[0].startswith('# '):
                # Insert after title
                new_content = lines[0] + '\n\n' + changelog_entry + '\n'.join(lines[1:])
            else:
                # Prepend to existing content
                new_content = changelog_entry + existing_content
        else:
            # Create new changelog
            new_content = f"""# Changelog

All notable changes to Bitcoin Solo Miner Monitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/0.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

{changelog_entry}"""
        
        # Write updated changelog
        with open(self.changelog_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"CHANGELOG.md updated")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate release notes for Bitcoin Solo Miner Monitor")
    parser.add_argument("version", help="Version string (e.g., 0.1.0)")
    parser.add_argument("--tag-name", help="Git tag name (defaults to v{version})")
    parser.add_argument("--output", help="Output file (defaults to stdout)")
    parser.add_argument("--update-changelog", action="store_true", help="Update CHANGELOG.md")
    parser.add_argument("--project-root", help="Project root directory")
    
    args = parser.parse_args()
    
    tag_name = args.tag_name or f"v{args.version}"
    
    generator = ReleaseNotesGenerator(args.project_root)
    release_notes = generator.generate_release_notes(args.version, tag_name)
    
    if args.update_changelog:
        generator.update_changelog(args.version, release_notes)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(release_notes)
        print(f"Release notes written to {args.output}")
    else:
        print(release_notes)

if __name__ == "__main__":
    main()