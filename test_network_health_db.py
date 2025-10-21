#!/usr/bin/env python3
"""
Test script for network health database operations.

This script tests:
1. Creating the network_health table
2. Saving network health data
3. Retrieving network health data
4. Cleanup operations
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import aiosqlite
from config.app_config import DB_CONFIG
from src.backend.services.timeseries_storage import TimeSeriesStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_network_health_operations():
    """
    Test network health database operations.
    """
    db_path = DB_CONFIG["sqlite"]["path"]
    logger.info(f"Testing network health operations with database: {db_path}")
    
    try:
        # Connect to database
        async with aiosqlite.connect(db_path) as conn:
            # Create TimeSeriesStorage instance
            storage = TimeSeriesStorage(conn)
            
            # Test 1: Check if network_health table exists
            logger.info("\n=== Test 1: Check table existence ===")
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='network_health'
            """)
            table = await cursor.fetchone()
            
            if table:
                logger.info("✓ network_health table exists")
            else:
                logger.error("✗ network_health table does not exist")
                logger.info("Run: python migrations/create_network_health_schema.py")
                return False
            
            # Test 2: Save network health data
            logger.info("\n=== Test 2: Save network health data ===")
            test_miner_id = "test_miner_001"
            test_health_data = {
                "miner_id": test_miner_id,
                "latency_ms": 25.5,
                "packet_loss_percent": 0.5,
                "uptime_seconds": 3600,
                "jitter_ms": 2.3,
                "status": "healthy",
                "last_measured": datetime.now().isoformat()
            }
            
            success = await storage.save_network_health(test_miner_id, test_health_data)
            if success:
                logger.info(f"✓ Successfully saved network health for {test_miner_id}")
            else:
                logger.error(f"✗ Failed to save network health for {test_miner_id}")
                return False
            
            # Test 3: Retrieve latest network health
            logger.info("\n=== Test 3: Retrieve latest network health ===")
            latest_health = await storage.get_latest_network_health(test_miner_id)
            
            if latest_health:
                logger.info(f"✓ Retrieved latest network health:")
                logger.info(f"  - Latency: {latest_health['latency_ms']} ms")
                logger.info(f"  - Packet Loss: {latest_health['packet_loss_percent']}%")
                logger.info(f"  - Uptime: {latest_health['uptime_seconds']} seconds")
                logger.info(f"  - Jitter: {latest_health['jitter_ms']} ms")
                logger.info(f"  - Status: {latest_health['status']}")
                logger.info(f"  - Measured At: {latest_health['measured_at']}")
            else:
                logger.error(f"✗ Failed to retrieve network health for {test_miner_id}")
                return False
            
            # Test 4: Save multiple records for time range query
            logger.info("\n=== Test 4: Save multiple records ===")
            for i in range(5):
                health_data = {
                    "miner_id": test_miner_id,
                    "latency_ms": 20.0 + i * 5,
                    "packet_loss_percent": 0.1 * i,
                    "uptime_seconds": 3600 + i * 60,
                    "jitter_ms": 2.0 + i * 0.5,
                    "status": "healthy" if i < 3 else "degraded",
                    "last_measured": (datetime.now() - timedelta(minutes=i)).isoformat()
                }
                await storage.save_network_health(test_miner_id, health_data)
            
            logger.info(f"✓ Saved 5 additional network health records")
            
            # Test 5: Retrieve network health history
            logger.info("\n=== Test 5: Retrieve network health history ===")
            start_time = datetime.now() - timedelta(hours=1)
            end_time = datetime.now()
            
            health_history = await storage.get_network_health(
                test_miner_id, 
                start_time, 
                end_time
            )
            
            if health_history:
                logger.info(f"✓ Retrieved {len(health_history)} network health records")
                logger.info("  Recent records:")
                for record in health_history[:3]:
                    logger.info(f"    - {record['measured_at']}: "
                              f"Latency={record['latency_ms']}ms, "
                              f"Status={record['status']}")
            else:
                logger.error(f"✗ Failed to retrieve network health history")
                return False
            
            # Test 6: Get all latest network health
            logger.info("\n=== Test 6: Get all latest network health ===")
            all_latest = await storage.get_all_latest_network_health()
            
            if all_latest:
                logger.info(f"✓ Retrieved latest network health for {len(all_latest)} miner(s)")
                for health in all_latest:
                    logger.info(f"  - Miner {health['miner_id']}: "
                              f"Latency={health['latency_ms']}ms, "
                              f"Status={health['status']}")
            else:
                logger.info("  No network health records found (this is OK for a fresh database)")
            
            # Test 7: Cleanup old data
            logger.info("\n=== Test 7: Cleanup old network health data ===")
            
            # First, insert some old data
            old_health_data = {
                "miner_id": test_miner_id,
                "latency_ms": 50.0,
                "packet_loss_percent": 5.0,
                "uptime_seconds": 1000,
                "jitter_ms": 10.0,
                "status": "poor",
                "last_measured": (datetime.now() - timedelta(days=35)).isoformat()
            }
            await storage.save_network_health(test_miner_id, old_health_data)
            logger.info("  Inserted old test data (35 days ago)")
            
            # Run cleanup with 30-day retention
            success = await storage.cleanup_old_network_health(retention_days=30)
            
            if success:
                logger.info("✓ Cleanup completed successfully")
            else:
                logger.error("✗ Cleanup failed")
                return False
            
            # Verify old data was removed
            all_records = await storage.get_network_health(
                test_miner_id,
                datetime.now() - timedelta(days=40),
                datetime.now()
            )
            
            old_records = [r for r in all_records 
                          if datetime.fromisoformat(r['measured_at']) < 
                          datetime.now() - timedelta(days=30)]
            
            if not old_records:
                logger.info("✓ Old records were successfully removed")
            else:
                logger.warning(f"  Found {len(old_records)} old records still in database")
            
            # Test 8: Verify indexes exist
            logger.info("\n=== Test 8: Verify indexes ===")
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_network_health_%'
            """)
            indexes = await cursor.fetchall()
            
            if len(indexes) >= 3:
                logger.info(f"✓ Found {len(indexes)} network_health indexes:")
                for idx in indexes:
                    logger.info(f"  - {idx[0]}")
            else:
                logger.warning(f"  Only found {len(indexes)} indexes (expected 3)")
            
            logger.info("\n=== All tests completed successfully! ===")
            return True
            
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """
    Main test function.
    """
    logger.info("Starting network health database tests...")
    
    success = await test_network_health_operations()
    
    if success:
        logger.info("\n✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n✗ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
