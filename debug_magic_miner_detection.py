#!/usr/bin/env python3
"""
Debug script to investigate Magic Miner get_device_info() method
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.backend.models.magic_miner import MagicMiner


async def debug_magic_miner_detection():
    """Debug Magic Miner detection step by step."""
    
    print("🔍 DEBUGGING MAGIC MINER get_device_info() METHOD\n")
    
    ip_address = "192.168.50.88"
    
    magic = MagicMiner(ip_address, 80)
    
    try:
        # Step 1: Connect
        print("Step 1: Connecting to Magic Miner...")
        connected = await magic.connect()
        print(f"  Connection result: {connected}")
        
        if not connected:
            print("❌ Connection failed, cannot proceed")
            return
        
        # Step 2: Test API endpoint directly
        print("\nStep 2: Testing /api/system/info endpoint...")
        try:
            api_response = await magic._http_get("/api/system/info")
            print(f"  API Response type: {type(api_response)}")
            print(f"  API Response: {api_response}")
            
            if api_response and isinstance(api_response, dict):
                hostname = str(api_response.get("hostname", "")).lower()
                asic_count = api_response.get("asicCount", 0)
                asic_model = str(api_response.get("ASICModel", "")).lower()
                
                print(f"  Hostname: '{hostname}'")
                print(f"  ASIC Count: {asic_count}")
                print(f"  ASIC Model: '{asic_model}'")
                
                # Test indicators
                magic_api_indicators = [
                    "magic" in hostname,
                    "magicminer" in hostname,
                    asic_count >= 9,
                    (asic_count >= 9 and "bm1368" in asic_model),
                ]
                
                print(f"  Magic indicators: {magic_api_indicators}")
                print(f"  Any indicator true: {any(magic_api_indicators)}")
            
        except Exception as e:
            print(f"  API Error: {str(e)}")
        
        # Step 3: Test HTML endpoints
        print("\nStep 3: Testing HTML endpoints...")
        try:
            main_html = await magic._http_get_text("/")
            print(f"  Main page length: {len(main_html) if main_html else 0}")
            if main_html:
                print(f"  Main page preview: {main_html[:200]}...")
        except Exception as e:
            print(f"  Main page error: {str(e)}")
        
        # Step 4: Call get_device_info
        print("\nStep 4: Calling get_device_info()...")
        device_info = await magic.get_device_info()
        print(f"  Device info result: {device_info}")
        
        # Step 5: Check internal state
        print(f"\nStep 5: Internal state check...")
        print(f"  magic.device_info: {magic.device_info}")
        
        await magic.disconnect()
        
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_magic_miner_detection())