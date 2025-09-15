"""
Tests for HTTP client utilities with retry logic.
"""

import asyncio
import pytest
import aiohttp
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiohttp import web

from src.backend.utils.http_client import (
    HTTPClient, http_client, get_json, post_json, check_endpoint_health
)
from src.backend.utils.retry_logic import RetryConfig, _retry_manager
from src.backend.exceptions import (
    MinerConnectionError, MinerTimeoutError, NetworkError
)


class TestHTTPClient:
    """Test HTTPClient class."""
    
    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Reset circuit breakers before each test."""
        # Clear all circuit breakers to avoid state leakage between tests
        async with _retry_manager._lock:
            _retry_manager._circuit_breakers.clear()
    
    @pytest.fixture
    def client(self):
        """HTTP client instance for testing."""
        return HTTPClient("10.0.0.100", 80)
    
    @pytest.fixture
    def retry_config(self):
        """Retry configuration for testing."""
        return RetryConfig(max_attempts=2, base_delay=0.1, max_delay=1.0)
    
    @pytest.fixture
    def client_with_retry(self, retry_config):
        """HTTP client with custom retry configuration."""
        return HTTPClient("10.0.0.100", 80, retry_config)
    
    def test_client_initialization(self, client):
        """Test HTTP client initialization."""
        assert client.ip_address == "10.0.0.100"
        assert client.port == 80
        assert client.base_url == "http://10.0.0.100:80"
        assert client.retry_config is not None
    
    def test_client_with_custom_config(self, client_with_retry, retry_config):
        """Test HTTP client with custom retry configuration."""
        assert client_with_retry.retry_config is retry_config
    
    @pytest.mark.asyncio
    async def test_get_request_success(self, client):
        """Test successful GET request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_manager = AsyncMock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_manager.get_session = AsyncMock(return_value=mock_session_context)
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            result = await client.get("/api/status")
            
            assert result == {"status": "ok"}
            mock_session.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_post_request_success(self, client):
        """Test successful POST request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"result": "created"})
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_manager = AsyncMock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_manager.get_session = AsyncMock(return_value=mock_session_context)
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            result = await client.post("/api/create", json={"name": "test"})
            
            assert result == {"result": "created"}
            mock_session.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, client):
        """Test connection error handling."""
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientConnectorError(None, OSError("Connection refused"))
        )
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            with pytest.raises(MinerConnectionError) as exc_info:
                await client.get("/")
            
            assert "Connection failed" in str(exc_info.value)
            assert exc_info.value.context['ip_address'] == "10.0.0.100"
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, client):
        """Test timeout error handling."""
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            with pytest.raises(MinerTimeoutError) as exc_info:
                await client.get("/")
            
            assert "Request timeout" in str(exc_info.value)
            assert exc_info.value.context['method'] == 'GET'
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self, client):
        """Test HTTP error status handling."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            with pytest.raises(NetworkError) as exc_info:
                await client.get("/")
            
            assert "Server error 500" in str(exc_info.value)
            assert exc_info.value.context['status_code'] == 500
    
    @pytest.mark.asyncio
    async def test_client_error_handling(self, client):
        """Test HTTP client error status handling."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            with pytest.raises(MinerConnectionError) as exc_info:
                await client.get("/")
            
            assert "Client error 404" in str(exc_info.value)
            assert exc_info.value.context['status_code'] == 404
    
    @pytest.mark.asyncio
    async def test_non_json_response(self, client):
        """Test handling of non-JSON responses."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(None, None))
        mock_response.text = AsyncMock(return_value="plain text response")
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            result = await client.get("/")
            
            assert result == {"response": "plain text response", "status": 200}
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            result = await client.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test failed health check."""
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientConnectorError(None, OSError("Connection refused"))
        )
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            result = await client.health_check()
            assert result is False
    
    def test_get_endpoint_info(self, client):
        """Test getting endpoint information."""
        info = client.get_endpoint_info()
        
        assert info['ip_address'] == "10.0.0.100"
        assert info['port'] == 80
        assert info['base_url'] == "http://10.0.0.100:80"
        assert 'retry_config' in info
        assert info['retry_config']['max_attempts'] == 3


class TestHTTPClientContextManager:
    """Test HTTP client context manager."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test HTTP client context manager."""
        async with http_client("10.0.0.100", 80) as client:
            assert isinstance(client, HTTPClient)
            assert client.ip_address == "10.0.0.100"
            assert client.port == 80
    
    @pytest.mark.asyncio
    async def test_context_manager_with_config(self):
        """Test HTTP client context manager with custom config."""
        config = RetryConfig(max_attempts=5)
        
        async with http_client("10.0.0.100", 80, config) as client:
            assert client.retry_config is config


class TestConvenienceFunctions:
    """Test convenience functions for HTTP requests."""
    
    @pytest.mark.asyncio
    async def test_get_json_success(self):
        """Test get_json convenience function."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "test"})
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            result = await get_json("10.0.0.100", 80, "/api/data")
            assert result == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_post_json_success(self):
        """Test post_json convenience function."""
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={"created": True})
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            result = await post_json("10.0.0.100", 80, "/api/create", {"name": "test"})
            assert result == {"created": True}
    
    @pytest.mark.asyncio
    async def test_check_endpoint_health_success(self):
        """Test check_endpoint_health convenience function."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            result = await check_endpoint_health("10.0.0.100", 80)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_check_endpoint_health_failure(self):
        """Test check_endpoint_health convenience function with failure."""
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session = AsyncMock()
        mock_session_manager.get_session.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        
        with patch('src.backend.utils.http_client.get_session_manager', return_value=mock_session_manager):
            result = await check_endpoint_health("10.0.0.100", 80)
            assert result is False


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])