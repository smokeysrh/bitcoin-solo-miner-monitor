#!/usr/bin/env python3
"""
Bitaxe API Data Collection Script

This script collects comprehensive API response data from Bitaxe devices
to help identify patterns for better model detection.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.backend.models.http_client_mixin import HTTPClientMixin


class BitaxeDataCollector(HTTPClientMixin):
    """Collect comprehensive data from Bitaxe devices."""
    
    def __init__(self, ip_address: str, port: int = 80):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
    
    async def collect_all_data(self) -> Dict[str, Any]:
        """Collect all available data from a Bitaxe device."""
        
        print(f"🔍 Collecting data from {self.ip_address}...")
        
        data = {
            "ip_address": self.ip_address,
            "port": self.port,
            "timestamp": datetime.now().isoformat(),
            "endpoints": {}
        }
        
        # List of known Bitaxe API endpoints
        endpoints = [
            "/api/system/info",
            "/api/system/statistics/dashboard", 
            "/api/system",
            "/api/system/statistics",
            "/api/swarm/info",
            "/api/swarm",
            "/",
            "/status",
            "/config",
            "/info"
        ]
        
        for endpoint in endpoints:
            print(f"  📡 Testing endpoint: {endpoint}")
            try:
                response = await self._http_get(endpoint)
                if response:
                    data["endpoints"][endpoint] = {
                        "success": True,
                        "data": response,
                        "data_type": type(response).__name__
                    }
                    print(f"    ✅ Success - {type(response).__name__}")
                else:
                    data["endpoints"][endpoint] = {
                        "success": False,
                        "error": "Empty response"
                    }
                    print(f"    ❌ Empty response")
            except Exception as e:
                data["endpoints"][endpoint] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"    ❌ Error: {str(e)}")
        
        # Extract key characteristics for analysis
        data["analysis"] = await self._analyze_device_data(data)
        
        return data
    
    async def _analyze_device_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze collected data to extract key characteristics."""
        
        analysis = {
            "device_identified": False,
            "likely_model": "Unknown",
            "confidence": 0.0,
            "key_indicators": {},
            "all_fields": set(),
            "unique_fields": set()
        }
        
        # Get the main system info if available
        system_info = None
        if "/api/system/info" in data["endpoints"] and data["endpoints"]["/api/system/info"]["success"]:
            system_info = data["endpoints"]["/api/system/info"]["data"]
        
        if system_info and isinstance(system_info, dict):
            analysis["device_identified"] = True
            
            # Extract key indicators
            analysis["key_indicators"] = {
                "asic_model": system_info.get("ASICModel", ""),
                "asic_count": system_info.get("asicCount", 0),
                "hash_rate": system_info.get("hashRate", 0),
                "hostname": system_info.get("hostname", ""),
                "version": system_info.get("version", ""),
                "board_version": system_info.get("boardVersion", ""),
                "idf_version": system_info.get("idfVersion", ""),
                "device_model": system_info.get("deviceModel", None),
                "mac_address": system_info.get("macAddr", ""),
                "core_count": system_info.get("smallCoreCount", 0),
                "frequency": system_info.get("frequency", 0),
                "voltage": system_info.get("voltage", 0),
                "power": system_info.get("power", 0),
                "temperature": system_info.get("temp", 0),
                "fan_speed": system_info.get("fanspeed", 0),
                "uptime": system_info.get("uptimeSeconds", 0)
            }
            
            # Collect all available fields
            analysis["all_fields"] = set(system_info.keys())
            
            # Attempt model identification
            analysis["likely_model"], analysis["confidence"] = self._identify_model(analysis["key_indicators"])
        
        return analysis
    
    def _identify_model(self, indicators: Dict[str, Any]) -> tuple[str, float]:
        """Attempt to identify the Bitaxe model based on indicators."""
        
        asic_model = str(indicators.get("asic_model", "")).lower()
        asic_count = indicators.get("asic_count", 0)
        hash_rate = indicators.get("hash_rate", 0)
        hostname = str(indicators.get("hostname", "")).lower()
        version = str(indicators.get("version", "")).lower()
        board_version = str(indicators.get("board_version", "")).lower()
        device_model = indicators.get("device_model")
        
        confidence = 0.0
        model = "Unknown"
        
        # Check for NerdQaxe/NerdAxe (has deviceModel field)
        if device_model:
            model = str(device_model)
            confidence = 0.95
            return model, confidence
        
        # Check ASIC model patterns
        if "bm1366" in asic_model:
            model = "Bitaxe Ultra"
            confidence = 0.9
        elif "bm1368" in asic_model and asic_count == 1:
            model = "Bitaxe Supra"
            confidence = 0.9
        elif "bm1397" in asic_model:
            model = "Bitaxe Gamma"
            confidence = 0.9
        elif "bm1370" in asic_model:
            # Need to differentiate between Gamma and Hex
            if hash_rate > 0:
                th_rate = hash_rate / 1000
                if th_rate >= 0.85:
                    model = "Bitaxe Hex"
                    confidence = 0.8
                else:
                    model = "Bitaxe Gamma"
                    confidence = 0.7
            else:
                # Check hostname for hints
                if "gamma" in hostname:
                    model = "Bitaxe Gamma"
                    confidence = 0.8
                elif "hex" in hostname:
                    model = "Bitaxe Hex"
                    confidence = 0.8
                else:
                    model = "Bitaxe (BM1370)"
                    confidence = 0.5
        
        return model, confidence


