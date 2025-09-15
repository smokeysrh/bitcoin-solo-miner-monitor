"""
WebSocket Manager Tests

This module provides tests for the WebSocketManager implementation.
"""

import unittest
import asyncio
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from src.backend.services.websocket_manager import WebSocketManager


class TestWebSocketManager(unittest.TestCase):
    """
    Test class for WebSocketManager implementation.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create WebSocketManager instance
        self.websocket_manager = WebSocketManager()
        
        # Create mock WebSocket
        self.mock_websocket = MagicMock()
        self.mock_websocket.send_json = AsyncMock()
        
    def tearDown(self):
        """
        Clean up after tests.
        """
        self.loop.close()
    
    def test_initialization(self):
        """
        Test initialization of WebSocketManager.
        """
        # Verify connections are initialized correctly
        self.assertIn("all", self.websocket_manager._connections)
        self.assertIn("miners", self.websocket_manager._connections)
        self.assertIn("alerts", self.websocket_manager._connections)
        self.assertIn("system", self.websocket_manager._connections)
        
        # Verify broadcast intervals are set
        self.assertEqual(self.websocket_manager._broadcast_intervals["miners"], 1.0)
        self.assertEqual(self.websocket_manager._broadcast_intervals["alerts"], 5.0)
        self.assertEqual(self.websocket_manager._broadcast_intervals["system"], 10.0)
    
    def test_connect(self):
        """
        Test connecting a WebSocket client.
        """
        # Test connect method
        client_id = self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        
        # Verify results
        self.assertIsNotNone(client_id)
        self.assertIn(self.mock_websocket, self.websocket_manager._connections["all"])
        self.mock_websocket.accept.assert_called_once()
        self.mock_websocket.send_json.assert_called_once()
        
        # Verify welcome message
        call_args = self.mock_websocket.send_json.call_args[0][0]
        self.assertEqual(call_args["type"], "connection_established")
        self.assertEqual(call_args["client_id"], client_id)
        self.assertIn("timestamp", call_args)
        self.assertIn("available_topics", call_args)
    
    def test_disconnect(self):
        """
        Test disconnecting a WebSocket client.
        """
        # First connect a client
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        
        # Reset mock
        self.mock_websocket.reset_mock()
        
        # Test disconnect method
        self.websocket_manager.disconnect(self.mock_websocket)
        
        # Verify results
        self.assertNotIn(self.mock_websocket, self.websocket_manager._connections["all"])
        self.assertNotIn(self.mock_websocket, self.websocket_manager._connections["miners"])
        self.assertNotIn(self.mock_websocket, self.websocket_manager._connections["alerts"])
        self.assertNotIn(self.mock_websocket, self.websocket_manager._connections["system"])
    
    def test_subscribe(self):
        """
        Test subscribing to topics.
        """
        # First connect a client
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        
        # Reset mock
        self.mock_websocket.reset_mock()
        
        # Test subscribe method
        topics = ["miners", "alerts"]
        self.loop.run_until_complete(self.websocket_manager.subscribe(self.mock_websocket, topics))
        
        # Verify results
        self.assertIn(self.mock_websocket, self.websocket_manager._connections["miners"])
        self.assertIn(self.mock_websocket, self.websocket_manager._connections["alerts"])
        self.mock_websocket.send_json.assert_called_once()
        
        # Verify subscription confirmation message
        call_args = self.mock_websocket.send_json.call_args[0][0]
        self.assertEqual(call_args["type"], "subscription_update")
        self.assertIn("subscribed_topics", call_args)
        self.assertIn("timestamp", call_args)
    
    def test_unsubscribe(self):
        """
        Test unsubscribing from topics.
        """
        # First connect a client and subscribe to topics
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        self.loop.run_until_complete(self.websocket_manager.subscribe(self.mock_websocket, ["miners", "alerts"]))
        
        # Reset mock
        self.mock_websocket.reset_mock()
        
        # Test unsubscribe method
        topics = ["miners"]
        self.loop.run_until_complete(self.websocket_manager.unsubscribe(self.mock_websocket, topics))
        
        # Verify results
        self.assertNotIn(self.mock_websocket, self.websocket_manager._connections["miners"])
        self.assertIn(self.mock_websocket, self.websocket_manager._connections["alerts"])
        self.mock_websocket.send_json.assert_called_once()
        
        # Verify unsubscription confirmation message
        call_args = self.mock_websocket.send_json.call_args[0][0]
        self.assertEqual(call_args["type"], "subscription_update")
        self.assertIn("unsubscribed_topics", call_args)
        self.assertIn("timestamp", call_args)
    
    def test_broadcast(self):
        """
        Test broadcasting a message to subscribers.
        """
        # First connect a client and subscribe to topics
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        self.loop.run_until_complete(self.websocket_manager.subscribe(self.mock_websocket, ["miners"]))
        
        # Reset mock
        self.mock_websocket.reset_mock()
        
        # Test broadcast method
        message = {"data": "test_data"}
        self.loop.run_until_complete(self.websocket_manager.broadcast("miners", message))
        
        # Verify results
        self.mock_websocket.send_json.assert_called_once()
        
        # Verify broadcast message
        call_args = self.mock_websocket.send_json.call_args[0][0]
        self.assertEqual(call_args["data"], "test_data")
        self.assertIn("timestamp", call_args)
        self.assertEqual(call_args["type"], "miners_update")
    
    def test_broadcast_miners(self):
        """
        Test broadcasting miners data.
        """
        # First connect a client and subscribe to topics
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        self.loop.run_until_complete(self.websocket_manager.subscribe(self.mock_websocket, ["miners"]))
        
        # Reset mock
        self.mock_websocket.reset_mock()
        
        # Test broadcast_miners method
        miners_data = [
            {"id": "miner1", "name": "Miner 1", "status": "online"},
            {"id": "miner2", "name": "Miner 2", "status": "offline"}
        ]
        self.loop.run_until_complete(self.websocket_manager.broadcast_miners(miners_data))
        
        # Verify results
        self.mock_websocket.send_json.assert_called_once()
        
        # Verify broadcast message
        call_args = self.mock_websocket.send_json.call_args[0][0]
        self.assertEqual(call_args["type"], "miners_update")
        self.assertEqual(len(call_args["data"]), 2)
        self.assertEqual(call_args["data"][0]["id"], "miner1")
        self.assertEqual(call_args["data"][1]["id"], "miner2")
    
    def test_broadcast_alerts(self):
        """
        Test broadcasting alerts data.
        """
        # First connect a client and subscribe to topics
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        self.loop.run_until_complete(self.websocket_manager.subscribe(self.mock_websocket, ["alerts"]))
        
        # Reset mock
        self.mock_websocket.reset_mock()
        
        # Test broadcast_alerts method
        alerts_data = [
            {"id": "alert1", "severity": "high", "message": "High temperature"},
            {"id": "alert2", "severity": "medium", "message": "Low hashrate"}
        ]
        self.loop.run_until_complete(self.websocket_manager.broadcast_alerts(alerts_data))
        
        # Verify results
        self.mock_websocket.send_json.assert_called_once()
        
        # Verify broadcast message
        call_args = self.mock_websocket.send_json.call_args[0][0]
        self.assertEqual(call_args["type"], "alerts_update")
        self.assertEqual(len(call_args["data"]), 2)
        self.assertEqual(call_args["data"][0]["id"], "alert1")
        self.assertEqual(call_args["data"][1]["id"], "alert2")
    
    def test_broadcast_system(self):
        """
        Test broadcasting system data.
        """
        # First connect a client and subscribe to topics
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        self.loop.run_until_complete(self.websocket_manager.subscribe(self.mock_websocket, ["system"]))
        
        # Reset mock
        self.mock_websocket.reset_mock()
        
        # Test broadcast_system method
        system_data = {
            "cpu_usage": 25.5,
            "memory_usage": 512.0,
            "disk_usage": 75.0,
            "uptime": 86400
        }
        self.loop.run_until_complete(self.websocket_manager.broadcast_system(system_data))
        
        # Verify results
        self.mock_websocket.send_json.assert_called_once()
        
        # Verify broadcast message
        call_args = self.mock_websocket.send_json.call_args[0][0]
        self.assertEqual(call_args["type"], "system_update")
        self.assertEqual(call_args["data"]["cpu_usage"], 25.5)
        self.assertEqual(call_args["data"]["memory_usage"], 512.0)
        self.assertEqual(call_args["data"]["disk_usage"], 75.0)
        self.assertEqual(call_args["data"]["uptime"], 86400)
    
    def test_handle_message_subscribe(self):
        """
        Test handling a subscribe message.
        """
        # First connect a client
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        
        # Reset mock
        self.mock_websocket.reset_mock()
        
        # Test handle_message method with subscribe message
        message = {"type": "subscribe", "topics": ["miners", "alerts"]}
        self.loop.run_until_complete(self.websocket_manager.handle_message(self.mock_websocket, message))
        
        # Verify results
        self.assertIn(self.mock_websocket, self.websocket_manager._connections["miners"])
        self.assertIn(self.mock_websocket, self.websocket_manager._connections["alerts"])
        self.mock_websocket.send_json.assert_called_once()
    
    def test_handle_message_unsubscribe(self):
        """
        Test handling an unsubscribe message.
        """
        # First connect a client and subscribe to topics
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        self.loop.run_until_complete(self.websocket_manager.subscribe(self.mock_websocket, ["miners", "alerts"]))
        
        # Reset mock
        self.mock_websocket.reset_mock()
        
        # Test handle_message method with unsubscribe message
        message = {"type": "unsubscribe", "topics": ["miners"]}
        self.loop.run_until_complete(self.websocket_manager.handle_message(self.mock_websocket, message))
        
        # Verify results
        self.assertNotIn(self.mock_websocket, self.websocket_manager._connections["miners"])
        self.assertIn(self.mock_websocket, self.websocket_manager._connections["alerts"])
        self.mock_websocket.send_json.assert_called_once()
    
    def test_handle_message_custom_handler(self):
        """
        Test handling a message with a custom handler.
        """
        # First connect a client
        self.loop.run_until_complete(self.websocket_manager.connect(self.mock_websocket))
        
        # Register custom message handler
        custom_handler = AsyncMock()
        self.websocket_manager.register_message_handler("custom_type", custom_handler)
        
        # Test handle_message method with custom message
        message = {"type": "custom_type", "data": "test_data"}
        self.loop.run_until_complete(self.websocket_manager.handle_message(self.mock_websocket, message))
        
        # Verify results
        custom_handler.assert_called_once_with(self.mock_websocket, message)
    
    def test_set_broadcast_interval(self):
        """
        Test setting broadcast interval.
        """
        # Test set_broadcast_interval method
        self.websocket_manager.set_broadcast_interval("miners", 2.0)
        
        # Verify results
        self.assertEqual(self.websocket_manager._broadcast_intervals["miners"], 2.0)


if __name__ == '__main__':
    unittest.main()