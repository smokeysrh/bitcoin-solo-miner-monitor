#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bitcoin Solo Miner Monitor - Release Creator
Orchestrates the complete release process including GitHub release creation
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure proper encoding for Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

class ReleaseCreator:
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent.parent).resolve()
        self.scripts_dir = self.project_root / "scripts" / "release"
        
    def run_command(self, cmd: list, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
        """Run a command and return the result"""
        cwd = cwd or self.project_root
        print(f"Running: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
    
    def check_git_status(self) -> bool:
        """Check if git working directory is clean"""
        try:
            result = self.run_command(["git", "status", "--porcelain"])
            if result.stdout.strip():
                print(" Git working directory is not clean. Please commit or stash changes.")
                print("Uncommitted changes:")
                print(result.stdout)
                return False
            return True
        except subprocess.CalledProcessError:
            print(" Failed to check git status")
            return False
    
    def create_git_tag(self, version: str, tag_name: str) -> bool:
        """Create and push a git tag"""
        try:
            # Create the tag
            print(f"Creating git tag {tag_name}...")
            self.run_command(["git", "tag", "-a", tag_name, "-m", f"Release version {version}"])
            
            # Push the tag
            print(f"Pushing tag {tag_name}...")
            self.run_command(["git", "push", "origin", tag_name])
            
            print(f" Git tag {tag_name} created and pushed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f" Failed to create/push git tag: {e}")
            return False
    
    def generate_release_notes(self, version: str, tag_name: str) -> str:
        """Generate release notes using the release notes generator"""
        try:
            print("Generating release notes...")
            
            # Run the release notes generator
            generator_script = self.scripts_dir / "generate-release-notes.py"
            result = self.run_command([
                sys.executable, str(generator_script),
                version,
                "--tag-name", tag_name,
                "--update-changelog"
            ])
            
            release_notes = result.stdout
            print(" Release notes generated")
            return release_notes
            
        except subprocess.CalledProcessError as e:
            print(f" Failed to generate release notes: {e}")
            print(f"Error output: {e.stderr}")
            return ""
    
    def update_documentation(self, version: str, tag_name: str) -> bool:
        """Update documentation with new version information"""
        try:
            print("Updating documentation...")
            
            # Run the documentation updater
            updater_script = self.scripts_dir / "update-documentation.py"
            self.run_command([
                sys.executable, str(updater_script),
                version,
                "--tag-name", tag_name
            ])
            
            print(" Documentation updated")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f" Failed to update documentation: {e}")
            print(f"Error output: {e.stderr}")
            return False
    
    def commit_documentation_changes(self, version: str) -> bool:
        """Commit documentation changes"""
        try:
            print("Committing documentation changes...")
            
            # Add all documentation changes
            self.run_command(["git", "add", "docs/", "CHANGELOG.md", "README.md"])
            
            # Check if there are changes to commit
            result = self.run_command(["git", "status", "--porcelain"], check=False)
            if not result.stdout.strip():
                print("No documentation changes to commit")
                return True
            
            # Commit the changes
            commit_message = f"docs: update documentation for release v{version}\n\n- Update download links and version references\n- Update installation guides\n- Update CHANGELOG.md\n- Create/update download page"
            self.run_command(["git", "commit", "-m", commit_message])
            
            # Push the changes
            self.run_command(["git", "push", "origin", "main"])
            
            print(" Documentation changes committed and pushed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f" Failed to commit documentation changes: {e}")
            return False
    
    def wait_for_build_completion(self, tag_name: str) -> bool:
        """Wait for GitHub Actions build to complete"""
        print(f"Waiting for GitHub Actions build to complete for tag {tag_name}...")
        print("This may take 15-30 minutes depending on the build complexity.")
        print("You can monitor the build progress at:")
        print(f"https://github.com/smokeysrh/bitcoin-solo-miner-monitor/actions")
        
        # For now, we'll just inform the user to wait
        # In a production environment, you might want to poll the GitHub API
        input("\nPress Enter once the build has completed successfully...")
        return True
    
    def create_github_release(self, version: str, tag_name: str, release_notes: str) -> bool:
        """Create GitHub release (this will be handled by GitHub Actions)"""
        print(f"GitHub release will be created automatically by GitHub Actions for tag {tag_name}")
        print("The release will include:")
        print("- All platform installers (Windows .exe, macOS .dmg, Linux packages)")
        print("- SHA256 checksums for verification")
        print("- Comprehensive release notes")
        print("- Installation instructions")
        
        return True
    
    def create_release(self, version: str, tag_name: Optional[str] = None, skip_build_wait: bool = False) -> bool:
        """Create a complete release"""
        tag_name = tag_name or f"v{version}"
        
        print(f" Creating release for Bitcoin Solo Miner Monitor v{version}")
        print(f"Tag: {tag_name}")
        print("=" * 60)
        
        # Step 1: Check git status
        print("\n Step 1: Checking git status...")
        if not self.check_git_status():
            return False
        
        # Step 2: Generate release notes
        print("\n Step 2: Generating release notes...")
        release_notes = self.generate_release_notes(version, tag_name)
        if not release_notes:
            print(" Failed to generate release notes")
            return False
        
        # Step 3: Update documentation
        print("\n Step 3: Updating documentation...")
        if not self.update_documentation(version, tag_name):
            return False
        
        # Step 4: Commit documentation changes
        print("\n Step 4: Committing documentation changes...")
        if not self.commit_documentation_changes(version):
            return False
        
        # Step 5: Create and push git tag
        print("\n  Step 5: Creating git tag...")
        if not self.create_git_tag(version, tag_name):
            return False
        
        # Step 6: Wait for build completion (unless skipped)
        if not skip_build_wait:
            print("\n Step 6: Waiting for build completion...")
            if not self.wait_for_build_completion(tag_name):
                return False
        else:
            print("\n  Step 6: Skipping build wait (as requested)")
        
        # Step 7: GitHub release creation (handled by GitHub Actions)
        print("\n Step 7: GitHub release creation...")
        if not self.create_github_release(version, tag_name, release_notes):
            return False
        
        print("\n" + "=" * 60)
        print(f" Release v{version} created successfully!")
        print("\nNext steps:")
        print(f"1. Monitor the build at: https://github.com/smokeysrh/bitcoin-solo-miner-monitor/actions")
        print(f"2. Once complete, check the release at: https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/{tag_name}")
        print(f"3. Test the installers on different platforms")
        print(f"4. Announce the release to the community")
        print(f"5. Update any external documentation or websites")
        
        return True
    
    def dry_run(self, version: str, tag_name: Optional[str] = None) -> bool:
        """Perform a dry run of the release process"""
        tag_name = tag_name or f"v{version}"
        
        print(f" DRY RUN: Release process for Bitcoin Solo Miner Monitor v{version}")
        print(f"Tag: {tag_name}")
        print("=" * 60)
        
        print("\n Would check git status...")
        print(" Git status check (simulated)")
        
        print("\n Would generate release notes...")
        try:
            generator_script = self.scripts_dir / "generate-release-notes.py"
            result = self.run_command([
                sys.executable, str(generator_script),
                version,
                "--tag-name", tag_name
            ])
            print(" Release notes generation (simulated)")
            print("Preview of release notes:")
            print("-" * 40)
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            print("-" * 40)
        except Exception as e:
            print(f" Release notes generation failed: {e}")
            return False
        
        print("\n Would update documentation...")
        print(" Documentation update (simulated)")
        
        print("\n Would commit documentation changes...")
        print(" Documentation commit (simulated)")
        
        print("\n  Would create git tag...")
        print(f" Git tag creation (simulated): {tag_name}")
        
        print("\n Would wait for build completion...")
        print(" Build wait (simulated)")
        
        print("\n Would create GitHub release...")
        print(" GitHub release creation (simulated)")
        
        print("\n" + "=" * 60)
        print(f" DRY RUN completed successfully for v{version}!")
        print("\nTo perform the actual release, run without --dry-run")
        
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a release for Bitcoin Solo Miner Monitor")
    parser.add_argument("version", help="Version string (e.g., 0.1.0)")
    parser.add_argument("--tag-name", help="Git tag name (defaults to v{version})")
    parser.add_argument("--skip-build-wait", action="store_true", help="Skip waiting for build completion")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    parser.add_argument("--project-root", help="Project root directory")
    
    args = parser.parse_args()
    
    creator = ReleaseCreator(args.project_root)
    
    if args.dry_run:
        success = creator.dry_run(args.version, args.tag_name)
    else:
        success = creator.create_release(args.version, args.tag_name, args.skip_build_wait)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()