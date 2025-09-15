"""
Test AppPaths functionality.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.backend.utils.app_paths import AppPaths, get_app_paths


def test_app_paths():
    """Test AppPaths functionality."""
    print("Testing AppPaths functionality...")
    
    # Test 1: Basic initialization
    print("1. Testing basic initialization...")
    app_paths = AppPaths()
    print(f"   ✓ Base path: {app_paths.base_path}")
    print(f"   ✓ Base path exists: {app_paths.base_path.exists()}")
    print(f"   ✓ Base path is absolute: {app_paths.base_path.is_absolute()}")
    
    # Test 2: Path properties
    print("2. Testing path properties...")
    print(f"   ✓ Source path: {app_paths.src_path}")
    print(f"   ✓ Backend path: {app_paths.backend_path}")
    print(f"   ✓ Frontend path: {app_paths.frontend_path}")
    print(f"   ✓ Frontend dist path: {app_paths.frontend_dist_path}")
    print(f"   ✓ Config path: {app_paths.config_path}")
    print(f"   ✓ Data path: {app_paths.data_path}")
    print(f"   ✓ Logs path: {app_paths.logs_path}")
    print(f"   ✓ Database path: {app_paths.database_path}")
    print(f"   ✓ Log file path: {app_paths.log_file_path}")
    
    # Test 3: Directory creation
    print("3. Testing directory creation...")
    app_paths.ensure_directories()
    print(f"   ✓ Data directory exists: {app_paths.data_path.exists()}")
    print(f"   ✓ Logs directory exists: {app_paths.logs_path.exists()}")
    
    # Test 4: Path resolution
    print("4. Testing path resolution...")
    relative_path = "config/app_config.py"
    resolved_path = app_paths.resolve_path(relative_path)
    print(f"   ✓ Relative path: {relative_path}")
    print(f"   ✓ Resolved path: {resolved_path}")
    print(f"   ✓ Resolved path exists: {resolved_path.exists()}")
    
    # Test 5: Safety checks
    print("5. Testing safety checks...")
    safe_path = app_paths.data_path / "test.db"
    unsafe_path = Path("/etc/passwd")
    print(f"   ✓ Safe path: {safe_path} -> {app_paths.is_safe_path(safe_path)}")
    print(f"   ✓ Unsafe path: {unsafe_path} -> {app_paths.is_safe_path(unsafe_path)}")
    
    # Test 6: File path helpers
    print("6. Testing file path helpers...")
    config_file = app_paths.get_config_file_path("app_config.py")
    data_file = app_paths.get_data_file_path("test.db")
    log_file = app_paths.get_log_file_path("test.log")
    print(f"   ✓ Config file path: {config_file}")
    print(f"   ✓ Data file path: {data_file}")
    print(f"   ✓ Log file path: {log_file}")
    
    # Test 7: Global instance
    print("7. Testing global instance...")
    global_paths = get_app_paths()
    print(f"   ✓ Global instance base path: {global_paths.base_path}")
    print(f"   ✓ Same as local instance: {global_paths.base_path == app_paths.base_path}")
    
    # Test 8: String representations
    print("8. Testing string representations...")
    print(f"   ✓ String representation: {str(app_paths)}")
    print(f"   ✓ Detailed representation:")
    print(f"     {repr(app_paths)}")
    
    print("\n✅ All AppPaths tests passed!")


if __name__ == "__main__":
    test_app_paths()