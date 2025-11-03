#!/usr/bin/env python3
"""
Debug script to investigate port scanning issues for 192.168.50.88
"""

import asyncio
import sys
import os
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.backend.services.miner_manager import MinerManager


async def debug_port_scanning():
    """Debug port scanning for specific IPs."""
    
    # Test IPs - known working and problematic
    test_ips = [
        "192.168.50.84",  # Known working Bitaxe
        "192.168.50.88",  # Problematic Magic Miner
        "192.168.50.86",  # Known working NerdQAxe
        "192.168.50.87",  # Known working Avalon Nano
    ]
    
    ports_to_check = [80, 4028]
    timeout = 5
    
    manager = MinerManager()
    
    print("=== PORT SCANNING DEBUG ===\n")
    
    for ip in test_ips:
        print(f"Testing {ip}:")
        
        try:
            # Test the port checking method directly
            start_time = time.time()
            open_ports = await manager._check_open_ports(ip, ports_to_check, timeout)
            end_time = time.time()
            
            print(f"  ✅ Open ports: {open_ports}")
            print(f"  ⏱️  Time taken: {end_time - start_time:.2f}s")
            
            if open_ports:
                # Test the full scan_host method
                print(f"  🔍 Testing full host scan...")
                start_time = time.time()
                scan_result = await manager._scan_host(ip, ports_to_check, timeout)
                end_time = time.time()
                
                if scan_result:
                    print(f"  ✅ Scan result: {scan_result.get('type', 'unknown')} - {scan_result.get('device_info', {}).get('model', 'unknown')}")
                else:
                    print(f"  ❌ Scan failed - no miner detected")
                print(f"  ⏱️  Full scan time: {end_time - start_time:.2f}s")
            else:
                print(f"  ❌ No open ports detected")
                
        except Exception as e:
            print(f"  💥 Error: {str(e)}")
        
        print()


async def debug_individual_port_connections():
    """Test individual port connections manually."""
    
    print("=== INDIVIDUAL PORT CONNECTION DEBUG ===\n")
    
    test_cases = [
        ("192.168.50.84", 80, "Bitaxe Hex"),
        ("192.168.50.88", 80, "Magic Miner"),
        ("192.168.50.86", 80, "NerdQAxe"),
        ("192.168.50.87", 4028, "Avalon Nano"),
    ]
    
    for ip, port, description in test_cases:
        print(f"Testing {description} at {ip}:{port}")
        
        try:
            # Test raw asyncio connection
            start_time = time.time()
            
            future = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=5)
            
            end_time = time.time()
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            print(f"  ✅ Connection successful")
            print(f"  ⏱️  Time: {end_time - start_time:.2f}s")
            
        except asyncio.TimeoutError:
            print(f"  ⏰ Connection timeout after 5s")
        except ConnectionRefusedError:
            print(f"  🚫 Connection refused")
        except OSError as e:
            print(f"  💥 OS Error: {str(e)}")
        except Exception as e:
            print(f"  💥 Error: {str(e)}")
        
        print()


async def debug_network_range_scanning():
    """Test scanning a small range around the problematic IP."""
    
    print("=== NETWORK RANGE SCANNING DEBUG ===\n")
    
    # Test IPs around 192.168.50.88
    test_range = [
        "192.168.50.86",  # Known working
        "192.168.50.87",  # Known working  
        "192.168.50.88",  # Problematic
        "192.168.50.89",  # Unknown
        "192.168.50.90",  # Unknown
    ]
    
    manager = MinerManager()
    
    for ip in test_range:
        print(f"Scanning {ip}...")
        
        try:
            # Use the same method as network discovery
            result = await manager._scan_host(ip, [80, 4028], 5)
            
            if result:
                device_type = result.get('type', 'unknown')
                device_info = result.get('device_info', {})
                model = device_info.get('model', 'unknown')
                print(f"  ✅ Found: {device_type} - {model}")
            else:
                print(f"  ❌ No miner detected")
                
        except Exception as e:
            print(f"  💥 Error: {str(e)}")
        
        print()


if __name__ == "__main__":
    async def main():
        print("🔍 DEBUGGING PORT SCANNING ISSUES FOR 192.168.50.88\n")
        
        await debug_individual_port_connections()
        await debug_port_scanning()
        await debug_network_range_scanning()
        
        print("🏁 Debug complete!")
    
    asyncio.run(main())