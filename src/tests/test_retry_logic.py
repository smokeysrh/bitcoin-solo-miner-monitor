"""
Tests for retry logic with exponential backoff and circuit breaker.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from src.backend.utils.retry_logic import (
    RetryConfig, CircuitBreaker, CircuitState, RetryManager,
    retry_with_backoff, retry_database_operation, retry_http_request,
    retry_miner_operation, calculate_delay, is_retryable_exception,
    get_retry_stats, reset_circuit_breaker
)
from src.backend.exceptions import (
    MinerConnectionError, MinerTimeoutError, DatabaseConnectionError,
    NetworkError, ValidationError
)


class TestRetryConfig:
    """Test RetryConfig dataclass."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.backoff_factor == 1.0
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 3
    
    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=1.5,
            jitter=False,
            backoff_factor=2.0,
            failure_threshold=10,
            recovery_timeout=120.0,
            success_threshold=5
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 1.5
        assert config.jitter is False
        assert config.backoff_factor == 2.0
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 120.0
        assert config.success_threshold == 5


class TestCalculateDelay:
    """Test delay calculation for exponential backoff."""
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, 
                           max_delay=60.0, jitter=False)
        
        # Test exponential growth
        assert calculate_delay(0, config) == 1.0  # 1.0 * 2^0 = 1.0
        assert calculate_delay(1, config) == 2.0  # 1.0 * 2^1 = 2.0
        assert calculate_delay(2, config) == 4.0  # 1.0 * 2^2 = 4.0
        assert calculate_delay(3, config) == 8.0  # 1.0 * 2^3 = 8.0
    
    def test_max_delay_limit(self):
        """Test maximum delay limit."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, 
                           max_delay=5.0, jitter=False)
        
        # Should be capped at max_delay
        assert calculate_delay(10, config) == 5.0
    
    def test_jitter(self):
        """Test jitter adds randomness."""
        config = RetryConfig(base_delay=10.0, exponential_base=1.0, 
                           max_delay=60.0, jitter=True)
        
        # With jitter, results should vary slightly
        delays = [calculate_delay(0, config) for _ in range(10)]
        
        # All delays should be around 10.0 but not exactly the same
        assert all(9.0 <= delay <= 11.0 for delay in delays)
        assert len(set(delays)) > 1  # Should have some variation
    
    def test_backoff_factor(self):
        """Test backoff factor multiplier."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, 
                           max_delay=60.0, backoff_factor=3.0, jitter=False)
        
        # Should multiply by backoff_factor
        assert calculate_delay(0, config) == 3.0  # 1.0 * 2^0 * 3.0 = 3.0
        assert calculate_delay(1, config) == 6.0  # 1.0 * 2^1 * 3.0 = 6.0


