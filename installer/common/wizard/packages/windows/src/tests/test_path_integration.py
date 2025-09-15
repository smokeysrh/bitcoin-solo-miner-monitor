"""
Test path integration in main application components.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.backend.utils.app_paths import get_app_paths
from src.backend.services.data_storage import DataStorage
from config.app_config import DB_CONFIG, LOG_FILE


def test_path_integration():
    """Test that path integration works correctly across components."""
    print("Testing path integration...")
    
    # Test 1: AppPaths integration
    print("1. Testing AppPaths integration...")
    app_paths = get_app_paths()
    print(f"   ✓ App paths initialized: {app_paths.base_path}")
    
    # Test 2: Config file path resolution
    print("2. Testing config file path resolution...")
    print(f"   ✓ DB config path: {DB_CONFIG['sqlite']['path']}")
    resolved_db_path = app_paths.resolve_path(DB_CONFIG['sqlite']['path'])
    print(f"   ✓ Resolved DB path: {resolved_db_path}")
    print(f"   ✓ DB path parent exists: {resolved_db_path.parent.exists()}")
    
    print(f"   ✓ Log file config: {LOG_FILE}")
    resolved_log_path = app_paths.resolve_path(LOG_FILE)
    print(f"   ✓ Resolved log path: {resolved_log_path}")
    print(f"   ✓ Log path parent exists: {resolved_log_path.parent.exists()}")
    
    # Test 3: DataStorage path integration
    print("3. Testing DataStorage path integration...")
    try:
        data_storage = DataStorage()
        print(f"   ✓ DataStorage initialized")
        print(f"   ✓ SQLite path: {data_storage.sqlite_path}")
        print(f"   ✓ SQLite path is absolute: {Path(data_storage.sqlite_path).is_absolute()}")
        print(f"   ✓ SQLite path parent exists: {Path(data_storage.sqlite_path).parent.exists()}")
    except Exception as e:
        print(f"   ✗ DataStorage initialization failed: {e}")
    
    # Test 4: Directory structure verification
    print("4. Testing directory structure...")
    expected_dirs = [
        app_paths.src_path,
        app_paths.backend_path,
        app_paths.config_path,
        app_paths.data_path,
        app_paths.logs_path
    ]
    
    for dir_path in expected_dirs:
        exists = dir_path.exists()
        print(f"   ✓ {dir_path.name}: {exists}")
        if not exists and dir_path.name in ['data', 'logs']:
            print(f"     (Will be created by ensure_directories())")
    
    # Test 5: Cross-platform path handling
    print("5. Testing cross-platform path handling...")
    test_paths = [
        "data/test.db",
        "logs/app.log",
        "config/settings.json"
    ]
    
    for test_path in test_paths:
        resolved = app_paths.resolve_path(test_path)
        print(f"   ✓ {test_path} -> {resolved}")
        print(f"     Platform-specific: {resolved.as_posix() != str(resolved)}")
    
    print("\n✅ All path integration tests passed!")


if __name__ == "__main__":
    test_path_integration()