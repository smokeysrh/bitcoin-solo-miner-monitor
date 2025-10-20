"""
Test script to verify NerdQaxe vs Bitaxe detection logic.
Uses real API response data to validate the differentiation strategy.
"""

# Real NerdQaxe++ response from 192.168.1.156
nerdqaxe_response = {
    "asicCount": 4,
    "smallCoreCount": 2040,
    "deviceModel": "NerdQAxe++",  # ← KEY FIELD
    "hostip": "192.168.1.156",
    "macAddr": "64:E8:33:76:C9:B8",
    "hostname": "nerdqaxe",
    "ASICModel": "BM1370",
    "version": "v1.0.30",
    "hashRate": 4822.423,
    "boardVersion": None  # Not present in NerdQaxe
}

# Real Bitaxe response from documentation
bitaxe_response = {
    "asicCount": 1,
    "smallCoreCount": 894,
    # NO deviceModel field!
    "macAddr": "C0-FA-38-6A-6E-B2",
    "hostname": "bitaxe",
    "ASICModel": "BM1366",
    "version": "v2.6.0",
    "hashRate": 2372.758,
    "boardVersion": "302"
}

def detect_device_type(device_info):
    """
    Detect device type using the deviceModel field.
    
    Returns:
        tuple: (device_type, model, confidence)
    """
    # CONCRETE DIFFERENTIATION: Check for deviceModel field
    device_model = device_info.get("deviceModel", None)
    asic_model = device_info.get("ASICModel", "").lower()
    asic_count = device_info.get("asicCount", 0)
    hostname = device_info.get("hostname", "").lower()
    
    if device_model:
        # This is a NerdQaxe/NerdAxe variant (has deviceModel field)
        device_type = device_model
        model = device_model
        confidence = "HIGH - deviceModel field present"
        return (device_type, model, confidence)
    else:
        # This is a standard Bitaxe (NO deviceModel field)
        device_type = "Bitaxe"
        
        # Determine Bitaxe model based on ASIC chip
        if "bm1366" in asic_model:
            model = "Bitaxe Ultra"
        elif "bm1368" in asic_model:
            model = "Bitaxe Supra"
        elif "bm1397" in asic_model:
            model = "Bitaxe Gamma"
        elif "bm1370" in asic_model:
            model = "Bitaxe Hex"
        else:
            model = "Bitaxe"
        
        confidence = "HIGH - deviceModel field absent (standard Bitaxe)"
        return (device_type, model, confidence)

def test_detection():
    """Test the detection logic with real data."""
    print("="*60)
    print("Testing Bitaxe vs NerdQaxe Detection Logic")
    print("="*60)
    
    # Test NerdQaxe
    print("\n1. Testing NerdQaxe++ (192.168.1.156):")
    print(f"   API Response has 'deviceModel': {nerdqaxe_response.get('deviceModel')}")
    device_type, model, confidence = detect_device_type(nerdqaxe_response)
    print(f"   ✓ Detected as: {device_type}")
    print(f"   ✓ Model: {model}")
    print(f"   ✓ Confidence: {confidence}")
    print(f"   ✓ ASIC Count: {nerdqaxe_response['asicCount']}")
    print(f"   ✓ Hash Rate: {nerdqaxe_response['hashRate']} GH/s")
    
    assert device_type == "NerdQAxe++", f"Expected 'NerdQAxe++', got '{device_type}'"
    assert "nerdqaxe" in device_type.lower() or "nerdaxe" in device_type.lower(), "Device type should contain 'nerd'"
    
    # Test Bitaxe
    print("\n2. Testing Bitaxe Ultra:")
    print(f"   API Response has 'deviceModel': {bitaxe_response.get('deviceModel', 'NOT PRESENT')}")
    device_type, model, confidence = detect_device_type(bitaxe_response)
    print(f"   ✓ Detected as: {device_type}")
    print(f"   ✓ Model: {model}")
    print(f"   ✓ Confidence: {confidence}")
    print(f"   ✓ ASIC Count: {bitaxe_response['asicCount']}")
    print(f"   ✓ Hash Rate: {bitaxe_response['hashRate']} GH/s")
    
    assert device_type == "Bitaxe", f"Expected 'Bitaxe', got '{device_type}'"
    assert model == "Bitaxe Ultra", f"Expected 'Bitaxe Ultra', got '{model}'"
    
    # Test edge cases
    print("\n3. Testing Edge Cases:")
    
    # Bitaxe with different chip
    bitaxe_supra = bitaxe_response.copy()
    bitaxe_supra["ASICModel"] = "BM1368"
    device_type, model, confidence = detect_device_type(bitaxe_supra)
    print(f"   ✓ Bitaxe with BM1368 → {model}")
    assert model == "Bitaxe Supra", f"Expected 'Bitaxe Supra', got '{model}'"
    
    # NerdQaxe with different model name
    nerdaxe = nerdqaxe_response.copy()
    nerdaxe["deviceModel"] = "NerdAxe"
    device_type, model, confidence = detect_device_type(nerdaxe)
    print(f"   ✓ Device with deviceModel='NerdAxe' → {model}")
    assert device_type == "NerdAxe", f"Expected 'NerdAxe', got '{device_type}'"
    
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED!")
    print("="*60)
    print("\nConclusion:")
    print("  The 'deviceModel' field is a RELIABLE differentiator:")
    print("  - Present → NerdQaxe/NerdAxe variant")
    print("  - Absent → Standard Bitaxe")
    print("\n  This works regardless of:")
    print("  - ASIC count (Bitaxe Hex has multiple ASICs)")
    print("  - Hash rate (varies by model and settings)")
    print("  - Hostname (user-configurable)")
    print("  - Board version (changes over time)")

if __name__ == "__main__":
    test_detection()
