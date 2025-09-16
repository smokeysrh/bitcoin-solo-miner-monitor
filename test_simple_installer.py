#!/usr/bin/env python3
"""
Simple test to create a minimal Windows installer
"""

import tempfile
import subprocess
from pathlib import Path

# Create a simple test app directory
with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    app_dir = temp_path / "app"
    app_dir.mkdir()
    
    # Create minimal test files
    (app_dir / "run.py").write_text("print('Hello World')")
    (app_dir / "README.txt").write_text("Test application")
    
    print(f"Created test app in: {app_dir}")
    print("Files:")
    for file in app_dir.rglob("*"):
        print(f"  {file}")
    
    # Try to run NSIS with minimal parameters
    nsis_cmd = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        f"/DVERSION=test",
        f"/DAPP_DIR={app_dir}",
        f"/DOUTPUT_FILE=test-installer.exe",
        "installer/windows/installer.nsi"
    ]
    
    print(f"Running: {' '.join(nsis_cmd)}")
    
    try:
        result = subprocess.run(nsis_cmd, capture_output=True, text=True, timeout=60)
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print("NSIS compilation timed out!")
    except Exception as e:
        print(f"Error: {e}")