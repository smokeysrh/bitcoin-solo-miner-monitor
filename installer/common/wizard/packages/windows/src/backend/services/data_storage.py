"""
Data Storage Service

This module provides a service for storing and retrieving miner data.
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import aiosqlite

from config.app_config import DB_CONFIG
from src.backend.services.query_optimizer import QueryOptimizer
from src.backend.services.timeseries_storage import TimeSeriesStorage
from src.backend.utils.app_paths import get_app_paths
from src.backend.utils.retry_logic import retry_database_operation
from src.backend.utils.query_builder import SafeQueryBuilder, DatabaseQueryExecutor
from src.backend.utils.validators import DataSanitizer
from src.backend.utils.thread_safety import AtomicDatabaseOperations, ThreadSafeCache

logger = logging.getLogger(__name__)


class DataStorage:
    """
    Service for storing and retrieving miner data.
    """
    
    def __init__(self):
        """
        Initialize a new DataStorage instance.
        """
        # Use AppPaths to resolve database path
        app_paths = get_app_paths()
        self.sqlite_path = str(app_paths.resolve_path(DB_CONFIG["sqlite"]["path"]))
        
        self.sqlite_conn = None
        
        # Initialize query optimizer
        self.query_optimizer = None
        
        # Initialize time-series storage
        self.timeseries_storage = None
        
        # Initialize safe query executor
        self.query_executor = None
        
        # Initialize atomic database operations
        self.atomic_db = None
        
        # Initialize thread-safe cache
        self.cache = ThreadSafeCache(default_ttl=300)  # 5 minutes TTL
        
        self.is_initialized = False
    
    @retry_database_operation(max_attempts=3, base_delay=1.0, max_delay=10.0)
    async def initialize(self):
        """
        Initialize the data storage service.
        """
        if self.is_initialized:
            return
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        
        # Initialize SQLite database
        await self._init_sqlite()
        
        # Initialize query optimizer
        self.query_optimizer = QueryOptimizer(sqlite_path=self.sqlite_path)
        await self.query_optimizer.initialize()
        
        # Initialize time-series storage
        self.timeseries_storage = TimeSeriesStorage(self.sqlite_conn)
        
        # Initialize safe query executor
        self.query_executor = DatabaseQueryExecutor(self.sqlite_conn)
        
        # Initialize atomic database operations
        self.atomic_db = AtomicDatabaseOperations(self.sqlite_conn)
        
        self.is_initialized = True
        logger.info("Data storage service initialized")
    
    async def close(self):
        """
        Close the data storage service.
        """
        if not self.is_initialized:
            return
        
        # Close SQLite connection
        if self.sqlite_conn:
            await self.sqlite_conn.close()
            self.sqlite_conn = None
        
        # Close query optimizer
        if self.query_optimizer:
            await self.query_optimizer.close()
            self.query_optimizer = None
        
        self.is_initialized = False
        logger.info("Data storage service closed")
    
    @retry_database_operation(max_attempts=3, base_delay=0.5, max_delay=5.0)
    async def save_miner_config(self, miner_id: str, config: Dict[str, Any]) -> bool:
        """
        Save miner configuration to SQLite database with input validation.
        
        Args:
            miner_id (str): ID of the miner
            config (Dict[str, Any]): Miner configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Validate and sanitize inputs
            miner_id = DataSanitizer.sanitize_string(miner_id, max_length=100)
            config = DataSanitizer.sanitize_json_data(config)
            
            # Convert config to JSON
            config_json = json.dumps(config)
            
            # Use safe query builder to check if miner exists
            check_query, check_params = SafeQueryBuilder.build_select_query(
                table='miners',
                columns=['id'],
                where_conditions={'id': miner_id}
            )
            
            existing_miners = await self.query_executor.execute_safe_query(check_query, check_params)
            exists = len(existing_miners) > 0
            
            current_time = datetime.now().isoformat()
            
            if exists:
                # Update existing miner using atomic operation
                update_query, update_params = SafeQueryBuilder.build_update_query(
                    table='miners',
                    data={
                        'config': config_json,
                        'updated_at': current_time
                    },
                    where_conditions={'id': miner_id}
                )
                success = await self.atomic_db.atomic_update(update_query, update_params)
                if not success:
                    logger.error(f"Failed to update miner config for {miner_id}")
                    return False
            else:
                # Insert new miner using atomic operation
                insert_query, insert_params = SafeQueryBuilder.build_insert_query(
                    table='miners',
                    data={
                        'id': miner_id,
                        'config': config_json,
                        'created_at': current_time,
                        'updated_at': current_time
                    }
                )
                success = await self.atomic_db.atomic_insert(insert_query, insert_params)
                if not success:
                    logger.error(f"Failed to insert miner config for {miner_id}")
                    return False
            
            # Invalidate caches
            if self.query_optimizer:
                self.query_optimizer.invalidate_sqlite_cache(f"get_miner_config:{miner_id}")
                self.query_optimizer.invalidate_sqlite_cache("get_all_miner_configs")
            
            # Invalidate thread-safe cache
            await self.cache.delete(f"miner_config:{miner_id}")
            await self.cache.delete("all_miner_configs")
            
            logger.info(f"Successfully saved configuration for miner {miner_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving miner configuration for {miner_id}: {str(e)}")
            return False
    
    @retry_database_operation(max_attempts=3, base_delay=0.5, max_delay=5.0)
    async def get_miner_config(self, miner_id: str) -> Optional[Dict[str, Any]]:
        """
        Get miner configuration from SQLite database.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Optional[Dict[str, Any]]: Miner configuration or None if not found
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Check thread-safe cache first
            cache_key = f"miner_config:{miner_id}"
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Use query optimizer with caching
            query = "SELECT config FROM miners WHERE id = ?"
            params = (miner_id,)
            
            results = await self.query_optimizer.optimize_sqlite_query(query, params)
            
            if results and len(results) > 0:
                config = json.loads(results[0]["config"])
                # Cache the result
                await self.cache.set(cache_key, config)
                return config
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting miner configuration for {miner_id}: {str(e)}")
            return None
    
    async def get_all_miner_configs(self) -> List[Dict[str, Any]]:
        """
        Get all miner configurations from SQLite database.
        
        Returns:
            List[Dict[str, Any]]: List of miner configurations
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Use query optimizer with caching
            query = "SELECT id, config, created_at, updated_at FROM miners"
            
            results = await self.query_optimizer.optimize_sqlite_query(query)
            
            configs = []
            for row in results:
                config = json.loads(row["config"])
                config["id"] = row["id"]
                config["created_at"] = row["created_at"]
                config["updated_at"] = row["updated_at"]
                configs.append(config)
            
            return configs
        except Exception as e:
            logger.error(f"Error getting all miner configurations: {str(e)}")
            return []
    
    async def delete_miner_config(self, miner_id: str) -> bool:
        """
        Delete miner configuration from SQLite database.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            await self.sqlite_conn.execute(
                "DELETE FROM miners WHERE id = ?", (miner_id,)
            )
            await self.sqlite_conn.commit()
            
            # Invalidate cache
            if self.query_optimizer:
                self.query_optimizer.invalidate_sqlite_cache(f"get_miner_config:{miner_id}")
                self.query_optimizer.invalidate_sqlite_cache("get_all_miner_configs")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting miner configuration for {miner_id}: {str(e)}")
            return False
    
    async def save_app_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save application settings to SQLite database.
        
        Args:
            settings (Dict[str, Any]): Application settings
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Convert settings to JSON
            settings_json = json.dumps(settings)
            
            # Check if settings exist
            async with self.sqlite_conn.execute(
                "SELECT COUNT(*) FROM settings WHERE id = 'app_settings'"
            ) as cursor:
                count = await cursor.fetchone()
                exists = count[0] > 0
            
            if exists:
                # Update existing settings
                await self.sqlite_conn.execute(
                    "UPDATE settings SET value = ?, updated_at = ? WHERE id = 'app_settings'",
                    (settings_json, datetime.now().isoformat())
                )
            else:
                # Insert new settings
                await self.sqlite_conn.execute(
                    "INSERT INTO settings (id, value, created_at, updated_at) VALUES ('app_settings', ?, ?, ?)",
                    (settings_json, datetime.now().isoformat(), datetime.now().isoformat())
                )
            
            await self.sqlite_conn.commit()
            
            # Invalidate cache
            if self.query_optimizer:
                self.query_optimizer.invalidate_sqlite_cache("get_app_settings")
            
            return True
        except Exception as e:
            logger.error(f"Error saving application settings: {str(e)}")
            return False
    
    async def get_app_settings(self) -> Dict[str, Any]:
        """
        Get application settings from SQLite database.
        
        Returns:
            Dict[str, Any]: Application settings
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Use query optimizer with caching
            query = "SELECT value FROM settings WHERE id = 'app_settings'"
            
            results = await self.query_optimizer.optimize_sqlite_query(query)
            
            if results and len(results) > 0:
                return json.loads(results[0]["value"])
            else:
                # Return default settings
                return {
                    "polling_interval": 30,
                    "theme": "dark",
                    "chart_retention_days": 30,
                    "refresh_interval": 10
                }
        except Exception as e:
            logger.error(f"Error getting application settings: {str(e)}")
            return {
                "polling_interval": 30,
                "theme": "dark",
                "chart_retention_days": 30,
                "refresh_interval": 10
            }
    
    @retry_database_operation(max_attempts=3, base_delay=0.5, max_delay=5.0)
    async def save_metrics(self, miner_id: str, metrics: Dict[str, Any], timestamp: Optional[datetime] = None) -> bool:
        """
        Save miner metrics to SQLite time-series storage.
        
        Args:
            miner_id (str): ID of the miner
            metrics (Dict[str, Any]): Miner metrics
            timestamp (Optional[datetime]): Optional timestamp, defaults to current time
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.timeseries_storage:
            logger.error("Time-series storage not initialized")
            return False
        
        try:
            # Save metrics using time-series storage
            result = await self.timeseries_storage.save_metrics(miner_id, metrics, timestamp)
            
            # Invalidate cache
            if self.query_optimizer:
                self.query_optimizer.invalidate_sqlite_cache(f"latest_metrics:{miner_id}")
                self.query_optimizer.invalidate_sqlite_cache(f"aggregated_metrics:{miner_id}")
            
            return result
        except Exception as e:
            logger.error(f"Error saving metrics for miner {miner_id}: {str(e)}")
            return False
    
    async def get_metrics(self, miner_id: str, start_time: datetime, end_time: datetime, 
                         interval: str = "1h", metric_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get miner metrics from SQLite time-series storage.
        
        Args:
            miner_id (str): ID of the miner
            start_time (datetime): Start time
            end_time (datetime): End time
            interval (str): Aggregation interval ('1m', '5m', '1h', '1d')
            metric_types (Optional[List[str]]): Optional list of specific metric types
            
        Returns:
            List[Dict[str, Any]]: List of metrics
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.timeseries_storage:
            logger.error("Time-series storage not initialized")
            return []
        
        try:
            # Get aggregated metrics from time-series storage
            return await self.timeseries_storage.get_aggregated_metrics(
                miner_id=miner_id,
                start_time=start_time,
                end_time=end_time,
                interval=interval,
                metric_types=metric_types
            )
        except Exception as e:
            logger.error(f"Error getting metrics for miner {miner_id}: {str(e)}")
            return []
    
    async def get_latest_metrics(self, miner_id: str) -> Dict[str, Any]:
        """
        Get latest metrics for a miner from SQLite time-series storage.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Dict[str, Any]: Latest metrics
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.timeseries_storage:
            logger.error("Time-series storage not initialized")
            return {}
        
        try:
            # Get latest metrics from time-series storage
            return await self.timeseries_storage.get_latest_metrics(miner_id)
        except Exception as e:
            logger.error(f"Error getting latest metrics for miner {miner_id}: {str(e)}")
            return {}
    
    async def save_miner_status(self, miner_id: str, status_data: Dict[str, Any], timestamp: Optional[datetime] = None) -> bool:
        """
        Save miner status snapshot to SQLite time-series storage.
        
        Args:
            miner_id (str): ID of the miner
            status_data (Dict[str, Any]): Complete status data
            timestamp (Optional[datetime]): Optional timestamp, defaults to current time
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.timeseries_storage:
            logger.error("Time-series storage not initialized")
            return False
        
        try:
            # Save status using time-series storage
            return await self.timeseries_storage.save_status(miner_id, status_data, timestamp)
        except Exception as e:
            logger.error(f"Error saving status for miner {miner_id}: {str(e)}")
            return False
    
    async def get_latest_miner_status(self, miner_id: str) -> Dict[str, Any]:
        """
        Get latest status for a miner from SQLite time-series storage.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Dict[str, Any]: Latest status data
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.timeseries_storage:
            logger.error("Time-series storage not initialized")
            return {}
        
        try:
            # Get latest status from time-series storage
            return await self.timeseries_storage.get_latest_status(miner_id)
        except Exception as e:
            logger.error(f"Error getting latest status for miner {miner_id}: {str(e)}")
            return {}
    
    async def get_metrics_raw(self, miner_id: str, start_time: datetime, end_time: datetime, 
                             metric_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get raw (non-aggregated) metrics for a miner from SQLite time-series storage.
        
        Args:
            miner_id (str): ID of the miner
            start_time (datetime): Start time
            end_time (datetime): End time
            metric_types (Optional[List[str]]): Optional list of specific metric types
            
        Returns:
            List[Dict[str, Any]]: List of raw metric records
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.timeseries_storage:
            logger.error("Time-series storage not initialized")
            return []
        
        try:
            # Get raw metrics from time-series storage
            return await self.timeseries_storage.get_metrics(
                miner_id=miner_id,
                start_time=start_time,
                end_time=end_time,
                metric_types=metric_types
            )
        except Exception as e:
            logger.error(f"Error getting raw metrics for miner {miner_id}: {str(e)}")
            return []
    
    async def cleanup_old_metrics(self, retention_days: int = 30) -> bool:
        """
        Clean up old time-series data beyond retention period.
        
        Args:
            retention_days (int): Number of days to retain data
            
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.timeseries_storage:
            logger.error("Time-series storage not initialized")
            return False
        
        try:
            # Clean up old data using time-series storage
            return await self.timeseries_storage.cleanup_old_data(retention_days)
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {str(e)}")
            return False
    
    @retry_database_operation(max_attempts=5, base_delay=1.0, max_delay=10.0)
    async def _init_sqlite(self):
        """
        Initialize SQLite database.
        """
        try:
            # Connect to database
            self.sqlite_conn = await aiosqlite.connect(self.sqlite_path)
            
            # Create tables if they don't exist
            await self.sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS miners (
                    id TEXT PRIMARY KEY,
                    config TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            await self.sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create time-series tables
            await self.sqlite_conn.execute("""
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
            
            await self.sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS miner_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    miner_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status_data TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (miner_id) REFERENCES miners (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for time-series queries
            await self.sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_metrics_miner_time 
                ON miner_metrics (miner_id, timestamp DESC)
            """)
            
            await self.sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_metrics_type_time 
                ON miner_metrics (metric_type, timestamp DESC)
            """)
            
            await self.sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_metrics_miner_type_time 
                ON miner_metrics (miner_id, metric_type, timestamp DESC)
            """)
            
            await self.sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_metrics_timestamp 
                ON miner_metrics (timestamp DESC)
            """)
            
            await self.sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_status_miner_time 
                ON miner_status (miner_id, timestamp DESC)
            """)
            
            await self.sqlite_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_miner_status_timestamp 
                ON miner_status (timestamp DESC)
            """)
            
            await self.sqlite_conn.commit()
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {str(e)}")
            raise
    

    
