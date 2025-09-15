"""
WebSocket Manager

This module provides a WebSocket manager for real-time updates in the Bitcoin Solo Miner Monitoring App.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Set, Optional, Callable
from fastapi import WebSocket, WebSocketDisconnect

from src.backend.utils.thread_safety import websocket_manager as thread_safe_ws_manager

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    WebSocket manager for handling real-time updates.
    """
    
    def __init__(self):
        """
        Initialize a new WebSocketManager instance.
        """
        # Use thread-safe WebSocket manager
        self._thread_safe_manager = thread_safe_ws_manager
        
        # Message handlers
        self._message_handlers: Dict[str, Callable] = {}
        
        # Broadcast tasks
        self._broadcast_tasks = []
        
        # Connection state tracking
        self._connection_states: Dict[Any, Dict[str, Any]] = {}
        self._connection_lock = asyncio.Lock()
        
        # Heartbeat configuration
        self._heartbeat_interval = 30.0  # seconds
        self._heartbeat_task = None
        
        # Broadcast intervals (in seconds)
        self._broadcast_intervals = {
            "miners": 1.0,
            "alerts": 5.0,
            "system": 10.0,
        }
    
    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """
        Connect a new WebSocket client with proper state management.
        No authentication required - open access for local network monitoring.
        
        Args:
            websocket (WebSocket): WebSocket connection
            client_id (str, optional): Client ID. If not provided, a new one will be generated.
            
        Returns:
            str: Client ID
        """
        try:
            # Accept connection without authentication
            await websocket.accept()
            
            # Generate client ID if not provided
            if not client_id:
                import uuid
                client_id = f"client_{uuid.uuid4().hex[:8]}"
            
            # Add to connections using thread-safe manager
            success = await self._thread_safe_manager.add_connection(websocket)
            
            if not success:
                logger.error(f"Failed to add client {client_id} to connection manager")
                await websocket.close(code=1011, reason="Connection management error")
                return client_id
            
            # Track connection state with enhanced information
            async with self._connection_lock:
                self._connection_states[websocket] = {
                    "client_id": client_id,
                    "connected_at": datetime.now(),
                    "last_ping": datetime.now(),
                    "last_activity": datetime.now(),
                    "subscribed_topics": set(),
                    "message_count": 0,
                    "connection_status": "active",
                    "user_agent": getattr(websocket, 'headers', {}).get('user-agent', 'unknown'),
                    "remote_addr": getattr(websocket, 'client', {}).host if hasattr(websocket, 'client') else 'unknown'
                }
            
            # Send welcome message with connection details
            await websocket.send_json({
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat(),
                "available_topics": ["miners", "alerts", "system", "metrics"],
                "heartbeat_interval": self._heartbeat_interval,
                "server_info": {
                    "version": "1.0.0",
                    "features": ["real_time_updates", "multi_topic_subscription", "heartbeat"]
                }
            })
            
            # Start heartbeat task if not already running
            if self._heartbeat_task is None or self._heartbeat_task.done():
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info(f"Client {client_id} connected successfully from {getattr(websocket, 'client', {}).host if hasattr(websocket, 'client') else 'unknown'}")
            
            return client_id
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket client: {e}")
            try:
                await websocket.close(code=1011, reason="Connection error")
            except Exception:
                pass
            return client_id or "unknown"
    
    async def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket client with comprehensive cleanup.
        Ensures proper resource cleanup for disconnected clients.
        
        Args:
            websocket (WebSocket): WebSocket connection
        """
        client_id = "unknown"
        connection_info = {}
        
        try:
            # Get client information for logging before cleanup
            async with self._connection_lock:
                if websocket in self._connection_states:
                    connection_info = self._connection_states[websocket].copy()
                    client_id = connection_info.get("client_id", "unknown")
                    
                    # Mark connection as disconnecting
                    self._connection_states[websocket]["connection_status"] = "disconnecting"
            
            # Remove from connections using thread-safe manager
            success = await self._thread_safe_manager.remove_connection(websocket)
            
            # Clean up connection state
            async with self._connection_lock:
                if websocket in self._connection_states:
                    del self._connection_states[websocket]
            
            if success:
                # Log connection statistics
                if connection_info:
                    connected_duration = (datetime.now() - connection_info.get("connected_at", datetime.now())).total_seconds()
                    logger.info(f"Client {client_id} disconnected successfully - Duration: {connected_duration:.1f}s, Messages: {connection_info.get('message_count', 0)}")
                else:
                    logger.info(f"Client {client_id} disconnected and cleaned up successfully")
            else:
                logger.warning(f"Client {client_id} disconnect cleanup had issues")
                
            # Attempt to close the WebSocket connection gracefully
            try:
                # Check if connection is still open before attempting to close
                if hasattr(websocket, 'client_state'):
                    if websocket.client_state.name not in ["DISCONNECTED", "CLOSED"]:
                        await websocket.close(code=1000, reason="Normal closure")
                elif hasattr(websocket, 'state'):
                    # Alternative state check for different WebSocket implementations
                    if websocket.state not in ["DISCONNECTED", "CLOSED"]:
                        await websocket.close(code=1000, reason="Normal closure")
                else:
                    # Fallback - attempt to close anyway
                    await websocket.close(code=1000, reason="Normal closure")
                    
            except Exception as e:
                logger.debug(f"WebSocket for client {client_id} already closed or error closing: {e}")
                
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect for client {client_id}: {e}")
            
            # Ensure cleanup even if there were errors
            try:
                async with self._connection_lock:
                    if websocket in self._connection_states:
                        del self._connection_states[websocket]
                await self._thread_safe_manager.remove_connection(websocket)
            except Exception as cleanup_error:
                logger.error(f"Error during emergency cleanup for client {client_id}: {cleanup_error}")
    
    async def subscribe(self, websocket: WebSocket, topics: List[str]):
        """
        Subscribe a client to specific topics with state tracking.
        
        Args:
            websocket (WebSocket): WebSocket connection
            topics (List[str]): Topics to subscribe to
        """
        client_id = "unknown"
        try:
            # Subscribe using thread-safe manager
            success = await self._thread_safe_manager.subscribe_to_topics(websocket, topics)
            
            if success:
                # Update connection state
                async with self._connection_lock:
                    if websocket in self._connection_states:
                        state = self._connection_states[websocket]
                        client_id = state.get("client_id", "unknown")
                        state["subscribed_topics"].update(topics)
                
                # Send confirmation
                await websocket.send_json({
                    "type": "subscription_update",
                    "subscribed_topics": topics,
                    "timestamp": datetime.now().isoformat(),
                })
                
                logger.debug(f"Client {client_id} subscribed to topics: {topics}")
            else:
                logger.error(f"Failed to subscribe client {client_id} to topics: {topics}")
                
        except Exception as e:
            logger.error(f"Error subscribing client {client_id} to topics {topics}: {e}")
    
    async def unsubscribe(self, websocket: WebSocket, topics: List[str]):
        """
        Unsubscribe a client from specific topics with state tracking.
        
        Args:
            websocket (WebSocket): WebSocket connection
            topics (List[str]): Topics to unsubscribe from
        """
        client_id = "unknown"
        try:
            # Unsubscribe using thread-safe manager
            success = await self._thread_safe_manager.unsubscribe_from_topics(websocket, topics)
            
            if success:
                # Update connection state
                async with self._connection_lock:
                    if websocket in self._connection_states:
                        state = self._connection_states[websocket]
                        client_id = state.get("client_id", "unknown")
                        state["subscribed_topics"].difference_update(topics)
                
                # Send confirmation
                await websocket.send_json({
                    "type": "subscription_update",
                    "unsubscribed_topics": topics,
                    "timestamp": datetime.now().isoformat(),
                })
                
                logger.debug(f"Client {client_id} unsubscribed from topics: {topics}")
            else:
                logger.error(f"Failed to unsubscribe client {client_id} from topics: {topics}")
                
        except Exception as e:
            logger.error(f"Error unsubscribing client {client_id} from topics {topics}: {e}")
    
    async def broadcast(self, topic: str, message: Dict[str, Any]):
        """
        Thread-safe broadcast of messages to all clients subscribed to a topic.
        Includes comprehensive error handling and automatic cleanup of failed connections.
        
        Args:
            topic (str): Topic to broadcast to
            message (Dict[str, Any]): Message to broadcast
        """
        # Validate topic
        valid_topics = ["miners", "alerts", "system", "metrics", "all"]
        if topic not in valid_topics:
            logger.warning(f"Invalid broadcast topic: {topic}")
            return
        
        # Prepare message with metadata
        broadcast_message = message.copy()
        if "timestamp" not in broadcast_message:
            broadcast_message["timestamp"] = datetime.now().isoformat()
        
        if "type" not in broadcast_message:
            broadcast_message["type"] = f"{topic}_update"
        
        # Add broadcast metadata
        broadcast_message["topic"] = topic
        broadcast_message["broadcast_id"] = f"{topic}_{datetime.now().timestamp()}"
        
        # Get connections using thread-safe manager
        connections = await self._thread_safe_manager.get_connections(topic)
        
        if not connections:
            logger.debug(f"No clients subscribed to topic: {topic}")
            return
        
        logger.debug(f"Broadcasting {broadcast_message['type']} to {len(connections)} clients on topic '{topic}'")
        
        # Track broadcast statistics
        successful_sends = 0
        failed_connections = []
        
        # Broadcast to all clients subscribed to the topic
        for websocket in connections:
            client_id = "unknown"
            try:
                # Get client ID for logging
                async with self._connection_lock:
                    if websocket in self._connection_states:
                        client_id = self._connection_states[websocket].get("client_id", "unknown")
                        # Update last activity
                        self._connection_states[websocket]["last_activity"] = datetime.now()
                
                # Send message with timeout to prevent hanging
                from config.app_config import CONNECTION_TIMEOUT
                await asyncio.wait_for(websocket.send_json(broadcast_message), timeout=CONNECTION_TIMEOUT)
                successful_sends += 1
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout sending message to client {client_id} on topic '{topic}'")
                failed_connections.append(websocket)
                
            except Exception as e:
                logger.warning(f"Error sending message to client {client_id} on topic '{topic}': {str(e)}")
                failed_connections.append(websocket)
        
        # Log broadcast results
        if failed_connections:
            logger.info(f"Broadcast to topic '{topic}': {successful_sends} successful, {len(failed_connections)} failed")
        else:
            logger.debug(f"Broadcast to topic '{topic}': {successful_sends} clients notified successfully")
        
        # Clean up failed connections asynchronously to avoid blocking
        if failed_connections:
            cleanup_tasks = [self.disconnect(websocket) for websocket in failed_connections]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    async def broadcast_miners(self, miners_data: List[Dict[str, Any]]):
        """
        Broadcast miners data to all subscribed clients.
        
        Args:
            miners_data (List[Dict[str, Any]]): Miners data
        """
        await self.broadcast("miners", {
            "type": "miners_update",
            "data": miners_data,
        })
    
    async def broadcast_alerts(self, alerts_data: List[Dict[str, Any]]):
        """
        Broadcast alerts to all subscribed clients.
        
        Args:
            alerts_data (List[Dict[str, Any]]): Alerts data
        """
        await self.broadcast("alerts", {
            "type": "alerts_update",
            "data": alerts_data,
        })
    
    async def broadcast_system(self, system_data: Dict[str, Any]):
        """
        Broadcast system information to all subscribed clients.
        
        Args:
            system_data (Dict[str, Any]): System data
        """
        await self.broadcast("system", {
            "type": "system_update",
            "data": system_data,
        })
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """
        Register a handler for a specific message type.
        
        Args:
            message_type (str): Message type
            handler (Callable): Handler function
        """
        self._message_handlers[message_type] = handler
    
    async def handle_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Handle a message from a client with comprehensive state tracking and validation.
        Supports all WebSocket message types without authentication requirements.
        
        Args:
            websocket (WebSocket): WebSocket connection
            message (Dict[str, Any]): Message from client
        """
        message_type = message.get("type")
        client_id = "unknown"
        
        try:
            # Update connection state and activity tracking
            async with self._connection_lock:
                if websocket in self._connection_states:
                    state = self._connection_states[websocket]
                    client_id = state.get("client_id", "unknown")
                    current_time = datetime.now()
                    state["last_ping"] = current_time
                    state["last_activity"] = current_time
                    state["message_count"] += 1
                    
                    # Update connection status if needed
                    if state.get("connection_status") != "active":
                        state["connection_status"] = "active"
            
            logger.debug(f"Handling message from client {client_id}: {message_type}")
            
            # Handle different message types
            if message_type == "subscribe":
                topics = message.get("topics", [])
                if isinstance(topics, str):
                    topics = [topics]
                
                # Validate topics
                valid_topics = ["miners", "alerts", "system", "metrics"]
                filtered_topics = [topic for topic in topics if topic in valid_topics]
                
                if filtered_topics:
                    await self.subscribe(websocket, filtered_topics)
                    logger.debug(f"Client {client_id} subscribed to topics: {filtered_topics}")
                else:
                    await websocket.send_json({
                        "type": "error",
                        "data": {
                            "message": f"No valid topics in subscription request. Valid topics: {valid_topics}",
                            "timestamp": datetime.now().isoformat()
                        }
                    })
                
            elif message_type == "unsubscribe":
                topics = message.get("topics", [])
                if isinstance(topics, str):
                    topics = [topics]
                await self.unsubscribe(websocket, topics)
                logger.debug(f"Client {client_id} unsubscribed from topics: {topics}")
                
            elif message_type == "ping":
                # Respond to ping with pong including client info
                pong_response = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                    "client_id": client_id
                }
                
                # Add connection stats if requested
                if message.get("include_stats", False):
                    async with self._connection_lock:
                        if websocket in self._connection_states:
                            state = self._connection_states[websocket]
                            pong_response["stats"] = {
                                "message_count": state.get("message_count", 0),
                                "connected_duration": (datetime.now() - state.get("connected_at", datetime.now())).total_seconds(),
                                "subscribed_topics": list(state.get("subscribed_topics", set()))
                            }
                
                await websocket.send_json(pong_response)
                
            elif message_type == "pong":
                # Client responded to our ping - update last ping time
                logger.debug(f"Received pong from client {client_id}")
                
            elif message_type == "get_status":
                # Send current connection status
                async with self._connection_lock:
                    if websocket in self._connection_states:
                        state = self._connection_states[websocket]
                        status_response = {
                            "type": "status_response",
                            "data": {
                                "client_id": client_id,
                                "connected_at": state.get("connected_at", datetime.now()).isoformat(),
                                "message_count": state.get("message_count", 0),
                                "subscribed_topics": list(state.get("subscribed_topics", set())),
                                "connection_status": state.get("connection_status", "unknown")
                            },
                            "timestamp": datetime.now().isoformat()
                        }
                        await websocket.send_json(status_response)
                
            elif message_type == "get_topics":
                # Send available topics
                await websocket.send_json({
                    "type": "topics_response",
                    "data": {
                        "available_topics": ["miners", "alerts", "system", "metrics"],
                        "description": {
                            "miners": "Real-time miner status and metrics",
                            "alerts": "System alerts and notifications",
                            "system": "System performance metrics",
                            "metrics": "Historical metrics data"
                        }
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
            elif message_type in self._message_handlers:
                # Handle custom message types
                await self._message_handlers[message_type](websocket, message)
                
            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")
                # Send error response with helpful information
                await websocket.send_json({
                    "type": "error",
                    "data": {
                        "message": f"Unknown message type: {message_type}",
                        "supported_types": ["subscribe", "unsubscribe", "ping", "pong", "get_status", "get_topics"],
                        "timestamp": datetime.now().isoformat()
                    }
                })
                
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
            # Send error response if possible
            try:
                await websocket.send_json({
                    "type": "error",
                    "data": {
                        "message": "Error processing message",
                        "error_type": type(e).__name__,
                        "timestamp": datetime.now().isoformat()
                    }
                })
            except Exception as send_error:
                logger.error(f"Failed to send error response to client {client_id}: {send_error}")
                # Connection might be closed, trigger cleanup
                await self.disconnect(websocket)
    
    async def start_broadcast_tasks(self, data_providers: Dict[str, Callable]):
        """
        Start background tasks for broadcasting updates.
        
        Args:
            data_providers (Dict[str, Callable]): Data provider functions for each topic
        """
        for topic, provider in data_providers.items():
            if topic in self._broadcast_intervals:
                task = asyncio.create_task(self._broadcast_task(topic, provider, self._broadcast_intervals[topic]))
                self._broadcast_tasks.append(task)
    
    async def _broadcast_task(self, topic: str, data_provider: Callable, interval: float):
        """
        Background task for broadcasting updates.
        
        Args:
            topic (str): Topic to broadcast to
            data_provider (Callable): Function that provides the data to broadcast
            interval (float): Broadcast interval in seconds
        """
        while True:
            try:
                # Skip if no subscribers
                connection_count = await self._thread_safe_manager.get_connection_count(topic)
                if connection_count == 0:
                    await asyncio.sleep(interval)
                    continue
                
                # Get data
                data = await data_provider()
                
                # Broadcast data
                await self.broadcast(topic, {
                    "type": f"{topic}_update",
                    "data": data,
                })
            except Exception as e:
                logger.error(f"Error in broadcast task for {topic}: {str(e)}")
            
            # Wait before next broadcast
            await asyncio.sleep(interval)
    
    def set_broadcast_interval(self, topic: str, interval: float):
        """
        Set the broadcast interval for a topic.
        
        Args:
            topic (str): Topic
            interval (float): Broadcast interval in seconds
        """
        if topic in self._broadcast_intervals:
            self._broadcast_intervals[topic] = interval
    
    async def _heartbeat_loop(self):
        """
        Enhanced background task for connection health monitoring and cleanup.
        Sends heartbeat pings and automatically cleans up stale/disconnected clients.
        """
        logger.info("Starting WebSocket heartbeat monitoring")
        
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                
                current_time = datetime.now()
                stale_connections = []
                inactive_connections = []
                
                # Check connection health and identify stale connections
                async with self._connection_lock:
                    for websocket, state in self._connection_states.items():
                        last_ping = state.get("last_ping", current_time)
                        last_activity = state.get("last_activity", current_time)
                        
                        # Check for stale connections (no ping response)
                        ping_timeout = (current_time - last_ping).total_seconds()
                        if ping_timeout > (self._heartbeat_interval * 2.5):
                            stale_connections.append((websocket, state.get('client_id', 'unknown'), ping_timeout))
                        
                        # Check for inactive connections (no activity)
                        activity_timeout = (current_time - last_activity).total_seconds()
                        if activity_timeout > (self._heartbeat_interval * 10):  # 10x heartbeat interval
                            inactive_connections.append((websocket, state.get('client_id', 'unknown'), activity_timeout))
                
                # Clean up stale connections
                if stale_connections:
                    logger.info(f"Cleaning up {len(stale_connections)} stale connections")
                    for websocket, client_id, timeout in stale_connections:
                        logger.warning(f"Client {client_id} is stale (no ping response for {timeout:.1f}s)")
                        await self.disconnect(websocket)
                
                # Warn about inactive connections but don't disconnect them yet
                for websocket, client_id, timeout in inactive_connections:
                    logger.info(f"Client {client_id} has been inactive for {timeout:.1f}s")
                
                # Send ping to active connections with error handling
                active_connections = await self._thread_safe_manager.get_connections("all")
                ping_failures = []
                
                if active_connections:
                    logger.debug(f"Sending heartbeat ping to {len(active_connections)} active connections")
                    
                    for websocket in active_connections:
                        client_id = "unknown"
                        try:
                            # Get client ID for logging
                            async with self._connection_lock:
                                if websocket in self._connection_states:
                                    client_id = self._connection_states[websocket].get("client_id", "unknown")
                            
                            # Send ping with timeout
                            ping_message = {
                                "type": "ping",
                                "timestamp": current_time.isoformat(),
                                "server_time": current_time.timestamp()
                            }
                            
                            from config.app_config import CONNECTION_TIMEOUT
                            await asyncio.wait_for(websocket.send_json(ping_message), timeout=CONNECTION_TIMEOUT // 2)
                            
                        except asyncio.TimeoutError:
                            logger.warning(f"Ping timeout for client {client_id}")
                            ping_failures.append(websocket)
                            
                        except Exception as e:
                            logger.debug(f"Failed to send ping to client {client_id}: {e}")
                            ping_failures.append(websocket)
                
                # Clean up connections that failed to receive ping
                if ping_failures:
                    logger.info(f"Cleaning up {len(ping_failures)} connections that failed ping")
                    cleanup_tasks = [self.disconnect(websocket) for websocket in ping_failures]
                    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                
                # Log connection statistics periodically
                if len(active_connections) > 0:
                    stats = await self.get_connection_stats()
                    logger.debug(f"Heartbeat complete - Active connections: {stats['total_connections']}, "
                               f"By topic: {stats['connections_by_topic']}")
                        
            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                # Continue the loop even if there's an error
                await asyncio.sleep(1)
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about WebSocket connections.
        
        Returns:
            Dict[str, Any]: Connection statistics
        """
        stats = {
            "total_connections": 0,
            "connections_by_topic": {},
            "connection_details": []
        }
        
        try:
            # Get connection counts by topic
            for topic in ["all", "miners", "alerts", "system"]:
                count = await self._thread_safe_manager.get_connection_count(topic)
                stats["connections_by_topic"][topic] = count
            
            stats["total_connections"] = stats["connections_by_topic"].get("all", 0)
            
            # Get connection details
            async with self._connection_lock:
                for websocket, state in self._connection_states.items():
                    stats["connection_details"].append({
                        "client_id": state.get("client_id", "unknown"),
                        "connected_at": state.get("connected_at", datetime.now()).isoformat(),
                        "last_ping": state.get("last_ping", datetime.now()).isoformat(),
                        "subscribed_topics": list(state.get("subscribed_topics", set())),
                        "message_count": state.get("message_count", 0)
                    })
                    
        except Exception as e:
            logger.error(f"Error getting connection stats: {e}")
            
        return stats
    
    async def stop(self):
        """
        Stop the WebSocket manager with proper cleanup.
        """
        logger.info("Stopping WebSocket manager...")
        
        # Cancel heartbeat task
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all broadcast tasks
        for task in self._broadcast_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Close all connections using thread-safe manager
        for topic in ["all", "miners", "alerts", "system"]:
            connections = await self._thread_safe_manager.get_connections(topic)
            for websocket in connections:
                try:
                    await websocket.close(code=1001, reason="Server shutdown")
                except Exception:
                    pass
                await self._thread_safe_manager.remove_connection(websocket)
        
        # Clear connection states
        async with self._connection_lock:
            self._connection_states.clear()
        
        logger.info("WebSocket manager stopped")