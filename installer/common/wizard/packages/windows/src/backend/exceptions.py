"""
Custom exception classes for the Bitcoin Solo Miner Monitoring App.

This module defines specific exception types to replace broad exception handling
and provide better error context and debugging information.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime


class AppError(Exception):
    """Base exception class for all application errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.now()
        
    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message
    
    def log_error(self, logger: logging.Logger) -> None:
        """Log this error with appropriate context."""
        logger.error(f"{self.__class__.__name__}: {self.message}", extra={
            'error_context': self.context,
            'error_timestamp': self.timestamp.isoformat(),
            'error_type': self.__class__.__name__
        })


class ConfigurationError(AppError):
    """Raised when configuration is invalid or missing."""
    pass


class DatabaseError(AppError):
    """Base class for database-related errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class DatabaseMigrationError(DatabaseError):
    """Raised when database migration fails."""
    pass


class DatabaseQueryError(DatabaseError):
    """Raised when database query execution fails."""
    pass


class MinerError(AppError):
    """Base class for miner-related errors."""
    
    def __init__(self, message: str, miner_id: Optional[str] = None, 
                 ip_address: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if miner_id:
            context['miner_id'] = miner_id
        if ip_address:
            context['ip_address'] = ip_address
        super().__init__(message, context)


class MinerConnectionError(MinerError):
    """Raised when connection to a miner fails."""
    pass


class MinerAuthenticationError(MinerError):
    """Raised when miner authentication fails."""
    pass


class MinerDataError(MinerError):
    """Raised when miner returns invalid or unexpected data."""
    pass


class MinerTimeoutError(MinerError):
    """Raised when miner operations timeout."""
    pass


class MinerConfigurationError(MinerError):
    """Raised when miner configuration is invalid."""
    pass


class NetworkError(AppError):
    """Base class for network-related errors."""
    pass


class HTTPSessionError(NetworkError):
    """Raised when HTTP session management fails."""
    pass


class WebSocketError(NetworkError):
    """Raised when WebSocket operations fail."""
    pass


class ValidationError(AppError):
    """Raised when input validation fails."""
    pass


class PathError(AppError):
    """Raised when file path operations fail."""
    pass


class PermissionError(AppError):
    """Raised when file/directory permission operations fail."""
    pass


class ServiceError(AppError):
    """Base class for service-related errors."""
    pass


class MinerManagerError(ServiceError):
    """Raised when miner manager operations fail."""
    pass


class DataStorageError(ServiceError):
    """Raised when data storage operations fail."""
    pass


class SystemMonitorError(ServiceError):
    """Raised when system monitoring operations fail."""
    pass


class TimeSeriesError(AppError):
    """Raised when time-series data operations fail."""
    pass


class DiscoveryError(AppError):
    """Raised when miner discovery operations fail."""
    pass


# Exception mapping for common error scenarios
ERROR_MAPPINGS = {
    'connection_refused': MinerConnectionError,
    'connection_timeout': MinerTimeoutError,
    'invalid_response': MinerDataError,
    'authentication_failed': MinerAuthenticationError,
    'database_locked': DatabaseConnectionError,
    'database_corrupt': DatabaseError,
    'invalid_config': ConfigurationError,
    'permission_denied': PermissionError,
    'path_not_found': PathError,
    'validation_failed': ValidationError,
    'session_error': HTTPSessionError,
    'websocket_error': WebSocketError,
}


def map_exception(error_type: str, message: str, **context) -> AppError:
    """Map a generic error type to a specific exception class."""
    exception_class = ERROR_MAPPINGS.get(error_type, AppError)
    return exception_class(message, context)


def handle_exception(func):
    """Decorator to handle exceptions and convert them to specific types."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert generic exceptions to specific ones based on error message
            error_msg = str(e).lower()
            
            if 'connection refused' in error_msg or 'connection failed' in error_msg:
                raise MinerConnectionError(str(e))
            elif 'timeout' in error_msg:
                raise MinerTimeoutError(str(e))
            elif 'permission denied' in error_msg:
                raise PermissionError(str(e))
            elif 'database' in error_msg and 'locked' in error_msg:
                raise DatabaseConnectionError(str(e))
            elif 'invalid' in error_msg or 'malformed' in error_msg:
                raise ValidationError(str(e))
            else:
                # Re-raise as generic AppError if we can't classify it
                raise AppError(str(e))
    
    return wrapper


async def handle_async_exception(func):
    """Async decorator to handle exceptions and convert them to specific types."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Convert generic exceptions to specific ones based on error message
            error_msg = str(e).lower()
            
            if 'connection refused' in error_msg or 'connection failed' in error_msg:
                raise MinerConnectionError(str(e))
            elif 'timeout' in error_msg:
                raise MinerTimeoutError(str(e))
            elif 'permission denied' in error_msg:
                raise PermissionError(str(e))
            elif 'database' in error_msg and 'locked' in error_msg:
                raise DatabaseConnectionError(str(e))
            elif 'invalid' in error_msg or 'malformed' in error_msg:
                raise ValidationError(str(e))
            else:
                # Re-raise as generic AppError if we can't classify it
                raise AppError(str(e))
    
    return wrapper