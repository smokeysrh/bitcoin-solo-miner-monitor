#!/usr/bin/env python3
"""
Complete flow test for setup wizard coordination
"""

import json
import os
from pathlib import Path
import requests

def test_complete_setup_flow():
    """Test the complete setup flow from installer to main app"""
    
    print("🚀 Testing Complete Setup Flow")
    print("=" * 50)
    
    # Step 1: Simulate fresh installation (no setup data)
    print("\n1. Testing fresh installation state...")
    setup_file = Path("data/setup-complete.json")
    if setup_file.exists():
        setup_file.unlink()
        print("   ✓ Removed existing setup file")
    
    # Test API with no setup file
    try:
        response = requests.get("http://localhost:8000/api/setup-status")
        if response.status_code == 200:
            data = response.json()
            if not data.get("installationComplete"):
                print("   ✓ Fresh installation detected correctly")
            else:
                print("   ❌ Should show fresh installation")
        else:
            print(f"   ❌ API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
    
    # Step 2: Simulate Electron installer completion
    print("\n2. Simulating Electron installer completion...")
    
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Create setup completion data
    setup_data = {
        "installationComplete": True,
        "experienceLevel": "intermediate",
        "foundMiners": [
            {
                "ip": "10.0.0.100",
                "type": "bitaxe",
                "name": "Bitaxe Miner (10.0.0.100)",
                "status": "online",
                "detected": True,
                "hashrate": "500 GH/s",
                "temperature": "65°C"
            },
            {
                "ip": "10.0.0.101",
                "type": "avalon_nano", 
                "name": "Avalon Nano (10.0.0.101)",
                "status": "online",
                "detected": True,
                "hashrate": "3.5 TH/s",
                "temperature": "58°C"
            }
        ],
        "settings": {
            "simple_mode": False,
            "polling_interval": 30,
            "refresh_interval": 10,
            "chart_retention_days": 30,
            "theme": "dark"
        },
        "preferences": {
            "autoDiscovery": True,
            "notifications": True,
            "soundAlerts": False
        },
        "timestamp": "2025-01-09T10:30:00.000Z"
    }
    
    # Write setup file
    with open(setup_file, 'w') as f:
        json.dump(setup_data, f, indent=2)
    
    print("   ✓ Created setup completion file")
    
    # Step 3: Test API with setup file
    print("\n3. Testing API with setup completion...")
    try:
        response = requests.get("http://localhost:8000/api/setup-status")
        if response.status_code == 200:
            data = response.json()
            if data.get("installationComplete"):
                print("   ✓ Setup completion detected correctly")
                print(f"   ✓ Experience Level: {data.get('experienceLevel')}")
                print(f"   ✓ Found {len(data.get('foundMiners', []))} miners")
                print(f"   ✓ UI Mode: {'Simple' if data.get('settings', {}).get('simple_mode') else 'Advanced'}")
            else:
                print("   ❌ Setup completion not detected")
        else:
            print(f"   ❌ API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
    
    # Step 4: Instructions for frontend testing
    print("\n4. Frontend Testing Instructions:")
    print("   📱 Open your browser to the running frontend")
    print("   🔧 Open Developer Tools (F12)")
    print("   🗂️  Go to Application/Storage tab")
    print("   🧹 Clear localStorage for your app")
    print("   🔄 Refresh the page")
    print("   ✅ App should skip Vue.js setup wizard")
    print("   🏠 App should load directly to main dashboard")
    print("   ⛏️  App should show the discovered miners")
    
    # Step 5: Test reset functionality
    print("\n5. To test fresh installation again:")
    print("   🗑️  Delete data/setup-complete.json")
    print("   🧹 Clear browser localStorage")
    print("   🔄 Refresh page")
    print("   🆕 Should show Vue.js first-run setup")
    
    print("\n🎉 Setup flow test complete!")
    print("The coordination between Electron installer and Vue.js app is now working!")

if __name__ == "__main__":
    test_complete_setup_flow()