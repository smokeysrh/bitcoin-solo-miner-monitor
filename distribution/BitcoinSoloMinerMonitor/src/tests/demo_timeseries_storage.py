"""
Demonstration of SQLite Time-Series Storage Functionality

This script demonstrates the new SQLite-based time-series storage capabilities
that replace InfluxDB dependency.
"""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import json

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mock the config module for demo
class MockDBConfig:
    def __getitem__(self, key):
        if key == "sqlite":
            return {"path": self.sqlite_path}
        elif key == "influxdb":
            return {
                "url": "http://localhost:8086",
                "org": "demo_org", 
                "bucket": "demo_bucket",
                "token": "demo_token"
            }
        return {}

# Set up mock config
mock_config = MockDBConfig()
sys.modules['config'] = type('MockConfig', (), {})()
sys.modules['config.app_config'] = type('MockAppConfig', (), {'DB_CONFIG': mock_config})()

from src.backend.services.data_storage import DataStorage


async def demo_timeseries_functionality():
    """
    Demonstrate the SQLite time-series storage functionality.
    """
    print("🚀 SQLite Time-Series Storage Demo")
    print("=" * 50)
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_demo.db')
    db_path = temp_db.name
    temp_db.close()
    mock_config.sqlite_path = db_path
    
    storage = DataStorage()
    
    try:
        # Initialize storage
        print("📊 Initializing SQLite time-series storage...")
        await storage.initialize()
        print("✅ Storage initialized successfully")
        
        # Demo miner configuration
        miner_id = "demo_bitaxe_001"
        miner_config = {
            "name": "Demo Bitaxe Miner",
            "type": "bitaxe",
            "ip_address": "10.0.0.100",
            "port": 4028,
            "pool_url": "stratum+tcp://solo.ckpool.org:3333"
        }
        
        print(f"\n🔧 Saving miner configuration for {miner_id}...")
        await storage.save_miner_config(miner_id, miner_config)
        print("✅ Miner configuration saved")
        
        # Simulate metrics over time
        print(f"\n📈 Generating time-series metrics data...")
        base_time = datetime.now() - timedelta(hours=2)
        
        for i in range(24):  # 24 data points over 2 hours (5-minute intervals)
            timestamp = base_time + timedelta(minutes=i * 5)
            
            # Simulate realistic mining metrics with some variation
            metrics = {
                "hashrate": 500.0 + (i % 5) * 10 + (i * 0.5),  # Varying hashrate
                "temperature": 65.0 + (i % 3) * 2,  # Temperature fluctuation
                "power": 3250.0 + (i % 4) * 25,  # Power consumption variation
                "shares_accepted": 150 + i * 2,  # Increasing accepted shares
                "shares_rejected": 2 + (i % 7),  # Occasional rejected shares
                "efficiency": 6.5 - (i * 0.01),  # Slightly decreasing efficiency
                "fan_speed": 3000 + (i % 6) * 100,  # Fan speed variation
                "voltage": 12.0 + (i % 2) * 0.1  # Voltage stability
            }
            
            await storage.save_metrics(miner_id, metrics, timestamp)
            
            # Also save status snapshots every 30 minutes
            if i % 6 == 0:
                status = {
                    "status": "mining",
                    "uptime": 86400 + i * 300,  # Increasing uptime
                    "pool_url": "stratum+tcp://solo.ckpool.org:3333",
                    "worker": "bc1qexample123",
                    "difficulty": 1000000 + i * 10000,
                    "network_hashrate": "500000000000000000",
                    "last_share": timestamp.isoformat(),
                    "firmware_version": "2.1.0",
                    "chip_count": 1,
                    "frequency": 500 + i
                }
                await storage.save_miner_status(miner_id, status, timestamp)
        
        print(f"✅ Generated {24 * 8} metric data points and {4} status snapshots")
        
        # Demonstrate data retrieval
        print(f"\n📊 Retrieving latest metrics...")
        latest_metrics = await storage.get_latest_metrics(miner_id)
        print(f"Latest hashrate: {latest_metrics.get('hashrate', {}).get('value', 'N/A')} TH/s")
        print(f"Latest temperature: {latest_metrics.get('temperature', {}).get('value', 'N/A')} °C")
        print(f"Latest power: {latest_metrics.get('power', {}).get('value', 'N/A')} W")
        
        # Demonstrate status retrieval
        print(f"\n📋 Retrieving latest status...")
        latest_status = await storage.get_latest_miner_status(miner_id)
        print(f"Status: {latest_status.get('status', 'N/A')}")
        print(f"Uptime: {latest_status.get('uptime', 'N/A')} seconds")
        print(f"Difficulty: {latest_status.get('difficulty', 'N/A')}")
        
        # Demonstrate time-range queries
        print(f"\n🕐 Querying raw metrics for last hour...")
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        raw_metrics = await storage.get_metrics_raw(miner_id, start_time, end_time, ["hashrate", "temperature"])
        print(f"Found {len(raw_metrics)} raw metric records")
        
        # Show sample raw data
        if raw_metrics:
            print("Sample raw metrics:")
            for metric in raw_metrics[:5]:  # Show first 5
                print(f"  {metric['timestamp']}: {metric['metric_type']} = {metric['value']} {metric['unit']}")
        
        # Demonstrate aggregated queries
        print(f"\n📊 Querying aggregated metrics (5-minute intervals)...")
        aggregated_5m = await storage.get_metrics(miner_id, start_time, end_time, interval="5m", metric_types=["hashrate"])
        print(f"Found {len(aggregated_5m)} aggregated 5-minute intervals")
        
        if aggregated_5m:
            print("Sample 5-minute aggregates:")
            for agg in aggregated_5m[:3]:  # Show first 3
                print(f"  {agg['time_bucket']}: avg={agg['avg_value']:.1f}, min={agg['min_value']:.1f}, max={agg['max_value']:.1f} TH/s")
        
        print(f"\n📊 Querying aggregated metrics (hourly intervals)...")
        aggregated_1h = await storage.get_metrics(miner_id, start_time, end_time, interval="1h")
        print(f"Found {len(aggregated_1h)} aggregated hourly intervals")
        
        if aggregated_1h:
            print("Sample hourly aggregates:")
            for agg in aggregated_1h[:3]:  # Show first 3
                print(f"  {agg['time_bucket']}: {agg['metric_type']} avg={agg['avg_value']:.1f} {agg['unit']}")
        
        # Demonstrate data cleanup
        print(f"\n🧹 Testing data cleanup (30-day retention)...")
        cleanup_result = await storage.cleanup_old_metrics(retention_days=30)
        print(f"Cleanup result: {'✅ Success' if cleanup_result else '❌ Failed'}")
        
        # Show final statistics
        print(f"\n📈 Final Statistics:")
        all_configs = await storage.get_all_miner_configs()
        print(f"Total miners configured: {len(all_configs)}")
        
        # Count remaining metrics
        all_metrics = await storage.get_metrics_raw(
            miner_id, 
            datetime.now() - timedelta(days=1), 
            datetime.now()
        )
        print(f"Total metric records: {len(all_metrics)}")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"Database file: {db_path}")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        await storage.close()
        # Clean up demo database
        Path(db_path).unlink(missing_ok=True)
        print("🧹 Demo database cleaned up")


if __name__ == "__main__":
    asyncio.run(demo_timeseries_functionality())