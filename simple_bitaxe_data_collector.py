#!/usr/bin/env python3
"""
Simple Bitaxe Data Collector

A lightweight script to collect API data from Bitaxe devices without complex session management.
This script uses direct aiohttp calls with shorter timeouts to avoid hanging.
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional


class SimpleBitaxeCollector:
    """Simple collector that uses direct aiohttp calls."""
    
    def __init__(self, ip_address: str, port: int = 80):
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
        self.timeout = aiohttp.ClientTimeout(total=5)  # Short timeout
    
    async def get_endpoint(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get data from a specific endpoint with short timeout."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except Exception as e:
                            print(f"    ⚠️  JSON parse error: {e}")
                            text = await response.text()
                            return {"_raw_text": text[:200]}  # First 200 chars
                    else:
                        print(f"    ❌ HTTP {response.status}")
                        return None
        except asyncio.TimeoutError:
            print(f"    ⏱️  Timeout")
            return None
        except aiohttp.ClientConnectorError:
            print(f"    🔌 Connection refused")
            return None
        except Exception as e:
            print(f"    💥 Error: {e}")
            return None
    
    async def collect_basic_data(self) -> Dict[str, Any]:
        """Collect basic data from key endpoints."""
        
        print(f"\n🔍 Collecting from {self.ip_address}")
        
        data = {
            "ip_address": self.ip_address,
            "timestamp": datetime.now().isoformat(),
            "endpoints": {}
        }
        
        # Key endpoints to test
        endpoints = [
            "/api/system/info",
            "/api/system/statistics/dashboard",
            "/api/system",
            "/"
        ]
        
        for endpoint in endpoints:
            print(f"  📡 {endpoint}", end=" ")
            result = await self.get_endpoint(endpoint)
            data["endpoints"][endpoint] = result
            
            if result:
                print("✅")
            else:
                print("❌")
        
        return data
    
    def analyze_device(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the collected data to identify device characteristics."""
        
        analysis = {
            "device_type": "Unknown",
            "model": "Unknown", 
            "confidence": 0.0,
            "key_fields": {},
            "detection_method": "None"
        }
        
        # Check main system info endpoint
        system_info = data["endpoints"].get("/api/system/info")
        
        if system_info and isinstance(system_info, dict):
            # Extract key identification fields
            key_fields = {
                "ASICModel": system_info.get("ASICModel", ""),
                "asicCount": system_info.get("asicCount", 0),
                "hashRate": system_info.get("hashRate", 0),
                "hostname": system_info.get("hostname", ""),
                "version": system_info.get("version", ""),
                "boardVersion": system_info.get("boardVersion", ""),
                "deviceModel": system_info.get("deviceModel", None),
                "macAddr": system_info.get("macAddr", ""),
                "idfVersion": system_info.get("idfVersion", ""),
                "smallCoreCount": system_info.get("smallCoreCount", 0),
                "frequency": system_info.get("frequency", 0),
                "power": system_info.get("power", 0),
                "temp": system_info.get("temp", 0),
                "voltage": system_info.get("voltage", 0),
                "current": system_info.get("current", 0),
                "fanspeed": system_info.get("fanspeed", 0),
                "fanrpm": system_info.get("fanrpm", 0),
                "uptimeSeconds": system_info.get("uptimeSeconds", 0),
                "sharesAccepted": system_info.get("sharesAccepted", 0),
                "sharesRejected": system_info.get("sharesRejected", 0),
                "bestDiff": system_info.get("bestDiff", ""),
                "stratumURL": system_info.get("stratumURL", ""),
                "stratumUser": system_info.get("stratumUser", ""),
                "stratumDiff": system_info.get("stratumDiff", 0),
            }
            
            analysis["key_fields"] = key_fields
            analysis["device_type"] = "Bitaxe"
            
            # Determine specific model
            asic_model = str(key_fields["ASICModel"]).lower()
            asic_count = key_fields["asicCount"]
            hash_rate = key_fields["hashRate"]
            hostname = str(key_fields["hostname"]).lower()
            device_model = key_fields["deviceModel"]
            
            # Check for NerdQaxe/NerdAxe (has deviceModel field)
            if device_model:
                analysis["model"] = str(device_model)
                analysis["confidence"] = 0.95
                analysis["detection_method"] = "deviceModel field"
            
            # Standard Bitaxe model detection
            elif "bm1366" in asic_model:
                analysis["model"] = "Bitaxe Ultra"
                analysis["confidence"] = 0.9
                analysis["detection_method"] = "ASIC model BM1366"
            
            elif "bm1368" in asic_model:
                analysis["model"] = "Bitaxe Supra"
                analysis["confidence"] = 0.9
                analysis["detection_method"] = "ASIC model BM1368"
            
            elif "bm1397" in asic_model:
                analysis["model"] = "Bitaxe Gamma"
                analysis["confidence"] = 0.9
                analysis["detection_method"] = "ASIC model BM1397"
            
            elif "bm1370" in asic_model:
                # This is the problematic case - need to differentiate Gamma vs Hex
                if hash_rate > 0:
                    th_rate = hash_rate / 1000  # Convert to TH/s
                    if th_rate >= 0.85:  # 850+ GH/s
                        analysis["model"] = "Bitaxe Hex"
                        analysis["confidence"] = 0.8
                        analysis["detection_method"] = f"BM1370 + high hashrate ({hash_rate} GH/s)"
                    else:
                        analysis["model"] = "Bitaxe Gamma"
                        analysis["confidence"] = 0.7
                        analysis["detection_method"] = f"BM1370 + moderate hashrate ({hash_rate} GH/s)"
                else:
                    # No hashrate data - check hostname
                    if "gamma" in hostname:
                        analysis["model"] = "Bitaxe Gamma"
                        analysis["confidence"] = 0.8
                        analysis["detection_method"] = "BM1370 + hostname hint (gamma)"
                    elif "hex" in hostname:
                        analysis["model"] = "Bitaxe Hex"
                        analysis["confidence"] = 0.8
                        analysis["detection_method"] = "BM1370 + hostname hint (hex)"
                    else:
                        analysis["model"] = "Bitaxe Gamma"  # Conservative default
                        analysis["confidence"] = 0.5
                        analysis["detection_method"] = "BM1370 + conservative default"
            
            else:
                analysis["model"] = "Bitaxe (Unknown ASIC)"
                analysis["confidence"] = 0.6
                analysis["detection_method"] = f"Unknown ASIC model: {asic_model}"
        
        return analysis


