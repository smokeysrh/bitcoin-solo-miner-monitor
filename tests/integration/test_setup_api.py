#!/usr/bin/env python3
"""
Test script to verify the setup status API endpoint works
"""

import requests
import json

def test_setup_status_api():
    """Test the /api/setup-status endpoint"""
    
    try:
        print("Testing /api/setup-status endpoint...")
        
        # Make request to the API
        response = requests.get("http://localhost:8000/api/setup-status")
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            setup_data = response.json()
            print("✓ API endpoint working!")
            print(f"Setup Data: {json.dumps(setup_data, indent=2)}")
            
            # Check if installation is complete
            if setup_data.get("installationComplete"):
                print("✓ Installation marked as complete")
                print(f"✓ Experience Level: {setup_data.get('experienceLevel', 'Not set')}")
                print(f"✓ Found Miners: {len(setup_data.get('foundMiners', []))}")
                print(f"✓ Settings: {setup_data.get('settings', {})}")
            else:
                print("⚠ Installation not marked as complete")
                
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend API")
        print("Make sure the backend is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_setup_status_api()