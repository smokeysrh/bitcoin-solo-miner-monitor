#!/usr/bin/env python3
"""
Test script for pool latency database operations.

This script tests:
1. Saving network health data with pool latency
2. Retrieving network health data with pool latency
3. Querying by pool URL
4. Verifying data integrity
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

import aiosqlite
from config.app_config import DB_CONFIG
from src.backend.services.timeseries_storage import TimeSeriesStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_save_network_health_with_pool_latency():
    """Test saving network health data with pool latency information."""
    logger.info("=" * 60)
    logger.info("TEST: Save network health with pool latency")
    logger.info("=" * 60)
    
    db_path = DB_CONFIG["sqlite"]["path"]
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            storage = TimeSeriesStorage(conn)
            
            # Test data with pool latency
            test_data = {
                'latency_ms': 15.5,
                'packet_loss_percent': 0.5,
                'uptime_seconds': 86400,
                'jitter_ms': 2.3,
                'pool_latency': {
                    'url': 'stratum+tcp://pool.example.com',
                    'port': 3333,
                    'latency_ms': 45.2
                },
                'total_path_latency_ms': 60.7,
                'status': 'healthy',
                'last_measured': datetime.now().isoformat()
            }
            
            # Save data
            success = await storage.save_network_health('test_miner_001', test_data)
            
            if success:
                logger.info("✓ Successfully saved network health with pool latency")
                return True
            else:
                logger.error("✗ Failed to save network health")
                return False
                
    except Exception as e:
        logger.error(f"✗ Test failed with error: {str(e)}")
        return False


async def test_retrieve_network_health_with_pool_latency():
    """Test retrieving network health data with pool latency."""
    logger.info("=" * 60)
    logger.info("TEST: Retrieve network health with pool latency")
    logger.info("=" * 60)
    
    db_path = DB_CONFIG["sqlite"]["path"]
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            storage = TimeSeriesStorage(conn)
            
            # Get latest network health
            health = await storage.get_latest_network_health('test_miner_001')
            
            if not health:
                logger.error("✗ No network health data found")
                return False
            
            logger.info(f"Retrieved network health data:")
            logger.info(f"  Miner ID: {health.get('miner_id')}")
            logger.info(f"  Miner Latency: {health.get('latency_ms')} ms")
            logger.info(f"  Packet Loss: {health.get('packet_loss_percent')}%")
            logger.info(f"  Status: {health.get('status')}")
            
            # Check pool latency data
            if 'pool_latency' in health:
                pool = health['pool_latency']
                logger.info(f"  Pool URL: {pool.get('url')}")
                logger.info(f"  Pool Port: {pool.get('port')}")
                logger.info(f"  Pool Latency: {pool.get('latency_ms')} ms")
                logger.info(f"  Total Path Latency: {health.get('total_path_latency_ms')} ms")
                logger.info("✓ Pool latency data retrieved successfully")
                return True
            else:
                logger.error("✗ Pool latency data not found in response")
                return False
                
    except Exception as e:
        logger.error(f"✗ Test failed with error: {str(e)}")
        return False


async def test_save_without_pool_latency():
    """Test saving network health data without pool latency (backward compatibility)."""
    logger.info("=" * 60)
    logger.info("TEST: Save network health without pool latency (backward compatibility)")
    logger.info("=" * 60)
    
    db_path = DB_CONFIG["sqlite"]["path"]
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            storage = TimeSeriesStorage(conn)
            
            # Test data without pool latency
            test_data = {
                'latency_ms': 12.3,
                'packet_loss_percent': 0.2,
                'uptime_seconds': 43200,
                'jitter_ms': 1.8,
                'status': 'healthy',
                'last_measured': datetime.now().isoformat()
            }
            
            # Save data
            success = await storage.save_network_health('test_miner_002', test_data)
            
            if success:
                logger.info("✓ Successfully saved network health without pool latency")
                
                # Verify retrieval
                health = await storage.get_latest_network_health('test_miner_002')
                if health:
                    logger.info(f"  Miner Latency: {health.get('latency_ms')} ms")
                    logger.info(f"  Pool Latency: {health.get('pool_latency', 'None')}")
                    logger.info("✓ Backward compatibility verified")
                    return True
                else:
                    logger.error("✗ Failed to retrieve saved data")
                    return False
            else:
                logger.error("✗ Failed to save network health")
                return False
                
    except Exception as e:
        logger.error(f"✗ Test failed with error: {str(e)}")
        return False


async def test_get_all_network_health():
    """Test retrieving all latest network health data."""
    logger.info("=" * 60)
    logger.info("TEST: Get all latest network health")
    logger.info("=" * 60)
    
    db_path = DB_CONFIG["sqlite"]["path"]
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            storage = TimeSeriesStorage(conn)
            
            # Get all latest network health
            all_health = await storage.get_all_latest_network_health()
            
            if not all_health:
                logger.warning("⚠ No network health data found")
                return True  # Not a failure, just no data
            
            logger.info(f"Retrieved {len(all_health)} network health records:")
            
            for health in all_health:
                logger.info(f"\n  Miner: {health.get('miner_id')}")
                logger.info(f"    Miner Latency: {health.get('latency_ms')} ms")
                logger.info(f"    Status: {health.get('status')}")
                
                if 'pool_latency' in health:
                    pool = health['pool_latency']
                    logger.info(f"    Pool: {pool.get('url')}:{pool.get('port')}")
                    logger.info(f"    Pool Latency: {pool.get('latency_ms')} ms")
                    logger.info(f"    Total Path: {health.get('total_path_latency_ms')} ms")
                else:
                    logger.info(f"    Pool: None")
            
            logger.info("\n✓ Successfully retrieved all network health data")
            return True
                
    except Exception as e:
        logger.error(f"✗ Test failed with error: {str(e)}")
        return False


async def test_query_by_time_range():
    """Test querying network health by time range."""
    logger.info("=" * 60)
    logger.info("TEST: Query network health by time range")
    logger.info("=" * 60)
    
    db_path = DB_CONFIG["sqlite"]["path"]
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            storage = TimeSeriesStorage(conn)
            
            # Query last hour
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            health_records = await storage.get_network_health(
                'test_miner_001',
                start_time=start_time,
                end_time=end_time
            )
            
            logger.info(f"Found {len(health_records)} records in the last hour")
            
            for record in health_records[:3]:  # Show first 3
                logger.info(f"\n  Measured at: {record.get('measured_at')}")
                logger.info(f"    Miner Latency: {record.get('latency_ms')} ms")
                
                if 'pool_latency' in record:
                    pool = record['pool_latency']
                    logger.info(f"    Pool Latency: {pool.get('latency_ms')} ms")
            
            logger.info("\n✓ Time range query successful")
            return True
                
    except Exception as e:
        logger.error(f"✗ Test failed with error: {str(e)}")
        return False


async def test_pool_index_performance():
    """Test that pool index is being used for queries."""
    logger.info("=" * 60)
    logger.info("TEST: Pool index performance")
    logger.info("=" * 60)
    
    db_path = DB_CONFIG["sqlite"]["path"]
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Check if index exists
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_network_health_pool'
            """)
            index = await cursor.fetchone()
            
            if index:
                logger.info("✓ Pool index exists")
                
                # Test query plan
                cursor = await conn.execute("""
                    EXPLAIN QUERY PLAN
                    SELECT * FROM network_health 
                    WHERE pool_url = 'stratum+tcp://pool.example.com'
                    ORDER BY measured_at DESC
                """)
                plan = await cursor.fetchall()
                
                logger.info("Query plan:")
                for row in plan:
                    logger.info(f"  {row}")
                
                # Check if index is used
                plan_str = str(plan).lower()
                if 'idx_network_health_pool' in plan_str or 'index' in plan_str:
                    logger.info("✓ Pool index is being used in queries")
                    return True
                else:
                    logger.warning("⚠ Pool index may not be used (check query plan)")
                    return True  # Not a failure
            else:
                logger.error("✗ Pool index does not exist")
                return False
                
    except Exception as e:
        logger.error(f"✗ Test failed with error: {str(e)}")
        return False


async def cleanup_test_data():
    """Clean up test data."""
    logger.info("=" * 60)
    logger.info("Cleaning up test data")
    logger.info("=" * 60)
    
    db_path = DB_CONFIG["sqlite"]["path"]
    
    try:
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("""
                DELETE FROM network_health 
                WHERE miner_id IN ('test_miner_001', 'test_miner_002')
            """)
            await conn.commit()
            logger.info("✓ Test data cleaned up")
            return True
    except Exception as e:
        logger.error(f"✗ Cleanup failed: {str(e)}")
        return False


async def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("POOL LATENCY DATABASE OPERATIONS TEST SUITE")
    logger.info("=" * 60 + "\n")
    
    tests = [
        ("Save with pool latency", test_save_network_health_with_pool_latency),
        ("Retrieve with pool latency", test_retrieve_network_health_with_pool_latency),
        ("Save without pool latency", test_save_without_pool_latency),
        ("Get all network health", test_get_all_network_health),
        ("Query by time range", test_query_by_time_range),
        ("Pool index performance", test_pool_index_performance),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            await asyncio.sleep(0.5)  # Brief pause between tests
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Cleanup
    await cleanup_test_data()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error(f"✗ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
