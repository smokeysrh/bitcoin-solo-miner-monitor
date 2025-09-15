"""
Tests for thread safety utilities.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.backend.utils.thread_safety import (
    AsyncRWLock,
    ThreadSafeMinerDataManager,
    ThreadSafeWebSocketManager,
    AtomicDatabaseOperations,
    ThreadSafeCache
)


class TestAsyncRWLock:
    """Test AsyncRWLock functionality."""
    
    @pytest.mark.asyncio
    async def test_read_lock_allows_multiple_readers(self):
        """Test that multiple readers can access simultaneously."""
        lock = AsyncRWLock()
        results = []
        
        async def reader(reader_id):
            async with lock.read_lock():
                results.append(f"reader_{reader_id}_start")
                await asyncio.sleep(0.1)
                results.append(f"reader_{reader_id}_end")
        
        # Start multiple readers
        tasks = [reader(i) for i in range(3)]
        await asyncio.gather(*tasks)
        
        # All readers should have started before any ended
        start_count = sum(1 for r in results if "start" in r)
        assert start_count == 3
    
    @pytest.mark.asyncio
    async def test_write_lock_excludes_readers(self):
        """Test that write lock excludes readers."""
        lock = AsyncRWLock()
        results = []
        
        async def writer():
            async with lock.write_lock():
                results.append("writer_start")
                await asyncio.sleep(0.1)
                results.append("writer_end")
        
        async def reader():
            async with lock.read_lock():
                results.append("reader_start")
                results.append("reader_end")
        
        # Start writer first, then reader
        writer_task = asyncio.create_task(writer())
        await asyncio.sleep(0.05)  # Let writer acquire lock
        reader_task = asyncio.create_task(reader())
        
        await asyncio.gather(writer_task, reader_task)
        
        # Writer should complete before reader starts
        assert results.index("writer_end") < results.index("reader_start")


class TestThreadSafeMinerDataManager:
    """Test ThreadSafeMinerDataManager functionality."""
    
    @pytest.mark.asyncio
    async def test_set_and_get_miner(self):
        """Test setting and getting miner data."""
        manager = ThreadSafeMinerDataManager()
        
        miner_data = {
            "id": "test_miner",
            "name": "Test Miner",
            "status": "online"
        }
        
        # Set miner data
        success = await manager.set_miner("test_miner", miner_data)
        assert success is True
        
        # Get miner data
        retrieved_data = await manager.get_miner("test_miner")
        assert retrieved_data == miner_data
    
    @pytest.mark.asyncio
    async def test_update_miner(self):
        """Test updating miner data."""
        manager = ThreadSafeMinerDataManager()
        
        # Set initial data
        initial_data = {"id": "test_miner", "status": "offline"}
        await manager.set_miner("test_miner", initial_data)
        
        # Update data
        updates = {"status": "online", "hashrate": 100}
        success = await manager.update_miner("test_miner", updates)
        assert success is True
        
        # Verify updates
        updated_data = await manager.get_miner("test_miner")
        assert updated_data["status"] == "online"
        assert updated_data["hashrate"] == 100
        assert updated_data["id"] == "test_miner"  # Original data preserved
    
    @pytest.mark.asyncio
    async def test_remove_miner(self):
        """Test removing miner data."""
        manager = ThreadSafeMinerDataManager()
        
        # Set miner data
        await manager.set_miner("test_miner", {"id": "test_miner"})
        
        # Verify exists
        assert await manager.exists("test_miner") is True
        
        # Remove miner
        success = await manager.remove_miner("test_miner")
        assert success is True
        
        # Verify removed
        assert await manager.exists("test_miner") is False
        assert await manager.get_miner("test_miner") is None
    
    @pytest.mark.asyncio
    async def test_get_all_miners(self):
        """Test getting all miners."""
        manager = ThreadSafeMinerDataManager()
        
        # Set multiple miners
        await manager.set_miner("miner1", {"id": "miner1", "name": "Miner 1"})
        await manager.set_miner("miner2", {"id": "miner2", "name": "Miner 2"})
        
        # Get all miners
        all_miners = await manager.get_all_miners()
        assert len(all_miners) == 2
        
        # Verify data
        miner_ids = [miner["id"] for miner in all_miners]
        assert "miner1" in miner_ids
        assert "miner2" in miner_ids
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent access to miner data."""
        manager = ThreadSafeMinerDataManager()
        
        async def writer(miner_id, value):
            await manager.set_miner(miner_id, {"id": miner_id, "value": value})
        
        async def reader(miner_id):
            return await manager.get_miner(miner_id)
        
        # Start concurrent operations
        tasks = []
        for i in range(10):
            tasks.append(writer(f"miner_{i}", i))
        
        await asyncio.gather(*tasks)
        
        # Verify all miners were set
        all_miners = await manager.get_all_miners()
        assert len(all_miners) == 10