async def collect_from_multiple_devices():
    """Collect data from multiple known Bitaxe devices."""
    
    print("🚀 BITAXE API DATA COLLECTION")
    print("=" * 50)
    
    # List of known/potential Bitaxe devices
    # Add your known Bitaxe IP addresses here
    devices = [
        "192.168.1.85",   # Known miner from your setup
        "192.168.50.84",  # From bug reports
        "192.168.50.83",  # From bug reports  
        "192.168.50.85",  # From bug reports
        # Add more IP addresses as needed
    ]
    
    all_data = []
    
    for ip in devices:
        print(f"\n📍 Processing device: {ip}")
        print("-" * 30)
        
        collector = BitaxeDataCollector(ip)
        
        try:
            device_data = await collector.collect_all_data()
            all_data.append(device_data)
            
            # Print summary
            analysis = device_data.get("analysis", {})
            if analysis.get("device_identified"):
                model = analysis.get("likely_model", "Unknown")
                confidence = analysis.get("confidence", 0.0)
                indicators = analysis.get("key_indicators", {})
                
                print(f"\n📋 DEVICE SUMMARY:")
                print(f"   Model: {model} (confidence: {confidence:.1%})")
                print(f"   ASIC: {indicators.get('asic_model')} (count: {indicators.get('asic_count')})")
                print(f"   Hashrate: {indicators.get('hash_rate')} GH/s")
                print(f"   Hostname: {indicators.get('hostname')}")
                print(f"   Version: {indicators.get('version')}")
                print(f"   Board: {indicators.get('board_version')}")
                
                if indicators.get('device_model'):
                    print(f"   Device Model: {indicators.get('device_model')}")
            else:
                print(f"   ❌ Device not identified or not responding")
                
        except Exception as e:
            print(f"   💥 Error collecting data: {str(e)}")
            all_data.append({
                "ip_address": ip,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    # Save all collected data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bitaxe_api_data_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(all_data, f, indent=2, default=str)
    
    print(f"\n💾 Data saved to: {filename}")
    
    # Generate analysis report
    await generate_analysis_report(all_data, timestamp)
    
    return all_data


async def generate_analysis_report(all_data: List[Dict], timestamp: str):
    """Generate a comprehensive analysis report."""
    
    report_filename = f"bitaxe_analysis_report_{timestamp}.md"
    
    with open(report_filename, 'w') as f:
        f.write("# Bitaxe API Data Analysis Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        # Summary statistics
        total_devices = len(all_data)
        successful_devices = len([d for d in all_data if not d.get("error")])
        identified_devices = len([d for d in all_data if d.get("analysis", {}).get("device_identified")])
        
        f.write("## Summary\n\n")
        f.write(f"- Total devices tested: {total_devices}\n")
        f.write(f"- Successful connections: {successful_devices}\n")
        f.write(f"- Devices identified: {identified_devices}\n\n")
        
        # Device details
        f.write("## Device Details\n\n")
        
        for i, device in enumerate(all_data, 1):
            ip = device.get("ip_address", "Unknown")
            f.write(f"### Device {i}: {ip}\n\n")
            
            if device.get("error"):
                f.write(f"**Status:** ❌ Error - {device['error']}\n\n")
                continue
            
            analysis = device.get("analysis", {})
            if analysis.get("device_identified"):
                indicators = analysis.get("key_indicators", {})
                
                f.write(f"**Status:** ✅ Identified\n")
                f.write(f"**Model:** {analysis.get('likely_model')} (confidence: {analysis.get('confidence', 0):.1%})\n\n")
                
                f.write("**Key Characteristics:**\n")
                f.write(f"- ASIC Model: {indicators.get('asic_model')}\n")
                f.write(f"- ASIC Count: {indicators.get('asic_count')}\n")
                f.write(f"- Hashrate: {indicators.get('hash_rate')} GH/s\n")
                f.write(f"- Hostname: {indicators.get('hostname')}\n")
                f.write(f"- Firmware Version: {indicators.get('version')}\n")
                f.write(f"- Board Version: {indicators.get('board_version')}\n")
                f.write(f"- IDF Version: {indicators.get('idf_version')}\n")
                
                if indicators.get('device_model'):
                    f.write(f"- Device Model Field: {indicators.get('device_model')}\n")
                
                f.write(f"- MAC Address: {indicators.get('mac_address')}\n")
                f.write(f"- Core Count: {indicators.get('core_count')}\n")
                f.write(f"- Frequency: {indicators.get('frequency')} MHz\n")
                f.write(f"- Voltage: {indicators.get('voltage')} V\n")
                f.write(f"- Power: {indicators.get('power')} W\n")
                f.write(f"- Temperature: {indicators.get('temperature')} °C\n")
                f.write(f"- Uptime: {indicators.get('uptime')} seconds\n\n")
                
                # Available API fields
                all_fields = analysis.get("all_fields", set())
                if all_fields:
                    f.write("**Available API Fields:**\n")
                    for field in sorted(all_fields):
                        f.write(f"- {field}\n")
                    f.write("\n")
            else:
                f.write(f"**Status:** ❌ Not identified\n\n")
        
        # Pattern analysis
        f.write("## Pattern Analysis\n\n")
        
        # Collect patterns by model
        models = {}
        for device in all_data:
            analysis = device.get("analysis", {})
            if analysis.get("device_identified"):
                model = analysis.get("likely_model", "Unknown")
                if model not in models:
                    models[model] = []
                models[model].append(analysis.get("key_indicators", {}))
        
        for model, devices in models.items():
            f.write(f"### {model} Pattern\n\n")
            f.write(f"**Count:** {len(devices)}\n\n")
            
            if devices:
                # Find common characteristics
                first_device = devices[0]
                f.write("**Common Characteristics:**\n")
                
                for key in first_device.keys():
                    values = [str(d.get(key, "")) for d in devices]
                    unique_values = set(v for v in values if v)
                    
                    if len(unique_values) == 1:
                        f.write(f"- {key}: {list(unique_values)[0]}\n")
                    elif len(unique_values) > 1:
                        f.write(f"- {key}: varies ({', '.join(sorted(unique_values))})\n")
                
                f.write("\n")
    
    print(f"📊 Analysis report saved to: {report_filename}")


async def test_single_device(ip_address: str):
    """Test a single device for detailed analysis."""
    
    print(f"🔍 DETAILED ANALYSIS OF {ip_address}")
    print("=" * 50)
    
    collector = BitaxeDataCollector(ip_address)
    
    try:
        device_data = await collector.collect_all_data()
        
        # Pretty print the results
        print(f"\n📊 COMPLETE DATA DUMP:")
        print(json.dumps(device_data, indent=2, default=str))
        
        # Save individual device data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bitaxe_device_{ip_address.replace('.', '_')}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(device_data, f, indent=2, default=str)
        
        print(f"\n💾 Device data saved to: {filename}")
        
    except Exception as e:
        print(f"💥 Error: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test single device
        ip = sys.argv[1]
        asyncio.run(test_single_device(ip))
    else:
        # Test multiple devices
        asyncio.run(collect_from_multiple_devices())