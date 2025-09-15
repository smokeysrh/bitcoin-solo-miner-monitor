#!/usr/bin/env python3
"""
Simple API test script to verify the backend is working
"""

import requests
import sys

def test_api():
    base_url = "http://localhost:8000"
    
    try:
        # Test health endpoint
        print(f"Testing {base_url}/health...")
        response = requests.get(f"{base_url}/health", timeout=5)
        
        if response.status_code == 200:
            print("✓ Health endpoint responding")
            print(f"  Response: {response.json()}")
        else:
            print(f"⚠ Health endpoint returned status {response.status_code}")
            
        # Test API miners endpoint
        print(f"Testing {base_url}/api/miners...")
        response = requests.get(f"{base_url}/api/miners", timeout=5)
        
        if response.status_code == 200:
            print("✓ Miners API endpoint responding")
            miners = response.json()
            print(f"  Found {len(miners)} miners")
        else:
            print(f"⚠ Miners API returned status {response.status_code}")
            
        # Test static file serving
        print(f"Testing {base_url}/ (frontend)...")
        response = requests.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            print("✓ Frontend serving properly")
            if "Bitcoin Solo Miner" in response.text:
                print("  Frontend content looks correct")
        else:
            print(f"⚠ Frontend returned status {response.status_code}")
            
        return True
        
    except requests.ConnectionError:
        print("✗ Connection refused - is the backend server running on port 8000?")
        return False
    except requests.Timeout:
        print("✗ Request timed out")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("Testing HTTP API endpoints...")
    success = test_api()
    
    if success:
        print("\n✓ API test completed!")
        sys.exit(0)
    else:
        print("\n✗ API test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()