"""
Thread Safety Utilities

This module provides thread-safe utilities for managing shared resources in the Bitcoin Solo Miner Monitoring App.
"""

import asyncio
import threading
import weakref
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, Set, List, TypeVar, Generic
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AsyncRWLock:
    """
    Async reader-writer lock implementation for protecting shared resources.
    Allows multiple readers or single writer access.
    """
    
    def __init__(self):
        self._readers = 0
        self._writers = 0
        self._read_ready = asyncio.Condition()
        self._write_ready = asyncio.Condition()
    
    @asynccontextmanager
    async def read_lock(self):
        """Acquire read lock (shared access)."""
        async with self._read_ready:
            while self._writers > 0:
                await self._read_ready.wait()
            self._readers += 1
        
        try:
            yield
        finally:
            async with self._read_ready:
                self._readers -= 1
                if self._readers == 0:
                    self._read_ready.notify_all()
    
    @asynccontextmanager
    async def write_lock(self):
        """Acquire write lock (exclusive access)."""
        async with self._write_ready:
            while self._writers > 0 or self._readers > 0:
                await self._write_ready.wait()
            self._writers += 1
        
        try:
            yield
        finally:
            async with self._write_ready:
                self._writers -= 1
                self._write_ready.notify_all()
                async with self._read_ready:
                    self._read_ready.notify_all()


class ThreadSafeMinerDataManager:
    """
    Thread-safe manager for miner data dictionary access.
    Provides atomic operations for miner data manipulation.
    """
    
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._lock = AsyncRWLock()
        self._last_updated: Dict[str, datetime] = {}
    
    @asynccontextmanager
    async def read_access(self):
        """Get read-only access to miner data."""
        async with self._lock.read_lock():
            yield self._data
    
    @asynccontextmanager
    async def write_access(self):
        """Get write access to miner data."""
        async with self._lock.write_lock():
            yield self._data
    
    async def get_miner(self, miner_id: str) -> Optional[Dict[str, Any]]:
        """
        Get miner data safely.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Optional[Dict[str, Any]]: Miner data or None if not found
        """
        async with self._lock.read_lock():
            return self._data.get(miner_id, {}).copy() if miner_id in self._data else None
    
    async def get_all_miners(self) -> List[Dict[str, Any]]:
        """
        Get all miner data safely.
        
        Returns:
            List[Dict[str, Any]]: List of all miner data
        """
        async with self._lock.read_lock():
            return [data.copy() for data in self._data.values()]
    
    async def set_miner(self, miner_id: str, data: Dict[str, Any]) -> bool:
        """
        Set miner data atomically.
        
        Args:
            miner_id (str): ID of the miner
            data (Dict[str, Any]): Miner data
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock.write_lock():
                self._data[miner_id] = data.copy()
                self._last_updated[miner_id] = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error setting miner data for {miner_id}: {e}")
            return False
    
    async def update_miner(self, miner_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update miner data atomically.
        
        Args:
            miner_id (str): ID of the miner
            updates (Dict[str, Any]): Updates to apply
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock.write_lock():
                if miner_id not in self._data:
                    self._data[miner_id] = {}
                
                self._data[miner_id].update(updates)
                self._last_updated[miner_id] = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error updating miner data for {miner_id}: {e}")
            return False
    
    async def remove_miner(self, miner_id: str) -> bool:
        """
        Remove miner data atomically.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock.write_lock():
                if miner_id in self._data:
                    del self._data[miner_id]
                if miner_id in self._last_updated:
                    del self._last_updated[miner_id]
            return True
        except Exception as e:
            logger.error(f"Error removing miner data for {miner_id}: {e}")
            return False
    
    async def exists(self, miner_id: str) -> bool:
        """
        Check if miner exists safely.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            bool: True if miner exists
        """
        async with self._lock.read_lock():
            return miner_id in self._data
    
    async def get_last_updated(self, miner_id: str) -> Optional[datetime]:
        """
        Get last updated timestamp for miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Optional[datetime]: Last updated timestamp or None
        """
        async with self._lock.read_lock():
            return self._last_updated.get(miner_id)