async def test_single_device(ip_address: str):
    """Test a single device and show detailed results."""
    
    print(f"🎯 TESTING SINGLE DEVICE: {ip_address}")
    print("=" * 60)
    
    collector = SimpleBitaxeCollector(ip_address)
    
    # Collect data
    data = await collector.collect_basic_data()
    
    # Analyze
    analysis = collector.analyze_device(data)
    
    # Show results
    print(f"\n📊 ANALYSIS RESULTS:")
    print(f"   Device Type: {analysis['device_type']}")
    print(f"   Model: {analysis['model']}")
    print(f"   Confidence: {analysis['confidence']:.1%}")
    print(f"   Detection Method: {analysis['detection_method']}")
    
    # Show key fields if available
    key_fields = analysis.get("key_fields", {})
    if key_fields:
        print(f"\n🔑 KEY IDENTIFICATION FIELDS:")
        for field, value in key_fields.items():
            if value:  # Only show non-empty values
                print(f"   {field}: {value}")
    
    # Show all available fields
    system_info = data["endpoints"].get("/api/system/info")
    if system_info and isinstance(system_info, dict):
        print(f"\n📋 ALL AVAILABLE FIELDS ({len(system_info)} total):")
        for field in sorted(system_info.keys()):
            value = system_info[field]
            # Truncate long values
            if isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            print(f"   {field}: {value}")
    
    # Save detailed data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bitaxe_data_{ip_address.replace('.', '_')}_{timestamp}.json"
    
    full_data = {
        "collection_data": data,
        "analysis": analysis
    }
    
    with open(filename, 'w') as f:
        json.dump(full_data, f, indent=2, default=str)
    
    print(f"\n💾 Data saved to: {filename}")


async def test_multiple_devices():
    """Test multiple devices quickly."""
    
    print("🚀 TESTING MULTIPLE DEVICES")
    print("=" * 40)
    
    # Known devices from your setup
    devices = [
        "192.168.1.85",   # Your known miner
        "192.168.50.84",  # From bug reports
        "192.168.50.83",  # From bug reports
        "192.168.50.85",  # From bug reports
    ]
    
    results = []
    
    for ip in devices:
        collector = SimpleBitaxeCollector(ip)
        data = await collector.collect_basic_data()
        analysis = collector.analyze_device(data)
        
        results.append({
            "ip": ip,
            "data": data,
            "analysis": analysis
        })
        
        # Quick summary
        print(f"\n📋 {ip}: {analysis['model']} ({analysis['confidence']:.0%})")
        if analysis['key_fields'].get('ASICModel'):
            asic = analysis['key_fields']['ASICModel']
            hashrate = analysis['key_fields']['hashRate']
            print(f"    ASIC: {asic}, Hashrate: {hashrate} GH/s")
    
    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bitaxe_multi_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {filename}")
    
    # Generate quick report
    print(f"\n📊 SUMMARY REPORT:")
    models = {}
    for result in results:
        model = result["analysis"]["model"]
        if model not in models:
            models[model] = []
        models[model].append(result["ip"])
    
    for model, ips in models.items():
        print(f"   {model}: {', '.join(ips)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test single device
        ip = sys.argv[1]
        asyncio.run(test_single_device(ip))
    else:
        # Test multiple devices
        asyncio.run(test_multiple_devices())