#!/usr/bin/env python3
"""
Test script to check if miners are in the database
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.backend.services.data_storage import DataStorage

async def test_database():
    """Test if miners are in the database"""
    
    print("🔧 Testing Database")
    print("=" * 20)
    
    # Initialize data storage
    data_storage = DataStorage()
    await data_storage.initialize()
    
    try:
        configs = await data_storage.get_all_miner_configs()
        print(f"Miner configs in database: {len(configs)}")
        
        for config in configs:
            print(f"- {config.get('name', 'Unknown')} ({config.get('ip_address', 'Unknown IP')})")
            print(f"  ID: {config.get('id', 'Unknown')}")
            print(f"  Type: {config.get('type', 'Unknown')}")
            print(f"  Status: {config.get('status', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await data_storage.close()

if __name__ == "__main__":
    asyncio.run(test_database())