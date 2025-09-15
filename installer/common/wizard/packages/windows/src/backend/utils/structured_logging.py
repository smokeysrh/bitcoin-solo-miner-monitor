"""
Structured logging utilities for better error analysis and debugging.

This module provides enhanced logging capabilities with structured data,
error context, and improved formatting for debugging purposes.
"""

import logging
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured log data."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create base log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add any extra context from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ErrorContextLogger:
    """Logger wrapper that adds error context and structured logging."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **context: Any) -> None:
        """Set persistent context that will be included in all log messages."""
        self._context.update(context)
    
    def clear_context(self) -> None:
        """Clear all persistent context."""
        self._context.clear()
    
    def _log_with_context(self, level: int, message: str, 
                         context: Optional[Dict[str, Any]] = None, 
                         exc_info: bool = False) -> None:
        """Log message with context information."""
        extra = dict(self._context)
        if context:
            extra.update(context)
        
        self.logger.log(level, message, extra=extra, exc_info=exc_info)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, context)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, context)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, context)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, 
              exc_info: bool = True) -> None:
        """Log error message with context and exception info."""
        self._log_with_context(logging.ERROR, message, context, exc_info)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, 
                 exc_info: bool = True) -> None:
        """Log critical message with context and exception info."""
        self._log_with_context(logging.CRITICAL, message, context, exc_info)
    
    def exception(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log exception with full traceback and context."""
        self._log_with_context(logging.ERROR, message, context, exc_info=True)


def setup_structured_logging(log_level: str = "INFO", 
                            log_file: Optional[Path] = None,
                            enable_console: bool = True,
                            enable_structured: bool = True) -> None:
    """
    Set up structured logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        enable_console: Whether to enable console logging
        enable_structured: Whether to use structured JSON formatting
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Create formatters
    if enable_structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> ErrorContextLogger:
    """Get a structured logger instance."""
    return ErrorContextLogger(name)


class LoggingContext:
    """Context manager for temporary logging context."""
    
    def __init__(self, logger: ErrorContextLogger, **context: Any):
        self.logger = logger
        self.context = context
        self.original_context = {}
    
    def __enter__(self):
        # Save original context
        self.original_context = dict(self.logger._context)
        # Add new context
        self.logger.set_context(**self.context)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original context
        self.logger._context = self.original_context


def log_function_call(logger: ErrorContextLogger):
    """Decorator to log function calls with parameters and results."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"Calling {func_name}", {
                'function': func_name,
                'args_count': len(args),
                'kwargs': list(kwargs.keys())
            })
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Completed {func_name}", {
                    'function': func_name,
                    'success': True
                })
                return result
            except Exception as e:
                logger.error(f"Error in {func_name}: {e}", {
                    'function': func_name,
                    'error_type': type(e).__name__,
                    'success': False
                })
                raise
        
        return wrapper
    return decorator


def log_async_function_call(logger: ErrorContextLogger):
    """Decorator to log async function calls with parameters and results."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"Calling async {func_name}", {
                'function': func_name,
                'args_count': len(args),
                'kwargs': list(kwargs.keys()),
                'async': True
            })
            
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"Completed async {func_name}", {
                    'function': func_name,
                    'success': True,
                    'async': True
                })
                return result
            except Exception as e:
                logger.error(f"Error in async {func_name}: {e}", {
                    'function': func_name,
                    'error_type': type(e).__name__,
                    'success': False,
                    'async': True
                })
                raise
        
        return wrapper
    return decorator