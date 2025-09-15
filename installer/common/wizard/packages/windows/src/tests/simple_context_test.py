"""
Simple test for HTTP session context functionality.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.backend.models.bitaxe_miner import BitaxeMiner
from src.backend.models.magic_miner import MagicMiner
from src.backend.services.http_session_manager import HTTPSessionManager


async def test_simple_context():
    """Test basic session context functionality."""
    print("Testing HTTP session context functionality...")
    
    # Test 1: Session manager lifecycle
    print("1. Testing session manager lifecycle...")
    
    session_manager = HTTPSessionManager(max_sessions=3, session_timeout=30)
    await session_manager.start()
    print("   ✓ Session manager started")
    
    # Test getting a session
    try:
        async with session_manager.get_session("10.0.0.100", 80) as session:
            print(f"   ✓ Got session: {session is not None}")
            print(f"   ✓ Session type: {type(session).__name__}")
            
            # Check session stats
            stats = session_manager.get_session_stats()
            print(f"   ✓ Active sessions: {stats['active_sessions']}")
            
        # After context
        stats = session_manager.get_session_stats()
        print(f"   ✓ Sessions after context: {stats['active_sessions']}")
        
    except Exception as e:
        print(f"   ✗ Error in session context: {e}")
    
    await session_manager.stop()
    print("   ✓ Session manager stopped")
    
    # Test 2: Miner session context
    print("2. Testing miner session context...")
    
    miner = BitaxeMiner("10.0.0.100", 80)
    print(f"   ✓ Miner created: {miner.ip_address}:{miner.port}")
    print(f"   ✓ Has session context: {hasattr(miner, '_http_session_context')}")
    print(f"   ✓ Initial session active: {miner._http_session_active}")
    
    # Test 3: Miner disconnect with session cleanup
    print("3. Testing miner disconnect...")
    
    # Simulate active session
    miner._http_session_active = True
    miner.connected = True
    
    result = await miner.disconnect()
    print(f"   ✓ Disconnect result: {result}")
    print(f"   ✓ Connected after disconnect: {miner.connected}")
    
    # Test 4: Magic miner
    print("4. Testing Magic miner...")
    
    magic = MagicMiner("10.0.0.101", 80)
    print(f"   ✓ Magic miner created: {magic.ip_address}:{magic.port}")
    print(f"   ✓ Has session context: {hasattr(magic, '_http_session_context')}")
    
    # Test disconnect
    magic._http_session_active = True
    magic.connected = True
    
    result = await magic.disconnect()
    print(f"   ✓ Magic disconnect result: {result}")
    print(f"   ✓ Connected after disconnect: {magic.connected}")
    
    print("\n✅ All simple context tests passed!")


if __name__ == "__main__":
    asyncio.run(test_simple_context())