"""
Query Optimizer Service

This module provides database query optimization for the Bitcoin Solo Miner Monitoring App.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
import asyncio
import functools
import aiosqlite
from contextlib import asynccontextmanager
import random

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class DatabaseTimeoutError(DatabaseError):
    """Exception raised when database operation times out."""
    pass


async def retry_with_exponential_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay on each retry
        jitter: Whether to add random jitter to delay
        
    Returns:
        Result of the function call
        
    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
                raise e
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            
            # Add jitter to prevent thundering herd
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)
            
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    raise last_exception


class DatabaseConnectionPool:
    """
    Connection pool for SQLite database connections with health monitoring.
    """
    
    def __init__(self, database_path: str, max_connections: int = 10, connection_timeout: float = 30.0):
        """
        Initialize the connection pool.
        
        Args:
            database_path (str): Path to SQLite database
            max_connections (int): Maximum number of connections in pool
            connection_timeout (float): Connection timeout in seconds
        """
        self.database_path = database_path
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self._pool = asyncio.Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = asyncio.Lock()
        self._health_check_task = None
        self._connection_stats = {
            'total_created': 0,
            'total_failed': 0,
            'active_connections': 0,
            'last_health_check': None
        }
    
    async def _create_connection(self) -> aiosqlite.Connection:
        """
        Create a new database connection with retry logic.
        
        Returns:
            aiosqlite.Connection: New database connection
            
        Raises:
            DatabaseConnectionError: If connection fails after retries
        """
        async def _connect():
            try:
                conn = await asyncio.wait_for(
                    aiosqlite.connect(self.database_path),
                    timeout=self.connection_timeout
                )
                conn.row_factory = aiosqlite.Row
                
                # Enable WAL mode for better concurrency
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.execute("PRAGMA cache_size=10000")
                await conn.execute("PRAGMA temp_store=memory")
                await conn.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
                await conn.commit()
                
                # Test the connection
                await self._test_connection(conn)
                
                self._connection_stats['total_created'] += 1
                logger.debug(f"Created new database connection to {self.database_path}")
                return conn
                
            except asyncio.TimeoutError:
                self._connection_stats['total_failed'] += 1
                raise DatabaseTimeoutError(f"Database connection timeout after {self.connection_timeout}s")
            except Exception as e:
                self._connection_stats['total_failed'] += 1
                raise DatabaseConnectionError(f"Failed to create database connection: {e}")
        
        return await retry_with_exponential_backoff(_connect, max_retries=3)
    
    async def _test_connection(self, conn: aiosqlite.Connection) -> bool:
        """
        Test if a database connection is healthy.
        
        Args:
            conn: Database connection to test
            
        Returns:
            bool: True if connection is healthy
            
        Raises:
            DatabaseError: If connection test fails
        """
        try:
            async with conn.execute("SELECT 1") as cursor:
                result = await cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            raise DatabaseError(f"Connection health check failed: {e}")
    
    async def _health_check_connections(self):
        """
        Periodically check the health of connections in the pool.
        """
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                healthy_connections = []
                unhealthy_count = 0
                
                # Check all connections in the pool
                while not self._pool.empty():
                    try:
                        conn = self._pool.get_nowait()
                        if await self._test_connection(conn):
                            healthy_connections.append(conn)
                        else:
                            await conn.close()
                            unhealthy_count += 1
                            async with self._lock:
                                self._created_connections -= 1
                    except asyncio.QueueEmpty:
                        break
                    except Exception as e:
                        logger.warning(f"Error during connection health check: {e}")
                        unhealthy_count += 1
                        async with self._lock:
                            self._created_connections -= 1
                
                # Return healthy connections to pool
                for conn in healthy_connections:
                    try:
                        self._pool.put_nowait(conn)
                    except asyncio.QueueFull:
                        await conn.close()
                        async with self._lock:
                            self._created_connections -= 1
                
                if unhealthy_count > 0:
                    logger.info(f"Removed {unhealthy_count} unhealthy connections from pool")
                
                self._connection_stats['last_health_check'] = datetime.now()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection health check: {e}")
    
    async def start_health_monitoring(self):
        """Start the health monitoring task."""
        if not self._health_check_task:
            self._health_check_task = asyncio.create_task(self._health_check_connections())
    
    async def stop_health_monitoring(self):
        """Stop the health monitoring task."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get a connection from the pool with retry logic.
        
        Yields:
            aiosqlite.Connection: Database connection
            
        Raises:
            DatabaseConnectionError: If unable to get a connection
        """
        conn = None
        connection_acquired = False
        
        try:
            # Try to get an existing connection from the pool
            try:
                conn = self._pool.get_nowait()
                connection_acquired = True
            except asyncio.QueueEmpty:
                # Create a new connection if pool is empty and we haven't reached the limit
                async with self._lock:
                    if self._created_connections < self.max_connections:
                        conn = await self._create_connection()
                        self._created_connections += 1
                        connection_acquired = True
                    else:
                        # Wait for a connection to become available with timeout
                        try:
                            conn = await asyncio.wait_for(self._pool.get(), timeout=30.0)
                            connection_acquired = True
                        except asyncio.TimeoutError:
                            raise DatabaseTimeoutError("Timeout waiting for database connection")
            
            # Test connection health before yielding
            if conn and not await self._test_connection_safe(conn):
                logger.warning("Connection failed health check, creating new one")
                await conn.close()
                async with self._lock:
                    self._created_connections -= 1
                conn = await self._create_connection()
                async with self._lock:
                    self._created_connections += 1
            
            self._connection_stats['active_connections'] += 1
            yield conn
            
        except Exception as e:
            logger.error(f"Error with database connection: {e}")
            # If there was an error, close the connection and don't return it to pool
            if conn and connection_acquired:
                try:
                    await conn.close()
                except:
                    pass
                async with self._lock:
                    self._created_connections -= 1
            raise
        else:
            # Return connection to pool if it's still healthy
            if conn:
                try:
                    if await self._test_connection_safe(conn):
                        self._pool.put_nowait(conn)
                    else:
                        await conn.close()
                        async with self._lock:
                            self._created_connections -= 1
                except asyncio.QueueFull:
                    # Pool is full, close the connection
                    await conn.close()
                    async with self._lock:
                        self._created_connections -= 1
        finally:
            if connection_acquired:
                self._connection_stats['active_connections'] -= 1
    
    async def _test_connection_safe(self, conn: aiosqlite.Connection) -> bool:
        """
        Safely test a connection without raising exceptions.
        
        Args:
            conn: Database connection to test
            
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            return await self._test_connection(conn)
        except Exception:
            return False
    
    async def close_all(self):
        """
        Close all connections in the pool.
        """
        # Stop health monitoring
        await self.stop_health_monitoring()
        
        # Close all connections in the pool
        closed_count = 0
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                await conn.close()
                closed_count += 1
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
        
        async with self._lock:
            self._created_connections = 0
        
        logger.info(f"Closed {closed_count} database connections")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics.
        
        Returns:
            Dict with connection statistics
        """
        return {
            'total_created': self._connection_stats['total_created'],
            'total_failed': self._connection_stats['total_failed'],
            'active_connections': self._connection_stats['active_connections'],
            'pool_size': self._pool.qsize(),
            'max_connections': self.max_connections,
            'created_connections': self._created_connections,
            'last_health_check': self._connection_stats['last_health_check']
        }

class QueryCache:
    """
    Cache for database queries.
    """
    
    def __init__(self, max_size: int = 100, ttl: int = 60):
        """
        Initialize a new QueryCache instance.
        
        Args:
            max_size (int): Maximum number of cached results
            ttl (int): Time-to-live in seconds
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a cached result.
        
        Args:
            key (str): Cache key
            
        Returns:
            Optional[Any]: Cached result or None if not found or expired
        """
        if key not in self.cache:
            return None
        
        result, timestamp = self.cache[key]
        
        # Check if expired
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
        
        return result
    
    def set(self, key: str, value: Any):
        """
        Set a cached result.
        
        Args:
            key (str): Cache key
            value (Any): Result to cache
        """
        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
            del self.cache[oldest_key]
        
        self.cache[key] = (value, time.time())
    
    def invalidate(self, key_prefix: str = None):
        """
        Invalidate cache entries.
        
        Args:
            key_prefix (str, optional): Prefix of keys to invalidate. If None, invalidate all.
        """
        if key_prefix is None:
            self.cache.clear()
        else:
            keys_to_delete = [key for key in self.cache if key.startswith(key_prefix)]
            for key in keys_to_delete:
                del self.cache[key]
    
    def clear_expired(self):
        """
        Clear expired cache entries.
        """
        now = time.time()
        keys_to_delete = [key for key, (_, timestamp) in self.cache.items() if now - timestamp > self.ttl]
        for key in keys_to_delete:
            del self.cache[key]


class QueryOptimizer:
    """
    Database query optimizer.
    """
    
    def __init__(self, sqlite_path: str, max_connections: int = 10):
        """
        Initialize a new QueryOptimizer instance.
        
        Args:
            sqlite_path (str): Path to SQLite database
            max_connections (int): Maximum number of connections in pool
        """
        self.sqlite_path = sqlite_path
        
        # Initialize cache
        self.sqlite_cache = QueryCache(max_size=100, ttl=60)  # 1 minute TTL for SQLite queries
        
        # Initialize connection pool
        self.connection_pool = DatabaseConnectionPool(sqlite_path, max_connections)
        
        # Cache maintenance task
        self.cache_maintenance_task = None
    
    async def initialize(self):
        """
        Initialize the query optimizer.
        """
        # Start connection health monitoring
        await self.connection_pool.start_health_monitoring()
        
        # Create indexes for SQLite database
        await self._create_sqlite_indexes()
        
        # Start cache maintenance task
        self.cache_maintenance_task = asyncio.create_task(self._cache_maintenance())
        
        logger.info("Query optimizer initialized")
    
    async def close(self):
        """
        Close the query optimizer.
        """
        # Close connection pool
        if self.connection_pool:
            await self.connection_pool.close_all()
        
        # Cancel cache maintenance task
        if self.cache_maintenance_task:
            self.cache_maintenance_task.cancel()
            try:
                await self.cache_maintenance_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Query optimizer closed")
    
    async def _create_sqlite_indexes(self):
        """
        Create indexes for SQLite database.
        """
        try:
            async with self.connection_pool.get_connection() as conn:
                # Check if indexes already exist
                async with conn.execute("SELECT name FROM sqlite_master WHERE type='index'") as cursor:
                    existing_indexes = [row[0] async for row in cursor]
                
                # Create indexes if they don't exist (only for columns that exist)
                if "idx_miners_id" not in existing_indexes:
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_miners_id ON miners (id)")
                
                if "idx_settings_id" not in existing_indexes:
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_settings_id ON settings (id)")
                
                await conn.commit()
                logger.info("SQLite indexes created")
        except Exception as e:
            logger.error(f"Error creating SQLite indexes: {str(e)}")
    
    async def _cache_maintenance(self):
        """
        Periodically clear expired cache entries.
        """
        while True:
            try:
                # Clear expired cache entries
                self.sqlite_cache.clear_expired()
                
                # Wait for next maintenance
                await asyncio.sleep(60)  # Run every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache maintenance: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def cached_sqlite_query(self, ttl: int = None):
        """
        Decorator for caching SQLite queries.
        
        Args:
            ttl (int, optional): Time-to-live in seconds. If None, use default TTL.
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
                # Check cache
                cached_result = self.sqlite_cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute query
                result = await func(*args, **kwargs)
                
                # Cache result
                if ttl:
                    # Create a new cache with custom TTL for this query
                    temp_cache = QueryCache(max_size=1, ttl=ttl)
                    temp_cache.set(cache_key, result)
                    self.sqlite_cache.cache[cache_key] = temp_cache.cache[cache_key]
                else:
                    self.sqlite_cache.set(cache_key, result)
                
                return result
            return wrapper
        return decorator
    

    
    def invalidate_sqlite_cache(self, key_prefix: str = None):
        """
        Invalidate SQLite cache entries.
        
        Args:
            key_prefix (str, optional): Prefix of keys to invalidate. If None, invalidate all.
        """
        self.sqlite_cache.invalidate(key_prefix)
    

    

    
    async def optimize_sqlite_query(self, query: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """
        Optimize and execute a SQLite query with retry logic.
        
        Args:
            query (str): SQLite query
            params (Tuple, optional): Query parameters
            
        Returns:
            List[Dict[str, Any]]: Query results
        """
        # Generate cache key
        cache_key = f"sqlite:{query}:{str(params)}"
        
        # Check cache
        cached_result = self.sqlite_cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        async def _execute_query():
            # Execute query using connection pool
            async with self.connection_pool.get_connection() as conn:
                try:
                    if params:
                        async with conn.execute(query, params) as cursor:
                            rows = await cursor.fetchall()
                    else:
                        async with conn.execute(query) as cursor:
                            rows = await cursor.fetchall()
                    
                    # Convert result to list of dictionaries
                    return [dict(row) for row in rows]
                    
                except aiosqlite.OperationalError as e:
                    if "database is locked" in str(e).lower():
                        raise DatabaseConnectionError(f"Database locked: {e}")
                    elif "no such table" in str(e).lower():
                        logger.warning(f"Table not found in query: {query}")
                        return []
                    else:
                        raise DatabaseError(f"SQLite operational error: {e}")
                except Exception as e:
                    raise DatabaseError(f"Query execution error: {e}")
        
        try:
            # Execute with retry logic
            records = await retry_with_exponential_backoff(_execute_query, max_retries=3)
            
            # Cache result
            self.sqlite_cache.set(cache_key, records)
            
            return records
            
        except Exception as e:
            logger.error(f"Error executing SQLite query after retries: {str(e)}")
            return []
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get database connection statistics.
        
        Returns:
            Dict with connection and cache statistics
        """
        pool_stats = self.connection_pool.get_connection_stats()
        cache_stats = {
            'cache_size': len(self.sqlite_cache.cache),
            'cache_max_size': self.sqlite_cache.max_size,
            'cache_ttl': self.sqlite_cache.ttl
        }
        
        return {
            'connection_pool': pool_stats,
            'query_cache': cache_stats
        }
    
