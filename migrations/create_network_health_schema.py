#!/usr/bin/env python3
"""
Database Migration: Create Network Health Schema

This script creates the network_health table for storing network health metrics
for miners including latency, packet loss, uptime, and jitter measurements.
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


async def create_network_health_table(db_path: str) -> bool:
    """
    Create network_health table for storing network health metrics.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if creation successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Create network_health table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS network_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    miner_id TEXT NOT NULL,
                    latency_ms REAL,
                    packet_loss_percent REAL,
                    uptime_seconds INTEGER,
                    jitter_ms REAL,
                    pool_url TEXT,
                    pool_port INTEGER,
                    pool_latency_ms REAL,
                    total_path_latency_ms REAL,
                    status TEXT,
                    measured_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (miner_id) REFERENCES miners (id) ON DELETE CASCADE
                )
            """)
            
            await conn.commit()
            logger.info("network_health table created successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error creating network_health table: {str(e)}")
        return False


async def create_network_health_indexes(db_path: str) -> bool:
    """
    Create indexes for efficient network health queries.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if index creation successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Primary index for miner + time queries (most common)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_network_health_miner_time 
                ON network_health (miner_id, measured_at DESC)
            """)
            
            # Index for status queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_network_health_status 
                ON network_health (status, measured_at DESC)
            """)
            
            # Index for timestamp only (for time-range queries)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_network_health_timestamp 
                ON network_health (measured_at DESC)
            """)
            
            # Index for pool queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_network_health_pool 
                ON network_health (pool_url, measured_at DESC)
            """)
            
            await conn.commit()
            logger.info("network_health indexes created successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error creating network_health indexes: {str(e)}")
        return False


async def verify_schema_creation(db_path: str) -> bool:
    """
    Verify that the network_health schema was created successfully.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if verification successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Check that network_health table exists
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='network_health'
            """)
            table = await cursor.fetchone()
            
            if not table:
                logger.error("network_health table was not created")
                return False
            
            # Check that indexes exist
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_network_health_%'
            """)
            indexes = await cursor.fetchall()
            
            if len(indexes) < 4:  # We created 4 indexes
                logger.error("Not all network_health indexes were created")
                return False
            
            # Verify table structure
            cursor = await conn.execute("PRAGMA table_info(network_health)")
            columns = await cursor.fetchall()
            expected_columns = {
                'id', 'miner_id', 'latency_ms', 'packet_loss_percent', 
                'uptime_seconds', 'jitter_ms', 'pool_url', 'pool_port',
                'pool_latency_ms', 'total_path_latency_ms', 'status', 
                'measured_at', 'created_at'
            }
            actual_columns = {col[1] for col in columns}
            
            if not expected_columns.issubset(actual_columns):
                logger.error("network_health table structure is incorrect")
                logger.error(f"Expected columns: {expected_columns}")
                logger.error(f"Actual columns: {actual_columns}")
                return False
            
            logger.info("Schema verification successful")
        
        return True
    except Exception as e:
        logger.error(f"Error verifying schema creation: {str(e)}")
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
    
    logger.info(f"Starting network_health schema creation for database: {db_path}")
    
    try:
        # Step 1: Create network_health table
        logger.info("Step 1: Creating network_health table...")
        if not await create_network_health_table(db_path):
            logger.error("Failed to create network_health table")
            return
        
        # Step 2: Create indexes for efficient queries
        logger.info("Step 2: Creating network_health indexes...")
        if not await create_network_health_indexes(db_path):
            logger.error("Failed to create network_health indexes")
            return
        
        # Step 3: Verify schema creation
        logger.info("Step 3: Verifying schema creation...")
        if not await verify_schema_creation(db_path):
            logger.error("Schema verification failed")
            return
        
        logger.info("network_health schema creation completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
