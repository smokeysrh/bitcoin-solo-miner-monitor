#!/usr/bin/env python3
"""
Simple test to add a single miner and verify it works
"""

import requests
import json

def test_add_single_miner():
    """Test adding a single miner"""
    
    print("🔧 Testing Add Single Miner")
    print("=" * 30)
    
    # Test data
    miner_data = {
        "type": "bitaxe",
        "ip_address": "10.0.0.100",
        # Don't include port field to use default
        "name": "Test Bitaxe Miner"
    }
    
    print(f"Adding miner: {json.dumps(miner_data, indent=2)}")
    
    try:
        response = requests.post(
            "http://localhost:8000/api/miners",
            json=miner_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result.get('name', 'Unknown')} added")
            print(f"Miner ID: {result.get('id', 'Unknown')}")
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error Details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error Text: {response.text}")
                
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Check if miner was added
    print(f"\nChecking miners list...")
    try:
        response = requests.get("http://localhost:8000/api/miners")
        if response.status_code == 200:
            miners = response.json()
            print(f"Total miners: {len(miners)}")
            for miner in miners:
                print(f"- {miner.get('name', 'Unknown')} ({miner.get('ip_address', 'Unknown IP')})")
        else:
            print(f"❌ Failed to get miners: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception getting miners: {e}")

if __name__ == "__main__":
    test_add_single_miner()