class ThreadSafeWebSocketManager:
    """
    Thread-safe manager for WebSocket connections.
    Provides atomic operations for connection management.
    """
    
    def __init__(self):
        self._connections: Dict[str, Set[Any]] = {
            "all": set(),
            "miners": set(),
            "alerts": set(),
            "system": set(),
        }
        self._lock = asyncio.Lock()
        self._client_topics: Dict[Any, Set[str]] = {}  # websocket -> topics
    
    async def add_connection(self, websocket: Any, topics: Optional[List[str]] = None) -> bool:
        """
        Add WebSocket connection atomically.
        
        Args:
            websocket: WebSocket connection
            topics (Optional[List[str]]): Topics to subscribe to
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                # Add to all connections
                self._connections["all"].add(websocket)
                
                # Initialize client topics
                self._client_topics[websocket] = set()
                
                # Subscribe to specified topics
                if topics:
                    for topic in topics:
                        if topic in self._connections:
                            self._connections[topic].add(websocket)
                            self._client_topics[websocket].add(topic)
            
            return True
        except Exception as e:
            logger.error(f"Error adding WebSocket connection: {e}")
            return False
    
    async def remove_connection(self, websocket: Any) -> bool:
        """
        Remove WebSocket connection atomically.
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                # Remove from all connection sets
                for connections in self._connections.values():
                    connections.discard(websocket)
                
                # Remove client topics tracking
                if websocket in self._client_topics:
                    del self._client_topics[websocket]
            
            return True
        except Exception as e:
            logger.error(f"Error removing WebSocket connection: {e}")
            return False
    
    async def subscribe_to_topics(self, websocket: Any, topics: List[str]) -> bool:
        """
        Subscribe WebSocket to topics atomically.
        
        Args:
            websocket: WebSocket connection
            topics (List[str]): Topics to subscribe to
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                if websocket not in self._client_topics:
                    self._client_topics[websocket] = set()
                
                for topic in topics:
                    if topic in self._connections:
                        self._connections[topic].add(websocket)
                        self._client_topics[websocket].add(topic)
            
            return True
        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")
            return False
    
    async def unsubscribe_from_topics(self, websocket: Any, topics: List[str]) -> bool:
        """
        Unsubscribe WebSocket from topics atomically.
        
        Args:
            websocket: WebSocket connection
            topics (List[str]): Topics to unsubscribe from
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                for topic in topics:
                    if topic in self._connections:
                        self._connections[topic].discard(websocket)
                    
                    if websocket in self._client_topics:
                        self._client_topics[websocket].discard(topic)
            
            return True
        except Exception as e:
            logger.error(f"Error unsubscribing from topics: {e}")
            return False
    
    async def get_connections(self, topic: str) -> List[Any]:
        """
        Get connections for a topic safely.
        
        Args:
            topic (str): Topic name
            
        Returns:
            List[Any]: List of WebSocket connections
        """
        async with self._lock:
            if topic in self._connections:
                return list(self._connections[topic])
            return []
    
    async def get_connection_count(self, topic: str) -> int:
        """
        Get connection count for a topic safely.
        
        Args:
            topic (str): Topic name
            
        Returns:
            int: Number of connections
        """
        async with self._lock:
            if topic in self._connections:
                return len(self._connections[topic])
            return 0
    
    async def get_client_topics(self, websocket: Any) -> Set[str]:
        """
        Get topics for a client safely.
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            Set[str]: Set of topics
        """
        async with self._lock:
            return self._client_topics.get(websocket, set()).copy()


class AtomicDatabaseOperations:
    """
    Provides atomic database operations with proper locking.
    """
    
    def __init__(self, connection):
        self.connection = connection
        self._lock = asyncio.Lock()
        self._transaction_lock = asyncio.Lock()
    
    @asynccontextmanager
    async def atomic_transaction(self):
        """
        Context manager for atomic database transactions.
        """
        async with self._transaction_lock:
            try:
                await self.connection.execute("BEGIN IMMEDIATE")
                yield self.connection
                await self.connection.commit()
            except Exception as e:
                await self.connection.rollback()
                logger.error(f"Database transaction failed, rolled back: {e}")
                raise
    
    async def atomic_insert(self, query: str, params: tuple) -> bool:
        """
        Perform atomic insert operation.
        
        Args:
            query (str): SQL query
            params (tuple): Query parameters
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                async with self.atomic_transaction() as conn:
                    await conn.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Atomic insert failed: {e}")
            return False
    
    async def atomic_update(self, query: str, params: tuple) -> bool:
        """
        Perform atomic update operation.
        
        Args:
            query (str): SQL query
            params (tuple): Query parameters
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                async with self.atomic_transaction() as conn:
                    await conn.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Atomic update failed: {e}")
            return False
    
    async def atomic_delete(self, query: str, params: tuple) -> bool:
        """
        Perform atomic delete operation.
        
        Args:
            query (str): SQL query
            params (tuple): Query parameters
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                async with self.atomic_transaction() as conn:
                    await conn.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Atomic delete failed: {e}")
            return False
    
    async def atomic_batch_operations(self, operations: List[tuple]) -> bool:
        """
        Perform multiple database operations atomically.
        
        Args:
            operations (List[tuple]): List of (query, params) tuples
            
        Returns:
            bool: True if all operations successful
        """
        try:
            async with self._lock:
                async with self.atomic_transaction() as conn:
                    for query, params in operations:
                        await conn.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Atomic batch operations failed: {e}")
            return False


class ThreadSafeCache(Generic[T]):
    """
    Thread-safe cache implementation with TTL support.
    """
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._lock = asyncio.Lock()
        self._default_ttl = default_ttl
    
    async def get(self, key: str) -> Optional[T]:
        """
        Get value from cache safely.
        
        Args:
            key (str): Cache key
            
        Returns:
            Optional[T]: Cached value or None if not found/expired
        """
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    return value
                else:
                    # Remove expired entry
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: T, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache safely.
        
        Args:
            key (str): Cache key
            value (T): Value to cache
            ttl (Optional[int]): Time to live in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            ttl = ttl or self._default_ttl
            expiry = datetime.now() + timedelta(seconds=ttl)
            
            async with self._lock:
                self._cache[key] = (value, expiry)
            return True
        except Exception as e:
            logger.error(f"Error setting cache value for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache safely.
        
        Args:
            key (str): Cache key
            
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                if key in self._cache:
                    del self._cache[key]
            return True
        except Exception as e:
            logger.error(f"Error deleting cache value for key {key}: {e}")
            return False
    
    async def clear(self) -> bool:
        """
        Clear all cache entries safely.
        
        Returns:
            bool: True if successful
        """
        try:
            async with self._lock:
                self._cache.clear()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    async def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            int: Number of entries removed
        """
        removed_count = 0
        current_time = datetime.now()
        
        async with self._lock:
            expired_keys = []
            for key, (value, expiry) in self._cache.items():
                if current_time >= expiry:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                removed_count += 1
        
        return removed_count
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics safely.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        async with self._lock:
            total_entries = len(self._cache)
            current_time = datetime.now()
            expired_entries = sum(1 for _, expiry in self._cache.values() if current_time >= expiry)
            
            return {
                "total_entries": total_entries,
                "expired_entries": expired_entries,
                "active_entries": total_entries - expired_entries
            }


# Global instances for shared use
miner_data_manager = ThreadSafeMinerDataManager()
websocket_manager = ThreadSafeWebSocketManager()