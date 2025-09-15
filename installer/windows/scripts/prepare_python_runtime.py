#!/usr/bin/env python3
"""
Python Runtime Preparation Script for Bitcoin Solo Miner Monitor
This script downloads and prepares the Python embeddable package for bundling
"""

import os
import sys
import urllib.request
import zipfile
import shutil
import subprocess
import tempfile
from pathlib import Path

# Configuration
PYTHON_VERSION = "3.11.7"
PYTHON_ARCH = "amd64"
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-{PYTHON_ARCH}.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

class PythonRuntimePreparer:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.python_dir = self.output_dir / "python"
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up temporary directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def download_file(self, url, destination):
        """Download a file with progress indication"""
        print(f"Downloading {url}...")
        
        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, (block_num * block_size * 100) // total_size)
                print(f"\rProgress: {percent}%", end="", flush=True)
        
        urllib.request.urlretrieve(url, destination, progress_hook)
        print()  # New line after progress
        
    def download_python_runtime(self):
        """Download Python embeddable package"""
        print(f"Downloading Python {PYTHON_VERSION} embeddable package...")
        
        python_zip = self.temp_dir / f"python-{PYTHON_VERSION}-embed-{PYTHON_ARCH}.zip"
        self.download_file(PYTHON_URL, python_zip)
        
        return python_zip
    
    def extract_python_runtime(self, python_zip):
        """Extract Python embeddable package"""
        print("Extracting Python runtime...")
        
        # Create python directory
        self.python_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract Python
        with zipfile.ZipFile(python_zip, 'r') as zip_ref:
            zip_ref.extractall(self.python_dir)
        
        print(f"Python runtime extracted to {self.python_dir}")
    
    def configure_python_path(self):
        """Configure Python path for embedded environment"""
        print("Configuring Python path...")
        
        # Create or modify python311._pth file
        pth_file = self.python_dir / "python311._pth"
        
        pth_content = [
            "python311.zip",
            ".",
            "Lib\\site-packages",
            "",
            "# Enable site module for pip functionality",
            "import site"
        ]
        
        with open(pth_file, 'w') as f:
            f.write('\n'.join(pth_content))
        
        print("Python path configured")
    
    def install_pip(self):
        """Install pip in the embedded Python environment"""
        print("Installing pip...")
        
        # Download get-pip.py
        get_pip_script = self.temp_dir / "get-pip.py"
        self.download_file(GET_PIP_URL, get_pip_script)
        
        # Create site-packages directory
        site_packages = self.python_dir / "Lib" / "site-packages"
        site_packages.mkdir(parents=True, exist_ok=True)
        
        # Install pip
        python_exe = self.python_dir / "python.exe"
        cmd = [
            str(python_exe),
            str(get_pip_script),
            "--target", str(site_packages),
            "--no-warn-script-location"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error installing pip: {result.stderr}")
            raise RuntimeError("Failed to install pip")
        
        print("Pip installed successfully")
    
    def install_dependencies(self, requirements_file):
        """Install Python dependencies from requirements.txt"""
        print("Installing Python dependencies...")
        
        if not Path(requirements_file).exists():
            print(f"Requirements file not found: {requirements_file}")
            return
        
        python_exe = self.python_dir / "python.exe"
        site_packages = self.python_dir / "Lib" / "site-packages"
        
        cmd = [
            str(python_exe),
            "-m", "pip", "install",
            "-r", str(requirements_file),
            "--target", str(site_packages),
            "--no-warn-script-location",
            "--no-deps"  # Install without dependencies first
        ]
        
        # First pass: install without dependencies
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Warning: Some packages failed to install without dependencies")
            print(result.stderr)
        
        # Second pass: install with dependencies
        cmd_with_deps = cmd[:-1]  # Remove --no-deps
        result = subprocess.run(cmd_with_deps, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error installing dependencies: {result.stderr}")
            raise RuntimeError("Failed to install dependencies")
        
        print("Dependencies installed successfully")
    
    def create_launcher_scripts(self):
        """Create launcher scripts for the application"""
        print("Creating launcher scripts...")
        
        # Create batch launcher
        launcher_bat = self.output_dir / "launch.bat"
        launcher_content = [
            "@echo off",
            "cd /d %~dp0",
            "set PYTHONPATH=%~dp0python;%~dp0python\\Lib\\site-packages",
            "python\\python.exe run.py",
            "pause"
        ]
        
        with open(launcher_bat, 'w') as f:
            f.write('\n'.join(launcher_content))
        
        # Create silent launcher
        silent_launcher = self.output_dir / "BitcoinSoloMinerMonitor.bat"
        silent_content = [
            "@echo off",
            "cd /d %~dp0",
            "set PYTHONPATH=%~dp0python;%~dp0python\\Lib\\site-packages",
            "start /min python\\python.exe run.py"
        ]
        
        with open(silent_launcher, 'w') as f:
            f.write('\n'.join(silent_content))
        
        print("Launcher scripts created")
    
    def verify_installation(self):
        """Verify the Python installation works correctly"""
        print("Verifying Python installation...")
        
        python_exe = self.python_dir / "python.exe"
        
        # Test Python execution
        result = subprocess.run([str(python_exe), "--version"], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError("Python installation verification failed")
        
        print(f"Python version: {result.stdout.strip()}")
        
        # Test pip
        result = subprocess.run([str(python_exe), "-m", "pip", "--version"], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Warning: Pip verification failed")
        else:
            print(f"Pip version: {result.stdout.strip()}")
        
        # Test basic imports
        test_imports = [
            "import sys",
            "import os", 
            "import json",
            "print('Basic imports successful')"
        ]
        
        test_script = "; ".join(test_imports)
        result = subprocess.run([str(python_exe), "-c", test_script], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Warning: Basic import test failed: {result.stderr}")
        else:
            print("Basic imports verified")
        
        print("Python installation verification complete")
    
    def prepare_runtime(self, requirements_file=None):
        """Main method to prepare the complete Python runtime"""
        print("=== Python Runtime Preparation ===")
        
        try:
            # Download and extract Python
            python_zip = self.download_python_runtime()
            self.extract_python_runtime(python_zip)
            
            # Configure Python environment
            self.configure_python_path()
            
            # Install pip
            self.install_pip()
            
            # Install dependencies if provided
            if requirements_file:
                self.install_dependencies(requirements_file)
            
            # Create launcher scripts
            self.create_launcher_scripts()
            
            # Verify installation
            self.verify_installation()
            
            print("\n=== Python Runtime Preparation Complete ===")
            print(f"Runtime location: {self.python_dir}")
            print(f"Launcher scripts: {self.output_dir}")
            
            return True
            
        except Exception as e:
            print(f"\nError preparing Python runtime: {e}")
            return False

def main():
    if len(sys.argv) < 2:
        print("Usage: prepare_python_runtime.py <output_directory> [requirements_file]")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    requirements_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    with PythonRuntimePreparer(output_dir) as preparer:
        success = preparer.prepare_runtime(requirements_file)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()