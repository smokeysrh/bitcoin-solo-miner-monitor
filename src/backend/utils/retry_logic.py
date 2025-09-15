"""
Retry Logic with Exponential Backoff and Circuit Breaker

This module provides retry decorators and utilities for database operations,
HTTP requests, and other operations that may fail temporarily.
"""

import asyncio
import functools
import logging
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union, Tuple
from dataclasses import dataclass

from src.backend.exceptions import (
    AppError, DatabaseError, MinerError, NetworkError, 
    MinerConnectionError, MinerTimeoutError, DatabaseConnectionError
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_factor: float = 1.0
    
    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3


@dataclass
class CircuitBreakerState:
    """State tracking for circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None


class RetryableError(Exception):
    """Base class for errors that should trigger retries."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should not trigger retries."""
    pass


# Default retryable exceptions
DEFAULT_RETRYABLE_EXCEPTIONS = (
    MinerConnectionError,
    MinerTimeoutError,
    DatabaseConnectionError,
    NetworkError,
    ConnectionError,
    TimeoutError,
    OSError,
)

# Default non-retryable exceptions
DEFAULT_NON_RETRYABLE_EXCEPTIONS = (
    ValueError,
    TypeError,
    AttributeError,
    KeyError,
    NonRetryableError,
)


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.state = CircuitBreakerState()
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            # Check circuit state
            if self.state.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state.state = CircuitState.HALF_OPEN
                    self.state.success_count = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise RetryableError("Circuit breaker is OPEN")
        
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Handle success
            async with self._lock:
                await self._on_success()
            
            return result
            
        except Exception as e:
            # Handle failure
            async with self._lock:
                await self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self.state.last_failure_time is None:
            return True
        
        time_since_failure = datetime.now() - self.state.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    async def _on_success(self):
        """Handle successful execution."""
        if self.state.state == CircuitState.HALF_OPEN:
            self.state.success_count += 1
            if self.state.success_count >= self.config.success_threshold:
                self.state.state = CircuitState.CLOSED
                self.state.failure_count = 0
                self.state.success_count = 0
                logger.info("Circuit breaker reset to CLOSED")
        elif self.state.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.state.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed execution."""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.now()
        
        if self.state.state == CircuitState.HALF_OPEN:
            # Go back to OPEN on any failure in HALF_OPEN
            self.state.state = CircuitState.OPEN
            logger.warning("Circuit breaker back to OPEN after failure in HALF_OPEN")
        elif (self.state.state == CircuitState.CLOSED and 
              self.state.failure_count >= self.config.failure_threshold):
            # Open circuit after threshold failures
            self.state.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.state.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state.state.value,
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count,
            "last_failure_time": self.state.last_failure_time.isoformat() if self.state.last_failure_time else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold
            }
        }


class RetryManager:
    """
    Manager for retry logic with exponential backoff and circuit breakers.
    """
    
    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_circuit_breaker(self, name: str, config: RetryConfig) -> CircuitBreaker:
        """Get or create a circuit breaker for the given name."""
        async with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(config)
            return self._circuit_breakers[name]
    
    def get_all_circuit_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers."""
        return {
            name: breaker.get_state() 
            for name, breaker in self._circuit_breakers.items()
        }


# Global retry manager instance
_retry_manager = RetryManager()


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for exponential backoff with jitter.
    
    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    # Calculate exponential delay
    delay = config.base_delay * (config.exponential_base ** attempt) * config.backoff_factor
    
    # Apply maximum delay limit
    delay = min(delay, config.max_delay)
    
    # Add jitter to prevent thundering herd
    if config.jitter:
        jitter_range = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0, delay)


