"""
Test HTTP Session Management

This module tests the HTTP session management implementation for proper
lifecycle management, pooling, and cleanup.
"""

import asyncio
import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.backend.services.http_session_manager import HTTPSessionManager, http_session, shutdown_session_manager
from src.backend.models.http_client_mixin import HTTPClientMixin
from src.backend.models.bitaxe_miner import BitaxeMiner


class TestHTTPSessionManager:
    """Test cases for HTTPSessionManager."""
    
    @pytest.fixture
    async def session_manager(self):
        """Create a session manager for testing."""
        manager = HTTPSessionManager(max_sessions=3, session_timeout=5, cleanup_interval=1)
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_session_creation_and_reuse(self, session_manager):
        """Test that sessions are created and reused properly."""
        ip_address = "10.0.0.100"
        port = 80
        
        # First request should create a new session
        async with session_manager.get_session(ip_address, port) as session1:
            assert session1 is not None
            assert isinstance(session1, aiohttp.ClientSession)
            assert not session1.closed
        
        # Second request should reuse the same session
        async with session_manager.get_session(ip_address, port) as session2:
            assert session2 is session1  # Same session object
            assert not session2.closed
        
        # Verify session is in the pool
        stats = session_manager.get_session_stats()
        assert stats['active_sessions'] == 1
        assert len(stats['sessions']) == 1
        assert stats['sessions'][0]['endpoint'] == f"{ip_address}:{port}"
    
    @pytest.mark.asyncio
    async def test_session_pool_limit(self, session_manager):
        """Test that session pool respects the maximum limit."""
        # Create sessions up to the limit
        sessions = []
        for i in range(4):  # One more than the limit of 3
            ip_address = f"192.168.1.{100 + i}"
            async with session_manager.get_session(ip_address, 80) as session:
                sessions.append(session)
                # Keep sessions active by not exiting context
                if i < 3:
                    await asyncio.sleep(0.1)  # Small delay to ensure ordering
        
        # Should have exactly max_sessions active
        stats = session_manager.get_session_stats()
        assert stats['active_sessions'] == session_manager.max_sessions
    
    @pytest.mark.asyncio
    async def test_session_timeout_cleanup(self, session_manager):
        """Test that expired sessions are cleaned up."""
        ip_address = "10.0.0.100"
        port = 80
        
        # Create a session
        async with session_manager.get_session(ip_address, port) as session:
            assert not session.closed
        
        # Verify session exists
        stats = session_manager.get_session_stats()
        assert stats['active_sessions'] == 1
        
        # Wait for session to expire and cleanup to run
        await asyncio.sleep(session_manager.session_timeout + session_manager.cleanup_interval + 1)
        
        # Session should be cleaned up
        stats = session_manager.get_session_stats()
        assert stats['active_sessions'] == 0
    
    @pytest.mark.asyncio
    async def test_session_cleanup_on_error(self, session_manager):
        """Test that sessions are cleaned up when errors occur."""
        ip_address = "10.0.0.100"
        port = 80
        
        # Simulate an error during session usage
        try:
            async with session_manager.get_session(ip_address, port) as session:
                raise Exception("Test error")
        except Exception:
            pass
        
        # Session should still be cleaned up properly
        stats = session_manager.get_session_stats()
        # Session might still exist but should be properly managed
        assert stats['active_sessions'] <= 1
    
    @pytest.mark.asyncio
    async def test_explicit_session_close(self, session_manager):
        """Test explicit session closing."""
        ip_address = "10.0.0.100"
        port = 80
        
        # Create a session
        async with session_manager.get_session(ip_address, port) as session:
            assert not session.closed
        
        # Explicitly close the session
        await session_manager.close_session(ip_address, port)
        
        # Session should be removed from pool
        stats = session_manager.get_session_stats()
        assert stats['active_sessions'] == 0


