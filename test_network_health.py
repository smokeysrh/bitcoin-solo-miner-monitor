"""
Test script for network health endpoint

This script tests the network health monitoring functionality by:
1. Testing the NetworkHealthMonitor service directly
2. Testing the API endpoint
"""

import asyncio
import sys
import requests
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

from src.backend.services.network_health import NetworkHealthMonitor


async def test_network_health_service():
    """Test the NetworkHealthMonitor service directly."""
    print("=" * 60)
    print("Testing NetworkHealthMonitor Service")
    print("=" * 60)
    
    monitor = NetworkHealthMonitor()
    
    # Test with localhost
    test_host = "127.0.0.1"
    print(f"\n1. Testing latency measurement for {test_host}...")
    latency = await monitor.measure_latency(test_host, count=3)
    if latency is not None:
        print(f"   ✓ Latency: {latency:.2f}ms")
    else:
        print(f"   ✗ Failed to measure latency")
    
    print(f"\n2. Testing packet loss measurement for {test_host}...")
    packet_loss = await monitor.measure_packet_loss(test_host, count=5)
    if packet_loss is not None:
        print(f"   ✓ Packet loss: {packet_loss:.1f}%")
    else:
        print(f"   ✗ Failed to measure packet loss")
    
    print(f"\n3. Testing connection uptime tracking...")
    test_miner_id = "test_miner_1"
    monitor.register_connection(test_miner_id)
    await asyncio.sleep(2)  # Wait 2 seconds
    uptime = monitor.get_connection_uptime(test_miner_id)
    if uptime is not None:
        print(f"   ✓ Uptime: {uptime} seconds")
    else:
        print(f"   ✗ Failed to get uptime")
    
    print(f"\n4. Testing comprehensive network health...")
    health = await monitor.get_network_health(test_miner_id, test_host)
    print(f"   Network Health Data:")
    print(f"   - Miner ID: {health.get('miner_id')}")
    print(f"   - Latency: {health.get('latency_ms')}ms")
    print(f"   - Packet Loss: {health.get('packet_loss_percent')}%")
    print(f"   - Uptime: {health.get('uptime_seconds')}s")
    print(f"   - Jitter: {health.get('jitter_ms')}ms")
    print(f"   - Status: {health.get('status')}")
    print(f"   - Last Measured: {health.get('last_measured')}")
    
    # Test with actual miner if available
    miner_host = "192.168.1.156"
    print(f"\n5. Testing with actual miner at {miner_host}...")
    miner_id = "bitaxe_192_168_1_156"
    health = await monitor.get_network_health(miner_id, miner_host)
    print(f"   Network Health Data:")
    print(f"   - Miner ID: {health.get('miner_id')}")
    print(f"   - Latency: {health.get('latency_ms')}ms")
    print(f"   - Packet Loss: {health.get('packet_loss_percent')}%")
    print(f"   - Uptime: {health.get('uptime_seconds')}s")
    print(f"   - Jitter: {health.get('jitter_ms')}ms")
    print(f"   - Status: {health.get('status')}")
    
    print("\n" + "=" * 60)
    print("Service tests completed!")
    print("=" * 60)


def test_api_endpoint():
    """Test the API endpoint."""
    print("\n" + "=" * 60)
    print("Testing API Endpoint")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # First, get list of miners
    print("\n1. Getting list of miners...")
    try:
        response = requests.get(f"{base_url}/api/miners", timeout=5)
        if response.status_code == 200:
            miners = response.json()
            print(f"   ✓ Found {len(miners)} miners")
            
            if miners:
                # Test network health for first miner
                miner = miners[0]
                miner_id = miner.get('id')
                print(f"\n2. Testing network health endpoint for miner: {miner_id}")
                
                # Use the exact URL format
                url = f"{base_url}/api/miners/{miner_id}/network-health"
                print(f"   Requesting: {url}")
                
                response = requests.get(
                    url,
                    timeout=30,  # Longer timeout for network tests
                    headers={"Accept": "application/json"}
                )
                
                print(f"   Response status: {response.status_code}")
                
                if response.status_code == 200:
                    health = response.json()
                    print(f"   ✓ Network health retrieved successfully:")
                    print(f"   - Miner ID: {health.get('miner_id')}")
                    print(f"   - Latency: {health.get('latency_ms')}ms")
                    print(f"   - Packet Loss: {health.get('packet_loss_percent')}%")
                    print(f"   - Uptime: {health.get('uptime_seconds')}s")
                    print(f"   - Jitter: {health.get('jitter_ms')}ms")
                    print(f"   - Status: {health.get('status')}")
                    print(f"   - Last Measured: {health.get('last_measured')}")
                else:
                    print(f"   ✗ Failed to get network health: {response.status_code}")
                    print(f"   Response: {response.text}")
            else:
                print("   ⚠ No miners found to test")
        else:
            print(f"   ✗ Failed to get miners: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ✗ Could not connect to API server")
        print("   Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("API endpoint tests completed!")
    print("=" * 60)


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Network Health Monitoring Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test service
    await test_network_health_service()
    
    # Test API endpoint
    test_api_endpoint()
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
