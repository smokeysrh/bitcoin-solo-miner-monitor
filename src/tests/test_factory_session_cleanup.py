"""
Test miner factory session cleanup functionality.
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.backend.models.miner_factory import MinerFactory
from src.backend.services.http_session_manager import HTTPSessionManager


async def test_factory_session_cleanup():
    """Test that MinerFactory properly handles session cleanup."""
    print("Testing MinerFactory session cleanup...")
    
    # Test 1: Test cleanup on connection failure
    print("1. Testing cleanup on connection failure...")
    
    with patch('src.backend.models.bitaxe_miner.BitaxeMiner.connect') as mock_connect:
        with patch('src.backend.models.bitaxe_miner.BitaxeMiner.disconnect') as mock_disconnect:
            # Simulate connection failure
            mock_connect.return_value = False
            mock_disconnect.return_value = True
            
            # Try to create miner
            miner = await MinerFactory.create_miner("bitaxe", "10.0.0.100", 80)
            
            print(f"   ✓ Miner creation result: {miner}")
            print(f"   ✓ Connect called: {mock_connect.called}")
            print(f"   ✓ Disconnect called: {mock_disconnect.called}")
            
            assert miner is None
            assert mock_connect.called
            assert mock_disconnect.called
    
    # Test 2: Test cleanup on exception
    print("2. Testing cleanup on exception...")
    
    with patch('src.backend.models.bitaxe_miner.BitaxeMiner.connect') as mock_connect:
        # Simulate exception during connection
        mock_connect.side_effect = Exception("Connection error")
        
        # Try to create miner
        miner = await MinerFactory.create_miner("bitaxe", "10.0.0.100", 80)
        
        print(f"   ✓ Miner creation result: {miner}")
        print(f"   ✓ Connect called: {mock_connect.called}")
        
        assert miner is None
        assert mock_connect.called
    
    # Test 3: Test successful creation
    print("3. Testing successful miner creation...")
    
    with patch('src.backend.models.bitaxe_miner.BitaxeMiner.connect') as mock_connect:
        with patch('src.backend.models.bitaxe_miner.BitaxeMiner.get_device_info') as mock_device_info:
            # Simulate successful connection
            mock_connect.return_value = True
            mock_device_info.return_value = {"type": "Bitaxe", "model": "BM1366"}
            
            # Try to create miner
            miner = await MinerFactory.create_miner("bitaxe", "10.0.0.100", 80)
            
            print(f"   ✓ Miner creation result: {miner is not None}")
            print(f"   ✓ Connect called: {mock_connect.called}")
            print(f"   ✓ Miner type: {miner.get_miner_type() if miner else 'None'}")
            
            assert miner is not None
            assert mock_connect.called
            
            # Clean up
            if miner:
                await miner.disconnect()
    
    # Test 4: Test detection cleanup
    print("4. Testing detection cleanup...")
    
    with patch('src.backend.models.bitaxe_miner.BitaxeMiner.connect') as mock_connect:
        with patch('src.backend.models.bitaxe_miner.BitaxeMiner.disconnect') as mock_disconnect:
            with patch('src.backend.models.bitaxe_miner.BitaxeMiner.get_device_info') as mock_device_info:
                # Simulate successful detection
                mock_connect.return_value = True
                mock_disconnect.return_value = True
                mock_device_info.return_value = {"type": "Bitaxe", "model": "BM1366"}
                
                # Test detection
                result = await MinerFactory.detect_miner_type("10.0.0.100", [80])
                
                print(f"   ✓ Detection result: {result}")
                print(f"   ✓ Connect called: {mock_connect.called}")
                print(f"   ✓ Disconnect called: {mock_disconnect.called}")
                
                assert "type" in result
                assert result["type"] == "bitaxe"
                assert mock_connect.called
                assert mock_disconnect.called
    
    # Test 5: Test unsupported miner type
    print("5. Testing unsupported miner type...")
    
    miner = await MinerFactory.create_miner("unsupported", "10.0.0.100", 80)
    print(f"   ✓ Unsupported miner result: {miner}")
    assert miner is None
    
    print("\n✅ All MinerFactory session cleanup tests passed!")


if __name__ == "__main__":
    asyncio.run(test_factory_session_cleanup())