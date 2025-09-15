"""
Integration tests for thread safety in services.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.services.miner_manager import MinerManager
from src.backend.services.websocket_manager import WebSocketManager
from src.backend.utils.thread_safety import miner_data_manager, websocket_manager


class TestMinerManagerThreadSafety:
    """Test thread safety in MinerManager."""
    
    @pytest.mark.asyncio
    async def test_concurrent_miner_operations(self):
        """Test concurrent miner operations are thread-safe."""
        manager = MinerManager()
        
        # Mock miner factory to avoid actual network calls
        with patch('src.backend.services.miner_manager.MinerFactory.create_miner') as mock_factory:
            mock_miner = AsyncMock()
            mock_miner.get_device_info.return_value = {"model": "Test Miner"}
            mock_miner.disconnect.return_value = None
            mock_factory.return_value = mock_miner
            
            # Start concurrent add operations
            tasks = []
            for i in range(5):
                tasks.append(manager.add_miner("test_type", f"10.0.0.{i+1}", 80, f"Miner {i+1}"))
            
            # Wait for all operations to complete
            results = await asyncio.gather(*tasks)
            
            # Verify all miners were added successfully
            successful_adds = [r for r in results if r is not None]
            assert len(successful_adds) == 5
            
            # Verify all miners are in the data manager
            all_miners = await manager.get_miners()
            assert len(all_miners) == 5
            
            # Test concurrent updates
            update_tasks = []
            for miner_id in successful_adds:
                update_tasks.append(manager.update_miner(miner_id, {"status": "updated"}))
            
            update_results = await asyncio.gather(*update_tasks)
            assert all(update_results)
            
            # Verify updates were applied
            for miner_id in successful_adds:
                miner_data = await manager.get_miner(miner_id)
                assert miner_data["status"] == "updated"
    
    @pytest.mark.asyncio
    async def test_concurrent_read_write_operations(self):
        """Test concurrent read and write operations."""
        manager = MinerManager()
        
        # Mock miner factory
        with patch('src.backend.services.miner_manager.MinerFactory.create_miner') as mock_factory:
            mock_miner = AsyncMock()
            mock_miner.get_device_info.return_value = {"model": "Test Miner"}
            mock_miner.disconnect.return_value = None
            mock_factory.return_value = mock_miner
            
            # Add a miner first
            miner_id = await manager.add_miner("test_type", "10.0.0.1", 80, "Test Miner")
            assert miner_id is not None
            
            # Start concurrent read and write operations
            async def reader():
                results = []
                for _ in range(10):
                    data = await manager.get_miner(miner_id)
                    if data:
                        results.append(data.get("counter", 0))
                    await asyncio.sleep(0.01)
                return results
            
            async def writer():
                for i in range(10):
                    await manager.update_miner(miner_id, {"counter": i})
                    await asyncio.sleep(0.01)
            
            # Run concurrent operations
            reader_task = asyncio.create_task(reader())
            writer_task = asyncio.create_task(writer())
            
            read_results, _ = await asyncio.gather(reader_task, writer_task)
            
            # Verify no data corruption occurred
            # All read values should be valid integers
            assert all(isinstance(val, int) for val in read_results if val is not None)
    
    @pytest.mark.asyncio
    async def test_miner_data_consistency(self):
        """Test that miner data remains consistent under concurrent access."""
        # Test concurrent operations on the same miner
        miner_id = "test_miner_consistency"
        
        # Remove any existing data for this miner
        await miner_data_manager.remove_miner(miner_id)
        
        async def updater(field, value):
            await miner_data_manager.update_miner(miner_id, {field: value})
        
        # Start concurrent updates to different fields
        tasks = [
            updater("field1", "value1"),
            updater("field2", "value2"),
            updater("field3", "value3"),
            updater("field4", "value4"),
            updater("field5", "value5"),
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all updates were applied
        final_data = await miner_data_manager.get_miner(miner_id)
        assert final_data is not None
        assert final_data["field1"] == "value1"
        assert final_data["field2"] == "value2"
        assert final_data["field3"] == "value3"
        assert final_data["field4"] == "value4"
        assert final_data["field5"] == "value5"


class TestWebSocketManagerThreadSafety:
    """Test thread safety in WebSocketManager."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_management(self):
        """Test concurrent WebSocket connection management."""
        ws_manager = WebSocketManager()
        
        # Mock WebSocket connections
        websockets = [MagicMock() for _ in range(10)]
        
        # Mock the accept method
        for ws in websockets:
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
        
        # Start concurrent connection operations
        connect_tasks = []
        for i, ws in enumerate(websockets):
            connect_tasks.append(ws_manager.connect(ws, f"client_{i}"))
        
        # Wait for all connections
        client_ids = await asyncio.gather(*connect_tasks)
        assert len(client_ids) == 10
        
        # Test concurrent subscription operations
        subscribe_tasks = []
        for ws in websockets[:5]:
            subscribe_tasks.append(ws_manager.subscribe(ws, ["miners", "alerts"]))
        
        await asyncio.gather(*subscribe_tasks)
        
        # Verify connection counts
        miners_count = await websocket_manager.get_connection_count("miners")
        alerts_count = await websocket_manager.get_connection_count("alerts")
        assert miners_count == 5
        assert alerts_count == 5
        
        # Test concurrent disconnection
        disconnect_tasks = []
        for ws in websockets:
            disconnect_tasks.append(ws_manager.disconnect(ws))
        
        await asyncio.gather(*disconnect_tasks)
        
        # Verify all connections removed
        final_miners_count = await websocket_manager.get_connection_count("miners")
        final_alerts_count = await websocket_manager.get_connection_count("alerts")
        assert final_miners_count == 0
        assert final_alerts_count == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_broadcast_operations(self):
        """Test concurrent broadcast operations."""
        ws_manager = WebSocketManager()
        
        # Mock WebSocket connections
        websockets = [MagicMock() for _ in range(5)]
        
        # Mock methods
        for ws in websockets:
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            ws.close = AsyncMock()
        
        # Connect and subscribe all websockets
        for i, ws in enumerate(websockets):
            await ws_manager.connect(ws, f"client_{i}")
            await ws_manager.subscribe(ws, ["miners"])
        
        # Start concurrent broadcast operations
        broadcast_tasks = []
        for i in range(10):
            message = {"data": f"message_{i}", "timestamp": f"time_{i}"}
            broadcast_tasks.append(ws_manager.broadcast("miners", message))
        
        # Wait for all broadcasts
        await asyncio.gather(*broadcast_tasks)
        
        # Verify all websockets received messages
        for ws in websockets:
            # Each websocket should have received 10 messages (plus connection message)
            assert ws.send_json.call_count >= 10
    
    @pytest.mark.asyncio
    async def test_websocket_topic_consistency(self):
        """Test WebSocket topic subscription consistency."""
        # Mock WebSocket
        websocket = MagicMock()
        
        # Test concurrent subscribe/unsubscribe operations
        async def subscriber():
            await websocket_manager.subscribe_to_topics(websocket, ["miners", "alerts"])
        
        async def unsubscriber():
            await websocket_manager.unsubscribe_from_topics(websocket, ["alerts"])
        
        # Add connection first
        await websocket_manager.add_connection(websocket)
        
        # Run concurrent operations
        tasks = [subscriber(), unsubscriber(), subscriber()]
        await asyncio.gather(*tasks)
        
        # Verify final state
        client_topics = await websocket_manager.get_client_topics(websocket)
        # Should have miners topic, alerts topic state depends on timing
        assert "miners" in client_topics


