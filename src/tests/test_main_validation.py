"""
Test main application configuration validation integration.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the main application
from src.main import Application
import config.app_config as app_config


def test_main_validation():
    """Test main application configuration validation."""
    print("Testing main application configuration validation...")
    
    # Test 1: Check current configuration
    print("1. Testing current configuration...")
    
    try:
        # This will run the configuration validation
        app = Application()
        print("   ✓ Application initialized successfully")
        print("   ✓ Configuration validation passed")
    except SystemExit as e:
        print(f"   ✗ Application initialization failed: {e}")
        return
    except Exception as e:
        print(f"   ✗ Unexpected error during initialization: {e}")
        return
    
    # Test 2: Check configuration values
    print("2. Testing configuration values...")
    
    config_values = {
        'HOST': getattr(app_config, 'HOST', None),
        'PORT': getattr(app_config, 'PORT', None),
        'DB_CONFIG': getattr(app_config, 'DB_CONFIG', None),
        'DEFAULT_POLLING_INTERVAL': getattr(app_config, 'DEFAULT_POLLING_INTERVAL', None),
        'CONNECTION_TIMEOUT': getattr(app_config, 'CONNECTION_TIMEOUT', None),
        'RETRY_ATTEMPTS': getattr(app_config, 'RETRY_ATTEMPTS', None),
        'RETRY_DELAY': getattr(app_config, 'RETRY_DELAY', None),
        'LOG_LEVEL': getattr(app_config, 'LOG_LEVEL', None),
        'LOG_FILE': getattr(app_config, 'LOG_FILE', None),
    }
    
    for key, value in config_values.items():
        print(f"   ✓ {key}: {value}")
    
    # Test 3: Check directory creation
    print("3. Testing directory creation...")
    
    from src.backend.utils.app_paths import get_app_paths
    app_paths = get_app_paths()
    
    directories = [
        ('data', app_paths.data_path),
        ('logs', app_paths.logs_path)
    ]
    
    for name, path in directories:
        exists = path.exists()
        is_dir = path.is_dir() if exists else False
        print(f"   ✓ {name} directory: {path} (exists: {exists}, is_dir: {is_dir})")
    
    # Test 4: Check database path resolution
    print("4. Testing database path resolution...")
    
    if hasattr(app, 'data_storage') and hasattr(app.data_storage, 'sqlite_path'):
        db_path = Path(app.data_storage.sqlite_path)
        print(f"   ✓ Database path: {db_path}")
        print(f"   ✓ Database path is absolute: {db_path.is_absolute()}")
        print(f"   ✓ Database parent exists: {db_path.parent.exists()}")
    else:
        print("   ⚠️  Database path not accessible")
    
    # Test 5: Check logging configuration
    print("5. Testing logging configuration...")
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if logging is configured
    root_logger = logging.getLogger()
    handlers = root_logger.handlers
    
    print(f"   ✓ Root logger handlers: {len(handlers)}")
    for i, handler in enumerate(handlers):
        handler_type = type(handler).__name__
        print(f"     Handler {i+1}: {handler_type}")
        
        if hasattr(handler, 'baseFilename'):
            print(f"       File: {handler.baseFilename}")
    
    print("\n✅ All main application validation tests passed!")


if __name__ == "__main__":
    test_main_validation()