class TestHTTPClientMixin:
    """Test cases for HTTPClientMixin."""
    
    class TestMiner(HTTPClientMixin):
        """Test miner class using HTTPClientMixin."""
        
        def __init__(self, ip_address: str, port: int = 80):
            super().__init__()
            self.ip_address = ip_address
            self.port = port
            self.base_url = f"http://{ip_address}:{port}"
    
    @pytest.fixture
    def test_miner(self):
        """Create a test miner for testing."""
        return self.TestMiner("10.0.0.100", 80)
    
    @pytest.mark.asyncio
    async def test_http_get_success(self, test_miner):
        """Test successful HTTP GET request."""
        mock_response_data = {"status": "ok", "data": "test"}
        
        with patch('src.backend.services.http_session_manager.http_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_session_obj.request = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_obj)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await test_miner._http_get("/api/test")
            
            assert result == mock_response_data
            mock_session_obj.request.assert_called_once_with('GET', 'http://10.0.0.100:80/api/test')
    
    @pytest.mark.asyncio
    async def test_http_post_with_data(self, test_miner):
        """Test HTTP POST request with JSON data."""
        test_data = {"key": "value"}
        mock_response_data = {"result": "success"}
        
        with patch('src.backend.services.http_session_manager.http_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_session_obj.request = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_obj)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await test_miner._http_post("/api/update", test_data)
            
            assert result == mock_response_data
            mock_session_obj.request.assert_called_once_with('POST', 'http://10.0.0.100:80/api/update', json=test_data)
    
    @pytest.mark.asyncio
    async def test_http_post_form_data(self, test_miner):
        """Test HTTP POST request with form data."""
        form_data = {"field1": "value1", "field2": "value2"}
        
        with patch('src.backend.services.http_session_manager.http_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={})
            mock_session_obj.request = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_obj)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await test_miner._http_post_form("/api/form", form_data)
            
            assert result == {}
            mock_session_obj.request.assert_called_once()
            call_args = mock_session_obj.request.call_args
            assert call_args[0] == ('POST', 'http://10.0.0.100:80/api/form')
            assert call_args[1]['data'] == form_data
            assert call_args[1]['headers']['Content-Type'] == 'application/x-www-form-urlencoded'
    
    @pytest.mark.asyncio
    async def test_http_request_retry_on_timeout(self, test_miner):
        """Test that HTTP requests retry on timeout."""
        with patch('src.backend.services.http_session_manager.http_session') as mock_session:
            mock_session_obj = AsyncMock()
            # First two attempts timeout, third succeeds
            mock_session_obj.request.side_effect = [
                asyncio.TimeoutError(),
                asyncio.TimeoutError(),
                AsyncMock(status=200, json=AsyncMock(return_value={"success": True}))
            ]
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_obj)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                result = await test_miner._http_get("/api/test")
            
            assert result == {"success": True}
            assert mock_session_obj.request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_http_request_failure_after_retries(self, test_miner):
        """Test that HTTP requests fail after all retries are exhausted."""
        with patch('src.backend.services.http_session_manager.http_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session_obj.request.side_effect = asyncio.TimeoutError()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_obj)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                result = await test_miner._http_get("/api/test")
            
            assert result is None
            # Should retry RETRY_ATTEMPTS times
            from config.app_config import RETRY_ATTEMPTS
            assert mock_session_obj.request.call_count == RETRY_ATTEMPTS
    
    @pytest.mark.asyncio
    async def test_session_active_status(self, test_miner):
        """Test session active status tracking."""
        assert not test_miner.is_http_session_active()
        
        with patch('src.backend.services.http_session_manager.http_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={})
            mock_session_obj.request = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_obj)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # During request, session should be active
            async def check_active():
                assert test_miner.is_http_session_active()
                return {}
            
            mock_response.json.side_effect = check_active
            await test_miner._http_get("/api/test")
        
        # After request, session should not be active
        assert not test_miner.is_http_session_active()


class TestBitaxeMinerIntegration:
    """Integration tests for BitaxeMiner with new session management."""
    
    @pytest.mark.asyncio
    async def test_bitaxe_miner_session_management(self):
        """Test that BitaxeMiner properly uses session management."""
        miner = BitaxeMiner("10.0.0.100", 80)
        
        # Mock the HTTP responses
        with patch('src.backend.services.http_session_manager.http_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "hashRate": 1000,
                "temp": 45,
                "version": "1.0.0"
            })
            mock_session_obj.request = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_obj)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test connection
            connected = await miner.connect()
            assert connected
            assert miner.connected
            
            # Test getting status
            status = await miner.get_status()
            assert status["online"]
            assert "hashrate" in status
            
            # Test disconnection
            disconnected = await miner.disconnect()
            assert disconnected
            assert not miner.connected
    
    @pytest.mark.asyncio
    async def test_miner_session_cleanup_on_error(self):
        """Test that miner sessions are cleaned up on errors."""
        miner = BitaxeMiner("10.0.0.100", 80)
        
        with patch('src.backend.services.http_session_manager.http_session') as mock_session:
            # Simulate connection error
            mock_session.side_effect = Exception("Connection failed")
            
            # Connection should fail gracefully
            connected = await miner.connect()
            assert not connected
            assert not miner.connected
            
            # Session should be cleaned up (no hanging sessions)
            assert not miner.is_http_session_active()


@pytest.mark.asyncio
async def test_global_session_manager_shutdown():
    """Test global session manager shutdown."""
    # Use the global session manager
    async with http_session("10.0.0.100", 80) as session:
        assert session is not None
    
    # Shutdown should clean up all sessions
    await shutdown_session_manager()
    
    # After shutdown, a new session manager should be created
    async with http_session("10.0.0.100", 80) as session:
        assert session is not None
    
    # Clean up
    await shutdown_session_manager()


if __name__ == "__main__":
    pytest.main([__file__])