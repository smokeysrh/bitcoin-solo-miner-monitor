#!/usr/bin/env python3
"""
Test Updated Bitaxe Detection

Test the updated BitaxeMiner class with improved BM1370 detection logic.
"""

import asyncio
import sys
import os
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.backend.models.bitaxe_miner import BitaxeMiner


async def test_real_device_detection():
    """Test detection with the real device at 192.168.50.85."""
    
    print("🧪 TESTING UPDATED BITAXE DETECTION")
    print("=" * 50)
    
    # Create BitaxeMiner instance
    miner = BitaxeMiner("192.168.50.85", 80)
    
    print(f"\n🔌 Connecting to {miner.ip_address}...")
    
    # Connect to the device
    connected = await miner.connect()
    
    if not connected:
        print("❌ Failed to connect to device")
        return
    
    print("✅ Connected successfully")
    
    # Get device info using the updated detection logic
    print(f"\n📊 Getting device information...")
    device_info = await miner.get_device_info()
    
    if device_info:
        print(f"\n🎯 DETECTION RESULTS:")
        print(f"   Device Type: {device_info.get('type', 'Unknown')}")
        print(f"   Model: {device_info.get('model', 'Unknown')}")
        print(f"   ASIC Model: {device_info.get('asic_model', 'Unknown')}")
        print(f"   ASIC Count: {device_info.get('asic_count', 0)}")
        print(f"   Board Version: {device_info.get('board_version', 'Unknown')}")
        print(f"   Firmware Version: {device_info.get('firmware_version', 'Unknown')}")
        print(f"   Hashrate: {device_info.get('hash_rate', 0)} GH/s")
        print(f"   Core Count: {device_info.get('core_count', 0)}")
        
        # Show additional characteristics
        print(f"\n🔍 ADDITIONAL CHARACTERISTICS:")
        print(f"   Hostname: {device_info.get('hostname', 'Unknown')}")
        print(f"   MAC Address: {device_info.get('mac_address', 'Unknown')}")
        print(f"   IDF Version: {device_info.get('idf_version', 'Unknown')}")
        
        # Save the results
        timestamp = "test_results"
        filename = f"bitaxe_detection_test_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(device_info, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {filename}")
        
        # Compare with expected results
        print(f"\n📋 ANALYSIS:")
        
        expected_model = "Bitaxe Gamma"  # CORRECTED: User confirmed this is actually a Gamma
        detected_model = device_info.get('model', 'Unknown')
        
        if detected_model == expected_model:
            print(f"   ✅ Correct detection: {detected_model}")
        else:
            print(f"   ❌ Incorrect detection: got '{detected_model}', expected '{expected_model}'")
        
        # Check key factors - updated understanding
        board_version = device_info.get('board_version', '')
        if board_version:
            print(f"   ℹ️  Board version {board_version} (modern Gammas can have 600+ versions)")
        
        core_count = device_info.get('core_count', 0)
        if core_count >= 2000:
            print(f"   ℹ️  High core count {core_count} (modern Gammas can have high core counts)")
        
        hashrate = device_info.get('hash_rate', 0)
        if hashrate > 1000:
            print(f"   ℹ️  High hashrate {hashrate} GH/s (modern Gammas can achieve 1+ TH/s)")
    
    else:
        print("❌ Failed to get device information")
    
    # Disconnect
    await miner.disconnect()
    print(f"\n🔌 Disconnected from device")


async def test_detection_scenarios():
    """Test detection with various simulated scenarios."""
    
    print(f"\n🔬 TESTING DETECTION SCENARIOS")
    print("-" * 30)
    
    # Create a test miner instance
    miner = BitaxeMiner("192.168.1.1", 80)  # Dummy IP
    
    # Test scenarios with different device_info configurations
    scenarios = [
        {
            "name": "Gamma with board 602 (modern Gamma)",
            "device_info": {
                "ASICModel": "BM1370",
                "asicCount": 1,
                "hashRate": 1100,
                "hostname": "bitaxe",
                "boardVersion": "602",
                "smallCoreCount": 2040,
                "frequency": 525,
                "power": 20
            },
            "expected": "Bitaxe Gamma"
        },
        {
            "name": "Gamma with board 300",
            "device_info": {
                "ASICModel": "BM1370", 
                "asicCount": 1,
                "hashRate": 600,
                "hostname": "bitaxe",
                "boardVersion": "300",
                "smallCoreCount": 1500,
                "frequency": 400,
                "power": 18
            },
            "expected": "Bitaxe Gamma"
        },
        {
            "name": "Gamma with BM1397",
            "device_info": {
                "ASICModel": "BM1397",
                "asicCount": 1,
                "hashRate": 450,
                "hostname": "bitaxe-gamma",
                "boardVersion": "250"
            },
            "expected": "Bitaxe Gamma"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n   Testing: {scenario['name']}")
        
        # Set the device_info for testing
        miner.device_info = scenario['device_info']
        
        # Test the detection logic
        asic_model = scenario['device_info']['ASICModel']
        asic_count = scenario['device_info']['asicCount']
        hashrate = scenario['device_info']['hashRate']
        hostname = scenario['device_info']['hostname']
        
        if asic_model.lower() == "bm1370":
            result = miner._differentiate_bm1370_models(hashrate, asic_count, hostname)
        else:
            result = miner._determine_bitaxe_model(asic_model, asic_count, hashrate, hostname)
        
        expected = scenario['expected']
        status = "✅" if result == expected else "❌"
        
        print(f"     Result: {result}")
        print(f"     Expected: {expected}")
        print(f"     Status: {status}")


if __name__ == "__main__":
    print("🚀 BITAXE DETECTION TEST SUITE")
    print("=" * 60)
    
    asyncio.run(test_real_device_detection())
    asyncio.run(test_detection_scenarios())