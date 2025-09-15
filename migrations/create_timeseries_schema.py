#!/usr/bin/env python3
"""
Database Migration: Create Time-Series Schema

This script creates new SQLite tables for time-series data storage,
replacing the InfluxDB dependency with SQLite-only storage.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to allow importing from src
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite
from config.app_config import DB_CONFIG

logger = logging.getLogger(__name__)


async def create_timeseries_tables(db_path: str) -> bool:
    """
    Create new time-series tables for miner metrics and status.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if creation successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Create miner_metrics table for time-series metrics data
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
            
            # Create miner_status table for status snapshots with JSON storage
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
            
            await conn.commit()
            logger.info("Time-series tables created successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error creating time-series tables: {str(e)}")
        return False


async def create_timeseries_indexes(db_path: str) -> bool:
    """
    Create indexes for efficient time-series queries.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if index creation successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Indexes for miner_metrics table
            
            # Primary index for miner + time queries (most common)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_metrics_miner_time 
                ON miner_metrics (miner_id, timestamp DESC)
            """)
            
            # Index for metric type + time queries (for specific metric analysis)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_metrics_type_time 
                ON miner_metrics (metric_type, timestamp DESC)
            """)
            
            # Composite index for miner + metric type + time (for filtered queries)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_metrics_miner_type_time 
                ON miner_metrics (miner_id, metric_type, timestamp DESC)
            """)
            
            # Index for timestamp only (for time-range queries across all miners)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_metrics_timestamp 
                ON miner_metrics (timestamp DESC)
            """)
            
            # Indexes for miner_status table
            
            # Primary index for miner + time queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_status_miner_time 
                ON miner_status (miner_id, timestamp DESC)
            """)
            
            # Index for timestamp only (for time-range queries)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_status_timestamp 
                ON miner_status (timestamp DESC)
            """)
            
            await conn.commit()
            logger.info("Time-series indexes created successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error creating time-series indexes: {str(e)}")
        return False


async def verify_schema_creation(db_path: str) -> bool:
    """
    Verify that the new schema was created successfully.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if verification successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Check that new tables exist
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('miner_metrics', 'miner_status')
            """)
            tables = await cursor.fetchall()
            
            if len(tables) != 2:
                logger.error("Not all time-series tables were created")
                return False
            
            # Check that indexes exist
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_miner_%'
            """)
            indexes = await cursor.fetchall()
            
            if len(indexes) < 6:  # We created 6 indexes
                logger.error("Not all time-series indexes were created")
                return False
            
            # Verify table structure for miner_metrics
            cursor = await conn.execute("PRAGMA table_info(miner_metrics)")
            columns = await cursor.fetchall()
            expected_columns = {'id', 'miner_id', 'timestamp', 'metric_type', 'value', 'unit', 'created_at'}
            actual_columns = {col[1] for col in columns}
            
            if not expected_columns.issubset(actual_columns):
                logger.error("miner_metrics table structure is incorrect")
                return False
            
            # Verify table structure for miner_status
            cursor = await conn.execute("PRAGMA table_info(miner_status)")
            columns = await cursor.fetchall()
            expected_columns = {'id', 'miner_id', 'timestamp', 'status_data', 'created_at'}
            actual_columns = {col[1] for col in columns}
            
            if not expected_columns.issubset(actual_columns):
                logger.error("miner_status table structure is incorrect")
                return False
            
            logger.info("Schema verification successful")
        
        return True
    except Exception as e:
        logger.error(f"Error verifying schema creation: {str(e)}")
        return False


async def create_sample_data(db_path: str) -> bool:
    """
    Create sample data to test the new schema (optional).
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if sample data creation successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Check if we have any miners to create sample data for
            cursor = await conn.execute("SELECT id FROM miners LIMIT 1")
            miner = await cursor.fetchone()
            
            if not miner:
                logger.info("No miners found, skipping sample data creation")
                return True
            
            miner_id = miner[0]
            current_time = datetime.now().isoformat()
            
            # Insert sample metrics
            sample_metrics = [
                (miner_id, current_time, 'hashrate', 500.0, 'TH/s'),
                (miner_id, current_time, 'temperature', 65.5, '°C'),
                (miner_id, current_time, 'power', 3250.0, 'W'),
                (miner_id, current_time, 'shares_accepted', 150, 'count'),
                (miner_id, current_time, 'shares_rejected', 2, 'count'),
            ]
            
            await conn.executemany("""
                INSERT INTO miner_metrics (miner_id, timestamp, metric_type, value, unit, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [(m[0], m[1], m[2], m[3], m[4], current_time) for m in sample_metrics])
            
            # Insert sample status
            sample_status = {
                "status": "mining",
                "uptime": 86400,
                "pool_url": "stratum+tcp://solo.ckpool.org:3333",
                "worker": "bc1qexample",
                "difficulty": 1000000,
                "network_hashrate": "500000000000000000",
                "last_share": current_time
            }
            
            await conn.execute("""
                INSERT INTO miner_status (miner_id, timestamp, status_data, created_at)
                VALUES (?, ?, ?, ?)
            """, (miner_id, current_time, str(sample_status).replace("'", '"'), current_time))
            
            await conn.commit()
            logger.info("Sample data created successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error creating sample data: {str(e)}")
        return False


async def main():
    """
    Main migration function.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Get database path
    db_path = DB_CONFIG["sqlite"]["path"]
    
    # Ensure database directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    logger.info(f"Starting time-series schema creation for database: {db_path}")
    
    try:
        # Step 1: Create time-series tables
        logger.info("Step 1: Creating time-series tables...")
        if not await create_timeseries_tables(db_path):
            logger.error("Failed to create time-series tables")
            return
        
        # Step 2: Create indexes for efficient queries
        logger.info("Step 2: Creating time-series indexes...")
        if not await create_timeseries_indexes(db_path):
            logger.error("Failed to create time-series indexes")
            return
        
        # Step 3: Verify schema creation
        logger.info("Step 3: Verifying schema creation...")
        if not await verify_schema_creation(db_path):
            logger.error("Schema verification failed")
            return
        
        # Step 4: Create sample data (optional)
        logger.info("Step 4: Creating sample data...")
        if not await create_sample_data(db_path):
            logger.warning("Failed to create sample data, but continuing...")
        
        logger.info("Time-series schema creation completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())