#!/usr/bin/env python3
"""
Debug script to investigate Bitaxe Gamma vs Hex detection issues.

This script tests the detection logic with various BM1370 device configurations
to understand why Gammas are being misidentified as Hexes.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.backend.models.bitaxe_miner import BitaxeMiner


def test_bitaxe_model_detection():
    """Test the _determine_bitaxe_model method with various BM1370 configurations."""
    
    print("🔍 TESTING BITAXE MODEL DETECTION LOGIC\n")
    
    # Create a BitaxeMiner instance for testing
    miner = BitaxeMiner("192.168.1.1", 80)  # Dummy IP for testing
    
    # Test cases based on real-world Bitaxe configurations
    test_cases = [
        # Format: (asic_model, asic_count, hash_rate_gh, hostname, expected_model, description)
        
        # Bitaxe Hex cases (BM1370, higher hashrate)
        ("BM1370", 1, 1000, "bitaxe", "Bitaxe Hex", "Hex: 1 TH/s"),
        ("BM1370", 1, 1200, "bitaxe", "Bitaxe Hex", "Hex: 1.2 TH/s"),
        ("BM1370", 1, 900, "bitaxe", "Bitaxe Hex", "Hex: 900 GH/s"),
        
        # Bitaxe Gamma cases (BM1370, lower hashrate)
        ("BM1370", 1, 400, "bitaxe", "Bitaxe Gamma", "Gamma: 400 GH/s"),
        ("BM1370", 1, 500, "bitaxe", "Bitaxe Gamma", "Gamma: 500 GH/s"),
        ("BM1370", 1, 600, "bitaxe", "Bitaxe Gamma", "Gamma: 600 GH/s"),
        
        # Edge cases
        ("BM1370", 1, 750, "bitaxe", "Bitaxe Gamma", "Edge: 750 GH/s (should be Gamma)"),
        ("BM1370", 1, 800, "bitaxe", "Bitaxe Hex", "Edge: 800 GH/s (should be Hex)"),
        ("BM1370", 1, 0, "bitaxe", "Bitaxe Hex", "No hashrate data (defaults to Hex)"),
        
        # Multiple ASICs (unusual)
        ("BM1370", 2, 1000, "bitaxe", "Bitaxe Hex", "Multiple ASICs"),
        
        # Other ASIC models for comparison
        ("BM1366", 1, 500, "bitaxe", "Bitaxe Ultra", "Ultra: BM1366"),
        ("BM1368", 1, 15000, "bitaxe", "Bitaxe Supra", "Supra: BM1368"),
        ("BM1397", 1, 400, "bitaxe", "Bitaxe Gamma", "Gamma: BM1397"),
    ]
    
    print("Testing _determine_bitaxe_model with various configurations:\n")
    
    for i, (asic_model, asic_count, hash_rate, hostname, expected, description) in enumerate(test_cases, 1):
        result = miner._determine_bitaxe_model(asic_model, asic_count, hash_rate, hostname)
        
        status = "✅" if result == expected else "❌"
        
        print(f"{i:2d}. {status} {description}")
        print(f"    Input:    ASIC={asic_model}, Count={asic_count}, Rate={hash_rate}GH/s")
        print(f"    Expected: {expected}")
        print(f"    Got:      {result}")
        
        if result != expected:
            print(f"    ⚠️  MISMATCH DETECTED!")
        
        print()


def analyze_detection_logic():
    """Analyze the current detection logic and identify issues."""
    
    print("📊 ANALYSIS OF CURRENT DETECTION LOGIC\n")
    
    print("Current BM1370 Detection Logic:")
    print("1. If hashrate > 0:")
    print("   - Convert GH/s to TH/s (divide by 1000)")
    print("   - If TH/s >= 0.8 (800+ GH/s) → Bitaxe Hex")
    print("   - If TH/s >= 0.3 (300-800 GH/s) → Bitaxe Gamma")
    print("   - If TH/s < 0.3 (< 300 GH/s) → Bitaxe Gamma")
    print("2. If no hashrate data:")
    print("   - If ASIC count == 1 → Default to Bitaxe Hex")
    print("   - If ASIC count != 1 → Default to Bitaxe Hex")
    print()
    
    print("IDENTIFIED ISSUES:")
    print("❌ Issue 1: Default behavior favors Hex over Gamma")
    print("   - When no hashrate data is available, always defaults to Hex")
    print("   - This causes Gammas to be misidentified as Hexes")
    print()
    
    print("❌ Issue 2: Hashrate thresholds may be inaccurate")
    print("   - 800 GH/s threshold might be too low for some Hex variants")
    print("   - Some Gamma variants might exceed 600 GH/s")
    print()
    
    print("❌ Issue 3: No consideration of other factors")
    print("   - Firmware version patterns not used")
    print("   - Board version not considered")
    print("   - Hostname patterns not leveraged")
    print()


def propose_improved_logic():
    """Propose improved detection logic."""
    
    print("💡 PROPOSED IMPROVED DETECTION LOGIC\n")
    
    print("Enhanced BM1370 Detection Strategy:")
    print("1. Primary: Use hashrate ranges (if available)")
    print("   - Hex: 800+ GH/s (confirmed high-performance)")
    print("   - Gamma: 200-799 GH/s (typical Gamma range)")
    print("   - Unknown: < 200 GH/s (investigate further)")
    print()
    
    print("2. Secondary: Use firmware/board version patterns")
    print("   - Check for model-specific version strings")
    print("   - Look for board revision indicators")
    print()
    
    print("3. Tertiary: Use hostname patterns")
    print("   - Look for user-configured model hints")
    print("   - Check for default naming patterns")
    print()
    
    print("4. Fallback: Conservative default")
    print("   - When uncertain, default to Gamma (more common)")
    print("   - Or return 'Bitaxe (BM1370)' for manual identification")
    print()


def create_test_device_data():
    """Create test device data for validation."""
    
    print("🧪 CREATING TEST DEVICE DATA\n")
    
    # Simulate device API responses for different models
    test_devices = {
        "bitaxe_hex_1": {
            "ASICModel": "BM1370",
            "asicCount": 1,
            "hashRate": 1000,  # 1 TH/s
            "hostname": "bitaxe-hex",
            "version": "2.1.4",
            "boardVersion": "204",
            "description": "Typical Bitaxe Hex"
        },
        "bitaxe_gamma_1": {
            "ASICModel": "BM1370", 
            "asicCount": 1,
            "hashRate": 450,  # 450 GH/s
            "hostname": "bitaxe-gamma",
            "version": "2.0.8",
            "boardVersion": "202",
            "description": "Typical Bitaxe Gamma"
        },
        "bitaxe_gamma_2": {
            "ASICModel": "BM1370",
            "asicCount": 1,
            "hashRate": 600,  # 600 GH/s
            "hostname": "bitaxe",
            "version": "2.1.0",
            "boardVersion": "203",
            "description": "High-performance Bitaxe Gamma"
        },
        "bitaxe_unknown": {
            "ASICModel": "BM1370",
            "asicCount": 1,
            "hashRate": 0,  # No hashrate data
            "hostname": "bitaxe",
            "version": "2.1.4",
            "boardVersion": "204",
            "description": "BM1370 with no hashrate data"
        }
    }
    
    miner = BitaxeMiner("192.168.1.1", 80)
    
    print("Testing with simulated device data:\n")
    
    for device_id, data in test_devices.items():
        result = miner._determine_bitaxe_model(
            data["ASICModel"],
            data["asicCount"], 
            data["hashRate"],
            data["hostname"]
        )
        
        print(f"Device: {device_id}")
        print(f"  Description: {data['description']}")
        print(f"  ASIC: {data['ASICModel']}, Count: {data['asicCount']}")
        print(f"  Hashrate: {data['hashRate']} GH/s")
        print(f"  Detected as: {result}")
        
        # Determine if this looks correct
        if "gamma" in device_id and "Gamma" in result:
            print(f"  Status: ✅ Correct")
        elif "hex" in device_id and "Hex" in result:
            print(f"  Status: ✅ Correct")
        elif "unknown" in device_id:
            print(f"  Status: ⚠️  Uncertain (no hashrate data)")
        else:
            print(f"  Status: ❌ Likely incorrect")
        
        print()


if __name__ == "__main__":
    print("=" * 80)
    print("BITAXE GAMMA vs HEX DETECTION ANALYSIS")
    print("=" * 80)
    print()
    
    test_bitaxe_model_detection()
    analyze_detection_logic()
    propose_improved_logic()
    create_test_device_data()
    
    print("🏁 Analysis complete!")
    print("\nNext steps:")
    print("1. Review the identified issues")
    print("2. Implement improved detection logic")
    print("3. Test with real devices")
    print("4. Update documentation")