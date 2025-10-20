"""
Test script to verify miner name cleaning logic.
Tests that trailing underscores are properly removed from miner names.
"""

def clean_miner_name(name):
    """
    Clean up miner name by removing trailing underscores.
    
    Args:
        name: The miner name to clean
        
    Returns:
        str: Cleaned miner name
    """
    if not name:
        return name
    
    # First strip whitespace, then remove trailing underscores
    return str(name).strip().rstrip('_')

def test_name_cleaning():
    """Test the name cleaning logic."""
    print("="*60)
    print("Testing Miner Name Cleaning Logic")
    print("="*60)
    
    test_cases = [
        ("NerdQaxe_", "NerdQaxe"),
        ("NerdQAxe++_", "NerdQAxe++"),
        ("Bitaxe Ultra", "Bitaxe Ultra"),
        ("Miner___", "Miner"),
        ("Test_Miner_", "Test_Miner"),
        ("NoTrailing", "NoTrailing"),
        ("  Spaces_  ", "Spaces"),
        ("", ""),
        (None, None),
    ]
    
    print("\nTest Cases:")
    all_passed = True
    for input_name, expected in test_cases:
        result = clean_miner_name(input_name)
        status = "✓" if result == expected else "✗"
        print(f"  {status} Input: '{input_name}' → Output: '{result}' (Expected: '{expected}')")
        if result != expected:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED!")
    print("="*60)
    
    return all_passed

if __name__ == "__main__":
    success = test_name_cleaning()
    exit(0 if success else 1)