def is_retryable_exception(
    exception: Exception,
    retryable_exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
    non_retryable_exceptions: Tuple[Type[Exception], ...] = DEFAULT_NON_RETRYABLE_EXCEPTIONS
) -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Args:
        exception: Exception to check
        retryable_exceptions: Tuple of exception types that should be retried
        non_retryable_exceptions: Tuple of exception types that should not be retried
        
    Returns:
        True if exception should be retried
    """
    # Check non-retryable first (takes precedence)
    if isinstance(exception, non_retryable_exceptions):
        return False
    
    # Check retryable
    if isinstance(exception, retryable_exceptions):
        return True
    
    # Default to non-retryable for unknown exceptions
    return False


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    non_retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    circuit_breaker_name: Optional[str] = None
):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        config: Retry configuration
        retryable_exceptions: Exceptions that should trigger retries
        non_retryable_exceptions: Exceptions that should not trigger retries
        circuit_breaker_name: Name for circuit breaker (if None, no circuit breaker)
        
    Returns:
        Decorated function
    """
    if config is None:
        config = RetryConfig()
    
    if retryable_exceptions is None:
        retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS
    
    if non_retryable_exceptions is None:
        non_retryable_exceptions = DEFAULT_NON_RETRYABLE_EXCEPTIONS
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            circuit_breaker = None
            if circuit_breaker_name:
                circuit_breaker = await _retry_manager.get_circuit_breaker(
                    circuit_breaker_name, config
                )
            
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    # Execute through circuit breaker if configured
                    if circuit_breaker:
                        return await circuit_breaker.call(func, *args, **kwargs)
                    else:
                        if asyncio.iscoroutinefunction(func):
                            return await func(*args, **kwargs)
                        else:
                            return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if not is_retryable_exception(e, retryable_exceptions, non_retryable_exceptions):
                        logger.debug(f"Non-retryable exception in {func.__name__}: {e}")
                        raise
                    
                    # Check if this is the last attempt
                    if attempt == config.max_attempts - 1:
                        logger.error(f"All retry attempts exhausted for {func.__name__}: {e}")
                        raise
                    
                    # Calculate delay and wait
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # For sync functions, we need to handle differently
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if not is_retryable_exception(e, retryable_exceptions, non_retryable_exceptions):
                        logger.debug(f"Non-retryable exception in {func.__name__}: {e}")
                        raise
                    
                    # Check if this is the last attempt
                    if attempt == config.max_attempts - 1:
                        logger.error(f"All retry attempts exhausted for {func.__name__}: {e}")
                        raise
                    
                    # Calculate delay and wait
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience decorators for common scenarios

def retry_database_operation(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
):
    """
    Decorator for database operations with retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True
    )
    
    return retry_with_backoff(
        config=config,
        retryable_exceptions=(DatabaseError, DatabaseConnectionError, OSError),
        circuit_breaker_name="database"
    )


def retry_http_request(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    """
    Decorator for HTTP requests with retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=True
    )
    
    return retry_with_backoff(
        config=config,
        retryable_exceptions=(
            MinerConnectionError, MinerTimeoutError, NetworkError,
            ConnectionError, TimeoutError, OSError
        ),
        circuit_breaker_name="http_requests"
    )


def retry_miner_operation(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0
):
    """
    Decorator for miner operations with retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=1.5,  # Slower exponential growth for miner operations
        jitter=True
    )
    
    return retry_with_backoff(
        config=config,
        retryable_exceptions=(MinerConnectionError, MinerTimeoutError, NetworkError),
        circuit_breaker_name="miner_operations"
    )


async def get_retry_stats() -> Dict[str, Any]:
    """
    Get statistics about retry operations and circuit breakers.
    
    Returns:
        Dictionary containing retry statistics
    """
    return {
        "circuit_breakers": _retry_manager.get_all_circuit_states(),
        "timestamp": datetime.now().isoformat()
    }


async def reset_circuit_breaker(name: str) -> bool:
    """
    Reset a specific circuit breaker to CLOSED state.
    
    Args:
        name: Name of the circuit breaker to reset
        
    Returns:
        True if reset successful, False if circuit breaker not found
    """
    async with _retry_manager._lock:
        if name in _retry_manager._circuit_breakers:
            breaker = _retry_manager._circuit_breakers[name]
            async with breaker._lock:
                breaker.state.state = CircuitState.CLOSED
                breaker.state.failure_count = 0
                breaker.state.success_count = 0
                breaker.state.last_failure_time = None
                logger.info(f"Circuit breaker '{name}' manually reset to CLOSED")
                return True
    return False


# Context manager for temporary retry configuration
class retry_context:
    """
    Context manager for temporary retry configuration.
    
    Example:
        async with retry_context(max_attempts=5, base_delay=2.0):
            result = await some_operation()
    """
    
    def __init__(self, **config_kwargs):
        self.config = RetryConfig(**config_kwargs)
        self.original_config = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def __call__(self, func):
        """Use as decorator within context."""
        return retry_with_backoff(config=self.config)(func)