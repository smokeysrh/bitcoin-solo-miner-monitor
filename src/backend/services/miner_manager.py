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
        # TimeSeriesStorage for metrics persistence (will be set by API service)
        self.timeseries_storage = None
        # Metrics saving configuration - decoupled from polling interval
        # Fixed at 60 seconds to align with Analytics minimum timeframe (1 minute)
        self.metrics_save_interval = 60  # seconds
        self.last_metrics_save: Dict[str, datetime] = {}  # Track last save time per miner
    
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
        
    async def load_miners_from_storage(self, data_storage) -> int:
        """
        Load saved miners from storage and start polling.
        This should be called during application startup to restore miners from the database.
        
        Args:
            data_storage: DataStorage instance to load configs from
            
        Returns:
            int: Number of miners successfully loaded
        """
        try:
            logger.info("=== [BACKEND] LOADING MINERS FROM STORAGE START ===")
            logger.info(f"Manager is_running: {self.is_running}")
            logger.info(f"Current miners count: {len(self.miners)}")
            
            # Get all saved miner configurations
            saved_configs = await data_storage.get_all_miner_configs()
            
            logger.info(f"Retrieved {len(saved_configs) if saved_configs else 0} configs from storage")
            
            if not saved_configs:
                logger.info("No saved miners found in database")
                return 0
            
            logger.info(f"Found {len(saved_configs)} saved miner(s) in database")
            
            loaded_count = 0
            
            for idx, config in enumerate(saved_configs):
                try:
                    logger.info(f"Processing config {idx + 1}/{len(saved_configs)}: {config.keys()}")
                    
                    miner_id = config.get('id')
                    # Use factory_type if available (new format), otherwise fall back to type (old format)
                    factory_type = config.get('factory_type')
                    display_type = config.get('type')
                    
                    # For backward compatibility: if no factory_type, try to infer from miner_id or type
                    if not factory_type:
                        # Try to extract from miner_id (e.g., "bitaxe_192_168_1_156" -> "bitaxe")
                        if miner_id and '_' in miner_id:
                            factory_type = miner_id.split('_')[0]
                        else:
                            # Fall back to type, but convert known device types to factory types
                            factory_type = display_type
                            if display_type and display_type.lower().startswith('nerdqaxe'):
                                factory_type = 'bitaxe'
                            elif display_type and display_type.lower().startswith('bitaxe'):
                                factory_type = 'bitaxe'
                    
                    ip_address = config.get('ip_address')
                    port = config.get('port')
                    name = config.get('name')
                    
                    logger.info(f"Config details - ID: {miner_id}, Display Type: {display_type}, Factory Type: {factory_type}, IP: {ip_address}, Port: {port}, Name: {name}")
                    
                    if not all([miner_id, factory_type, ip_address]):
                        logger.warning(f"Skipping incomplete miner config - missing required fields")
                        continue
                    
                    logger.info(f"Creating miner instance for {miner_id} ({name}) - factory_type: {factory_type} at {ip_address}:{port}")
                    
                    # Create miner instance using factory_type
                    miner = await MinerFactory.create_miner(factory_type, ip_address, port)
                    
                    if not miner:
                        logger.error(f"MinerFactory returned None for {miner_id}")
                        continue
                    
                    logger.info(f"Miner instance created successfully for {miner_id}")
                    
                    # Add miner to manager with thread safety
                    async with self._miners_lock:
                        self.miners[miner_id] = miner
                        logger.info(f"Added {miner_id} to self.miners dict (now has {len(self.miners)} miners)")
                    
                    # Store miner data in thread-safe manager
                    await self.miner_data_manager.set_miner(miner_id, config)
                    logger.info(f"Stored {miner_id} in miner_data_manager")
                    
                    # Start polling if manager is running
                    if self.is_running:
                        await self.start_polling(miner_id)
                        logger.info(f"Started polling for miner {miner_id}")
                    else:
                        logger.warning(f"Manager not running, skipping polling start for {miner_id}")
                    
                    loaded_count += 1
                    logger.info(f"Successfully loaded miner {miner_id} ({loaded_count}/{len(saved_configs)})")
                    
                except Exception as e:
                    logger.error(f"Error loading miner {config.get('id', 'unknown')}: {str(e)}", exc_info=True)
                    continue
            
            logger.info(f"=== [BACKEND] LOADED {loaded_count}/{len(saved_configs)} MINERS FROM STORAGE ===")
            logger.info(f"Final miners count in self.miners: {len(self.miners)}")
            return loaded_count
            
        except Exception as e:
            logger.error(f"Error in load_miners_from_storage: {str(e)}", exc_info=True)
            return 0
        
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
            
            # Get device info to determine actual type and model
            device_info = await miner.get_device_info()
            
            # Determine the actual device type from device_info
            # This allows proper differentiation between Bitaxe and NerdQaxe variants
            actual_type = miner_type  # Default to the factory type
            if device_info and "type" in device_info:
                actual_type = device_info["type"]
                logger.debug(f"Device type from device_info: {actual_type}")
            
            # Generate miner ID using the factory type (for consistency)
            miner_id = f"{miner_type}_{ip_address}".replace(".", "_")
            
            # Generate name if not provided
            if not name:
                if device_info and "model" in device_info:
                    # Clean up model name by removing trailing underscores
                    model_name = str(device_info['model']).strip().rstrip('_')
                    name = f"{model_name} - {ip_address}"
                else:
                    name = f"{miner_type.capitalize()} - {ip_address}"
            else:
                # Clean up provided name by removing trailing underscores
                name = str(name).strip().rstrip('_')
            
            # Add miner to manager with thread safety
            async with self._miners_lock:
                self.miners[miner_id] = miner
            
            # Use thread-safe miner data manager
            # Store both factory_type (for recreation) and actual type (for display)
            await self.miner_data_manager.set_miner(miner_id, {
                "id": miner_id,
                "name": name,
                "type": actual_type,  # Actual device type for display (e.g., "NerdQaxe++")
                "factory_type": miner_type,  # Factory type for recreation (e.g., "bitaxe")
                "ip_address": ip_address,
                "port": port,
                "added_at": datetime.now().isoformat(),
                "status": "connected",
                "last_updated": None,
                "metrics": {},
                "device_info": device_info  # Store full device_info for reference
            })
            
            # Start polling for this miner if manager is running
            if self.is_running:
                await self.start_polling(miner_id)
            
            logger.info(f"Added miner {miner_id} ({name}) with type {actual_type}", {
                'miner_id': miner_id,
                'miner_type': actual_type,
                'factory_type': miner_type,
                'ip_address': ip_address,
                'port': port,
                'miner_name': name
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
            
            # Clean up metrics save tracking
            if miner_id in self.last_metrics_save:
                del self.last_metrics_save[miner_id]
            
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
        logger.info(f"=== MINER MANAGER START_DISCOVERY CALLED ===")
        logger.info(f"Network: {network}")
        logger.info(f"Ports: {ports}")
        logger.info(f"Timeout: {timeout}")
        logger.info(f"Current discovery task: {self.discovery_task}")
        logger.info(f"Discovery task done: {self.discovery_task.done() if self.discovery_task else 'N/A'}")
        logger.info(f"WebSocket manager available: {self.websocket_manager is not None}")
        if self.websocket_manager:
            connection_count = await self.websocket_manager._thread_safe_manager.get_connection_count("all")
            logger.info(f"WebSocket connections: {connection_count}")
        
        if self.discovery_task and not self.discovery_task.done():
            logger.warning("Discovery already in progress")
            return False
        
        try:
            # PRE-CALCULATE total_hosts before initializing state
            logger.info("Pre-calculating total hosts from network range...")
            total_hosts = 0
            try:
                if '-' in network:
                    # Handle IP range format: "192.168.1.1-192.168.1.254"
                    start_ip, end_ip = network.split('-')
                    start_addr = ipaddress.ip_address(start_ip.strip())
                    end_addr = ipaddress.ip_address(end_ip.strip())
                    total_hosts = int(end_addr) - int(start_addr) + 1
                    logger.info(f"IP range format: {total_hosts} hosts from {start_ip} to {end_ip}")
                else:
                    # Handle CIDR notation: "192.168.1.0/24"
                    network_obj = ipaddress.ip_network(network)
                    total_hosts = len(list(network_obj.hosts()))
                    logger.info(f"CIDR format: {total_hosts} hosts in {network}")
            except (ValueError, ipaddress.AddressValueError) as e:
                logger.error(f"Invalid network format: {network} - {str(e)}")
                total_hosts = 0
            
            logger.info("Initializing discovery state...")
            # Initialize discovery state with correct total_hosts
            self.discovery_state = {
                "status": "starting",
                "network": network,
                "ports": ports or [80, 4028],
                "timeout": timeout,
                "total_hosts": total_hosts,  # Now has correct value!
                "scanned_hosts": 0,
                "current_ip": None,
                "found_miners": [],
                "start_time": datetime.now(),
                "end_time": None,
                "error": None
            }
            logger.info(f"Discovery state initialized with {total_hosts} total hosts")
            
            # Broadcast initial state immediately
            if self.websocket_manager:
                logger.info("Broadcasting initial discovery state...")
                await self.websocket_manager.broadcast_to_topic("discovery", {
                    "type": "discovery_update",
                    "data": self.discovery_state
                })
                logger.info("Initial discovery state broadcasted successfully")
            else:
                logger.warning("WebSocket manager not available - no real-time updates will be sent")
            
            logger.info("Creating discovery task...")
            self.discovery_task = asyncio.create_task(self._discover_miners(network, ports, timeout))
            logger.info(f"Discovery task created: {self.discovery_task}")
            
            self.last_discovery = datetime.now()
            logger.info("=== MINER MANAGER START_DISCOVERY COMPLETED SUCCESSFULLY ===")
            return True
        except DiscoveryError as e:
            logger.error(f"Discovery error starting discovery", {
                'error_type': 'discovery_error',
                'error': str(e)
            })
            return False
        except NetworkError as e:
            logger.error(f"Network error starting discovery", {
                'error_type': 'network_error',
                'error': str(e)
            })
            return False
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error starting discovery", {
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
        except Exception as e:
            logger.error(f"Unexpected error starting discovery", {
                'error_type': 'unexpected_error',
                'error': str(e)
            })
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
    
    def set_timeseries_storage(self, timeseries_storage):
        """
        Set the timeseries storage instance for metrics persistence.
        
        Args:
            timeseries_storage: TimeSeriesStorage instance
        """
        self.timeseries_storage = timeseries_storage
    
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
        logger.info(f"=== [BACKEND] START POLLING CALLED === miner_id={miner_id}, is_running={self.is_running}")
        
        if miner_id not in self.miners:
            logger.warning(f"=== [BACKEND] START POLLING FAILED === miner_id={miner_id} not in miners dict, available_miners={list(self.miners.keys())}")
            return False
        
        if miner_id in self.polling_tasks and not self.polling_tasks[miner_id].done():
            # Already polling
            logger.info(f"=== [BACKEND] POLLING ALREADY RUNNING === miner_id={miner_id}")
            return True
        
        try:
            logger.info(f"=== [BACKEND] CREATING POLLING TASK === miner_id={miner_id}, interval={self.polling_interval}s")
            self.polling_tasks[miner_id] = asyncio.create_task(self._poll_miner(miner_id))
            logger.info(f"=== [BACKEND] POLLING TASK CREATED === miner_id={miner_id}, task_id={id(self.polling_tasks[miner_id])}")
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
    
    def _extract_metrics(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant metrics from miner status for storage.
        Returns a flat dictionary of metric_name: value pairs.
        
        Args:
            status: Miner status dictionary
            
        Returns:
            Dict[str, Any]: Flat dictionary of metrics
        """
        metrics = {}
        
        # Extract common metrics
        if 'hashrate' in status:
            metrics['hashrate'] = status['hashrate']
        if 'temperature' in status:
            metrics['temperature'] = status['temperature']
        if 'power' in status:
            metrics['power'] = status['power']
        if 'fan_speed' in status:
            metrics['fan_speed'] = status['fan_speed']
        if 'shares_accepted' in status:
            metrics['shares_accepted'] = status['shares_accepted']
        if 'shares_rejected' in status:
            metrics['shares_rejected'] = status['shares_rejected']
        if 'uptime' in status:
            metrics['uptime'] = status['uptime']
        
        return metrics
    
    async def _poll_miner(self, miner_id: str):
        """
        Poll a miner for status and metrics.
        
        Args:
            miner_id (str): ID of the miner
        """
        logger.info(f"=== [BACKEND] POLL MINER START === miner_id={miner_id}, is_running={self.is_running}")
        
        if miner_id not in self.miners:
            logger.warning(f"=== [BACKEND] POLL MINER SKIPPED === miner_id={miner_id} not in miners dict")
            return
        
        miner = self.miners[miner_id]
        poll_count = 0
        
        while self.is_running:
            poll_count += 1
            poll_start_time = datetime.now()
            
            logger.info(f"=== [BACKEND] POLL CYCLE START === miner_id={miner_id}, poll_count={poll_count}, time={poll_start_time.isoformat()}")
            
            try:
                # Get status
                logger.debug(f"=== [BACKEND] FETCHING STATUS === miner_id={miner_id}")
                status = await miner.get_status()
                logger.info(f"=== [BACKEND] STATUS RECEIVED === miner_id={miner_id}, online={status.get('online')}, keys={list(status.keys())}")
                
                # Get metrics
                logger.debug(f"=== [BACKEND] FETCHING METRICS === miner_id={miner_id}")
                metrics = await miner.get_metrics()
                logger.info(f"=== [BACKEND] METRICS RECEIVED === miner_id={miner_id}, metrics_keys={list(metrics.keys()) if metrics else None}")
                
                # Get pool info
                logger.debug(f"=== [BACKEND] FETCHING POOL INFO === miner_id={miner_id}")
                pool_info = await miner.get_pool_info()
                logger.info(f"=== [BACKEND] POOL INFO RECEIVED === miner_id={miner_id}, pool_count={len(pool_info) if pool_info else 0}")
                
                # Get device info to keep type and model updated
                logger.debug(f"=== [BACKEND] FETCHING DEVICE INFO === miner_id={miner_id}")
                device_info = await miner.get_device_info()
                logger.info(f"=== [BACKEND] DEVICE INFO RECEIVED === miner_id={miner_id}, device_keys={list(device_info.keys()) if device_info else None}")
                
                # Prepare update data
                update_timestamp = datetime.now().isoformat()
                update_data = {
                    "status": "online" if status.get("online", False) else "offline",
                    "last_updated": update_timestamp,
                    "metrics": metrics,
                    "pool_info": pool_info,
                    "device_info": device_info
                }
                
                # Add status data (excluding 'online' as we already set it)
                for key, value in status.items():
                    if key != "online":
                        update_data[key] = value
                
                logger.info(f"=== [BACKEND] UPDATING MINER DATA === miner_id={miner_id}, last_updated={update_timestamp}, status={update_data['status']}")
                
                # Update miner data using thread-safe manager
                await self.miner_data_manager.update_miner(miner_id, update_data)
                
                logger.info(f"=== [BACKEND] MINER DATA UPDATED === miner_id={miner_id}, poll_count={poll_count}")
                
                # Save metrics to timeseries storage (throttled to metrics_save_interval)
                # This is decoupled from polling_interval to reduce storage usage
                # while maintaining responsive UI updates
                if self.timeseries_storage and status:
                    current_time = datetime.now()
                    last_save = self.last_metrics_save.get(miner_id)
                    
                    # Check if enough time has passed since last save
                    should_save = (
                        last_save is None or 
                        (current_time - last_save).total_seconds() >= self.metrics_save_interval
                    )
                    
                    logger.info(f"Metrics save check for {miner_id}: should_save={should_save}, "
                               f"last_save={last_save}, interval={self.metrics_save_interval}s")
                    
                    if should_save:
                        try:
                            # Extract metrics from status
                            extracted_metrics = self._extract_metrics(status)
                            # Also include metrics from the metrics dict
                            if metrics:
                                extracted_metrics.update(metrics)
                            
                            # Save to timeseries storage
                            await self.timeseries_storage.save_metrics(
                                miner_id, 
                                extracted_metrics, 
                                current_time
                            )
                            
                            # Update last save time
                            self.last_metrics_save[miner_id] = current_time
                            
                            logger.info(f"Saved metrics for miner {miner_id} to timeseries storage "
                                       f"(interval: {self.metrics_save_interval}s)")
                            
                            # Broadcast metrics update via WebSocket
                            if self.websocket_manager:
                                await self.websocket_manager.broadcast_metrics(
                                    miner_id,
                                    extracted_metrics,
                                    current_time.isoformat()
                                )
                                logger.info(f"Broadcasted metrics update for miner {miner_id}")
                        except Exception as e:
                            logger.error(f"Failed to save metrics for {miner_id}: {e}")
                            # Don't fail the polling cycle - just log the error
                    else:
                        elapsed = (current_time - last_save).total_seconds()
                        logger.debug(f"Skipping metrics save for {miner_id} "
                                   f"(elapsed: {elapsed:.1f}s, interval: {self.metrics_save_interval}s)")
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
            # Default ports to check - include Bitcoin node ports
            ports = [80, 4028, 8332, 18332, 8333, 18333, 8080]
        
        discovered_miners = []
        
        try:
            # Parse network - handle both CIDR notation and IP ranges
            if '-' in network:
                # Handle IP range format: "192.168.1.83-192.168.1.88"
                logger.info(f"Parsing IP range: {network}")
                start_ip, end_ip = network.split('-')
                start_ip = start_ip.strip()
                end_ip = end_ip.strip()
                
                # Convert to IP address objects
                start_addr = ipaddress.ip_address(start_ip)
                end_addr = ipaddress.ip_address(end_ip)
                
                # Generate list of IPs in the range
                hosts = []
                current = int(start_addr)
                end = int(end_addr)
                
                while current <= end:
                    hosts.append(ipaddress.ip_address(current))
                    current += 1
                
                logger.info(f"Generated {len(hosts)} hosts from range {start_ip} to {end_ip}")
            else:
                # Handle CIDR notation: "192.168.1.0/24"
                logger.info(f"Parsing CIDR network: {network}")
                network_obj = ipaddress.ip_network(network)
                hosts = list(network_obj.hosts())
                logger.info(f"Generated {len(hosts)} hosts from CIDR {network}")
            
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
            
            # Scan hosts with optimized concurrency for better performance
            # Increased from 3 to 15 for faster scanning while maintaining stability
            semaphore = asyncio.Semaphore(15)  # Allow 15 concurrent scans for better performance
            
            async def scan_with_progress(host_ip: str) -> Optional[Dict[str, Any]]:
                async with semaphore:
                    try:
                        # Update current IP being scanned
                        if self.discovery_state:
                            self.discovery_state["current_ip"] = host_ip
                            
                            # Improved update frequency for better UX
                            # Small networks (<=20): Update every host
                            # Medium networks (21-100): Update every 5 hosts
                            # Large networks (>100): Update every 10 hosts
                            total = self.discovery_state["total_hosts"]
                            scanned = self.discovery_state["scanned_hosts"]
                            
                            if total <= 20:
                                update_frequency = 1
                            elif total <= 100:
                                update_frequency = 5
                            else:
                                update_frequency = 10
                            
                            should_update = (
                                scanned % update_frequency == 0 or 
                                scanned == 0 or
                                scanned == total - 1
                            )
                            
                            if should_update and self.websocket_manager:
                                logger.debug(f"Broadcasting progress: {scanned}/{total} hosts scanned, current IP: {host_ip}")
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
                                # Broadcast immediately when a miner is found
                                if self.websocket_manager:
                                    logger.info(f"Miner found at {host_ip}! Broadcasting update...")
                                    await self.websocket_manager.broadcast_to_topic("discovery", {
                                        "type": "discovery_update",
                                        "data": self.discovery_state
                                    })
                        
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
                    logger.info(f"Broadcasting final discovery status: {len(discovered_miners)} miners found")
                    await self.websocket_manager.broadcast_to_topic("discovery", {
                        "type": "discovery_update",
                        "data": self.discovery_state
                    })
                    logger.info("Final discovery status broadcasted successfully")
                else:
                    logger.warning("WebSocket manager not available for final broadcast")
            
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
        try:
            # First check if ports are open (this is fast)
            open_ports = await self._check_open_ports(ip_address, ports, timeout)
            if not open_ports:
                return None
            
            # Try to detect miner type with a reasonable timeout
            # Use 6x the connection timeout for full miner detection (allows time for sequential Bitcoin port checks)
            detection_timeout = timeout * 6
            
            try:
                logger.info(f"Starting miner type detection for {ip_address} with open ports: {open_ports}")
                result = await asyncio.wait_for(
                    MinerFactory.detect_miner_type(ip_address, open_ports),
                    timeout=detection_timeout
                )
                if result:
                    logger.info(f"Miner detected on {ip_address}: {result}")
                    return result
                else:
                    logger.info(f"No miner detected on {ip_address}")
            except asyncio.TimeoutError:
                logger.info(f"Miner detection timed out for {ip_address} after {detection_timeout}s")
                return None
            
            return None
        except Exception as e:
            logger.debug(f"Error scanning host {ip_address}: {str(e)}")
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
                # Use a shorter timeout for initial port checking (1/3 of the main timeout)
                port_timeout = max(1, timeout // 3)
                
                # Use asyncio to create connection with timeout
                future = asyncio.open_connection(ip_address, port)
                reader, writer = await asyncio.wait_for(future, timeout=port_timeout)
                
                # Close connection immediately
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