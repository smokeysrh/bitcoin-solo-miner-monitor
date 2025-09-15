#!/usr/bin/env python3
"""
Test SPA routing to see if the backend properly serves index.html for client-side routes
"""

import requests
import sys

def test_spa_routes():
    base_url = "http://localhost:8000"
    
    routes_to_test = [
        "/",
        "/setup", 
        "/miners",
        "/analytics",
        "/dashboard-simple",
        "/nonexistent-route"
    ]
    
    print("Testing SPA routing...")
    
    for route in routes_to_test:
        try:
            print(f"\nTesting route: {route}")
            response = requests.get(f"{base_url}{route}", timeout=5)
            
            print(f"  Status Code: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                # Check if it's serving the index.html (should contain "Bitcoin Solo Miner")
                if "Bitcoin Solo Miner" in response.text:
                    print(f"  ✅ Correctly serving SPA content")
                else:
                    print(f"  ⚠️  Serving content but not SPA index.html")
                    print(f"  Content preview: {response.text[:200]}...")
            elif response.status_code == 404:
                print(f"  ❌ Route not found - SPA routing not working")
            else:
                print(f"  ⚠️  Unexpected status code")
                
        except requests.ConnectionError:
            print(f"  ❌ Connection refused - is the server running?")
            return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    return True

def test_api_routes():
    base_url = "http://localhost:8000"
    
    api_routes = [
        "/api/miners",
        "/api/settings"
    ]
    
    print("\n\nTesting API routes...")
    
    for route in api_routes:
        try:
            print(f"\nTesting API route: {route}")
            response = requests.get(f"{base_url}{route}", timeout=5)
            
            print(f"  Status Code: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                print(f"  ✅ API route working")
                try:
                    data = response.json()
                    print(f"  Response type: {type(data)}")
                except:
                    print(f"  ⚠️  Response not JSON")
            else:
                print(f"  ⚠️  API route returned {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    return True

def main():
    print("=== SPA Routing Test ===")
    
    spa_success = test_spa_routes()
    api_success = test_api_routes()
    
    if spa_success and api_success:
        print("\n✅ All tests completed")
    else:
        print("\n❌ Some tests failed")
    
    return spa_success and api_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)