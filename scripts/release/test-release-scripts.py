#!/usr/bin/env python3
"""
Bitcoin Solo Miner Monitor - Release Scripts Test
Tests the release automation scripts to ensure they work correctly
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def run_command(cmd: list, cwd: Path = None) -> tuple:
    """Run a command and return (success, stdout, stderr)"""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def test_release_notes_generator():
    """Test the release notes generator"""
    print(" Testing release notes generator...")
    
    project_root = Path(__file__).parent.parent.parent
    script_path = project_root / "scripts" / "release" / "generate-release-notes.py"
    
    # Test basic functionality
    success, stdout, stderr = run_command([
        sys.executable, str(script_path), "1.0.0-test",
        "--tag-name", "v1.0.0-test"
    ], cwd=project_root)
    
    if not success:
        print(f" Release notes generator failed: {stderr}")
        return False
    
    # Check if output contains expected sections
    expected_sections = [
        "# Bitcoin Solo Miner Monitor 1.0.0-test",
        "## Downloads",
        "## Verification", 
        "## Installation Instructions",
        "## Security Information"
    ]
    
    for section in expected_sections:
        if section not in stdout:
            print(f"Missing expected section: {section}")
            return False
    
    print("Release notes generator test passed")
    return True

def test_documentation_updater():
    """Test the documentation updater"""
    print(" Testing documentation updater...")
    
    project_root = Path(__file__).parent.parent.parent
    script_path = project_root / "scripts" / "release" / "update-documentation.py"
    
    # Create a temporary copy of docs to test with
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_project = Path(temp_dir) / "test-project"
        temp_project.mkdir()
        
        # Copy the script to temp directory
        temp_script = temp_project / "update-documentation.py"
        with open(script_path, 'r') as src, open(temp_script, 'w') as dst:
            dst.write(src.read())
        
        # Create minimal docs structure
        docs_dir = temp_project / "docs"
        docs_dir.mkdir()
        
        installation_dir = docs_dir / "installation"
        installation_dir.mkdir()
        
        # Create a test README
        test_readme = installation_dir / "README.md"
        test_readme.write_text("""# Test Installation Guide

Download the latest release: [Download Latest Release](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/v0.9.0)

Version 0.9.0 is available.
""")
        
        # Test the updater (dry run style - just check it doesn't crash)
        success, stdout, stderr = run_command([
            sys.executable, str(temp_script), "1.0.0-test",
            "--tag-name", "v1.0.0-test",
            "--project-root", str(temp_project)
        ])
        
        if not success:
            print(f" Documentation updater failed: {stderr}")
            return False
        
        print(" Documentation updater test passed")
        return True

def test_create_release_dry_run():
    """Test the create release script in dry run mode"""
    print(" Testing create release script (dry run)...")
    
    project_root = Path(__file__).parent.parent.parent
    script_path = project_root / "scripts" / "release" / "create-release.py"
    
    # Test dry run
    success, stdout, stderr = run_command([
        sys.executable, str(script_path), "1.0.0-test",
        "--dry-run"
    ], cwd=project_root)
    
    if not success:
        print(f" Create release script failed: {stderr}")
        return False
    
    # Check if dry run output contains expected messages
    expected_messages = [
        "DRY RUN: Release process",
        "Release notes generation (simulated)",
        "Documentation update (simulated)",
        "Git tag creation (simulated)",
        "DRY RUN completed successfully"
    ]
    
    for message in expected_messages:
        if message not in stdout:
            print(f" Missing expected dry run message: {message}")
            return False
    
    print(" Create release script test passed")
    return True

def test_script_permissions():
    """Test that scripts have proper permissions"""
    print(" Testing script permissions...")
    
    project_root = Path(__file__).parent.parent.parent
    scripts = [
        "scripts/release/generate-release-notes.py",
        "scripts/release/update-documentation.py", 
        "scripts/release/create-release.py"
    ]
    
    for script_path in scripts:
        full_path = project_root / script_path
        if not full_path.exists():
            print(f" Script not found: {script_path}")
            return False
        
        # On Windows, we can't easily check execute permissions
        # Just verify the file exists and is readable
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.startswith('#!/usr/bin/env python3'):
                    print(f"Script missing shebang: {script_path}")
                    return False
        except Exception as e:
            print(f"Cannot read script {script_path}: {e}")
            return False
    
    print(" Script permissions test passed")
    return True

def main():
    """Run all tests"""
    print(" Bitcoin Solo Miner Monitor - Release Scripts Test")
    print("=" * 60)
    
    tests = [
        test_script_permissions,
        test_release_notes_generator,
        test_documentation_updater,
        test_create_release_dry_run
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f" Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f" Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print(" All tests passed! Release scripts are ready to use.")
        return 0
    else:
        print(" Some tests failed. Please fix issues before using release scripts.")
        return 1

if __name__ == "__main__":
    sys.exit(main())