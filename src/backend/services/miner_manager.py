"""
Miner Manager Service

This module provides a service for managing miners, including discovery, monitoring, and control.
"""

import asyncio
import ipaddress
import logging
import socket
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple

from src.backend.models.miner_interface import MinerInterface
from src.backend.models.miner_factory import MinerFactory
from src.backend.exceptions import (
    MinerManagerError, MinerError, MinerConnectionError, 
    DiscoveryError, ValidationError, NetworkError
)
from src.backend.utils.structured_logging import get_logger
from src.backend.utils.retry_logic import retry_miner_operation, retry_http_request
from src.backend.utils.thread_safety import miner_data_manager
from config.app_config import DEFAULT_POLLING_INTERVAL

logger = get_logger(__name__)


class MinerManager:
    """
    Service for managing miners, including discovery, monitoring, and control.
    """
    
    def __init__(self):
        """
        Initialize a new MinerManager instance.
        """
        self.miners: Dict[str, MinerInterface] = {}  # key: miner_id, value: miner instance
        # Use thread-safe miner data manager instead of direct dictionary
        self.miner_data_manager = miner_data_manager
        self.polling_tasks: Dict[str, asyncio.Task] = {}  # key: miner_id, value: polling task
        self.polling_interval = DEFAULT_POLLING_INTERVAL
        self.discovery_task = None
        self.discovery_state = None
        self.is_running = False
        self.last_discovery = None
        # Add lock for miners dictionary access
        self._miners_lock = asyncio.Lock()
        # WebSocket manager for real-time updates (will be set by API service)
        self.websocket_manager = None
    
    async def start(self):
        """
        Start the miner manager service.
        """
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting miner manager service")
        
        # Start polling for existing miners
        for miner_id in self.miners:
            await self.start_polling(miner_id)
    
    async def stop(self):
        """
        Stop the miner manager service.
        """
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping miner manager service")
        
        # Stop discovery task if running
        if self.discovery_task and not self.discovery_task.done():
            self.discovery_task.cancel()
            try:
                await self.discovery_task
            except asyncio.CancelledError:
                pass
        
        # Stop polling tasks
        for miner_id, task in self.polling_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.polling_tasks.clear()
        
        # Disconnect all miners to ensure proper session cleanup
        for miner_id, miner in self.miners.items():
            try:
                await miner.disconnect()
                logger.debug(f"Disconnected miner {miner_id}")
            except MinerError as e:
                logger.error(f"Miner error disconnecting miner {miner_id}", {
                    'miner_id': miner_id,
                    'error_type': 'miner_error'
                })
            except (RuntimeError, OSError) as e:
                logger.error(f"System error disconnecting miner {miner_id}", {
                    'miner_id': miner_id,
                    'error_type': 'system_error',
                    'error': str(e)
                })
    
    @retry_miner_operation(max_attempts=3, base_delay=2.0, max_delay=30.0)
    async def add_miner(self, miner_type: str, ip_address: str, port: Optional[int] = None, name: Optional[str] = None) -> Optional[str]:
        """
        Add a new miner to the manager.
        
        Args:
            miner_type (str): Type of miner to add
            ip_address (str): IP address of the miner
            port (Optional[int]): Port number (if None, default port for the miner type will be used)
            name (Optional[str]): Custom name for the miner (if None, a name will be generated)
            
        Returns:
            Optional[str]: Miner ID if successful, None otherwise
        """
        try:
            # Create miner instance
            miner = await MinerFactory.create_miner(miner_type, ip_address, port)
            if not miner:
                return None
            
            # Generate miner ID
            miner_id = f"{miner_type}_{ip_address}".replace(".", "_")
            
            # Generate name if not provided
            if not name:
                device_info = await miner.get_device_info()
                if device_info and "model" in device_info:
                    name = f"{device_info['model']} ({ip_address})"
                else:
                    name = f"{miner_type.capitalize()} ({ip_address})"
            
            # Add miner to manager with thread safety
            async with self._miners_lock:
                self.miners[miner_id] = miner
            
            # Use thread-safe miner data manager
            await self.miner_data_manager.set_miner(miner_id, {
                "id": miner_id,
                "name": name,
                "type": miner_type,
                "ip_address": ip_address,
                "port": port,
                "added_at": datetime.now().isoformat(),
                "status": "connected",
                "last_updated": None,
                "metrics": {}
            })
            
            # Start polling for this miner if manager is running
            if self.is_running:
                await self.start_polling(miner_id)
            
            logger.info(f"Added miner {miner_id} ({name})", {
                'miner_id': miner_id,
                'miner_type': miner_type,
                'ip_address': ip_address,
                'port': port,
                'name': name
            })
            return miner_id
        except MinerError as e:
            logger.error(f"Miner error adding miner", {
                'ip_address': ip_address,
                'miner_type': miner_type,
                'error_type': 'miner_error'
            })
            return None
        except ValidationError as e:
            logger.error(f"Validation error adding miner", {
                'ip_address': ip_address,
                'miner_type': miner_type,
                'error_type': 'validation_error'
            })
            return None
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error adding miner", {
                'ip_address': ip_address,
                'miner_type': miner_type,
                'error_type': 'system_error',
                'error': str(e)
            })
            return None
    
    async def remove_miner(self, miner_id: str) -> bool:
        """
        Remove a miner from the manager.
        
        Args:
            miner_id (str): ID of the miner to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        if miner_id not in self.miners:
            return False
        
        try:
            # Stop polling task if running
            if miner_id in self.polling_tasks:
                task = self.polling_tasks[miner_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.polling_tasks[miner_id]
            
            # Disconnect from miner
            async with self._miners_lock:
                miner = self.miners[miner_id]
                await miner.disconnect()
                
                # Remove miner from manager
                del self.miners[miner_id]
            
            # Remove miner data using thread-safe manager
            await self.miner_data_manager.remove_miner(miner_id)
            
            logger.info(f"Removed miner {miner_id}", {
                'miner_id': miner_id
            })
            return True
        except MinerError as e:
            logger.error(f"Miner error removing miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'miner_error'
            })
            return False
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error removing miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
    
    async def get_miner(self, miner_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Optional[Dict[str, Any]]: Miner information or None if miner not found
        """
        return await self.miner_data_manager.get_miner(miner_id)
    
    async def get_miners(self) -> List[Dict[str, Any]]:
        """
        Get information about all miners.
        
        Returns:
            List[Dict[str, Any]]: List of miner information
        """
        return await self.miner_data_manager.get_all_miners()
    
    async def update_miner(self, miner_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update miner information.
        
        Args:
            miner_id (str): ID of the miner
            updates (Dict[str, Any]): Updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not await self.miner_data_manager.exists(miner_id):
            return False
        
        try:
            # Filter out protected fields
            filtered_updates = {}
            for key, value in updates.items():
                if key not in ["id", "type", "ip_address", "port", "added_at"]:
                    filtered_updates[key] = value
            
            # Update miner data using thread-safe manager
            await self.miner_data_manager.update_miner(miner_id, filtered_updates)
            
            # If updating settings, apply to miner
            if "settings" in updates:
                async with self._miners_lock:
                    if miner_id in self.miners:
                        miner = self.miners[miner_id]
                        await miner.update_settings(updates["settings"])
            
            return True
        except MinerError as e:
            logger.error(f"Miner error updating miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'miner_error'
            })
            return False
        except ValidationError as e:
            logger.error(f"Validation error updating miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'validation_error'
            })
            return False
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error updating miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
    
    @retry_miner_operation(max_attempts=3, base_delay=2.0, max_delay=30.0)
    async def restart_miner(self, miner_id: str) -> bool:
        """
        Restart a miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            bool: True if successful, False otherwise
        """
        if miner_id not in self.miners:
            return False
        
        try:
            miner = self.miners[miner_id]
            result = await miner.restart()
            
            if result:
                # Update status using thread-safe manager
                await self.miner_data_manager.update_miner(miner_id, {
                    "status": "restarting",
                    "last_restarted": datetime.now().isoformat()
                })
            
            return result
        except MinerError as e:
            logger.error(f"Miner error restarting miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'miner_error'
            })
            return False
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error restarting miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
    
    async def start_discovery(self, network: str, ports: Optional[List[int]] = None, timeout: int = 5) -> bool:
        """
        Start discovery of miners on the network.
        
        Args:
            network (str): Network to scan (e.g., "192.168.1.0/24")
            ports (Optional[List[int]]): Ports to check (if None, default ports will be checked)
            timeout (int): Timeout in seconds for each connection attempt
            
        Returns:
            bool: True if discovery started successfully, False otherwise
        """
        if self.discovery_task and not self.discovery_task.done():
            logger.warning("Discovery already in progress")
            return False
        
        try:
            # Initialize discovery state
            self.discovery_state = {
                "status": "starting",
                "network": network,
                "ports": ports or [80, 4028],
                "timeout": timeout,
                "total_hosts": 0,
                "scanned_hosts": 0,
                "current_ip": None,
                "found_miners": [],
                "start_time": datetime.now(),
                "end_time": None,
                "error": None
            }
            
            self.discovery_task = asyncio.create_task(self._discover_miners(network, ports, timeout))
            self.last_discovery = datetime.now()
            return True
        except DiscoveryError as e:
            logger.error(f"Discovery error starting discovery", {
                'error_type': 'discovery_error'
            })
            return False
        except NetworkError as e:
            logger.error(f"Network error starting discovery", {
                'error_type': 'network_error'
            })
            return False
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error starting discovery", {
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
    
    async def get_discovery_status(self) -> Dict[str, Any]:
        """
        Get the status of the discovery process.
        
        Returns:
            Dict[str, Any]: Discovery status information
        """
        if not self.discovery_task:
            return {
                "status": "not_started",
                "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None
            }
        
        # Return current discovery state if available
        if self.discovery_state:
            status_data = self.discovery_state.copy()
            
            # Convert datetime objects to ISO strings
            if status_data.get("start_time"):
                status_data["start_time"] = status_data["start_time"].isoformat()
            if status_data.get("end_time"):
                status_data["end_time"] = status_data["end_time"].isoformat()
            
            # Calculate progress percentage
            if status_data["total_hosts"] > 0:
                status_data["progress"] = (status_data["scanned_hosts"] / status_data["total_hosts"]) * 100
            else:
                status_data["progress"] = 0
            
            return status_data
        
        if self.discovery_task.done():
            try:
                result = self.discovery_task.result()
                return {
                    "status": "completed",
                    "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None,
                    "miners_found": len(result),
                    "result": result
                }
            except DiscoveryError as e:
                return {
                    "status": "error",
                    "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None,
                    "error": "Discovery failed",
                    "error_type": "discovery_error"
                }
            except (RuntimeError, MemoryError) as e:
                return {
                    "status": "error",
                    "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None,
                    "error": "System error",
                    "error_type": "system_error"
                }
        else:
            return {
                "status": "in_progress",
                "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None
            }
    
    async def stop_discovery(self) -> bool:
        """
        Stop the current discovery process.
        
        Returns:
            bool: True if discovery was stopped, False if no discovery was running
        """
        if not self.discovery_task or self.discovery_task.done():
            return False
        
        try:
            self.discovery_task.cancel()
            try:
                await self.discovery_task
            except asyncio.CancelledError:
                pass
            
            # Update discovery state
            if self.discovery_state:
                self.discovery_state["status"] = "cancelled"
                self.discovery_state["end_time"] = datetime.now()
                
                # Broadcast final status update
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_to_topic("discovery", {
                        "type": "discovery_update",
                        "data": self.discovery_state
                    })
            
            logger.info("Discovery process stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping discovery: {str(e)}")
            return False
    
    def set_websocket_manager(self, websocket_manager):
        """
        Set the WebSocket manager for real-time updates.
        
        Args:
            websocket_manager: WebSocket manager instance
        """
        self.websocket_manager = websocket_manager
    
    async def set_polling_interval(self, interval: int) -> bool:
        """
        Set the polling interval for all miners.
        
        Args:
            interval (int): Polling interval in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        if interval < 1:
            return False
        
        self.polling_interval = interval
        
        # Restart polling tasks with new interval
        if self.is_running:
            for miner_id in self.miners:
                await self.stop_polling(miner_id)
                await self.start_polling(miner_id)
        
        return True
    
    async def start_polling(self, miner_id: str) -> bool:
        """
        Start polling for a specific miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            bool: True if successful, False otherwise
        """
        if miner_id not in self.miners:
            return False
        
        if miner_id in self.polling_tasks and not self.polling_tasks[miner_id].done():
            # Already polling
            return True
        
        try:
            self.polling_tasks[miner_id] = asyncio.create_task(self._poll_miner(miner_id))
            return True
        except MinerError as e:
            logger.error(f"Miner error starting polling for miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'miner_error'
            })
            return False
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error starting polling for miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
    
    async def stop_polling(self, miner_id: str) -> bool:
        """
        Stop polling for a specific miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            bool: True if successful, False otherwise
        """
        if miner_id not in self.polling_tasks:
            return False
        
        try:
            task = self.polling_tasks[miner_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            del self.polling_tasks[miner_id]
            return True
        except MinerError as e:
            logger.error(f"Miner error stopping polling for miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'miner_error'
            })
            return False
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error stopping polling for miner {miner_id}", {
                'miner_id': miner_id,
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
    
    async def _poll_miner(self, miner_id: str):
        """
        Poll a miner for status and metrics.
        
        Args:
            miner_id (str): ID of the miner
        """
        if miner_id not in self.miners:
            return
        
        miner = self.miners[miner_id]
        
        while self.is_running:
            try:
                # Get status
                status = await miner.get_status()
                
                # Get metrics
                metrics = await miner.get_metrics()
                
                # Get pool info
                pool_info = await miner.get_pool_info()
                
                # Prepare update data
                update_data = {
                    "status": "online" if status.get("online", False) else "offline",
                    "last_updated": datetime.now().isoformat(),
                    "metrics": metrics,
                    "pool_info": pool_info
                }
                
                # Add status data (excluding 'online' as we already set it)
                for key, value in status.items():
                    if key != "online":
                        update_data[key] = value
                
                # Update miner data using thread-safe manager
                await self.miner_data_manager.update_miner(miner_id, update_data)
            except MinerConnectionError as e:
                logger.error(f"Connection error polling miner {miner_id}", {
                    'miner_id': miner_id,
                    'error_type': 'connection_error'
                })
                await self.miner_data_manager.update_miner(miner_id, {
                    "status": "offline",
                    "error": "Connection failed"
                })
            except MinerError as e:
                logger.error(f"Miner error polling miner {miner_id}", {
                    'miner_id': miner_id,
                    'error_type': 'miner_error'
                })
                await self.miner_data_manager.update_miner(miner_id, {
                    "status": "error",
                    "error": "Miner error"
                })
            except (RuntimeError, MemoryError) as e:
                logger.error(f"System error polling miner {miner_id}", {
                    'miner_id': miner_id,
                    'error_type': 'system_error',
                    'error': str(e)
                })
                await self.miner_data_manager.update_miner(miner_id, {
                    "status": "error",
                    "error": "System error"
                })
            
            # Wait for next polling interval
            await asyncio.sleep(self.polling_interval)
    
    async def _discover_miners(self, network: str, ports: Optional[List[int]] = None, timeout: int = 5) -> List[Dict[str, Any]]:
        """
        Discover miners on the network with real-time progress updates.
        
        Args:
            network (str): Network to scan (e.g., "192.168.1.0/24")
            ports (Optional[List[int]]): Ports to check (if None, default ports will be checked)
            timeout (int): Timeout in seconds for each connection attempt
            
        Returns:
            List[Dict[str, Any]]: List of discovered miners
        """
        if ports is None:
            # Default ports to check
            ports = [80, 4028]
        
        discovered_miners = []
        
        try:
            # Parse network
            network_obj = ipaddress.ip_network(network)
            
            # Get list of hosts to scan
            hosts = list(network_obj.hosts())
            
            # Update discovery state
            if self.discovery_state:
                self.discovery_state["status"] = "scanning"
                self.discovery_state["total_hosts"] = len(hosts)
                self.discovery_state["scanned_hosts"] = 0
                
                # Broadcast initial status
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_to_topic("discovery", {
                        "type": "discovery_update",
                        "data": self.discovery_state
                    })
            
            # Scan hosts sequentially for better progress tracking
            # Use semaphore to limit concurrent scans for better control
            semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent scans
            
            async def scan_with_progress(host_ip: str) -> Optional[Dict[str, Any]]:
                async with semaphore:
                    try:
                        # Update current IP being scanned
                        if self.discovery_state:
                            self.discovery_state["current_ip"] = host_ip
                            
                            # Broadcast progress update every 5 hosts or for first/last host
                            if (self.discovery_state["scanned_hosts"] % 5 == 0 or 
                                self.discovery_state["scanned_hosts"] == 0 or
                                self.discovery_state["scanned_hosts"] == self.discovery_state["total_hosts"] - 1):
                                if self.websocket_manager:
                                    await self.websocket_manager.broadcast_to_topic("discovery", {
                                        "type": "discovery_update",
                                        "data": self.discovery_state
                                    })
                        
                        # Scan the host
                        result = await self._scan_host(host_ip, ports, timeout)
                        
                        # Update progress
                        if self.discovery_state:
                            self.discovery_state["scanned_hosts"] += 1
                            if result:
                                self.discovery_state["found_miners"].append(result)
                        
                        return result
                    except asyncio.CancelledError:
                        # Discovery was cancelled
                        raise
                    except Exception as e:
                        # Log error but continue scanning
                        logger.debug(f"Error scanning host {host_ip}: {str(e)}")
                        if self.discovery_state:
                            self.discovery_state["scanned_hosts"] += 1
                        return None
            
            # Create scan tasks
            scan_tasks = [scan_with_progress(str(host)) for host in hosts]
            
            # Execute scans with progress tracking
            results = await asyncio.gather(*scan_tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    if isinstance(result, asyncio.CancelledError):
                        # Discovery was cancelled
                        if self.discovery_state:
                            self.discovery_state["status"] = "cancelled"
                            self.discovery_state["end_time"] = datetime.now()
                        raise result
                    # Other exceptions are already logged, continue
                    continue
                elif result:
                    discovered_miners.append(result)
            
            # Update final discovery state
            if self.discovery_state:
                self.discovery_state["status"] = "completed"
                self.discovery_state["end_time"] = datetime.now()
                self.discovery_state["current_ip"] = None
                
                # Broadcast final status
                if self.websocket_manager:
                    await self.websocket_manager.broadcast_to_topic("discovery", {
                        "type": "discovery_update",
                        "data": self.discovery_state
                    })
            
            logger.info(f"Discovery completed. Found {len(discovered_miners)} miners on network {network}")
            return discovered_miners
            
        except asyncio.CancelledError:
            # Discovery was cancelled
            logger.info("Discovery process was cancelled")
            raise
        except (ValueError, ipaddress.AddressValueError) as e:
            logger.error(f"Invalid network address for discovery", {
                'network': network,
                'error_type': 'address_error'
            })
            if self.discovery_state:
                self.discovery_state["status"] = "error"
                self.discovery_state["error"] = f"Invalid network address: {network}"
                self.discovery_state["end_time"] = datetime.now()
            raise DiscoveryError(f"Invalid network address: {network}")
        except NetworkError as e:
            logger.error(f"Network error during miner discovery", {
                'network': network,
                'error_type': 'network_error'
            })
            if self.discovery_state:
                self.discovery_state["status"] = "error"
                self.discovery_state["error"] = "Network error"
                self.discovery_state["end_time"] = datetime.now()
            raise
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error during miner discovery", {
                'network': network,
                'error_type': 'system_error',
                'error': str(e)
            })
            if self.discovery_state:
                self.discovery_state["status"] = "error"
                self.discovery_state["error"] = "System error"
                self.discovery_state["end_time"] = datetime.now()
            raise DiscoveryError(f"Discovery failed: {str(e)}")
    
    async def _scan_host(self, ip_address: str, ports: List[int], timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Scan a host for miners.
        
        Args:
            ip_address (str): IP address to scan
            ports (List[int]): Ports to check
            timeout (int): Timeout in seconds for each connection attempt
            
        Returns:
            Optional[Dict[str, Any]]: Discovered miner information or None if no miner found
        """
        # First check if ports are open
        open_ports = await self._check_open_ports(ip_address, ports, timeout)
        if not open_ports:
            return None
        
        # Try to detect miner type
        result = await MinerFactory.detect_miner_type(ip_address, open_ports)
        if result:
            return result
        
        return None
    
    async def _check_open_ports(self, ip_address: str, ports: List[int], timeout: int = 5) -> List[int]:
        """
        Check which ports are open on a host.
        
        Args:
            ip_address (str): IP address to check
            ports (List[int]): Ports to check
            timeout (int): Timeout in seconds for each connection attempt
            
        Returns:
            List[int]: List of open ports
        """
        open_ports = []
        
        async def check_port(port: int) -> Optional[int]:
            try:
                # Use asyncio to create connection with timeout
                future = asyncio.open_connection(ip_address, port)
                reader, writer = await asyncio.wait_for(future, timeout=timeout)
                
                # Close connection
                writer.close()
                await writer.wait_closed()
                
                return port
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return None
            except Exception:
                return None
        
        # Check all ports concurrently
        port_tasks = [check_port(port) for port in ports]
        results = await asyncio.gather(*port_tasks, return_exceptions=True)
        
        # Collect open ports
        for result in results:
            if isinstance(result, int):
                open_ports.append(result)
        
        return open_ports