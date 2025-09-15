"""
Tests for WebSocket connection management.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.services.websocket_manager import WebSocketManager
from src.backend.models.validation_models import WebSocketMessage


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, client_id: str = None):
        self.client_id = client_id or f"test_client_{datetime.now().timestamp()}"
        self.client_state = MagicMock()
        self.client_state.name = "CONNECTED"
        self.accept = AsyncMock()
        self.send_json = AsyncMock()
        self.receive_json = AsyncMock()
        self.close = AsyncMock()
        self.closed = False
        
    async def mock_close(self, code=1000, reason="Normal closure"):
        self.closed = True
        self.client_state.name = "DISCONNECTED"


@pytest.fixture
def isolated_manager():
    """Create a fresh WebSocket manager for each test."""
    from src.backend.utils.thread_safety import ThreadSafeWebSocketManager
    
    # Create a new manager instance for isolation
    manager = WebSocketManager()
    manager._thread_safe_manager = ThreadSafeWebSocketManager()
    return manager


class TestWebSocketManager:
    """Test WebSocket manager functionality."""
    
    @pytest.mark.asyncio
    async def test_connection_establishment(self, isolated_manager):
        """Test WebSocket connection establishment."""
        websocket = MockWebSocket()
        
        # Test connection
        client_id = await isolated_manager.connect(websocket)
        
        # Verify connection was established
        assert client_id is not None
        assert websocket.accept.called
        assert websocket.send_json.called
        
        # Verify welcome message
        welcome_call = websocket.send_json.call_args[0][0]
        assert welcome_call["type"] == "connection_established"
        assert welcome_call["client_id"] == client_id
        assert "available_topics" in welcome_call
        assert "heartbeat_interval" in welcome_call
    
    @pytest.mark.asyncio
    async def test_connection_cleanup(self, isolated_manager):
        """Test proper connection cleanup on disconnect."""
        websocket = MockWebSocket()
        
        # Connect client
        client_id = await isolated_manager.connect(websocket)
        
        # Verify connection exists
        stats = await isolated_manager.get_connection_stats()
        assert stats["total_connections"] == 1
        
        # Disconnect client
        await isolated_manager.disconnect(websocket)
        
        # Verify cleanup
        stats = await isolated_manager.get_connection_stats()
        assert stats["total_connections"] == 0
    
    @pytest.mark.asyncio
    async def test_subscription_management(self, isolated_manager):
        """Test topic subscription and unsubscription."""
        websocket = MockWebSocket()
        
        # Connect client
        await isolated_manager.connect(websocket)
        
        # Test subscription
        await isolated_manager.subscribe(websocket, ["miners", "alerts"])
        
        # Verify subscription confirmation was sent
        assert websocket.send_json.call_count >= 2  # Welcome + subscription confirmation
        
        # Test unsubscription
        await isolated_manager.unsubscribe(websocket, ["alerts"])
        
        # Verify unsubscription confirmation was sent
        assert websocket.send_json.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_message_handling(self, isolated_manager):
        """Test WebSocket message handling."""
        websocket = MockWebSocket()
        
        # Connect client
        await isolated_manager.connect(websocket)
        
        # Test ping message
        ping_message = {"type": "ping"}
        await isolated_manager.handle_message(websocket, ping_message)
        
        # Should respond with pong
        pong_calls = [call for call in websocket.send_json.call_args_list 
                     if call[0][0].get("type") == "pong"]
        assert len(pong_calls) > 0
        
        # Test subscription message
        sub_message = {"type": "subscribe", "topics": ["miners"]}
        await isolated_manager.handle_message(websocket, sub_message)
        
        # Should send subscription confirmation
        sub_calls = [call for call in websocket.send_json.call_args_list 
                    if call[0][0].get("type") == "subscription_update"]
        assert len(sub_calls) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_message_handling(self, isolated_manager):
        """Test handling of invalid messages."""
        websocket = MockWebSocket()
        
        # Connect client
        await isolated_manager.connect(websocket)
        
        # Test invalid message type
        invalid_message = {"type": "invalid_type"}
        await isolated_manager.handle_message(websocket, invalid_message)
        
        # Should send error response
        error_calls = [call for call in websocket.send_json.call_args_list 
                      if call[0][0].get("type") == "error"]
        assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_broadcast_functionality(self, isolated_manager):
        """Test message broadcasting to subscribed clients."""
        
        # Connect multiple clients
        clients = []
        for i in range(3):
            websocket = MockWebSocket(f"client_{i}")
            await isolated_manager.connect(websocket)
            await isolated_manager.subscribe(websocket, ["miners"])
            clients.append(websocket)
        
        # Broadcast message
        test_message = {
            "type": "miners_update",
            "data": {"test": "data"}
        }
        await isolated_manager.broadcast("miners", test_message)
        
        # Verify all clients received the message
        for client in clients:
            broadcast_calls = [call for call in client.send_json.call_args_list 
                             if call[0][0].get("type") == "miners_update"]
            assert len(broadcast_calls) > 0
    
    @pytest.mark.asyncio
    async def test_failed_connection_cleanup(self, isolated_manager):
        """Test cleanup of failed connections during broadcast."""
        
        # Create a client that will fail on send
        failing_websocket = MockWebSocket()
        failing_websocket.send_json = AsyncMock(side_effect=Exception("Connection failed"))
        
        # Create a normal client
        normal_websocket = MockWebSocket()
        
        # Connect both clients
        await isolated_manager.connect(failing_websocket)
        await isolated_manager.connect(normal_websocket)
        await isolated_manager.subscribe(failing_websocket, ["miners"])
        await isolated_manager.subscribe(normal_websocket, ["miners"])
        
        # Broadcast message
        test_message = {"type": "test", "data": {}}
        await isolated_manager.broadcast("miners", test_message)
        
        # Verify failed connection was cleaned up
        stats = await isolated_manager.get_connection_stats()
        assert stats["total_connections"] == 1  # Only the normal client should remain
    
    @pytest.mark.asyncio
    async def test_connection_stats(self, isolated_manager):
        """Test connection statistics functionality."""
        
        # Connect clients with different subscriptions
        client1 = MockWebSocket("client1")
        client2 = MockWebSocket("client2")
        
        await isolated_manager.connect(client1)
        await isolated_manager.connect(client2)
        await isolated_manager.subscribe(client1, ["miners", "alerts"])
        await isolated_manager.subscribe(client2, ["miners"])
        
        # Get stats
        stats = await isolated_manager.get_connection_stats()
        
        # Verify stats
        assert stats["total_connections"] == 2
        assert stats["connections_by_topic"]["miners"] == 2
        assert stats["connections_by_topic"]["alerts"] == 1
        assert len(stats["connection_details"]) == 2
        
        # Verify connection details
        for detail in stats["connection_details"]:
            assert "client_id" in detail
            assert "connected_at" in detail
            assert "subscribed_topics" in detail
            assert "message_count" in detail
    
    @pytest.mark.asyncio
    async def test_heartbeat_functionality(self, isolated_manager):
        """Test heartbeat ping/pong functionality."""
        isolated_manager._heartbeat_interval = 0.1  # Short interval for testing
        
        websocket = MockWebSocket()
        await isolated_manager.connect(websocket)
        
        # Wait for heartbeat
        await asyncio.sleep(0.2)
        
        # Should have received ping
        ping_calls = [call for call in websocket.send_json.call_args_list 
                     if call[0][0].get("type") == "ping"]
        assert len(ping_calls) > 0
    
    @pytest.mark.asyncio
    async def test_stale_connection_cleanup(self, isolated_manager):
        """Test cleanup of stale connections."""
        isolated_manager._heartbeat_interval = 0.1  # Short interval for testing
        
        websocket = MockWebSocket()
        await isolated_manager.connect(websocket)
        
        # Manually set last_ping to old time to simulate stale connection
        async with isolated_manager._connection_lock:
            if websocket in isolated_manager._connection_states:
                isolated_manager._connection_states[websocket]["last_ping"] = datetime.now() - timedelta(seconds=1)
        
        # Wait for heartbeat cleanup
        await asyncio.sleep(0.3)
        
        # Connection should be cleaned up
        stats = await isolated_manager.get_connection_stats()
        assert stats["total_connections"] == 0
    
    @pytest.mark.asyncio
    async def test_manager_stop(self, isolated_manager):
        """Test proper manager shutdown."""
        
        # Connect clients
        clients = []
        for i in range(2):
            websocket = MockWebSocket(f"client_{i}")
            await isolated_manager.connect(websocket)
            clients.append(websocket)
        
        # Stop manager
        await isolated_manager.stop()
        
        # Verify all connections were closed
        for client in clients:
            assert client.close.called
        
        # Verify stats are cleared
        stats = await isolated_manager.get_connection_stats()
        assert stats["total_connections"] == 0


class TestWebSocketMessageValidation:
    """Test WebSocket message validation."""
    
    def test_valid_message_types(self):
        """Test validation of valid message types."""
        valid_types = ['subscribe', 'unsubscribe', 'ping', 'pong', 'data', 'heartbeat', 'status']
        
        for msg_type in valid_types:
            message = WebSocketMessage(type=msg_type)
            assert message.type == msg_type
    
    def test_invalid_message_type(self):
        """Test validation of invalid message types."""
        with pytest.raises(Exception):  # Should raise validation error
            WebSocketMessage(type="invalid_type")
    
    def test_valid_topics(self):
        """Test validation of valid topics."""
        valid_topics = ['miners', 'alerts', 'system', 'metrics']
        
        for topic in valid_topics:
            message = WebSocketMessage(type="subscribe", topic=topic)
            assert message.topic == topic
    
    def test_invalid_topic(self):
        """Test validation of invalid topics."""
        with pytest.raises(Exception):  # Should raise validation error
            WebSocketMessage(type="subscribe", topic="invalid_topic")
    
    def test_message_with_data(self):
        """Test message validation with data payload."""
        test_data = {"key": "value", "number": 123}
        message = WebSocketMessage(type="data", data=test_data)
        assert message.data == test_data


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, isolated_manager):
        """Test handling of concurrent WebSocket connections."""
        
        async def connect_client(client_id):
            websocket = MockWebSocket(client_id)
            await isolated_manager.connect(websocket)
            await isolated_manager.subscribe(websocket, ["miners"])
            return websocket
        
        # Connect multiple clients concurrently
        tasks = [connect_client(f"client_{i}") for i in range(10)]
        clients = await asyncio.gather(*tasks)
        
        # Verify all connections
        stats = await isolated_manager.get_connection_stats()
        assert stats["total_connections"] == 10
        assert stats["connections_by_topic"]["miners"] == 10
        
        # Test concurrent broadcast
        test_message = {"type": "test", "data": {"concurrent": True}}
        await isolated_manager.broadcast("miners", test_message)
        
        # Verify all clients received the message
        for client in clients:
            assert client.send_json.call_count >= 3  # Welcome + subscription + broadcast
    
    @pytest.mark.asyncio
    async def test_connection_recovery(self, isolated_manager):
        """Test connection recovery scenarios."""
        
        # Connect client
        websocket = MockWebSocket()
        client_id = await isolated_manager.connect(websocket)
        
        # Simulate connection failure during message handling
        websocket.send_json = AsyncMock(side_effect=Exception("Connection lost"))
        
        # Try to handle message (should trigger cleanup)
        await isolated_manager.handle_message(websocket, {"type": "ping"})
        
        # Connection should be cleaned up
        stats = await isolated_manager.get_connection_stats()
        assert stats["total_connections"] == 0
    
    @pytest.mark.asyncio
    async def test_enhanced_message_handling(self, isolated_manager):
        """Test enhanced message handling with new message types."""
        
        websocket = MockWebSocket()
        await isolated_manager.connect(websocket)
        
        # Test get_status message
        await isolated_manager.handle_message(websocket, {"type": "get_status"})
        
        # Should receive status response
        status_calls = [call for call in websocket.send_json.call_args_list 
                       if call[0][0].get("type") == "status_response"]
        assert len(status_calls) > 0
        
        # Test get_topics message
        await isolated_manager.handle_message(websocket, {"type": "get_topics"})
        
        # Should receive topics response
        topics_calls = [call for call in websocket.send_json.call_args_list 
                       if call[0][0].get("type") == "topics_response"]
        assert len(topics_calls) > 0
    
    @pytest.mark.asyncio
    async def test_enhanced_ping_pong(self, isolated_manager):
        """Test enhanced ping/pong with statistics."""
        
        websocket = MockWebSocket()
        await isolated_manager.connect(websocket)
        
        # Test ping with stats request
        await isolated_manager.handle_message(websocket, {
            "type": "ping", 
            "include_stats": True
        })
        
        # Should receive pong with stats
        pong_calls = [call for call in websocket.send_json.call_args_list 
                     if call[0][0].get("type") == "pong"]
        assert len(pong_calls) > 0
        
        # Check if stats are included
        pong_message = pong_calls[-1][0][0]
        assert "stats" in pong_message
        assert "message_count" in pong_message["stats"]
    
    @pytest.mark.asyncio
    async def test_broadcast_with_metadata(self, isolated_manager):
        """Test enhanced broadcast functionality with metadata."""
        
        websocket = MockWebSocket()
        await isolated_manager.connect(websocket)
        await isolated_manager.subscribe(websocket, ["miners"])
        
        # Broadcast message
        test_message = {"data": {"test": "data"}}
        await isolated_manager.broadcast("miners", test_message)
        
        # Verify message includes metadata
        broadcast_calls = [call for call in websocket.send_json.call_args_list 
                          if "broadcast_id" in call[0][0]]
        assert len(broadcast_calls) > 0
        
        broadcast_message = broadcast_calls[-1][0][0]
        assert "topic" in broadcast_message
        assert "broadcast_id" in broadcast_message
        assert "timestamp" in broadcast_message
    
    @pytest.mark.asyncio
    async def test_connection_state_tracking(self, isolated_manager):
        """Test enhanced connection state tracking."""
        
        websocket = MockWebSocket()
        client_id = await isolated_manager.connect(websocket)
        
        # Send some messages to update state
        await isolated_manager.handle_message(websocket, {"type": "ping"})
        await isolated_manager.handle_message(websocket, {"type": "get_status"})
        
        # Get connection stats
        stats = await isolated_manager.get_connection_stats()
        
        # Verify enhanced state tracking
        assert len(stats["connection_details"]) == 1
        client_detail = stats["connection_details"][0]
        
        assert client_detail["client_id"] == client_id
        assert "connected_at" in client_detail
        assert "last_ping" in client_detail
        assert client_detail["message_count"] >= 2  # At least ping and get_status
    
    @pytest.mark.asyncio
    async def test_subscription_persistence(self, isolated_manager):
        """Test that subscriptions persist across message handling."""
        
        websocket = MockWebSocket()
        await isolated_manager.connect(websocket)
        await isolated_manager.subscribe(websocket, ["miners", "alerts"])
        
        # Handle some messages
        await isolated_manager.handle_message(websocket, {"type": "ping"})
        await isolated_manager.handle_message(websocket, {"type": "ping"})
        
        # Subscriptions should still be active
        stats = await isolated_manager.get_connection_stats()
        client_detail = stats["connection_details"][0]
        assert "miners" in client_detail["subscribed_topics"]
        assert "alerts" in client_detail["subscribed_topics"]


if __name__ == "__main__":
    pytest.main([__file__])