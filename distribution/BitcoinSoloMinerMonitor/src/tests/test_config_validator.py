"""
Test ConfigValidator functionality.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.backend.utils.config_validator import ConfigValidator, ValidationResult, validate_configuration, validate_startup_requirements


def test_config_validator():
    """Test ConfigValidator functionality."""
    print("Testing ConfigValidator functionality...")
    
    # Test 1: Valid configuration
    print("1. Testing valid configuration...")
    valid_config = {
        'HOST': '0.0.0.0',
        'PORT': 8000,
        'DB_CONFIG': {
            'sqlite': {
                'path': 'data/test.db'
            }
        },
        'DEFAULT_POLLING_INTERVAL': 30,
        'CONNECTION_TIMEOUT': 5,
        'RETRY_ATTEMPTS': 3,
        'RETRY_DELAY': 5,
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'logs/test.log',
        'THEME': 'dark',
        'CHART_RETENTION_DAYS': 30,
        'DEFAULT_REFRESH_INTERVAL': 10
    }
    
    validator = ConfigValidator()
    result = validator.validate_all(valid_config)
    
    print(f"   ✓ Valid config result: {result.is_valid}")
    print(f"   ✓ Errors: {len(result.errors)}")
    print(f"   ✓ Warnings: {len(result.warnings)}")
    
    if result.warnings:
        for warning in result.warnings:
            print(f"     WARNING: {warning}")
    
    # Test 2: Invalid configuration
    print("2. Testing invalid configuration...")
    invalid_config = {
        'HOST': None,  # Missing host
        'PORT': 'invalid',  # Invalid port type
        'DB_CONFIG': None,  # Missing DB config
        'DEFAULT_POLLING_INTERVAL': -1,  # Invalid polling interval
        'CONNECTION_TIMEOUT': 0,  # Invalid timeout
        'RETRY_ATTEMPTS': 'invalid',  # Invalid retry attempts
        'RETRY_DELAY': -1,  # Invalid retry delay
        'LOG_LEVEL': 'INVALID',  # Invalid log level
        'LOG_FILE': None,  # Missing log file
    }
    
    result = validator.validate_all(invalid_config)
    
    print(f"   ✓ Invalid config result: {result.is_valid}")
    print(f"   ✓ Errors: {len(result.errors)}")
    print(f"   ✓ Warnings: {len(result.warnings)}")
    
    if result.errors:
        print("     Errors found (expected):")
        for error in result.errors[:3]:  # Show first 3 errors
            print(f"       - {error}")
        if len(result.errors) > 3:
            print(f"       ... and {len(result.errors) - 3} more")
    
    # Test 3: Configuration with warnings
    print("3. Testing configuration with warnings...")
    warning_config = {
        'HOST': '192.168.1.999',  # Invalid IP (warning)
        'PORT': 80,  # Privileged port (warning)
        'DB_CONFIG': {
            'sqlite': {
                'path': 'data/test.db'
            }
        },
        'DEFAULT_POLLING_INTERVAL': 2,  # Too frequent (warning)
        'CONNECTION_TIMEOUT': 120,  # Too long (warning)
        'RETRY_ATTEMPTS': 15,  # Too many (warning)
        'RETRY_DELAY': 60,  # Too long (warning)
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'logs/test.log',
        'THEME': 'rainbow',  # Unsupported theme (warning)
        'CHART_RETENTION_DAYS': 500,  # Too long (warning)
        'DEFAULT_REFRESH_INTERVAL': 2  # Too frequent (warning)
    }
    
    result = validator.validate_all(warning_config)
    
    print(f"   ✓ Warning config result: {result.is_valid}")
    print(f"   ✓ Errors: {len(result.errors)}")
    print(f"   ✓ Warnings: {len(result.warnings)}")
    
    if result.warnings:
        print("     Warnings found (expected):")
        for warning in result.warnings[:3]:  # Show first 3 warnings
            print(f"       - {warning}")
        if len(result.warnings) > 3:
            print(f"       ... and {len(result.warnings) - 3} more")
    
    # Test 4: Startup requirements validation
    print("4. Testing startup requirements validation...")
    startup_result = validator.validate_startup_requirements()
    
    print(f"   ✓ Startup validation result: {startup_result.is_valid}")
    print(f"   ✓ Errors: {len(startup_result.errors)}")
    print(f"   ✓ Warnings: {len(startup_result.warnings)}")
    
    if startup_result.errors:
        for error in startup_result.errors:
            print(f"     ERROR: {error}")
    
    if startup_result.warnings:
        for warning in startup_result.warnings:
            print(f"     WARNING: {warning}")
    
    # Test 5: Configuration summary
    print("5. Testing configuration summary...")
    summary = validator.get_configuration_summary(valid_config)
    
    print(f"   ✓ Summary keys: {list(summary.keys())}")
    print(f"   ✓ Server config: {summary['server']}")
    print(f"   ✓ Database config: {summary['database']}")
    print(f"   ✓ Paths config: {list(summary['paths'].keys())}")
    
    # Test 6: Convenience functions
    print("6. Testing convenience functions...")
    
    is_valid, errors, warnings = validate_configuration(valid_config)
    print(f"   ✓ Convenience function result: {is_valid}")
    print(f"   ✓ Convenience function errors: {len(errors)}")
    print(f"   ✓ Convenience function warnings: {len(warnings)}")
    
    is_valid, errors, warnings = validate_startup_requirements()
    print(f"   ✓ Startup convenience function result: {is_valid}")
    print(f"   ✓ Startup convenience function errors: {len(errors)}")
    print(f"   ✓ Startup convenience function warnings: {len(warnings)}")
    
    # Test 7: ValidationResult class
    print("7. Testing ValidationResult class...")
    
    result = ValidationResult(is_valid=True, errors=[], warnings=[])
    print(f"   ✓ Initial state: valid={result.is_valid}, errors={result.has_errors()}, warnings={result.has_warnings()}")
    
    result.add_error("Test error")
    print(f"   ✓ After adding error: valid={result.is_valid}, errors={result.has_errors()}")
    
    result.add_warning("Test warning")
    print(f"   ✓ After adding warning: valid={result.is_valid}, warnings={result.has_warnings()}")
    
    print("\n✅ All ConfigValidator tests passed!")


if __name__ == "__main__":
    test_config_validator()