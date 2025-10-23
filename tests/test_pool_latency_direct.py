"""
Direct test script for pool latency measurement functionality.

This script tests pool latency measurement without requiring miners to be added.
"""

import asyncio
from src.backend.services.network_health import NetworkHealthMonitor


async def test_dns_resolution():
    """Test DNS resolution functionality."""
    print("=" * 60)
    print("Testing DNS Resolution")
    print("=" * 60)
    
    health_monitor = NetworkHealthMonitor()
    
    test_hostnames = [
        "public-pool.io",
        "solo.ckpool.org",
        "stratum.slushpool.com",
        "192.168.1.1",  # IP address (should not need resolution)
    ]
    
    for hostname in test_hostnames:
        print(f"\nResolving: {hostname}")
        ip = await health_monitor._resolve_hostname(hostname)
        if ip:
            print(f"  ✓ Resolved to: {ip}")
        else:
            print(f"  ⚠ Could not resolve")


async def test_pool_latency_measurement():
    """Test pool latency measurement with various pool URLs."""
    print("\n" + "=" * 60)
    print("Testing Pool Latency Measurement")
    print("=" * 60)
    
    health_monitor = NetworkHealthMonitor()
    
    # Test various pool URL formats
    test_pools = [
        ("stratum+tcp://public-pool.io", 21496),
        ("solo.ckpool.org", 3333),
        ("stratum.slushpool.com", 3333),
        ("192.168.1.1", 3333),  # Local pool/node
    ]
    
    for pool_url, pool_port in test_pools:
        print(f"\nTesting: {pool_url}:{pool_port}")
        
        latency = await health_monitor.measure_pool_latency(pool_url, pool_port)
        
        if latency is not None:
            print(f"  ✓ Latency: {latency:.2f} ms")
            
            # Calculate health status
            status = health_monitor._calculate_pool_health_status(latency)
            print(f"  ✓ Status: {status}")
            
            # Show color coding
            if status == "healthy":
                print(f"  ✓ Color: Green (< 100ms)")
            elif status == "warning":
                print(f"  ⚠ Color: Yellow (100-200ms)")
            elif status == "critical":
                print(f"  ❌ Color: Red (>= 200ms)")
        else:
            print(f"  ⚠ Could not measure latency (pool may be unreachable)")


async def test_tcp_fallback():
    """Test TCP connection timing fallback."""
    print("\n" + "=" * 60)
    print("Testing TCP Connection Timing Fallback")
    print("=" * 60)
    
    health_monitor = NetworkHealthMonitor()
    
    # Test TCP connection to a known server
    test_servers = [
        ("8.8.8.8", 53),  # Google DNS
        ("1.1.1.1", 53),  # Cloudflare DNS
    ]
    
    for host, port in test_servers:
        print(f"\nTesting TCP connection: {host}:{port}")
        
        latency = await health_monitor._measure_tcp_latency(host, port)
        
        if latency is not None:
            print(f"  ✓ TCP Latency: {latency:.2f} ms")
        else:
            print(f"  ⚠ TCP connection failed")


async def test_health_status_calculation():
    """Test health status calculation with different latency values."""
    print("\n" + "=" * 60)
    print("Testing Health Status Calculation")
    print("=" * 60)
    
    health_monitor = NetworkHealthMonitor()
    
    test_cases = [
        (50, 1, 50, "healthy"),
        (150, 1, 50, "degraded"),
        (250, 1, 50, "poor"),
        (50, 1, 150, "degraded"),
        (50, 1, 250, "poor"),
        (50, 6, 50, "poor"),
    ]
    
    print("\nTest Cases (miner_latency, packet_loss, pool_latency -> expected_status):")
    for miner_lat, packet_loss, pool_lat, expected in test_cases:
        status = health_monitor._calculate_health_status(miner_lat, packet_loss, pool_lat)
        result = "✓" if status == expected else "❌"
        print(f"  {result} ({miner_lat}ms, {packet_loss}%, {pool_lat}ms) -> {status} (expected: {expected})")


async def main():
    """Run all tests."""
    try:
        await test_dns_resolution()
        await test_pool_latency_measurement()
        await test_tcp_fallback()
        await test_health_status_calculation()
        
        print("\n" + "=" * 60)
        print("✓ All direct tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
