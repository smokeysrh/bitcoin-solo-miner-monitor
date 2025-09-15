"""
Test configuration validation integration.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.backend.utils.config_validator import ConfigValidator
from src.backend.utils.app_paths import get_app_paths
import config.app_config as app_config


def test_config_integration():
    """Test configuration validation integration with actual config."""
    print("Testing configuration validation integration...")
    
    # Test 1: Validate actual application configuration
    print("1. Testing actual application configuration...")
    
    # Create configuration dictionary from app_config module
    config = {
        'HOST': getattr(app_config, 'HOST', None),
        'PORT': getattr(app_config, 'PORT', None),
        'DB_CONFIG': getattr(app_config, 'DB_CONFIG', None),
        'DEFAULT_POLLING_INTERVAL': getattr(app_config, 'DEFAULT_POLLING_INTERVAL', None),
        'CONNECTION_TIMEOUT': getattr(app_config, 'CONNECTION_TIMEOUT', None),
        'RETRY_ATTEMPTS': getattr(app_config, 'RETRY_ATTEMPTS', None),
        'RETRY_DELAY': getattr(app_config, 'RETRY_DELAY', None),
        'LOG_LEVEL': getattr(app_config, 'LOG_LEVEL', None),
        'LOG_FILE': getattr(app_config, 'LOG_FILE', None),
        'THEME': getattr(app_config, 'THEME', None),
        'CHART_RETENTION_DAYS': getattr(app_config, 'CHART_RETENTION_DAYS', None),
        'DEFAULT_REFRESH_INTERVAL': getattr(app_config, 'DEFAULT_REFRESH_INTERVAL', None),
    }
    
    print("   Configuration values:")
    for key, value in config.items():
        print(f"     {key}: {value}")
    
    # Validate configuration
    validator = ConfigValidator()
    result = validator.validate_all(config)
    
    print(f"\n   ✓ Configuration valid: {result.is_valid}")
    print(f"   ✓ Errors: {len(result.errors)}")
    print(f"   ✓ Warnings: {len(result.warnings)}")
    
    if result.errors:
        print("   Configuration errors:")
        for error in result.errors:
            print(f"     ERROR: {error}")
    
    if result.warnings:
        print("   Configuration warnings:")
        for warning in result.warnings:
            print(f"     WARNING: {warning}")
    
    # Test 2: Validate startup requirements
    print("\n2. Testing startup requirements...")
    
    startup_result = validator.validate_startup_requirements()
    
    print(f"   ✓ Startup requirements valid: {startup_result.is_valid}")
    print(f"   ✓ Errors: {len(startup_result.errors)}")
    print(f"   ✓ Warnings: {len(startup_result.warnings)}")
    
    if startup_result.errors:
        print("   Startup errors:")
        for error in startup_result.errors:
            print(f"     ERROR: {error}")
    
    if startup_result.warnings:
        print("   Startup warnings:")
        for warning in startup_result.warnings:
            print(f"     WARNING: {warning}")
    
    # Test 3: Check path resolution
    print("\n3. Testing path resolution...")
    
    app_paths = get_app_paths()
    
    # Test database path resolution
    db_path_config = config.get('DB_CONFIG', {}).get('sqlite', {}).get('path')
    if db_path_config:
        resolved_db_path = app_paths.resolve_path(db_path_config)
        print(f"   ✓ DB path config: {db_path_config}")
        print(f"   ✓ DB path resolved: {resolved_db_path}")
        print(f"   ✓ DB path is safe: {app_paths.is_safe_path(resolved_db_path)}")
        print(f"   ✓ DB path parent exists: {resolved_db_path.parent.exists()}")
    
    # Test log file path resolution
    log_file_config = config.get('LOG_FILE')
    if log_file_config:
        resolved_log_path = app_paths.resolve_path(log_file_config)
        print(f"   ✓ Log file config: {log_file_config}")
        print(f"   ✓ Log file resolved: {resolved_log_path}")
        print(f"   ✓ Log file is safe: {app_paths.is_safe_path(resolved_log_path)}")
        print(f"   ✓ Log file parent exists: {resolved_log_path.parent.exists()}")
    
    # Test 4: Configuration summary
    print("\n4. Testing configuration summary...")
    
    summary = validator.get_configuration_summary(config)
    
    print("   Configuration summary:")
    print(f"     Server: {summary['server']['host']}:{summary['server']['port']}")
    print(f"     Database: {summary['database']['type']} at {summary['database']['path']}")
    print(f"     Polling interval: {summary['miner_settings']['polling_interval']}s")
    print(f"     Connection timeout: {summary['miner_settings']['connection_timeout']}s")
    print(f"     Log level: {summary['logging']['level']}")
    print(f"     Theme: {summary['ui']['theme']}")
    print(f"     Base path: {summary['paths']['base']}")
    
    # Test 5: Directory creation test
    print("\n5. Testing directory creation...")
    
    app_paths.ensure_directories()
    
    directories = [
        ('data', app_paths.data_path),
        ('logs', app_paths.logs_path)
    ]
    
    for name, path in directories:
        exists = path.exists()
        is_dir = path.is_dir() if exists else False
        writable = False
        
        if exists and is_dir:
            try:
                test_file = path / '.write_test'
                test_file.touch()
                test_file.unlink()
                writable = True
            except Exception:
                writable = False
        
        print(f"   ✓ {name} directory: exists={exists}, is_dir={is_dir}, writable={writable}")
    
    # Overall result
    overall_valid = result.is_valid and startup_result.is_valid
    
    if overall_valid:
        print("\n✅ All configuration integration tests passed!")
    else:
        print("\n❌ Configuration integration tests failed!")
        print("Please fix the configuration errors above.")
    
    return overall_valid


if __name__ == "__main__":
    test_config_integration()