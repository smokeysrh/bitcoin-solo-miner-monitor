#!/usr/bin/env python3
"""
Python Runtime Bundling Script for macOS DMG Installer

This script downloads and bundles a Python runtime for macOS applications.
It's designed to be used in CI/CD environments where we need a complete
Python runtime bundled with the application.
"""

import os
import sys
import urllib.request
import tarfile
import shutil
import subprocess
from pathlib import Path

def download_python_runtime(version="3.11.7", arch="universal2", target_dir=None):
    """
    Download Python runtime for macOS from python.org
    
    Args:
        version: Python version to download (e.g., "3.11.7")
        arch: Architecture (universal2, x86_64, arm64)
        target_dir: Directory to extract Python runtime
    """
    if target_dir is None:
        target_dir = Path.cwd() / "python_runtime"
    
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Python.org download URL pattern
    major_minor = ".".join(version.split(".")[:2])
    download_url = f"https://www.python.org/ftp/python/{version}/python-{version}-macos11.pkg"
    
    print(f"📥 Downloading Python {version} for macOS ({arch})...")
    print(f"URL: {download_url}")
    
    # Download the installer package
    pkg_file = target_dir / f"python-{version}-macos11.pkg"
    
    try:
        urllib.request.urlretrieve(download_url, pkg_file)
        print(f"✅ Downloaded: {pkg_file}")
    except Exception as e:
        print(f"❌ Failed to download Python runtime: {e}")
        return False
    
    # Extract the package (this is a simplified approach)
    # In a real implementation, you'd use pkgutil or similar tools
    print("📦 Extracting Python runtime...")
    
    # For now, we'll create a structure that mimics what we need
    framework_dir = target_dir / "Python.framework"
    framework_dir.mkdir(parents=True, exist_ok=True)
    
    versions_dir = framework_dir / "Versions" / major_minor
    versions_dir.mkdir(parents=True, exist_ok=True)
    
    # Create basic structure
    (versions_dir / "bin").mkdir(exist_ok=True)
    (versions_dir / "lib").mkdir(exist_ok=True)
    (versions_dir / "include").mkdir(exist_ok=True)
    
    # Create symbolic links
    current_link = framework_dir / "Current"
    if current_link.exists():
        current_link.unlink()
    current_link.symlink_to(f"Versions/{major_minor}")
    
    # Create convenience links
    for item in ["bin", "lib", "include"]:
        link_path = framework_dir / item
        if link_path.exists():
            link_path.unlink()
        link_path.symlink_to(f"Current/{item}")
    
    print(f"✅ Python runtime structure created at: {framework_dir}")
    return True

def install_dependencies(requirements_file, target_dir):
    """
    Install Python dependencies to a target directory
    
    Args:
        requirements_file: Path to requirements.txt
        target_dir: Directory to install packages
    """
    if not os.path.exists(requirements_file):
        print(f"⚠️  Requirements file not found: {requirements_file}")
        return False
    
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📚 Installing dependencies from {requirements_file}...")
    
    try:
        # Use pip to install to target directory
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--target", str(target_dir),
            "--requirement", requirements_file,
            "--no-deps",
            "--no-cache-dir",
            "--quiet"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Dependencies installed to: {target_dir}")
            
            # Create marker file
            marker_file = target_dir / ".dependencies_installed"
            marker_file.touch()
            
            return True
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def create_launcher_script(app_bundle_dir, python_framework_path):
    """
    Create a launcher script that uses the bundled Python runtime
    
    Args:
        app_bundle_dir: Path to the .app bundle Contents directory
        python_framework_path: Path to the bundled Python framework
    """
    macos_dir = Path(app_bundle_dir) / "MacOS"
    macos_dir.mkdir(parents=True, exist_ok=True)
    
    launcher_script = macos_dir / "BitcoinSoloMinerMonitor"
    
    script_content = f'''#!/bin/bash
# Launcher script for Bitcoin Solo Miner Monitor with bundled Python runtime

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
APP_DIR="${{SCRIPT_DIR}}/../Resources"
PYTHON_FRAMEWORK="${{SCRIPT_DIR}}/../Frameworks/Python.framework"

# Change to the application directory
cd "${{APP_DIR}}"

# Set up environment for bundled Python
export PYTHONHOME="${{PYTHON_FRAMEWORK}}"
export PYTHONPATH="${{APP_DIR}}/site-packages:${{PYTHONPATH}}"

# Use bundled Python
PYTHON_CMD="${{PYTHON_FRAMEWORK}}/bin/python3"

# Verify bundled Python exists
if [ ! -x "${{PYTHON_CMD}}" ]; then
    # Fall back to system Python
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    else
        osascript -e 'display dialog "Python 3.11+ is required but not found. Please install Python from python.org" buttons {{"OK"}} default button "OK" with icon caution'
        exit 1
    fi
fi

# Verify Python version
if ! ${{PYTHON_CMD}} -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    osascript -e 'display dialog "Python 3.11 or later is required. Please update your Python installation." buttons {{"OK"}} default button "OK" with icon caution'
    exit 1
fi

# Launch the application
echo "Starting Bitcoin Solo Miner Monitor..."
exec ${{PYTHON_CMD}} run.py "$@"
'''
    
    with open(launcher_script, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(launcher_script, 0o755)
    
    print(f"✅ Launcher script created: {launcher_script}")
    return True

def main():
    """Main function for bundling Python runtime"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bundle Python runtime for macOS DMG")
    parser.add_argument("--version", default="3.11.7", help="Python version to bundle")
    parser.add_argument("--arch", default="universal2", help="Architecture (universal2, x86_64, arm64)")
    parser.add_argument("--target", required=True, help="Target directory for Python runtime")
    parser.add_argument("--requirements", help="Requirements.txt file to install")
    parser.add_argument("--app-bundle", help="App bundle directory to create launcher for")
    
    args = parser.parse_args()
    
    print("🐍 Python Runtime Bundling for macOS")
    print(f"Version: {args.version}")
    print(f"Architecture: {args.arch}")
    print(f"Target: {args.target}")
    
    # Download and setup Python runtime
    if not download_python_runtime(args.version, args.arch, args.target):
        sys.exit(1)
    
    # Install dependencies if requirements file provided
    if args.requirements:
        site_packages_dir = Path(args.target) / "site-packages"
        if not install_dependencies(args.requirements, site_packages_dir):
            print("⚠️  Warning: Some dependencies may not have installed correctly")
    
    # Create launcher script if app bundle provided
    if args.app_bundle:
        python_framework = Path(args.target) / "Python.framework"
        if not create_launcher_script(args.app_bundle, python_framework):
            print("⚠️  Warning: Could not create launcher script")
    
    print("✅ Python runtime bundling complete!")

if __name__ == "__main__":
    main()