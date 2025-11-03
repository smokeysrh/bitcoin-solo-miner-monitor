#!/usr/bin/env python3
"""
Test script for device fingerprinting.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.backend.models.device_fingerprinting import DeviceFingerprinter


async def test_fingerprinting():
    """Test device fingerprinting on known devices."""
    
    # Test devices
    test_devices = [
        ("192.168.50.88", "Magic Miner"),  # Known Magic Miner
        ("192.168.50.84", "Bitaxe Hex"),   # Known Bitaxe
        ("192.168.50.86", "NerdQAxe++"),   # Known NerdQAxe
    ]
    
    for ip, expected in test_devices:
        print(f"\n=== Testing {ip} (Expected: {expected}) ===")
        
        try:
            fingerprinter = DeviceFingerprinter(ip, 80)
            result = await fingerprinter.fingerprint_device()
            
            if result:
                print(f"✅ Detected: {result.device_type.value}")
                print(f"   Model: {result.model}")
                print(f"   Confidence: {result.confidence:.2f}")
                print(f"   Method: {result.detection_method}")
                print(f"   Characteristics: {list(result.characteristics.keys())}")
                
                # Check if detection matches expectation
                expected_lower = expected.lower()
                detected_lower = result.device_type.value.lower()
                
                correct = (
                    ("magic" in expected_lower and "magic" in detected_lower) or
                    ("bitaxe" in expected_lower and "bitaxe" in detected_lower) or
                    ("nerd" in expected_lower and "nerd" in detected_lower) or
                    (expected_lower in detected_lower) or
                    (detected_lower in expected_lower)
                )
                
                if correct:
                    print("✅ CORRECT DETECTION")
                else:
                    print("❌ INCORRECT DETECTION")
            else:
                print("❌ No device detected")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_fingerprinting())