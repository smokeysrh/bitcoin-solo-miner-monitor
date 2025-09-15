#!/usr/bin/env python3
"""
Test script to check static file serving
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.backend.utils.app_paths import get_app_paths

def test_static_files():
    """Test if static files exist and paths are correct"""
    app_paths = get_app_paths()
    
    print(f"Base path: {app_paths.base_path}")
    print(f"Frontend path: {app_paths.frontend_path}")
    print(f"Frontend dist path: {app_paths.frontend_dist_path}")
    
    print(f"\nDist directory exists: {app_paths.frontend_dist_path.exists()}")
    
    if app_paths.frontend_dist_path.exists():
        print("Contents of dist directory:")
        for item in app_paths.frontend_dist_path.iterdir():
            print(f"  {item.name}")
        
        index_html = app_paths.frontend_dist_path / "index.html"
        print(f"\nindex.html exists: {index_html.exists()}")
        
        if index_html.exists():
            print(f"index.html size: {index_html.stat().st_size} bytes")
    
    return True

if __name__ == "__main__":
    test_static_files()