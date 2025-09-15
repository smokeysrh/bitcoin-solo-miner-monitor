"""
Tests for TimeSeriesStorage class

This module contains unit tests for the time-series storage functionality.
"""

import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite

# Import the class we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backend.services.timeseries_storage import TimeSeriesStorage


class TestTimeSeriesStorage(unittest.TestCase):
    """
    Test cases for TimeSeriesStorage class.
    """
    
    def setUp(self):
        """
        Set up test database and storage instance.
        """
        # Create unique temp file for each test
        import uuid
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=f'_{uuid.uuid4().hex[:8]}.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Test data
        self.test_miner_id = "test_miner_001"
        self.test_timestamp = datetime.now()
        self.test_metrics = {
            "hashrate": 500.0,
            "temperature": 65.5,
            "power": 3250.0,
            "shares_accepted": 150,
            "shares_rejected": 2
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
    
    async def create_test_schema(self, conn: aiosqlite.Connection):
        """
        Create the test schema in the database.
        """
        # Create miners table (prerequisite)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS miners (
                id TEXT PRIMARY KEY,
                config TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create time-series tables
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS miner_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                miner_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (miner_id) REFERENCES miners (id) ON DELETE CASCADE
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS miner_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                miner_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status_data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (miner_id) REFERENCES miners (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_miner_metrics_miner_time 
            ON miner_metrics (miner_id, timestamp DESC)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_miner_status_miner_time 
            ON miner_status (miner_id, timestamp DESC)
        """)
        
        # Insert test miner (use INSERT OR IGNORE to avoid conflicts)
        await conn.execute("""
            INSERT OR IGNORE INTO miners (id, config, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (self.test_miner_id, '{"type": "test"}', 
              self.test_timestamp.isoformat(), self.test_timestamp.isoformat()))
        
        await conn.commit()
    
    async def test_save_metrics(self):
        """
        Test saving metrics to the database.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await self.create_test_schema(conn)
            storage = TimeSeriesStorage(conn)
            
            # Test saving metrics
            result = await storage.save_metrics(self.test_miner_id, self.test_metrics, self.test_timestamp)
            self.assertTrue(result)
            
            # Verify metrics were saved
            cursor = await conn.execute("""
                SELECT metric_type, value, unit FROM miner_metrics 
                WHERE miner_id = ? ORDER BY metric_type
            """, (self.test_miner_id,))
            
            rows = await cursor.fetchall()
            self.assertEqual(len(rows), len(self.test_metrics))
            
            # Check specific metrics
            metrics_dict = {row[0]: (row[1], row[2]) for row in rows}
            self.assertIn('hashrate', metrics_dict)
            self.assertEqual(metrics_dict['hashrate'][0], 500.0)
            self.assertEqual(metrics_dict['hashrate'][1], 'TH/s')
    
    async def test_save_status(self):
        """
        Test saving status to the database.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await self.create_test_schema(conn)
            storage = TimeSeriesStorage(conn)
            
            # Test saving status
            result = await storage.save_status(self.test_miner_id, self.test_status, self.test_timestamp)
            self.assertTrue(result)
            
            # Verify status was saved
            cursor = await conn.execute("""
                SELECT status_data FROM miner_status WHERE miner_id = ?
            """, (self.test_miner_id,))
            
            row = await cursor.fetchone()
            self.assertIsNotNone(row)
            
            saved_status = json.loads(row[0])
            self.assertEqual(saved_status['status'], 'mining')
            self.assertEqual(saved_status['uptime'], 86400)
    
    async def test_get_latest_metrics(self):
        """
        Test retrieving latest metrics.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await self.create_test_schema(conn)
            storage = TimeSeriesStorage(conn)
            
            # Save test metrics
            await storage.save_metrics(self.test_miner_id, self.test_metrics, self.test_timestamp)
            
            # Get latest metrics
            latest = await storage.get_latest_metrics(self.test_miner_id)
            
            self.assertIsInstance(latest, dict)
            self.assertIn('hashrate', latest)
            self.assertEqual(latest['hashrate']['value'], 500.0)
            self.assertEqual(latest['hashrate']['unit'], 'TH/s')
    
    async def test_get_metrics_time_range(self):
        """
        Test retrieving metrics within a time range.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await self.create_test_schema(conn)
            storage = TimeSeriesStorage(conn)
            
            # Save metrics at different times
            base_time = self.test_timestamp
            for i in range(3):
                timestamp = base_time + timedelta(minutes=i)
                metrics = {"hashrate": 500.0 + i * 10}
                await storage.save_metrics(self.test_miner_id, metrics, timestamp)
            
            # Get metrics in time range
            start_time = base_time
            end_time = base_time + timedelta(minutes=5)
            
            results = await storage.get_metrics(self.test_miner_id, start_time, end_time)
            
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0]['value'], 500.0)
            self.assertEqual(results[1]['value'], 510.0)
            self.assertEqual(results[2]['value'], 520.0)
    
    async def test_get_aggregated_metrics(self):
        """
        Test retrieving aggregated metrics.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await self.create_test_schema(conn)
            storage = TimeSeriesStorage(conn)
            
            # Save multiple metrics for aggregation
            base_time = self.test_timestamp
            values = [500.0, 510.0, 520.0, 530.0]
            
            for i, value in enumerate(values):
                timestamp = base_time + timedelta(minutes=i * 15)  # 15-minute intervals
                metrics = {"hashrate": value}
                await storage.save_metrics(self.test_miner_id, metrics, timestamp)
            
            # Get aggregated metrics (hourly)
            start_time = base_time
            end_time = base_time + timedelta(hours=2)
            
            results = await storage.get_aggregated_metrics(
                self.test_miner_id, start_time, end_time, interval="1h"
            )
            
            self.assertGreater(len(results), 0)
            
            # Check aggregation values
            result = results[0]
            self.assertEqual(result['metric_type'], 'hashrate')
            self.assertGreater(result['avg_value'], 0)
            self.assertGreater(result['sample_count'], 0)
    
    async def test_metric_unit_mapping(self):
        """
        Test that metric units are correctly assigned.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await self.create_test_schema(conn)
            storage = TimeSeriesStorage(conn)
            
            # Test various metrics with expected units
            test_metrics = {
                "hashrate": 500.0,      # Should get TH/s
                "temperature": 65.5,    # Should get °C
                "power": 3250.0,        # Should get W
                "voltage": 12.5,        # Should get V
                "fan_speed": 3000,      # Should get RPM
                "custom_metric": 100.0  # Should get None
            }
            
            await storage.save_metrics(self.test_miner_id, test_metrics, self.test_timestamp)
            
            # Check units were assigned correctly
            cursor = await conn.execute("""
                SELECT metric_type, unit FROM miner_metrics 
                WHERE miner_id = ? ORDER BY metric_type
            """, (self.test_miner_id,))
            
            rows = await cursor.fetchall()
            units_dict = {row[0]: row[1] for row in rows}
            
            self.assertEqual(units_dict['hashrate'], 'TH/s')
            self.assertEqual(units_dict['temperature'], '°C')
            self.assertEqual(units_dict['power'], 'W')
            self.assertEqual(units_dict['voltage'], 'V')
            self.assertEqual(units_dict['fan_speed'], 'RPM')
            self.assertIsNone(units_dict['custom_metric'])
    
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
            await run_single_test(self.test_save_metrics)
            await run_single_test(self.test_save_status)
            await run_single_test(self.test_get_latest_metrics)
            await run_single_test(self.test_get_metrics_time_range)
            await run_single_test(self.test_get_aggregated_metrics)
            await run_single_test(self.test_metric_unit_mapping)
        
        asyncio.run(run_all_tests())


def run_tests():
    """
    Run all tests and return success status.
    """
    try:
        test_case = TestTimeSeriesStorage()
        test_case.setUp()
        
        print("Running TimeSeriesStorage tests...")
        test_case.test_sync_wrapper()
        
        test_case.tearDown()
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Tests failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)