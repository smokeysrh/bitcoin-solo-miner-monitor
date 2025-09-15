#!/usr/bin/env python3
"""
Test script to check if miners are in the miner data manager
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.backend.utils.thread_safety import miner_data_manager

async def test_miner_data():
    """Test if miners are in the miner data manager"""
    
    print("🔧 Testing Miner Data Manager")
    print("=" * 30)
    
    try:
        miners = await miner_data_manager.get_all_miners()
        print(f"Miners in data manager: {len(miners)}")
        
        for miner in miners:
            print(f"- {miner.get('name', 'Unknown')} ({miner.get('ip_address', 'Unknown IP')})")
            print(f"  Status: {miner.get('status', 'Unknown')}")
            print(f"  Hashrate: {miner.get('hashrate', 0)} H/s")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_miner_data())