#!/usr/bin/env python3
"""
Database Migration: Remove User Tables

This script safely removes user-related tables from existing SQLite databases
as part of the authentication system removal.
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


async def backup_user_data(db_path: str) -> bool:
    """
    Create a backup of user data before removal.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if backup successful, False otherwise
    """
    try:
        backup_path = f"{db_path}.user_backup"
        
        # Connect to database
        async with aiosqlite.connect(db_path) as conn:
            # Check if users table exists
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            table_exists = await cursor.fetchone()
            
            if not table_exists:
                logger.info("Users table does not exist, no backup needed")
                return True
            
            # Export user data to backup file
            cursor = await conn.execute("SELECT * FROM users")
            users = await cursor.fetchall()
            
            if users:
                # Get column names
                cursor = await conn.execute("PRAGMA table_info(users)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                # Write backup file
                with open(backup_path, 'w') as f:
                    f.write("# User data backup created during authentication removal\n")
                    f.write(f"# Columns: {', '.join(column_names)}\n")
                    for user in users:
                        f.write(f"{user}\n")
                
                logger.info(f"User data backed up to {backup_path}")
            else:
                logger.info("No user data found to backup")
        
        return True
    except Exception as e:
        logger.error(f"Error backing up user data: {str(e)}")
        return False


async def remove_user_tables(db_path: str) -> bool:
    """
    Remove user-related tables and indexes from the database.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        bool: True if removal successful, False otherwise
    """
    try:
        async with aiosqlite.connect(db_path) as conn:
            # Drop user table indexes
            await conn.execute("DROP INDEX IF EXISTS idx_users_username")
            await conn.execute("DROP INDEX IF EXISTS idx_users_email")
            await conn.execute("DROP INDEX IF EXISTS idx_users_api_key")
            
            # Drop users table
            await conn.execute("DROP TABLE IF EXISTS users")
            
            await conn.commit()
            
            logger.info("User tables and indexes removed successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error removing user tables: {str(e)}")
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
            # Check that users table no longer exists
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            table_exists = await cursor.fetchone()
            
            if table_exists:
                logger.error("Users table still exists after migration")
                return False
            
            # Check that other tables still exist
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('miners', 'settings')"
            )
            tables = await cursor.fetchall()
            
            if len(tables) < 2:
                logger.error("Essential tables missing after migration")
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
    
    # Ensure database directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    logger.info(f"Starting user table removal migration for database: {db_path}")
    
    # Check if database exists
    if not os.path.exists(db_path):
        logger.info("Database does not exist, no migration needed")
        return
    
    try:
        # Step 1: Backup user data
        logger.info("Step 1: Backing up user data...")
        if not await backup_user_data(db_path):
            logger.error("Failed to backup user data, aborting migration")
            return
        
        # Step 2: Remove user tables
        logger.info("Step 2: Removing user tables...")
        if not await remove_user_tables(db_path):
            logger.error("Failed to remove user tables")
            return
        
        # Step 3: Verify migration
        logger.info("Step 3: Verifying migration...")
        if not await verify_migration(db_path):
            logger.error("Migration verification failed")
            return
        
        logger.info("User table removal migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())