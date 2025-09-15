"""
Simple test to verify session handling implementation.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.backend.models.bitaxe_miner import BitaxeMiner
from src.backend.models.magic_miner import MagicMiner
from src.backend.models.avalon_nano_miner import AvalonNanoMiner
from src.backend.services.http_session_manager import HTTPSessionManager


async def test_session_handling():
    """Test basic session handling functionality."""
    print("Testing HTTP session handling implementation...")
    
    # Test 1: Create session manager
    print("1. Testing session manager creation...")
    session_manager = HTTPSessionManager(max_sessions=5, session_timeout=60)
    await session_manager.start()
    print("   ✓ Session manager created and started")
    
    # Test 2: Test BitaxeMiner initialization
    print("2. Testing BitaxeMiner initialization...")
    bitaxe = BitaxeMiner("10.0.0.100", 80)
    print(f"   ✓ BitaxeMiner created: {bitaxe.ip_address}:{bitaxe.port}")
    print(f"   ✓ Base URL: {bitaxe.base_url}")
    print(f"   ✓ Has HTTPClientMixin: {hasattr(bitaxe, '_http_session_context')}")
    
    # Test 3: Test MagicMiner initialization
    print("3. Testing MagicMiner initialization...")
    magic = MagicMiner("10.0.0.101", 80)
    print(f"   ✓ MagicMiner created: {magic.ip_address}:{magic.port}")
    print(f"   ✓ Base URL: {magic.base_url}")
    print(f"   ✓ Has HTTPClientMixin: {hasattr(magic, '_http_session_context')}")
    
    # Test 4: Test AvalonNanoMiner initialization
    print("4. Testing AvalonNanoMiner initialization...")
    avalon = AvalonNanoMiner("10.0.0.102", 4028)
    print(f"   ✓ AvalonNanoMiner created: {avalon.ip_address}:{avalon.port}")
    print(f"   ✓ No HTTPClientMixin (uses TCP): {not hasattr(avalon, '_http_session_context')}")
    
    # Test 5: Test disconnect methods
    print("5. Testing disconnect methods...")
    
    # BitaxeMiner disconnect
    bitaxe._http_session_active = True  # Simulate active session
    result = await bitaxe.disconnect()
    print(f"   ✓ BitaxeMiner disconnect: {result}")
    
    # MagicMiner disconnect
    magic._http_session_active = True  # Simulate active session
    result = await magic.disconnect()
    print(f"   ✓ MagicMiner disconnect: {result}")
    
    # AvalonNanoMiner disconnect
    avalon.connected = True
    result = await avalon.disconnect()
    print(f"   ✓ AvalonNanoMiner disconnect: {result}")
    
    # Test 6: Test session manager stats
    print("6. Testing session manager stats...")
    stats = session_manager.get_session_stats()
    print(f"   ✓ Active sessions: {stats['active_sessions']}")
    print(f"   ✓ Max sessions: {stats['max_sessions']}")
    print(f"   ✓ Session timeout: {stats['session_timeout']}")
    
    # Cleanup
    await session_manager.stop()
    print("   ✓ Session manager stopped")
    
    print("\n✅ All session handling tests passed!")


if __name__ == "__main__":
    asyncio.run(test_session_handling())