"""
Configuration Validator

This module provides validation for application configuration settings.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass

from src.backend.utils.app_paths import get_app_paths
from src.backend.utils.structured_logging import get_logger
from src.backend.exceptions import ConfigurationError, ValidationError

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class ConfigValidator:
    """
    Configuration validator for the Bitcoin Solo Miner Monitoring App.
    
    This class validates application configuration settings, checks required
    directories, and provides clear error messages for configuration issues.
    """
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.app_paths = get_app_paths()
    
    def validate_all(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate all configuration settings.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
            
        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Validate server settings
        self._validate_server_settings(config, result)
        
        # Validate database settings
        self._validate_database_settings(config, result)
        
        # Validate miner settings
        self._validate_miner_settings(config, result)
        
        # Validate logging settings
        self._validate_logging_settings(config, result)
        
        # Validate UI settings
        self._validate_ui_settings(config, result)
        
        # Validate paths and directories
        self._validate_paths_and_directories(result)
        
        return result
    
    def validate_startup_requirements(self) -> ValidationResult:
        """
        Validate startup requirements for the application.
        
        Returns:
            ValidationResult: Validation result for startup requirements
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check required directories
        self._check_required_directories(result)
        
        # Check file permissions
        self._check_file_permissions(result)
        
        # Check database accessibility
        self._check_database_accessibility(result)
        
        return result
    
    def _validate_server_settings(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate server configuration settings."""
        # Check HOST setting
        host = config.get('HOST')
        if not host:
            result.add_error("HOST setting is required")
        elif not isinstance(host, str):
            result.add_error("HOST must be a string")
        elif host not in ['0.0.0.0', '127.0.0.1', 'localhost'] and not self._is_valid_ip(host):
            result.add_warning(f"HOST '{host}' may not be a valid IP address")
        
        # Check PORT setting
        port = config.get('PORT')
        if port is None:
            result.add_error("PORT setting is required")
        elif not isinstance(port, int):
            result.add_error("PORT must be an integer")
        elif not (1 <= port <= 65535):
            result.add_error(f"PORT {port} must be between 1 and 65535")
        elif port < 1024:
            result.add_warning(f"PORT {port} is a privileged port (< 1024)")
    
    def _validate_database_settings(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate database configuration settings."""
        db_config = config.get('DB_CONFIG')
        if not db_config:
            result.add_error("DB_CONFIG setting is required")
            return
        
        if not isinstance(db_config, dict):
            result.add_error("DB_CONFIG must be a dictionary")
            return
        
        # Check SQLite configuration
        sqlite_config = db_config.get('sqlite')
        if not sqlite_config:
            result.add_error("SQLite configuration is required in DB_CONFIG")
            return
        
        if not isinstance(sqlite_config, dict):
            result.add_error("SQLite configuration must be a dictionary")
            return
        
        # Check database path
        db_path = sqlite_config.get('path')
        if not db_path:
            result.add_error("Database path is required in SQLite configuration")
        elif not isinstance(db_path, str):
            result.add_error("Database path must be a string")
        else:
            # Resolve and validate database path
            try:
                resolved_path = self.app_paths.resolve_path(db_path)
                if not self.app_paths.is_safe_path(resolved_path):
                    result.add_error(f"Database path '{db_path}' is outside application directory")
                
                # Check if parent directory exists or can be created
                parent_dir = resolved_path.parent
                if not parent_dir.exists():
                    try:
                        parent_dir.mkdir(parents=True, exist_ok=True)
                    except PermissionError as e:
                        result.add_error(f"Permission denied creating database directory '{parent_dir}': {e}")
                    except OSError as e:
                        result.add_error(f"Cannot create database directory '{parent_dir}': {e}")
            except (ValueError, OSError) as e:
                result.add_error(f"Invalid database path '{db_path}': {e}")
    
    def _validate_miner_settings(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate miner configuration settings."""
        # Check polling interval
        polling_interval = config.get('DEFAULT_POLLING_INTERVAL')
        if polling_interval is None:
            result.add_error("DEFAULT_POLLING_INTERVAL setting is required")
        elif not isinstance(polling_interval, int):
            result.add_error("DEFAULT_POLLING_INTERVAL must be an integer")
        elif polling_interval < 1:
            result.add_error("DEFAULT_POLLING_INTERVAL must be at least 1 second")
        elif polling_interval < 5:
            result.add_warning("DEFAULT_POLLING_INTERVAL less than 5 seconds may cause high CPU usage")
        elif polling_interval > 300:
            result.add_warning("DEFAULT_POLLING_INTERVAL greater than 5 minutes may miss important events")
        
        # Check connection timeout
        timeout = config.get('CONNECTION_TIMEOUT')
        if timeout is None:
            result.add_error("CONNECTION_TIMEOUT setting is required")
        elif not isinstance(timeout, (int, float)):
            result.add_error("CONNECTION_TIMEOUT must be a number")
        elif timeout <= 0:
            result.add_error("CONNECTION_TIMEOUT must be greater than 0")
        elif timeout > 60:
            result.add_warning("CONNECTION_TIMEOUT greater than 60 seconds may cause slow responses")
        
        # Check retry attempts
        retry_attempts = config.get('RETRY_ATTEMPTS')
        if retry_attempts is None:
            result.add_error("RETRY_ATTEMPTS setting is required")
        elif not isinstance(retry_attempts, int):
            result.add_error("RETRY_ATTEMPTS must be an integer")
        elif retry_attempts < 0:
            result.add_error("RETRY_ATTEMPTS must be non-negative")
        elif retry_attempts > 10:
            result.add_warning("RETRY_ATTEMPTS greater than 10 may cause long delays")
        
        # Check retry delay
        retry_delay = config.get('RETRY_DELAY')
        if retry_delay is None:
            result.add_error("RETRY_DELAY setting is required")
        elif not isinstance(retry_delay, (int, float)):
            result.add_error("RETRY_DELAY must be a number")
        elif retry_delay < 0:
            result.add_error("RETRY_DELAY must be non-negative")
        elif retry_delay > 30:
            result.add_warning("RETRY_DELAY greater than 30 seconds may cause long delays")
    
    def _validate_logging_settings(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate logging configuration settings."""
        # Check log level
        log_level = config.get('LOG_LEVEL')
        if not log_level:
            result.add_error("LOG_LEVEL setting is required")
        elif not isinstance(log_level, str):
            result.add_error("LOG_LEVEL must be a string")
        elif log_level.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            result.add_error(f"LOG_LEVEL '{log_level}' is not a valid logging level")
        
        # Check log file path
        log_file = config.get('LOG_FILE')
        if not log_file:
            result.add_error("LOG_FILE setting is required")
        elif not isinstance(log_file, str):
            result.add_error("LOG_FILE must be a string")
        else:
            # Resolve and validate log file path
            try:
                resolved_path = self.app_paths.resolve_path(log_file)
                if not self.app_paths.is_safe_path(resolved_path):
                    result.add_error(f"Log file path '{log_file}' is outside application directory")
                
                # Check if parent directory exists or can be created
                parent_dir = resolved_path.parent
                if not parent_dir.exists():
                    try:
                        parent_dir.mkdir(parents=True, exist_ok=True)
                    except PermissionError as e:
                        result.add_error(f"Permission denied creating log directory '{parent_dir}': {e}")
                    except OSError as e:
                        result.add_error(f"Cannot create log directory '{parent_dir}': {e}")
            except (ValueError, OSError) as e:
                result.add_error(f"Invalid log file path '{log_file}': {e}")
    
    def _validate_ui_settings(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate UI configuration settings."""
        # Check theme
        theme = config.get('THEME')
        if theme and not isinstance(theme, str):
            result.add_error("THEME must be a string")
        elif theme and theme not in ['light', 'dark', 'auto']:
            result.add_warning(f"THEME '{theme}' may not be supported")
        
        # Check chart retention days
        retention_days = config.get('CHART_RETENTION_DAYS')
        if retention_days is not None:
            if not isinstance(retention_days, int):
                result.add_error("CHART_RETENTION_DAYS must be an integer")
            elif retention_days < 1:
                result.add_error("CHART_RETENTION_DAYS must be at least 1")
            elif retention_days > 365:
                result.add_warning("CHART_RETENTION_DAYS greater than 365 may use excessive storage")
        
        # Check refresh interval
        refresh_interval = config.get('DEFAULT_REFRESH_INTERVAL')
        if refresh_interval is not None:
            if not isinstance(refresh_interval, int):
                result.add_error("DEFAULT_REFRESH_INTERVAL must be an integer")
            elif refresh_interval < 1:
                result.add_error("DEFAULT_REFRESH_INTERVAL must be at least 1 second")
            elif refresh_interval < 5:
                result.add_warning("DEFAULT_REFRESH_INTERVAL less than 5 seconds may cause high network usage")
    
    def _validate_paths_and_directories(self, result: ValidationResult) -> None:
        """Validate application paths and directories."""
        # Check base directory
        if not self.app_paths.base_path.exists():
            result.add_error(f"Base application directory does not exist: {self.app_paths.base_path}")
        
        # Check source directory
        if not self.app_paths.src_path.exists():
            result.add_error(f"Source directory does not exist: {self.app_paths.src_path}")
        
        # Check backend directory
        if not self.app_paths.backend_path.exists():
            result.add_error(f"Backend directory does not exist: {self.app_paths.backend_path}")
        
        # Check config directory
        if not self.app_paths.config_path.exists():
            result.add_error(f"Config directory does not exist: {self.app_paths.config_path}")
    
    def _check_required_directories(self, result: ValidationResult) -> None:
        """Check that required directories exist or can be created."""
        required_dirs = [
            ('data', self.app_paths.data_path),
            ('logs', self.app_paths.logs_path)
        ]
        
        for name, path in required_dirs:
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created {name} directory: {path}")
                except PermissionError as e:
                    result.add_error(f"Permission denied creating {name} directory '{path}': {e}")
                except OSError as e:
                    result.add_error(f"Cannot create {name} directory '{path}': {e}")
            elif not path.is_dir():
                result.add_error(f"{name.capitalize()} path exists but is not a directory: {path}")
    
    def _check_file_permissions(self, result: ValidationResult) -> None:
        """Check file permissions for required operations."""
        # Check data directory write permissions
        if self.app_paths.data_path.exists():
            try:
                test_file = self.app_paths.data_path / '.write_test'
                test_file.touch()
                test_file.unlink()
            except PermissionError as e:
                result.add_error(f"No write permission for data directory '{self.app_paths.data_path}': {e}")
            except OSError as e:
                result.add_error(f"Cannot write to data directory '{self.app_paths.data_path}': {e}")
        
        # Check logs directory write permissions
        if self.app_paths.logs_path.exists():
            try:
                test_file = self.app_paths.logs_path / '.write_test'
                test_file.touch()
                test_file.unlink()
            except PermissionError as e:
                result.add_error(f"No write permission for logs directory '{self.app_paths.logs_path}': {e}")
            except OSError as e:
                result.add_error(f"Cannot write to logs directory '{self.app_paths.logs_path}': {e}")
    
    def _check_database_accessibility(self, result: ValidationResult) -> None:
        """Check database accessibility."""
        try:
            import sqlite3
            
            # Try to connect to database
            db_path = self.app_paths.database_path
            
            # If database doesn't exist, try to create it
            if not db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    conn.execute("SELECT 1")
                    conn.close()
                    db_path.unlink()  # Remove test database
                except PermissionError as e:
                    result.add_error(f"Permission denied creating database at '{db_path}': {e}")
                except sqlite3.Error as e:
                    result.add_error(f"SQLite error creating database at '{db_path}': {e}")
                except OSError as e:
                    result.add_error(f"Cannot create database at '{db_path}': {e}")
            else:
                # Database exists, try to connect
                try:
                    conn = sqlite3.connect(str(db_path))
                    conn.execute("SELECT 1")
                    conn.close()
                except sqlite3.Error as e:
                    result.add_error(f"SQLite error connecting to database at '{db_path}': {e}")
                except PermissionError as e:
                    result.add_error(f"Permission denied accessing database at '{db_path}': {e}")
                except OSError as e:
                    result.add_error(f"Cannot connect to existing database at '{db_path}': {e}")
        
        except ImportError:
            result.add_error("SQLite3 module is not available")
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if a string is a valid IP address."""
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def get_configuration_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a summary of the current configuration.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
            
        Returns:
            Dict[str, Any]: Configuration summary
        """
        return {
            'server': {
                'host': config.get('HOST'),
                'port': config.get('PORT')
            },
            'database': {
                'type': 'SQLite',
                'path': config.get('DB_CONFIG', {}).get('sqlite', {}).get('path')
            },
            'miner_settings': {
                'polling_interval': config.get('DEFAULT_POLLING_INTERVAL'),
                'connection_timeout': config.get('CONNECTION_TIMEOUT'),
                'retry_attempts': config.get('RETRY_ATTEMPTS'),
                'retry_delay': config.get('RETRY_DELAY')
            },
            'logging': {
                'level': config.get('LOG_LEVEL'),
                'file': config.get('LOG_FILE')
            },
            'ui': {
                'theme': config.get('THEME'),
                'chart_retention_days': config.get('CHART_RETENTION_DAYS'),
                'refresh_interval': config.get('DEFAULT_REFRESH_INTERVAL')
            },
            'paths': {
                'base': str(self.app_paths.base_path),
                'data': str(self.app_paths.data_path),
                'logs': str(self.app_paths.logs_path),
                'config': str(self.app_paths.config_path)
            }
        }


def validate_configuration(config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate configuration.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary
        
    Returns:
        Tuple[bool, List[str], List[str]]: (is_valid, errors, warnings)
    """
    validator = ConfigValidator()
    result = validator.validate_all(config)
    return result.is_valid, result.errors, result.warnings


def validate_startup_requirements() -> Tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate startup requirements.
    
    Returns:
        Tuple[bool, List[str], List[str]]: (is_valid, errors, warnings)
    """
    validator = ConfigValidator()
    result = validator.validate_startup_requirements()
    return result.is_valid, result.errors, result.warnings