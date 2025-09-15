#!/usr/bin/env python3
"""
Test script to check if the backend starts without errors
"""

import sys
import os
import asyncio

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def test_backend():
    """Test if backend services can be imported and initialized"""
    try:
        print("Testing backend imports...")
        
        # Test imports
        from src.backend.services.miner_manager import MinerManager
        from src.backend.services.data_storage import DataStorage
        from src.backend.api.api_service import APIService
        print("✓ All imports successful")
        
        # Test service initialization
        print("Testing service initialization...")
        data_storage = DataStorage()
        miner_manager = MinerManager()
        api_service = APIService(miner_manager, data_storage)
        print("✓ All services initialized")
        
        # Test data storage initialization
        print("Testing data storage...")
        await data_storage.initialize()
        print("✓ Data storage initialized")
        
        # Test getting miners (should return empty list initially)
        print("Testing get_miners...")
        miners = await miner_manager.get_miners()
        print(f"✓ get_miners returned: {miners}")
        
        # Cleanup
        await data_storage.close()
        print("✓ Cleanup completed")
        
        print("\n🎉 All backend tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Backend test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_backend())
    sys.exit(0 if success else 1)