class TestThreadSafeWebSocketManager:
    """Test ThreadSafeWebSocketManager functionality."""
    
    @pytest.mark.asyncio
    async def test_add_and_remove_connection(self):
        """Test adding and removing WebSocket connections."""
        manager = ThreadSafeWebSocketManager()
        
        # Mock WebSocket
        websocket = MagicMock()
        
        # Add connection
        success = await manager.add_connection(websocket, ["miners"])
        assert success is True
        
        # Verify connection count
        count = await manager.get_connection_count("miners")
        assert count == 1
        
        # Remove connection
        success = await manager.remove_connection(websocket)
        assert success is True
        
        # Verify connection removed
        count = await manager.get_connection_count("miners")
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing from topics."""
        manager = ThreadSafeWebSocketManager()
        
        # Mock WebSocket
        websocket = MagicMock()
        
        # Add connection
        await manager.add_connection(websocket)
        
        # Subscribe to topics
        success = await manager.subscribe_to_topics(websocket, ["miners", "alerts"])
        assert success is True
        
        # Verify subscriptions
        miners_count = await manager.get_connection_count("miners")
        alerts_count = await manager.get_connection_count("alerts")
        assert miners_count == 1
        assert alerts_count == 1
        
        # Unsubscribe from one topic
        success = await manager.unsubscribe_from_topics(websocket, ["alerts"])
        assert success is True
        
        # Verify unsubscription
        miners_count = await manager.get_connection_count("miners")
        alerts_count = await manager.get_connection_count("alerts")
        assert miners_count == 1
        assert alerts_count == 0
    
    @pytest.mark.asyncio
    async def test_get_connections(self):
        """Test getting connections for a topic."""
        manager = ThreadSafeWebSocketManager()
        
        # Mock WebSockets
        ws1 = MagicMock()
        ws2 = MagicMock()
        
        # Add connections
        await manager.add_connection(ws1, ["miners"])
        await manager.add_connection(ws2, ["miners"])
        
        # Get connections
        connections = await manager.get_connections("miners")
        assert len(connections) == 2
        assert ws1 in connections
        assert ws2 in connections


class TestAtomicDatabaseOperations:
    """Test AtomicDatabaseOperations functionality."""
    
    @pytest.mark.asyncio
    async def test_atomic_insert(self):
        """Test atomic insert operation."""
        # Mock connection
        mock_conn = AsyncMock()
        atomic_db = AtomicDatabaseOperations(mock_conn)
        
        # Test successful insert
        query = "INSERT INTO test (id, name) VALUES (?, ?)"
        params = ("1", "test")
        
        success = await atomic_db.atomic_insert(query, params)
        assert success is True
        
        # Verify transaction was used
        mock_conn.execute.assert_any_call("BEGIN IMMEDIATE")
        mock_conn.execute.assert_any_call(query, params)
        mock_conn.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_atomic_transaction_rollback(self):
        """Test transaction rollback on error."""
        # Mock connection that raises error
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = [None, Exception("Database error")]
        
        atomic_db = AtomicDatabaseOperations(mock_conn)
        
        query = "INSERT INTO test (id, name) VALUES (?, ?)"
        params = ("1", "test")
        
        success = await atomic_db.atomic_insert(query, params)
        assert success is False
        
        # Verify rollback was called
        mock_conn.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_atomic_batch_operations(self):
        """Test atomic batch operations."""
        mock_conn = AsyncMock()
        atomic_db = AtomicDatabaseOperations(mock_conn)
        
        operations = [
            ("INSERT INTO test (id, name) VALUES (?, ?)", ("1", "test1")),
            ("INSERT INTO test (id, name) VALUES (?, ?)", ("2", "test2")),
        ]
        
        success = await atomic_db.atomic_batch_operations(operations)
        assert success is True
        
        # Verify all operations were executed in transaction
        assert mock_conn.execute.call_count == 3  # BEGIN + 2 operations
        mock_conn.commit.assert_called_once()


class TestThreadSafeCache:
    """Test ThreadSafeCache functionality."""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting cache values."""
        cache = ThreadSafeCache(default_ttl=60)
        
        # Set value
        success = await cache.set("test_key", "test_value")
        assert success is True
        
        # Get value
        value = await cache.get("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = ThreadSafeCache(default_ttl=1)  # 1 second TTL
        
        # Set value
        await cache.set("test_key", "test_value")
        
        # Get value immediately
        value = await cache.get("test_key")
        assert value == "test_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Value should be expired
        value = await cache.get("test_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting cache values."""
        cache = ThreadSafeCache()
        
        # Set value
        await cache.set("test_key", "test_value")
        
        # Verify exists
        value = await cache.get("test_key")
        assert value == "test_value"
        
        # Delete value
        success = await cache.delete("test_key")
        assert success is True
        
        # Verify deleted
        value = await cache.get("test_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing all cache values."""
        cache = ThreadSafeCache()
        
        # Set multiple values
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Clear cache
        success = await cache.clear()
        assert success is True
        
        # Verify all values cleared
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = ThreadSafeCache(default_ttl=1)
        
        # Set values with different TTLs
        await cache.set("key1", "value1", ttl=1)  # Will expire
        await cache.set("key2", "value2", ttl=60)  # Won't expire
        
        # Wait for first key to expire
        await asyncio.sleep(1.1)
        
        # Cleanup expired entries
        removed_count = await cache.cleanup_expired()
        assert removed_count == 1
        
        # Verify only expired entry was removed
        assert await cache.get("key1") is None
        assert await cache.get("key2") == "value2"
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting cache statistics."""
        cache = ThreadSafeCache(default_ttl=1)
        
        # Set values
        await cache.set("key1", "value1", ttl=1)
        await cache.set("key2", "value2", ttl=60)
        
        # Wait for one to expire
        await asyncio.sleep(1.1)
        
        # Get stats
        stats = await cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["expired_entries"] == 1
        assert stats["active_entries"] == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent cache access."""
        cache = ThreadSafeCache()
        
        async def writer(key, value):
            await cache.set(key, value)
        
        async def reader(key):
            return await cache.get(key)
        
        # Start concurrent operations
        tasks = []
        for i in range(10):
            tasks.append(writer(f"key_{i}", f"value_{i}"))
        
        await asyncio.gather(*tasks)
        
        # Verify all values were set
        for i in range(10):
            value = await cache.get(f"key_{i}")
            assert value == f"value_{i}"


if __name__ == "__main__":
    pytest.main([__file__])