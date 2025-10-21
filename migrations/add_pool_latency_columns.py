#!/usr/bin/env python3
"""
Database Migration: Add Pool Latency Columns to Network Health

This script adds pool latency tracking columns to the existing network_health table:
- pool_url: URL of the mining pool or Bitcoin node
- pool_port: Port number of the pool connection
- pool_latency_ms: Network latency to the pool server
- total_path_latency_ms: Combined miner + pool latency

This migration is safe to run multiple times (idempotent).
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path to allow importing from src
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite
from config.app_config import DB_CONFIG

logger = logging.getLogger(__name__)


async def check_column_exists(conn: aiosqlite.Connection, table: str, column: str) -> bool:
    """
    Check if a column exists in a table.
    
    Args:
        conn: Database connection
        table: Table name
        column: Column name
        
    Returns:
        bool: True if column exists, False otherwise
    """
    try:
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        columns = await cursor.fetchall()
        column_names = {col[1] for col in columns}
        return column in column_names
    except Exception as e:
        logger.error(f"Error checking column existence: {str(e)}")
        return False


async def add_pool_latency_columns(db_path: str) -> bool:
    """
    Add pool latency columns to network_health table.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if migration successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Check if table exists
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='network_health'
            """)
            table = await cursor.fetchone()
            
            if not table:
                logger.warning("network_health table does not exist. Run create_network_health_schema.py first.")
                return False
            
            # Add pool_url column if it doesn't exist
            if not await check_column_exists(conn, 'network_health', 'pool_url'):
                logger.info("Adding pool_url column...")
                await conn.execute("""
                    ALTER TABLE network_health 
                    ADD COLUMN pool_url TEXT
                """)
                logger.info("pool_url column added successfully")
            else:
                logger.info("pool_url column already exists")
            
            # Add pool_port column if it doesn't exist
            if not await check_column_exists(conn, 'network_health', 'pool_port'):
                logger.info("Adding pool_port column...")
                await conn.execute("""
                    ALTER TABLE network_health 
                    ADD COLUMN pool_port INTEGER
                """)
                logger.info("pool_port column added successfully")
            else:
                logger.info("pool_port column already exists")
            
            # Add pool_latency_ms column if it doesn't exist
            if not await check_column_exists(conn, 'network_health', 'pool_latency_ms'):
                logger.info("Adding pool_latency_ms column...")
                await conn.execute("""
                    ALTER TABLE network_health 
                    ADD COLUMN pool_latency_ms REAL
                """)
                logger.info("pool_latency_ms column added successfully")
            else:
                logger.info("pool_latency_ms column already exists")
            
            # Add total_path_latency_ms column if it doesn't exist
            if not await check_column_exists(conn, 'network_health', 'total_path_latency_ms'):
                logger.info("Adding total_path_latency_ms column...")
                await conn.execute("""
                    ALTER TABLE network_health 
                    ADD COLUMN total_path_latency_ms REAL
                """)
                logger.info("total_path_latency_ms column added successfully")
            else:
                logger.info("total_path_latency_ms column already exists")
            
            await conn.commit()
            logger.info("Pool latency columns migration completed successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error adding pool latency columns: {str(e)}")
        return False


async def create_pool_index(db_path: str) -> bool:
    """
    Create index for pool queries if it doesn't exist.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if index creation successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Check if index already exists
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_network_health_pool'
            """)
            index = await cursor.fetchone()
            
            if not index:
                logger.info("Creating pool index...")
                await conn.execute("""
                    CREATE INDEX idx_network_health_pool 
                    ON network_health (pool_url, measured_at DESC)
                """)
                await conn.commit()
                logger.info("Pool index created successfully")
            else:
                logger.info("Pool index already exists")
        
        return True
    except Exception as e:
        logger.error(f"Error creating pool index: {str(e)}")
        return False


async def verify_migration(db_path: str) -> bool:
    """
    Verify that the migration was successful.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if verification successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Verify all new columns exist
            cursor = await conn.execute("PRAGMA table_info(network_health)")
            columns = await cursor.fetchall()
            column_names = {col[1] for col in columns}
            
            required_columns = {'pool_url', 'pool_port', 'pool_latency_ms', 'total_path_latency_ms'}
            
            if not required_columns.issubset(column_names):
                logger.error("Migration verification failed: Not all columns were added")
                logger.error(f"Required columns: {required_columns}")
                logger.error(f"Actual columns: {column_names}")
                return False
            
            # Verify pool index exists
            cursor = await conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_network_health_pool'
            """)
            index = await cursor.fetchone()
            
            if not index:
                logger.error("Migration verification failed: Pool index was not created")
                return False
            
            logger.info("Migration verification successful")
        
        return True
    except Exception as e:
        logger.error(f"Error verifying migration: {str(e)}")
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
    
    # Ensure database exists
    if not os.path.exists(db_path):
        logger.error(f"Database does not exist at {db_path}")
        logger.error("Please run the application first to create the database")
        sys.exit(1)
    
    logger.info(f"Starting pool latency columns migration for database: {db_path}")
    
    try:
        # Step 1: Add pool latency columns
        logger.info("Step 1: Adding pool latency columns...")
        if not await add_pool_latency_columns(db_path):
            logger.error("Failed to add pool latency columns")
            return
        
        # Step 2: Create pool index
        logger.info("Step 2: Creating pool index...")
        if not await create_pool_index(db_path):
            logger.error("Failed to create pool index")
            return
        
        # Step 3: Verify migration
        logger.info("Step 3: Verifying migration...")
        if not await verify_migration(db_path):
            logger.error("Migration verification failed")
            return
        
        logger.info("Pool latency columns migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