class TestDatabaseThreadSafety:
    """Test database operation thread safety."""
    
    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self):
        """Test concurrent database operations are atomic."""
        # Mock database connection
        mock_conn = AsyncMock()
        
        from src.backend.utils.thread_safety import AtomicDatabaseOperations
        atomic_db = AtomicDatabaseOperations(mock_conn)
        
        # Test concurrent insert operations
        insert_tasks = []
        for i in range(5):
            query = "INSERT INTO test (id, value) VALUES (?, ?)"
            params = (f"id_{i}", f"value_{i}")
            insert_tasks.append(atomic_db.atomic_insert(query, params))
        
        # Wait for all operations
        results = await asyncio.gather(*insert_tasks)
        
        # All operations should succeed
        assert all(results)
        
        # Verify each operation used a transaction
        begin_calls = [call for call in mock_conn.execute.call_args_list if call[0][0] == "BEGIN IMMEDIATE"]
        assert len(begin_calls) == 5
        
        # Verify all transactions were committed
        assert mock_conn.commit.call_count == 5
    
    @pytest.mark.asyncio
    async def test_cache_thread_safety(self):
        """Test cache operations are thread-safe."""
        from src.backend.utils.thread_safety import ThreadSafeCache
        cache = ThreadSafeCache(default_ttl=60)
        
        # Test concurrent cache operations
        async def cache_writer(key, value):
            await cache.set(key, value)
        
        async def cache_reader(key):
            return await cache.get(key)
        
        # Start concurrent operations
        write_tasks = []
        for i in range(10):
            write_tasks.append(cache_writer(f"key_{i}", f"value_{i}"))
        
        await asyncio.gather(*write_tasks)
        
        # Start concurrent reads
        read_tasks = []
        for i in range(10):
            read_tasks.append(cache_reader(f"key_{i}"))
        
        read_results = await asyncio.gather(*read_tasks)
        
        # Verify all values were read correctly
        for i, value in enumerate(read_results):
            assert value == f"value_{i}"
        
        # Test concurrent cache cleanup
        cleanup_tasks = [cache.cleanup_expired() for _ in range(3)]
        cleanup_results = await asyncio.gather(*cleanup_tasks)
        
        # All cleanup operations should succeed
        assert all(isinstance(result, int) for result in cleanup_results)


if __name__ == "__main__":
    pytest.main([__file__])