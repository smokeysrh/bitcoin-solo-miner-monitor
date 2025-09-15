"""
Integration tests for retry logic implementation.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch

from src.backend.utils.retry_logic import (
    retry_database_operation, retry_http_request, retry_miner_operation,
    RetryConfig, retry_with_backoff
)
from src.backend.exceptions import (
    DatabaseConnectionError, MinerConnectionError, MinerTimeoutError,
    NetworkError, ValidationError
)


class TestRetryIntegration:
    """Integration tests for retry decorators."""
    
    @pytest.mark.asyncio
    async def test_database_retry_success_after_failure(self):
        """Test database operation succeeds after initial failure."""
        call_count = 0
        
        @retry_database_operation(max_attempts=3, base_delay=0.1)
        async def db_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise DatabaseConnectionError("Database locked")
            return "success"
        
        result = await db_operation()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_http_retry_success_after_failure(self):
        """Test HTTP request succeeds after initial failure."""
        call_count = 0
        
        @retry_http_request(max_attempts=3, base_delay=0.1)
        async def http_request():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise MinerConnectionError("Connection refused")
            return {"status": "ok"}
        
        result = await http_request()
        assert result == {"status": "ok"}
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_miner_retry_success_after_failure(self):
        """Test miner operation succeeds after initial failure."""
        call_count = 0
        
        @retry_miner_operation(max_attempts=3, base_delay=0.1)
        async def miner_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise MinerTimeoutError("Miner timeout")
            return {"hashrate": 100}
        
        result = await miner_operation()
        assert result == {"hashrate": 100}
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception_no_retry(self):
        """Test that non-retryable exceptions don't trigger retries."""
        call_count = 0
        
        @retry_database_operation(max_attempts=3, base_delay=0.1)
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise ValidationError("Invalid input")
        
        with pytest.raises(ValidationError):
            await failing_operation()
        
        assert call_count == 1  # Should not retry
    
    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test behavior when all retries are exhausted."""
        call_count = 0
        
        @retry_http_request(max_attempts=3, base_delay=0.1)
        async def always_failing():
            nonlocal call_count
            call_count += 1
            raise NetworkError("Always fails")
        
        with pytest.raises(NetworkError):
            await always_failing()
        
        assert call_count == 3  # Should try all attempts
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff timing works correctly."""
        call_times = []
        
        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.2, jitter=False))
        async def timing_test():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise MinerConnectionError("Test failure")
            return "success"
        
        start_time = time.time()
        result = await timing_test()
        
        assert result == "success"
        assert len(call_times) == 3
        
        # Check timing intervals (allowing some tolerance)
        interval1 = call_times[1] - call_times[0]
        interval2 = call_times[2] - call_times[1]
        
        # First retry should be after ~0.2s, second after ~0.4s
        assert 0.15 <= interval1 <= 0.25  # ~0.2s with tolerance
        assert 0.35 <= interval2 <= 0.45  # ~0.4s with tolerance
    
    def test_sync_function_retry(self):
        """Test retry decorator with synchronous functions."""
        call_count = 0
        
        @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.1))
        def sync_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise MinerConnectionError("Connection failed")
            return "sync_success"
        
        result = sync_operation()
        assert result == "sync_success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_custom_retry_config(self):
        """Test retry with custom configuration."""
        call_count = 0
        
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.05,
            max_delay=1.0,
            exponential_base=1.5
        )
        
        @retry_with_backoff(config)
        async def custom_retry_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise MinerConnectionError("Custom retry test")
            return "custom_success"
        
        result = await custom_retry_operation()
        assert result == "custom_success"
        assert call_count == 4


class TestRetryWithRealServices:
    """Test retry logic with mock services that simulate real behavior."""
    
    @pytest.mark.asyncio
    async def test_database_connection_retry(self):
        """Test database connection with retry logic."""
        connection_attempts = 0
        
        async def mock_connect():
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts < 3:
                raise DatabaseConnectionError("Database unavailable")
            return "connected"
        
        @retry_database_operation(max_attempts=5, base_delay=0.1)
        async def connect_to_db():
            return await mock_connect()
        
        result = await connect_to_db()
        assert result == "connected"
        assert connection_attempts == 3
    
    @pytest.mark.asyncio
    async def test_miner_communication_retry(self):
        """Test miner communication with retry logic."""
        request_attempts = 0
        
        async def mock_miner_request():
            nonlocal request_attempts
            request_attempts += 1
            if request_attempts == 1:
                raise MinerConnectionError("Connection refused")
            elif request_attempts == 2:
                raise MinerTimeoutError("Request timeout")
            else:
                return {"status": "online", "hashrate": 150}
        
        @retry_miner_operation(max_attempts=4, base_delay=0.1)
        async def get_miner_status():
            return await mock_miner_request()
        
        result = await get_miner_status()
        assert result == {"status": "online", "hashrate": 150}
        assert request_attempts == 3
    
    @pytest.mark.asyncio
    async def test_http_session_retry(self):
        """Test HTTP session management with retry logic."""
        session_attempts = 0
        
        async def mock_http_request():
            nonlocal session_attempts
            session_attempts += 1
            if session_attempts < 2:
                raise NetworkError("Network unreachable")
            return {"data": "response"}
        
        @retry_http_request(max_attempts=3, base_delay=0.1)
        async def make_http_request():
            return await mock_http_request()
        
        result = await make_http_request()
        assert result == {"data": "response"}
        assert session_attempts == 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])