class TestIsRetryableException:
    """Test exception classification for retries."""
    
    def test_retryable_exceptions(self):
        """Test that retryable exceptions are identified correctly."""
        assert is_retryable_exception(MinerConnectionError("test"))
        assert is_retryable_exception(MinerTimeoutError("test"))
        assert is_retryable_exception(DatabaseConnectionError("test"))
        assert is_retryable_exception(NetworkError("test"))
        assert is_retryable_exception(ConnectionError("test"))
        assert is_retryable_exception(TimeoutError("test"))
        assert is_retryable_exception(OSError("test"))
    
    def test_non_retryable_exceptions(self):
        """Test that non-retryable exceptions are identified correctly."""
        assert not is_retryable_exception(ValueError("test"))
        assert not is_retryable_exception(TypeError("test"))
        assert not is_retryable_exception(AttributeError("test"))
        assert not is_retryable_exception(KeyError("test"))
        assert not is_retryable_exception(ValidationError("test"))
    
    def test_custom_exception_lists(self):
        """Test custom exception classification."""
        # Custom retryable exceptions
        assert is_retryable_exception(
            ValueError("test"),
            retryable_exceptions=(ValueError,),
            non_retryable_exceptions=()
        )
        
        # Custom non-retryable exceptions
        assert not is_retryable_exception(
            MinerConnectionError("test"),
            retryable_exceptions=(),
            non_retryable_exceptions=(MinerConnectionError,)
        )


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def config(self):
        """Circuit breaker configuration for testing."""
        return RetryConfig(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            success_threshold=2
        )
    
    @pytest.fixture
    def circuit_breaker(self, config):
        """Circuit breaker instance for testing."""
        return CircuitBreaker(config)
    
    @pytest.mark.asyncio
    async def test_circuit_closed_success(self, circuit_breaker):
        """Test circuit breaker in CLOSED state with successful calls."""
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state.state == CircuitState.CLOSED
        assert circuit_breaker.state.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Test circuit breaker opens after threshold failures."""
        async def failing_func():
            raise MinerConnectionError("test failure")
        
        # Should fail 3 times before opening
        for i in range(3):
            with pytest.raises(MinerConnectionError):
                await circuit_breaker.call(failing_func)
            
            if i < 2:
                assert circuit_breaker.state.state == CircuitState.CLOSED
            else:
                assert circuit_breaker.state.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_open_fails_fast(self, circuit_breaker):
        """Test circuit breaker fails fast when OPEN."""
        # Force circuit to OPEN state
        circuit_breaker.state.state = CircuitState.OPEN
        circuit_breaker.state.last_failure_time = datetime.now()
        
        async def any_func():
            return "should not be called"
        
        with pytest.raises(Exception):  # Should fail fast
            await circuit_breaker.call(any_func)
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_recovery(self, circuit_breaker):
        """Test circuit breaker recovery through HALF_OPEN state."""
        # Force circuit to OPEN state with old failure time
        circuit_breaker.state.state = CircuitState.OPEN
        circuit_breaker.state.last_failure_time = datetime.now() - timedelta(seconds=2)
        
        async def success_func():
            return "success"
        
        # First call should transition to HALF_OPEN
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state.state == CircuitState.HALF_OPEN
        
        # Second successful call should close the circuit
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_failure(self, circuit_breaker):
        """Test circuit breaker goes back to OPEN on failure in HALF_OPEN."""
        # Set to HALF_OPEN state
        circuit_breaker.state.state = CircuitState.HALF_OPEN
        
        async def failing_func():
            raise MinerConnectionError("test failure")
        
        with pytest.raises(MinerConnectionError):
            await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state.state == CircuitState.OPEN
    
    def test_get_state(self, circuit_breaker):
        """Test getting circuit breaker state."""
        state = circuit_breaker.get_state()
        
        assert "state" in state
        assert "failure_count" in state
        assert "success_count" in state
        assert "last_failure_time" in state
        assert "config" in state
        
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["success_count"] == 0


class TestRetryDecorator:
    """Test retry decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test successful call doesn't trigger retries."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_retryable_exception(self):
        """Test retry on retryable exceptions."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MinerConnectionError("test failure")
            return "success"
        
        result = await failing_func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_exception(self):
        """Test no retry on non-retryable exceptions."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("non-retryable error")
        
        with pytest.raises(ValueError):
            await failing_func()
        
        assert call_count == 1  # Should not retry
    
    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test behavior when all retries are exhausted."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise MinerConnectionError("always fails")
        
        with pytest.raises(MinerConnectionError):
            await always_failing_func()
        
        assert call_count == 3  # Should try all attempts
    
    def test_sync_function_retry(self):
        """Test retry decorator with synchronous functions."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
        def failing_sync_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MinerConnectionError("test failure")
            return "success"
        
        result = failing_sync_func()
        assert result == "success"
        assert call_count == 3


class TestConvenienceDecorators:
    """Test convenience decorators for specific use cases."""
    
    @pytest.mark.asyncio
    async def test_database_operation_decorator(self):
        """Test database operation decorator."""
        call_count = 0
        
        @retry_database_operation(max_attempts=2, base_delay=0.1)
        async def db_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise DatabaseConnectionError("db connection failed")
            return "db success"
        
        result = await db_operation()
        assert result == "db success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_http_request_decorator(self):
        """Test HTTP request decorator."""
        call_count = 0
        
        @retry_http_request(max_attempts=2, base_delay=0.1)
        async def http_request():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise MinerConnectionError("connection failed")
            return "http success"
        
        result = await http_request()
        assert result == "http success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_miner_operation_decorator(self):
        """Test miner operation decorator."""
        call_count = 0
        
        @retry_miner_operation(max_attempts=2, base_delay=0.1)
        async def miner_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise MinerTimeoutError("miner timeout")
            return "miner success"
        
        result = await miner_operation()
        assert result == "miner success"
        assert call_count == 2


class TestRetryManager:
    """Test retry manager functionality."""
    
    @pytest.mark.asyncio
    async def test_get_circuit_breaker(self):
        """Test getting circuit breaker from manager."""
        manager = RetryManager()
        config = RetryConfig()
        
        breaker1 = await manager.get_circuit_breaker("test", config)
        breaker2 = await manager.get_circuit_breaker("test", config)
        
        # Should return the same instance
        assert breaker1 is breaker2
    
    @pytest.mark.asyncio
    async def test_get_all_circuit_states(self):
        """Test getting all circuit breaker states."""
        manager = RetryManager()
        config = RetryConfig()
        
        await manager.get_circuit_breaker("test1", config)
        await manager.get_circuit_breaker("test2", config)
        
        states = manager.get_all_circuit_states()
        
        assert "test1" in states
        assert "test2" in states
        assert states["test1"]["state"] == "closed"
        assert states["test2"]["state"] == "closed"


class TestRetryStats:
    """Test retry statistics functionality."""
    
    @pytest.mark.asyncio
    async def test_get_retry_stats(self):
        """Test getting retry statistics."""
        stats = await get_retry_stats()
        
        assert "circuit_breakers" in stats
        assert "timestamp" in stats
        assert isinstance(stats["circuit_breakers"], dict)
    
    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self):
        """Test resetting circuit breaker."""
        # Create a circuit breaker and force it to OPEN
        from src.backend.utils.retry_logic import _retry_manager
        
        config = RetryConfig(failure_threshold=1)
        breaker = await _retry_manager.get_circuit_breaker("test_reset", config)
        
        # Force to OPEN state
        breaker.state.state = CircuitState.OPEN
        breaker.state.failure_count = 5
        
        # Reset it
        result = await reset_circuit_breaker("test_reset")
        assert result is True
        assert breaker.state.state == CircuitState.CLOSED
        assert breaker.state.failure_count == 0
        
        # Try to reset non-existent breaker
        result = await reset_circuit_breaker("non_existent")
        assert result is False


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])