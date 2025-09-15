"""
Test HTTP session handling in miner implementations.
"""

import asyncio
import pytest
import logging
from unittest.mock import AsyncMock, patch, MagicMock

from src.backend.models.bitaxe_miner import BitaxeMiner
from src.backend.models.magic_miner import MagicMiner
from src.backend.models.avalon_nano_miner import AvalonNanoMiner
from src.backend.models.miner_factory import MinerFactory
from src.backend.services.http_session_manager import HTTPSessionManager

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestMinerSessionHandling:
    """Test proper HTTP session handling in miner implementations."""
    
    @pytest.fixture
    async def session_manager(self):
        """Create a test session manager."""
        manager = HTTPSessionManager(max_sessions=5, session_timeout=60)
        await manager.start()
        yield manager
        await manager.stop()
    
    async def test_bitaxe_session_cleanup_on_disconnect(self):
        """Test that BitaxeMiner properly cleans up sessions on disconnect."""
        with patch('src.backend.services.http_session_manager.get_session_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            miner = BitaxeMiner("10.0.0.100", 80)
            miner._http_session_active = True  # Simulate active session
            
            # Test disconnect
            result = await miner.disconnect()
            
            assert result is True
            assert miner.connected is False
            mock_manager.close_session.assert_called_once_with("10.0.0.100", 80)
    
    async def test_magic_miner_session_cleanup_on_disconnect(self):
        """Test that MagicMiner properly cleans up sessions on disconnect."""
        with patch('src.backend.services.http_session_manager.get_session_manager') as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            miner = MagicMiner("10.0.0.101", 80)
            miner._http_session_active = True  # Simulate active session
            
            # Test disconnect
            result = await miner.disconnect()
            
            assert result is True
            assert miner.connected is False
            mock_manager.close_session.assert_called_once_with("10.0.0.101", 80)
    
    async def test_avalon_nano_disconnect_no_session_cleanup(self):
        """Test that AvalonNanoMiner disconnect works (no HTTP sessions)."""
        miner = AvalonNanoMiner("10.0.0.102", 4028)
        miner.connected = True
        
        # Test disconnect
        result = await miner.disconnect()
        
        assert result is True
        assert miner.connected is False
    
    async def test_miner_factory_cleanup_on_connection_failure(self):
        """Test that MinerFactory cleans up sessions when connection fails."""
        with patch('src.backend.models.bitaxe_miner.BitaxeMiner.connect') as mock_connect:
            with patch('src.backend.models.bitaxe_miner.BitaxeMiner.disconnect') as mock_disconnect:
                with patch('src.backend.services.http_session_manager.get_session_manager') as mock_get_manager:
                    mock_manager = AsyncMock()
                    mock_get_manager.return_value = mock_manager
                    
                    # Simulate connection failure
                    mock_connect.return_value = False
                    mock_disconnect.return_value = True
                    
                    # Try to create miner
                    miner = await MinerFactory.create_miner("bitaxe", "10.0.0.100", 80)
                    
                    assert miner is None
                    mock_connect.assert_called_once()
                    mock_disconnect.assert_called_once()
    
    async def test_miner_factory_cleanup_on_exception(self):
        """Test that MinerFactory cleans up sessions when exception occurs."""
        with patch('src.backend.models.bitaxe_miner.BitaxeMiner.connect') as mock_connect:
            with patch('src.backend.services.http_session_manager.get_session_manager') as mock_get_manager:
                mock_manager = AsyncMock()
                mock_get_manager.return_value = mock_manager
                
                # Simulate exception during connection
                mock_connect.side_effect = Exception("Connection error")
                
                # Try to create miner
                miner = await MinerFactory.create_miner("bitaxe", "10.0.0.100", 80)
                
                assert miner is None
                mock_connect.assert_called_once()
    
    async def test_miner_factory_detection_cleanup(self):
        """Test that MinerFactory detection properly cleans up sessions."""
        with patch('src.backend.models.bitaxe_miner.BitaxeMiner.connect') as mock_connect:
            with patch('src.backend.models.bitaxe_miner.BitaxeMiner.disconnect') as mock_disconnect:
                with patch('src.backend.models.bitaxe_miner.BitaxeMiner.get_device_info') as mock_device_info:
                    with patch('src.backend.services.http_session_manager.get_session_manager') as mock_get_manager:
                        mock_manager = AsyncMock()
                        mock_get_manager.return_value = mock_manager
                        
                        # Simulate successful detection
                        mock_connect.return_value = True
                        mock_disconnect.return_value = True
                        mock_device_info.return_value = {"type": "Bitaxe", "model": "BM1366"}
                        
                        # Test detection
                        result = await MinerFactory.detect_miner_type("10.0.0.100", [80])
                        
                        assert result["type"] == "bitaxe"
                        assert result["ip_address"] == "10.0.0.100"
                        assert result["port"] == 80
                        
                        mock_connect.assert_called_once()
                        mock_disconnect.assert_called_once()
                        mock_manager.close_session.assert_called_once_with("10.0.0.100", 80)
    
    async def test_http_client_mixin_session_context(self):
        """Test that HTTPClientMixin properly manages session context."""
        from src.backend.models.http_client_mixin import HTTPClientMixin
        
        class TestMiner(HTTPClientMixin):
            def __init__(self, ip_address, port):
                super().__init__()
                self.ip_address = ip_address
                self.port = port
                self.base_url = f"http://{ip_address}:{port}"
        
        with patch('src.backend.services.http_session_manager.http_session') as mock_session:
            mock_session_obj = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session_obj)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            miner = TestMiner("10.0.0.100", 80)
            
            # Test session context
            async with miner._http_session_context() as session:
                assert miner._http_session_active is True
                assert session == mock_session_obj
            
            assert miner._http_session_active is False
    
    async def test_http_client_mixin_request_with_retry(self):
        """Test that HTTPClientMixin properly handles requests with retry logic."""
        from src.backend.models.http_client_mixin import HTTPClientMixin
        import aiohttp
        
        class TestMiner(HTTPClientMixin):
            def __init__(self, ip_address, port):
                super().__init__()
                self.ip_address = ip_address
                self.port = port
                self.base_url = f"http://{ip_address}:{port}"
        
        with patch('src.backend.services.http_session_manager.http_session') as mock_session_ctx:
            # Mock session and response
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"status": "ok"})
            
            mock_session.request = AsyncMock()
            mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            
            miner = TestMiner("10.0.0.100", 80)
            
            # Test successful request
            result = await miner._http_get("/api/status")
            
            assert result == {"status": "ok"}
            mock_session.request.assert_called_once_with("GET", "http://10.0.0.100:80/api/status")


async def run_tests():
    """Run all tests."""
    test_instance = TestMinerSessionHandling()
    
    tests = [
        test_instance.test_bitaxe_session_cleanup_on_disconnect,
        test_instance.test_magic_miner_session_cleanup_on_disconnect,
        test_instance.test_avalon_nano_disconnect_no_session_cleanup,
        test_instance.test_miner_factory_cleanup_on_connection_failure,
        test_instance.test_miner_factory_cleanup_on_exception,
        test_instance.test_miner_factory_detection_cleanup,
        test_instance.test_http_client_mixin_session_context,
        test_instance.test_http_client_mixin_request_with_retry,
    ]
    
    for test in tests:
        try:
            await test()
            logger.info(f"✓ {test.__name__} passed")
        except Exception as e:
            logger.error(f"✗ {test.__name__} failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_tests())