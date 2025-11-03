#!/usr/bin/env python3
"""
Debug script to investigate miner detection logic issues for 192.168.50.88
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.backend.models.miner_factory import MinerFactory


async def debug_detection_logic():
    """Debug the miner detection logic for 192.168.1.85."""
    
    print("🔍 DEBUGGING MINER DETECTION LOGIC FOR 192.168.1.85\n")
    
    ip_address = "192.168.1.85"
    open_ports = [80]
    
    print(f"Testing MinerFactory.detect_miner_type() for {ip_address} with ports {open_ports}")
    
    try:
        # Call the detection method directly
        result = await MinerFactory.detect_miner_type(ip_address, open_ports)
        
        if result:
            print(f"✅ Detection successful!")
            print(f"   Type: {result.get('type')}")
            print(f"   IP: {result.get('ip_address')}")
            print(f"   Port: {result.get('port')}")
            print(f"   Device Info: {result.get('device_info', {})}")
        else:
            print(f"❌ Detection failed - returned empty result")
            
    except Exception as e:
        print(f"💥 Detection error: {str(e)}")
        import traceback
        traceback.print_exc()


async def debug_individual_miner_types():
    """Test each miner type detection individually."""
    
    print("\n=== INDIVIDUAL MINER TYPE DETECTION ===\n")
    
    ip_address = "192.168.1.85"
    
    # Test Bitaxe detection
    print("Testing Bitaxe detection:")
    try:
        from src.backend.models.bitaxe_miner import BitaxeMiner
        
        bitaxe = BitaxeMiner(ip_address, 80)
        connected = await bitaxe.connect()
        
        if connected:
            print("  ✅ Bitaxe connection successful")
            device_info = await bitaxe.get_device_info()
            print(f"  📋 Device info: {device_info}")
            await bitaxe.disconnect()
        else:
            print("  ❌ Bitaxe connection failed")
            
    except Exception as e:
        print(f"  💥 Bitaxe error: {str(e)}")
    
    # Test Magic Miner detection
    print("\nTesting Magic Miner detection:")
    try:
        from src.backend.models.magic_miner import MagicMiner
        
        magic = MagicMiner(ip_address, 80)
        connected = await magic.connect()
        
        if connected:
            print("  ✅ Magic Miner connection successful")
            device_info = await magic.get_device_info()
            print(f"  📋 Device info: {device_info}")
            await magic.disconnect()
        else:
            print("  ❌ Magic Miner connection failed")
            
    except Exception as e:
        print(f"  💥 Magic Miner error: {str(e)}")


async def debug_fingerprinting():
    """Test the fingerprinting system directly."""
    
    print("\n=== FINGERPRINTING SYSTEM DEBUG ===\n")
    
    ip_address = "192.168.1.85"
    
    try:
        from src.backend.models.device_fingerprinting import DeviceFingerprinter
        
        fingerprinter = DeviceFingerprinter(ip_address, 80)
        result = await fingerprinter.fingerprint_device()
        
        if result:
            print(f"✅ Fingerprinting successful!")
            print(f"   Device Type: {result.device_type.value}")
            print(f"   Model: {result.model}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Method: {result.detection_method}")
            print(f"   Characteristics: {list(result.characteristics.keys())}")
        else:
            print(f"❌ Fingerprinting failed")
            
    except Exception as e:
        print(f"💥 Fingerprinting error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    async def main():
        await debug_detection_logic()
        await debug_individual_miner_types()
        await debug_fingerprinting()
        
        print("\n🏁 Detection debug complete!")
    
    asyncio.run(main())