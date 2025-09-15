#!/usr/bin/env python3
"""
Test script to verify discovered miners are properly added to the main app
"""

import json
import requests
from pathlib import Path

def test_miner_integration():
    """Test that discovered miners from installer are added to the main app"""
    
    print("🔧 Testing Miner Integration")
    print("=" * 50)
    
    # Step 1: Clear existing miners
    print("\n1. Checking current miners...")
    try:
        response = requests.get("http://localhost:8000/api/miners")
        if response.status_code == 200:
            current_miners = response.json()
            print(f"   Current miners: {len(current_miners)}")
            for miner in current_miners:
                print(f"   - {miner.get('name', 'Unknown')} ({miner.get('ip_address', 'Unknown IP')})")
        else:
            print(f"   ❌ Failed to get miners: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting miners: {e}")
    
    # Step 2: Create fresh setup data with miners
    print("\n2. Creating fresh setup data with discovered miners...")
    
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
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
            },
            {
                "ip": "10.0.0.102",
                "type": "magic_miner",
                "name": "Magic Miner (10.0.0.102)",
                "status": "online",
                "detected": True,
                "hashrate": "15 TH/s",
                "temperature": "72°C"
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
    
    setup_file = data_dir / "setup-complete.json"
    with open(setup_file, 'w') as f:
        json.dump(setup_data, f, indent=2)
    
    print(f"   ✓ Created setup file with {len(setup_data['foundMiners'])} discovered miners")
    
    # Step 3: Verify API can read the setup data
    print("\n3. Verifying setup status API...")
    try:
        response = requests.get("http://localhost:8000/api/setup-status")
        if response.status_code == 200:
            api_data = response.json()
            if api_data.get("installationComplete"):
                print(f"   ✓ API returns {len(api_data.get('foundMiners', []))} discovered miners")
            else:
                print("   ❌ API doesn't show installation complete")
        else:
            print(f"   ❌ API error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
    
    # Step 4: Instructions for frontend testing
    print("\n4. Frontend Testing Steps:")
    print("   🌐 Open your browser to the frontend")
    print("   🔧 Open Developer Tools (F12)")
    print("   📂 Go to Application/Storage tab")
    print("   🧹 Clear localStorage completely")
    print("   🔄 Refresh the page")
    print("   ✅ App should skip setup wizard")
    print("   ⛏️  App should automatically add the 3 discovered miners")
    print("   📊 Check the miners list in the app")
    
    print("\n5. Expected Results:")
    print("   - App loads directly to main dashboard")
    print("   - Shows 3 miners in the miners list:")
    print("     • Bitaxe Miner (10.0.0.100)")
    print("     • Avalon Nano (10.0.0.101)")
    print("     • Magic Miner (10.0.0.102)")
    print("   - Shows success message about adding miners")
    
    print("\n🎉 Test setup complete!")
    print("Clear your browser localStorage and refresh to test the integration!")

if __name__ == "__main__":
    test_miner_integration()