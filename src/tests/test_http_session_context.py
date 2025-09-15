"""
Test HTTP session context manager functionality.
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.backend.models.bitaxe_miner import BitaxeMiner
from src.backend.models.magic_miner import MagicMiner
from src.backend.services.http_session_manager import HTTPSessionManager, http_session


async def test_http_session_context():
    """Test HTTP session context manager functionality."""
    print("Testing HTTP session context managers...")
    
    # Test 1: Test session manager context
    print("1. Testing session manager context...")
    
    session_manager = HTTPSessionManager(max_sessions=3, session_timeout=30)
    await session_manager.start()
    
    try:
        # Test getting a session
        async with session_manager.get_session("10.0.0.100", 80) as session:
            print(f"   ✓ Got session: {session is not None}")
            print(f"   ✓ Session closed: {session.closed}")
            
            # Check session stats
            stats = session_manager.get_session_stats()
            print(f"   ✓ Active sessions: {stats['active_sessions']}")
            assert stats['active_sessions'] == 1
        
        # After context, session should still be in pool but available for reuse
        stats = session_manager.get_session_stats()
        print(f"   ✓ Sessions after context: {stats['active_sessions']}")
        
    finally:
        await session_manager.stop()
    
    # Test 2: Test convenience function
    print("2. Testing convenience http_session function...")
    
    with patch('src.backend.services.http_session_manager.get_session_manager') as mock_get_manager:
        mock_manager = AsyncMock()
        mock_session = AsyncMock()
        mock_manager.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_manager.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_get_manager.return_value = mock_manager
        
        async with http_session("10.0.0.100", 80) as session:
            print(f"   ✓ Got session from convenience function: {session is not None}")
            assert session == mock_session
        
        mock_get_manager.assert_called_once()
        mock_manager.get_session.assert_called_once_with("10.0.0.100", 80)
    
    # Test 3: Test HTTPClientMixin session context
    print("3. Testing HTTPClientMixin session context...")
    
    with patch('src.backend.services.http_session_manager.http_session') as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
        
        miner = BitaxeMiner("10.0.0.100", 80)
        
        # Test session context
        async with miner._http_session_context() as session:
            print(f"   ✓ Miner session active: {miner._http_session_active}")
            print(f"   ✓ Got session: {session is not None}")
            assert miner._http_session_active is True
            assert session == mock_session
        
        print(f"   ✓ Miner session active after context: {miner._http_session_active}")
        assert miner._http_session_active is False
        
        mock_session_ctx.assert_called_once_with("10.0.0.100", 80)
    
    # Test 4: Test HTTP request with session context
    print("4. Testing HTTP request with session context...")
    
    with patch('src.backend.services.http_session_manager.http_session') as mock_session_ctx:
        # Mock session and response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"hashrate": 1000, "temperature": 45})
        
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
        
        miner = BitaxeMiner("10.0.0.100", 80)
        
        # Test HTTP GET request
        result = await miner._http_get("/api/system/info")
        
        print(f"   ✓ HTTP GET result: {result}")
        print(f"   ✓ Session context called: {mock_session_ctx.called}")
        print(f"   ✓ Request made: {mock_session.request.called}")
        
        assert result == {"hashrate": 1000, "temperature": 45}
        mock_session_ctx.assert_called_with("10.0.0.100", 80)
        mock_session.request.assert_called_with("GET", "http://10.0.0.100:80/api/system/info")
    
    # Test 5: Test error handling in session context
    print("5. Testing error handling in session context...")
    
    with patch('src.backend.services.http_session_manager.http_session') as mock_session_ctx:
        # Mock session that raises an exception
        mock_session_ctx.side_effect = Exception("Connection failed")
        
        miner = BitaxeMiner("10.0.0.100", 80)
        
        # Test that exception is properly handled
        result = await miner._http_get("/api/system/info")
        
        print(f"   ✓ HTTP GET result on error: {result}")
        print(f"   ✓ Session active after error: {miner._http_session_active}")
        
        assert result is None
        assert miner._http_session_active is False
    
    # Test 6: Test session cleanup on disconnect
    print("6. Testing session cleanup on disconnect...")
    
    with patch('src.backend.services.http_session_manager.get_session_manager') as mock_get_manager:
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        
        miner = BitaxeMiner("10.0.0.100", 80)
        miner._http_session_active = True  # Simulate active session
        miner.connected = True
        
        # Test disconnect
        result = await miner.disconnect()
        
        print(f"   ✓ Disconnect result: {result}")
        print(f"   ✓ Session cleanup called: {mock_manager.close_session.called}")
        
        assert result is True
        assert miner.connected is False
        mock_manager.close_session.assert_called_once_with("10.0.0.100", 80)
    
    print("\n✅ All HTTP session context tests passed!")


if __name__ == "__main__":
    asyncio.run(test_http_session_context())