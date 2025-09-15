"""
Integration tests for DataStorage class with SQLite time-series functionality

This module tests the integration between DataStorage and TimeSeriesStorage.
"""

import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import json

# Mock the config module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mock DB_CONFIG
class MockDBConfig:
    def __getitem__(self, key):
        if key == "sqlite":
            return {"path": self.sqlite_path}
        elif key == "influxdb":
            return {
                "url": "http://localhost:8086",
                "org": "test_org",
                "bucket": "test_bucket",
                "token": "test_token"
            }
        return {}

# Set up mock config
mock_config = MockDBConfig()
sys.modules['config'] = type('MockConfig', (), {})()
sys.modules['config.app_config'] = type('MockAppConfig', (), {'DB_CONFIG': mock_config})()

from src.backend.services.data_storage import DataStorage


class TestDataStorageIntegration(unittest.TestCase):
    """
    Integration test cases for DataStorage with SQLite time-series.
    """
    
    def setUp(self):
        """
        Set up test database and storage instance.
        """
        import uuid
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=f'_{uuid.uuid4().hex[:8]}.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Set the mock config path
        mock_config.sqlite_path = self.db_path
        
        # Test data
        self.test_miner_id = "integration_test_miner"
        self.test_timestamp = datetime.now()
        self.test_metrics = {
            "hashrate": 500.0,
            "temperature": 65.5,
            "power": 3250.0,
            "shares_accepted": 150,
            "shares_rejected": 2,
            "efficiency": 6.5
        }
        self.test_config = {
            "name": "Test Miner",
            "type": "bitaxe",
            "ip_address": "10.0.0.100",
            "port": 4028
        }
        self.test_status = {
            "status": "mining",
            "uptime": 86400,
            "pool_url": "stratum+tcp://solo.ckpool.org:3333",
            "worker": "bc1qexample",
            "difficulty": 1000000
        }
    
    def tearDown(self):
        """
        Clean up test database.
        """
        Path(self.db_path).unlink(missing_ok=True)
    
    async def test_full_integration_workflow(self):
        """
        Test complete workflow: save config, save metrics, save status, retrieve data.
        """
        storage = DataStorage()
        
        try:
            # Initialize storage
            await storage.initialize()
            
            # 1. Save miner configuration
            config_result = await storage.save_miner_config(self.test_miner_id, self.test_config)
            self.assertTrue(config_result)
            
            # 2. Retrieve miner configuration
            retrieved_config = await storage.get_miner_config(self.test_miner_id)
            self.assertIsNotNone(retrieved_config)
            self.assertEqual(retrieved_config["name"], "Test Miner")
            self.assertEqual(retrieved_config["type"], "bitaxe")
            
            # 3. Save metrics
            metrics_result = await storage.save_metrics(self.test_miner_id, self.test_metrics, self.test_timestamp)
            self.assertTrue(metrics_result)
            
            # 4. Save status
            status_result = await storage.save_miner_status(self.test_miner_id, self.test_status, self.test_timestamp)
            self.assertTrue(status_result)
            
            # 5. Retrieve latest metrics
            latest_metrics = await storage.get_latest_metrics(self.test_miner_id)
            self.assertIsInstance(latest_metrics, dict)
            self.assertIn('hashrate', latest_metrics)
            self.assertEqual(latest_metrics['hashrate']['value'], 500.0)
            self.assertEqual(latest_metrics['hashrate']['unit'], 'TH/s')
            
            # 6. Retrieve latest status
            latest_status = await storage.get_latest_miner_status(self.test_miner_id)
            self.assertIsInstance(latest_status, dict)
            self.assertEqual(latest_status['status'], 'mining')
            self.assertEqual(latest_status['uptime'], 86400)
            
            # 7. Test time-range queries
            start_time = self.test_timestamp - timedelta(minutes=5)
            end_time = self.test_timestamp + timedelta(minutes=5)
            
            raw_metrics = await storage.get_metrics_raw(self.test_miner_id, start_time, end_time)
            self.assertGreater(len(raw_metrics), 0)
            
            # 8. Test aggregated queries
            aggregated_metrics = await storage.get_metrics(self.test_miner_id, start_time, end_time, interval="1h")
            self.assertGreater(len(aggregated_metrics), 0)
            
        finally:
            await storage.close()
    
    async def test_multiple_metrics_over_time(self):
        """
        Test saving and retrieving multiple metrics over time.
        """
        storage = DataStorage()
        
        try:
            await storage.initialize()
            
            # Save miner config first
            await storage.save_miner_config(self.test_miner_id, self.test_config)
            
            # Save metrics at different times
            base_time = self.test_timestamp
            for i in range(5):
                timestamp = base_time + timedelta(minutes=i * 10)
                metrics = {
                    "hashrate": 500.0 + i * 10,
                    "temperature": 65.0 + i * 2,
                    "power": 3250.0 + i * 50
                }
                result = await storage.save_metrics(self.test_miner_id, metrics, timestamp)
                self.assertTrue(result)
            
            # Query metrics over time range
            start_time = base_time
            end_time = base_time + timedelta(hours=1)
            
            raw_metrics = await storage.get_metrics_raw(self.test_miner_id, start_time, end_time)
            self.assertEqual(len(raw_metrics), 15)  # 5 timestamps * 3 metrics each
            
            # Test aggregated metrics
            aggregated = await storage.get_metrics(self.test_miner_id, start_time, end_time, interval="1h")
            self.assertGreater(len(aggregated), 0)
            
            # Verify aggregation values
            hashrate_agg = next((m for m in aggregated if m['metric_type'] == 'hashrate'), None)
            self.assertIsNotNone(hashrate_agg)
            self.assertGreaterEqual(hashrate_agg['avg_value'], 500.0)
            self.assertGreaterEqual(hashrate_agg['min_value'], 500.0)
            self.assertGreaterEqual(hashrate_agg['max_value'], 500.0)
            self.assertGreater(hashrate_agg['sample_count'], 0)
            
        finally:
            await storage.close()
    
    async def test_data_cleanup(self):
        """
        Test data cleanup functionality.
        """
        storage = DataStorage()
        
        try:
            await storage.initialize()
            
            # Save miner config
            await storage.save_miner_config(self.test_miner_id, self.test_config)
            
            # Save old metrics (beyond retention period)
            old_timestamp = datetime.now() - timedelta(days=35)
            old_metrics = {"hashrate": 400.0, "temperature": 60.0}
            await storage.save_metrics(self.test_miner_id, old_metrics, old_timestamp)
            
            # Save recent metrics
            recent_timestamp = datetime.now() - timedelta(hours=1)
            recent_metrics = {"hashrate": 500.0, "temperature": 65.0}
            await storage.save_metrics(self.test_miner_id, recent_metrics, recent_timestamp)
            
            # Verify both metrics exist
            all_metrics = await storage.get_metrics_raw(
                self.test_miner_id, 
                old_timestamp - timedelta(days=1), 
                datetime.now()
            )
            self.assertEqual(len(all_metrics), 4)  # 2 timestamps * 2 metrics each
            
            # Clean up old data (30 day retention)
            cleanup_result = await storage.cleanup_old_metrics(retention_days=30)
            self.assertTrue(cleanup_result)
            
            # Verify old metrics are gone, recent metrics remain
            remaining_metrics = await storage.get_metrics_raw(
                self.test_miner_id,
                old_timestamp - timedelta(days=1),
                datetime.now()
            )
            self.assertEqual(len(remaining_metrics), 2)  # Only recent metrics should remain
            
        finally:
            await storage.close()
    
    def test_sync_wrapper(self):
        """
        Wrapper to run async tests.
        """
        async def run_single_test(test_func):
            # Create fresh setup for each test
            self.setUp()
            try:
                await test_func()
            finally:
                self.tearDown()
        
        async def run_all_tests():
            await run_single_test(self.test_full_integration_workflow)
            await run_single_test(self.test_multiple_metrics_over_time)
            await run_single_test(self.test_data_cleanup)
        
        asyncio.run(run_all_tests())


def run_integration_tests():
    """
    Run all integration tests and return success status.
    """
    try:
        test_case = TestDataStorageIntegration()
        
        print("Running DataStorage integration tests...")
        test_case.test_sync_wrapper()
        
        print("✅ All integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration tests failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)