"""
WebSocket Load Testing

This module provides load testing for WebSocket connections.
"""

import asyncio
import logging
import time
import random
import argparse
import websockets
import json
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    WebSocket client for load testing.
    """
    
    def __init__(self, url: str, client_id: str):
        """
        Initialize a new WebSocketClient instance.
        
        Args:
            url (str): WebSocket URL
            client_id (str): Client ID
        """
        self.url = url
        self.client_id = client_id
        self.websocket = None
        self.connected = False
        self.messages_received = 0
        self.last_message_time = None
        self.connection_time = None
        self.subscribed_topics = []
    
    async def connect(self) -> bool:
        """
        Connect to the WebSocket server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            start_time = time.time()
            self.websocket = await websockets.connect(self.url)
            self.connection_time = time.time() - start_time
            self.connected = True
            logger.debug(f"Client {self.client_id} connected in {self.connection_time:.3f}s")
            return True
        except Exception as e:
            logger.error(f"Client {self.client_id} connection error: {str(e)}")
            return False
    
    async def subscribe(self, topics: List[str]) -> bool:
        """
        Subscribe to topics.
        
        Args:
            topics (List[str]): Topics to subscribe to
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            message = {
                "type": "subscribe",
                "topics": topics
            }
            await self.websocket.send(json.dumps(message))
            self.subscribed_topics = topics
            logger.debug(f"Client {self.client_id} subscribed to {topics}")
            return True
        except Exception as e:
            logger.error(f"Client {self.client_id} subscription error: {str(e)}")
            return False
    
    async def receive_messages(self, duration: int) -> None:
        """
        Receive messages for a specified duration.
        
        Args:
            duration (int): Duration in seconds
        """
        if not self.connected:
            return
        
        end_time = time.time() + duration
        
        try:
            while time.time() < end_time:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    self.messages_received += 1
                    self.last_message_time = time.time()
                    logger.debug(f"Client {self.client_id} received message: {message[:100]}...")
                except asyncio.TimeoutError:
                    # No message received within timeout
                    pass
        except Exception as e:
            logger.error(f"Client {self.client_id} receive error: {str(e)}")
    
    async def disconnect(self) -> None:
        """
        Disconnect from the WebSocket server.
        """
        if self.websocket:
            try:
                await self.websocket.close()
                self.connected = False
                logger.debug(f"Client {self.client_id} disconnected")
            except Exception as e:
                logger.error(f"Client {self.client_id} disconnect error: {str(e)}")


class WebSocketLoadTest:
    """
    WebSocket load test manager.
    """
    
    def __init__(self, url: str, num_clients: int, duration: int, ramp_up: int = 0):
        """
        Initialize a new WebSocketLoadTest instance.
        
        Args:
            url (str): WebSocket URL
            num_clients (int): Number of clients to create
            duration (int): Test duration in seconds
            ramp_up (int, optional): Ramp-up period in seconds. Defaults to 0.
        """
        self.url = url
        self.num_clients = num_clients
        self.duration = duration
        self.ramp_up = ramp_up
        self.clients: List[WebSocketClient] = []
        self.results: Dict[str, Any] = {}
    
    async def run(self) -> Dict[str, Any]:
        """
        Run the load test.
        
        Returns:
            Dict[str, Any]: Test results
        """
        logger.info(f"Starting WebSocket load test with {self.num_clients} clients for {self.duration}s")
        
        # Create clients
        self.clients = [
            WebSocketClient(self.url, f"client_{i}")
            for i in range(self.num_clients)
        ]
        
        # Connect clients with ramp-up
        start_time = time.time()
        connection_tasks = []
        
        for i, client in enumerate(self.clients):
            # Calculate delay for ramp-up
            if self.ramp_up > 0:
                delay = (i / self.num_clients) * self.ramp_up
                await asyncio.sleep(delay)
            
            # Connect client
            connection_tasks.append(asyncio.create_task(client.connect()))
        
        # Wait for all connections
        await asyncio.gather(*connection_tasks)
        
        connection_time = time.time() - start_time
        logger.info(f"All clients connected in {connection_time:.3f}s")
        
        # Count successful connections
        connected_clients = [client for client in self.clients if client.connected]
        logger.info(f"{len(connected_clients)}/{self.num_clients} clients connected successfully")
        
        # Subscribe to topics
        subscription_tasks = []
        for client in connected_clients:
            # Randomly select topics to subscribe to
            topics = random.sample(["miners", "alerts", "system"], random.randint(1, 3))
            subscription_tasks.append(asyncio.create_task(client.subscribe(topics)))
        
        # Wait for all subscriptions
        await asyncio.gather(*subscription_tasks)
        logger.info(f"All clients subscribed to topics")
        
        # Receive messages
        receive_tasks = []
        for client in connected_clients:
            receive_tasks.append(asyncio.create_task(client.receive_messages(self.duration)))
        
        # Wait for test duration
        await asyncio.gather(*receive_tasks)
        logger.info(f"Test completed after {self.duration}s")
        
        # Disconnect clients
        disconnect_tasks = []
        for client in connected_clients:
            disconnect_tasks.append(asyncio.create_task(client.disconnect()))
        
        # Wait for all disconnections
        await asyncio.gather(*disconnect_tasks)
        logger.info(f"All clients disconnected")
        
        # Calculate results
        total_messages = sum(client.messages_received for client in self.clients)
        avg_messages_per_client = total_messages / len(connected_clients) if connected_clients else 0
        avg_connection_time = sum(client.connection_time for client in connected_clients if client.connection_time) / len(connected_clients) if connected_clients else 0
        
        self.results = {
            "test_start": start_time,
            "test_end": time.time(),
            "test_duration": self.duration,
            "num_clients": self.num_clients,
            "connected_clients": len(connected_clients),
            "connection_success_rate": len(connected_clients) / self.num_clients if self.num_clients > 0 else 0,
            "avg_connection_time": avg_connection_time,
            "total_messages": total_messages,
            "avg_messages_per_client": avg_messages_per_client,
            "messages_per_second": total_messages / self.duration if self.duration > 0 else 0
        }
        
        return self.results


async def main():
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(description="WebSocket Load Test")
    parser.add_argument("--url", type=str, default="ws://localhost:8000/ws", help="WebSocket URL")
    parser.add_argument("--clients", type=int, default=10, help="Number of clients")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--ramp-up", type=int, default=5, help="Ramp-up period in seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Run load test
    load_test = WebSocketLoadTest(args.url, args.clients, args.duration, args.ramp_up)
    results = await load_test.run()
    
    # Print results
    print("\n=== WebSocket Load Test Results ===")
    print(f"Test Duration: {results['test_duration']}s")
    print(f"Number of Clients: {results['num_clients']}")
    print(f"Connected Clients: {results['connected_clients']} ({results['connection_success_rate'] * 100:.1f}%)")
    print(f"Average Connection Time: {results['avg_connection_time'] * 1000:.2f}ms")
    print(f"Total Messages Received: {results['total_messages']}")
    print(f"Average Messages per Client: {results['avg_messages_per_client']:.2f}")
    print(f"Messages per Second: {results['messages_per_second']:.2f}")
    print("=====================================")


if __name__ == "__main__":
    asyncio.run(main())