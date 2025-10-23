"""
Test script for pool latency measurement functionality.

This script tests the enhanced network health service with pool latency monitoring.
"""

import asyncio
import sys
from src.backend.services.network_health import NetworkHealthMonitor
from src.backend.services.miner_manager import MinerManager


async def test_pool_latency():
    """Test pool latency measurement functionality."""
    print("=" * 60)
    print("Testing Pool Latency Measurement")
    print("=" * 60)
    
    # Initialize network health monitor
    health_monitor = NetworkHealthMonitor()
    
    # Initialize miner manager
    miner_manager = MinerManager()
    health_monitor.set_miner_manager(miner_manager)
    
    # Start miner manager
    await miner_manager.start()
    
    try:
        # Get all miners
        miners = await miner_manager.get_miners()
        
        if not miners:
            print("\n❌ No miners found. Please add a miner first.")
            return
        
        print(f"\n✓ Found {len(miners)} miner(s)")
        
        # Test each miner
        for miner in miners:
            miner_id = miner.get('id')
            miner_name = miner.get('name', 'Unknown')
            ip_address = miner.get('ip_address')
            
            print(f"\n{'=' * 60}")
            print(f"Testing Miner: {miner_name} ({miner_id})")
            print(f"IP Address: {ip_address}")
            print(f"{'=' * 60}")
            
            # Test 1: Get pool info from miner
            print("\n1. Getting pool configuration...")
            pool_info = await health_monitor.get_pool_info_from_miner(miner_id)
            
            if pool_info:
                print(f"   ✓ Found {len(pool_info)} pool(s):")
                for i, pool in enumerate(pool_info, 1):
                    print(f"     Pool {i}:")
                    print(f"       URL: {pool.get('url')}")
                    print(f"       Port: {pool.get('port')}")
                    print(f"       Active: {pool.get('is_active')}")
                    print(f"       Fallback: {pool.get('is_fallback', False)}")
            else:
                print("   ⚠ No pool configuration found")
            
            # Test 2: Measure pool latency
            if pool_info:
                print("\n2. Measuring pool latency...")
                active_pool = next((p for p in pool_info if p.get('is_active')), pool_info[0])
                pool_url = active_pool.get('url')
                pool_port = active_pool.get('port')
                
                print(f"   Testing pool: {pool_url}:{pool_port}")
                
                pool_latency = await health_monitor.measure_pool_latency(pool_url, pool_port)
                
                if pool_latency is not None:
                    print(f"   ✓ Pool latency: {pool_latency:.2f} ms")
                    
                    # Calculate pool health status
                    pool_status = health_monitor._calculate_pool_health_status(pool_latency)
                    print(f"   ✓ Pool status: {pool_status}")
                else:
                    print("   ⚠ Could not measure pool latency")
            
            # Test 3: Get comprehensive network health (including pool latency)
            print("\n3. Getting comprehensive network health...")
            health_data = await health_monitor.get_network_health(miner_id, ip_address)
            
            print(f"   Miner Latency: {health_data.get('miner_latency_ms')} ms")
            print(f"   Packet Loss: {health_data.get('packet_loss_percent')}%")
            print(f"   Uptime: {health_data.get('uptime_seconds')} seconds")
            
            pool_data = health_data.get('pool_latency')
            if pool_data:
                print(f"\n   Pool Information:")
                print(f"     URL: {pool_data.get('url')}")
                print(f"     Port: {pool_data.get('port')}")
                print(f"     Latency: {pool_data.get('latency_ms')} ms")
                print(f"     Status: {pool_data.get('status')}")
            
            total_latency = health_data.get('total_path_latency_ms')
            if total_latency:
                print(f"\n   Total Path Latency: {total_latency:.2f} ms")
            
            print(f"\n   Overall Status: {health_data.get('status')}")
        
        # Test 4: Get aggregate network health
        print(f"\n{'=' * 60}")
        print("Testing Aggregate Network Health")
        print(f"{'=' * 60}")
        
        # Collect health data for all miners
        all_health_data = []
        for miner in miners:
            health_data = await health_monitor.get_network_health(
                miner.get('id'),
                miner.get('ip_address')
            )
            all_health_data.append(health_data)
        
        aggregate = await health_monitor.get_aggregate_network_health(all_health_data)
        
        print(f"\nAggregate Statistics:")
        print(f"  Total Miners: {aggregate.get('total_miners')}")
        print(f"  Average Miner Latency: {aggregate.get('average_miner_latency_ms')} ms")
        print(f"  Average Pool Latency: {aggregate.get('average_pool_latency_ms')} ms")
        print(f"  Average Total Path Latency: {aggregate.get('average_total_path_latency_ms')} ms")
        print(f"  Average Packet Loss: {aggregate.get('average_packet_loss_percent')}%")
        print(f"\nHealth Status Counts:")
        print(f"  Healthy: {aggregate.get('healthy_count')}")
        print(f"  Degraded: {aggregate.get('degraded_count')}")
        print(f"  Poor: {aggregate.get('poor_count')}")
        print(f"  Unknown: {aggregate.get('unknown_count')}")
        
        unique_pools = aggregate.get('unique_pools', [])
        if unique_pools:
            print(f"\nUnique Pools ({len(unique_pools)}):")
            for pool in unique_pools:
                print(f"  {pool.get('url')}:{pool.get('port')}")
                print(f"    Latency: {pool.get('latency_ms')} ms")
                print(f"    Status: {pool.get('status')}")
                print(f"    Miners: {pool.get('miner_count')}")
        
        print(f"\n{'=' * 60}")
        print("✓ All tests completed successfully!")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Stop miner manager
        await miner_manager.stop()


if __name__ == "__main__":
    asyncio.run(test_pool_latency())
