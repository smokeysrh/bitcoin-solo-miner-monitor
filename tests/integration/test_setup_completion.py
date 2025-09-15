#!/usr/bin/env python3
"""
Test script to simulate Electron installer completion
This creates the setup-complete.json file that the main app should read
"""

import json
import os
from pathlib import Path

def create_mock_setup_data():
    """Create mock setup completion data like the Electron installer would"""
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Mock setup data that would come from the Electron installer
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
    
    # Write setup completion file
    setup_file = data_dir / "setup-complete.json"
    with open(setup_file, 'w') as f:
        json.dump(setup_data, f, indent=2)
    
    print(f"✓ Created mock setup completion file: {setup_file}")
    print(f"✓ Setup data: {json.dumps(setup_data, indent=2)}")
    
    return setup_file

def clear_browser_storage():
    """Instructions for clearing browser storage to test first-run flow"""
    print("\n" + "="*60)
    print("TESTING INSTRUCTIONS:")
    print("="*60)
    print("1. Open your browser's Developer Tools (F12)")
    print("2. Go to Application/Storage tab")
    print("3. Clear localStorage for your app (usually localhost:5173)")
    print("4. Refresh the page")
    print("5. The app should now skip the Vue.js setup wizard")
    print("6. It should load directly into the main application")
    print("7. Check that discovered miners are loaded")
    print("="*60)

if __name__ == "__main__":
    print("Creating mock Electron installer completion data...")
    setup_file = create_mock_setup_data()
    clear_browser_storage()
    
    print(f"\n🎉 Mock setup complete! The main app should now:")
    print("   - Skip the Vue.js first-run wizard")
    print("   - Load directly into the main dashboard")
    print("   - Show the discovered miners from the installer")
    print("   - Use the settings from the installer")