"""
Bitcoin Node Implementation

This module implements detection and monitoring for Bitcoin Core nodes.
"""

import aiohttp
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.backend.models.miner_interface import MinerInterface
from src.backend.models.http_client_mixin import HTTPClientMixin
from config.app_config import CONNECTION_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY

logger = logging.getLogger(__name__)


class BitcoinNode(HTTPClientMixin, MinerInterface):
    """
    Implementation for Bitcoin Core node detection and monitoring.
    
    Bitcoin nodes typically expose RPC interfaces and web interfaces
    that can be detected and monitored.
    """
    
    def __init__(self, ip_address: str, port: int = 8332):
        """
        Initialize a new BitcoinNode instance.
        
        Args:
            ip_address (str): IP address of the Bitcoin node
            port (int, optional): Port number. Defaults to 8332 (Bitcoin RPC port).
        """
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
        self.connected = False
        self.last_updated = None
        self.node_info = {}
        self.detected_ports = []
        
    async def connect(self) -> bool:
        """
        Establish connection to the Bitcoin node.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Try to detect Bitcoin node on common ports
            detection_result = await self._detect_bitcoin_node()
            if detection_result:
                self.connected = True
                self.node_info = detection_result
                logger.info(f"Connected to Bitcoin node at {self.ip_address}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Bitcoin node at {self.ip_address}: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the Bitcoin node.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            self.connected = False
            
            # Cleanup HTTP session if active
            if hasattr(self, '_http_session_active') and self._http_session_active:
                from src.backend.services.http_session_manager import get_session_manager
                session_manager = await get_session_manager()
                await session_manager.close_session(self.ip_address, self.port)
            
            logger.info(f"Disconnected from Bitcoin node at {self.ip_address}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Bitcoin node at {self.ip_address}: {str(e)}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Bitcoin node.
        
        Returns:
            Dict[str, Any]: Dictionary containing node status information
        """
        status_data = {}
        
        try:
            if self.node_info.get("type") == "web_interface":
                # Try to get status from web interface
                status_data = await self._get_web_status()
            elif self.node_info.get("type") == "rpc_interface":
                # Try to get status from RPC interface (if accessible)
                status_data = await self._get_rpc_status()
            else:
                # Basic connectivity check
                status_data = {
                    "online": True,
                    "type": "Bitcoin Node",
                    "interface": self.node_info.get("interface", "unknown"),
                    "port": self.port
                }
                
            self.last_updated = datetime.now()
            return status_data
        except Exception as e:
            logger.error(f"Error getting status from Bitcoin node at {self.ip_address}: {str(e)}")
            return {"online": False, "error": str(e)}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get the current metrics of the Bitcoin node.
        
        Returns:
            Dict[str, Any]: Dictionary containing node metrics
        """
        try:
            metrics = {
                "node_type": "Bitcoin Core",
                "interface_type": self.node_info.get("interface", "unknown"),
                "detected_ports": self.detected_ports,
                "connection_count": 0,  # Will be populated if RPC is accessible
                "block_height": 0,      # Will be populated if RPC is accessible
                "sync_progress": 0.0    # Will be populated if RPC is accessible
            }
            
            # Try to get additional metrics if RPC is available
            if self.node_info.get("type") == "rpc_interface":
                rpc_metrics = await self._get_rpc_metrics()
                metrics.update(rpc_metrics)
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting metrics from Bitcoin node at {self.ip_address}: {str(e)}")
            return {}
    
    async def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the Bitcoin node.
        
        Returns:
            Dict[str, Any]: Dictionary containing device information
        """
        if not self.node_info:
            detection_result = await self._detect_bitcoin_node()
            if detection_result:
                self.node_info = detection_result
            else:
                return {}
        
        # Return node information
        if self.node_info:
            return {
                "type": "Bitcoin Node",
                "interface": self.node_info.get("interface", "unknown"),
                "detected_ports": self.detected_ports,
                "software": "Bitcoin Core",  # Assume Bitcoin Core for now
                "version": self.node_info.get("version", "Unknown"),
                "network": self.node_info.get("network", "Unknown")
            }
        
        return {}
    
    async def _detect_bitcoin_node(self) -> Dict[str, Any]:
        """
        Detect if this is a Bitcoin node by checking common ports and interfaces.
        
        Returns:
            Dict[str, Any]: Detection result with node information
        """
        logger.info(f"Starting Bitcoin node detection for {self.ip_address}")
        
        # ONLY check Bitcoin-specific ports (NOT port 80 which is used by miners)
        bitcoin_ports = [
            8332,  # Bitcoin RPC (mainnet)
            18332, # Bitcoin RPC (testnet)
            8333,  # Bitcoin P2P (mainnet)
            18333, # Bitcoin P2P (testnet)
        ]
        
        detected_info = {}
        
        for port in bitcoin_ports:
            logger.info(f"Checking Bitcoin node on {self.ip_address}:{port}")
            try:
                # Update port for this check
                original_port = self.port
                self.port = port
                self.base_url = f"http://{self.ip_address}:{port}"
                
                if port in [8332, 18332]:
                    # Try RPC detection
                    logger.info(f"Attempting RPC detection on {self.ip_address}:{port}")
                    rpc_result = await self._check_rpc_interface(port)
                    if rpc_result:
                        logger.info(f"Bitcoin RPC interface detected on {self.ip_address}:{port}")
                        self.detected_ports.append(port)
                        detected_info = {
                            "type": "rpc_interface",
                            "interface": "RPC",
                            "port": port,
                            **rpc_result
                        }
                        self.port = port  # Keep the working port
                        return detected_info
                    else:
                        logger.info(f"No RPC interface found on {self.ip_address}:{port}")
                
                elif port in [80, 8080]:
                    # Try web interface detection
                    logger.info(f"Attempting web interface detection on {self.ip_address}:{port}")
                    web_result = await self._check_web_interface(port)
                    if web_result:
                        logger.info(f"Bitcoin web interface detected on {self.ip_address}:{port}")
                        self.detected_ports.append(port)
                        detected_info = {
                            "type": "web_interface", 
                            "interface": "Web",
                            "port": port,
                            **web_result
                        }
                        self.port = port  # Keep the working port
                        return detected_info
                    else:
                        logger.info(f"No web interface found on {self.ip_address}:{port}")
                
                elif port in [8333, 18333]:
                    # Try P2P port detection (basic connectivity check)
                    logger.info(f"Attempting P2P port detection on {self.ip_address}:{port}")
                    p2p_result = await self._check_p2p_port(port)
                    if p2p_result:
                        logger.info(f"Bitcoin P2P port detected on {self.ip_address}:{port}")
                        self.detected_ports.append(port)
                        detected_info = {
                            "type": "p2p_interface",
                            "interface": "P2P",
                            "port": port,
                            **p2p_result
                        }
                        self.port = port  # Keep the working port
                        return detected_info
                    else:
                        logger.info(f"No P2P port found on {self.ip_address}:{port}")
                
                # Restore original port if this one didn't work
                self.port = original_port
                self.base_url = f"http://{self.ip_address}:{original_port}"
                
            except Exception as e:
                logger.info(f"Bitcoin node detection failed on port {port}: {str(e)}")
                continue
        
        logger.info(f"Bitcoin node detection completed for {self.ip_address}. No Bitcoin node detected.")
        return detected_info
    
    async def _check_rpc_interface(self, port: int) -> Dict[str, Any]:
        """
        Check if there's a Bitcoin RPC interface on the given port.
        
        Args:
            port (int): Port to check
            
        Returns:
            Dict[str, Any]: RPC interface information if detected
        """
        try:
            logger.info(f"Testing RPC interface on {self.ip_address}:{port}")
            
            # Try a basic RPC call (this will likely fail due to auth, but we can detect the interface)
            rpc_data = {
                "jsonrpc": "1.0",
                "id": "test",
                "method": "getblockchaininfo",
                "params": []
            }
            
            # First try to make a simple HTTP request to see if anything responds
            try:
                response = await self._http_post("/", rpc_data)
                logger.info(f"RPC POST response received from {self.ip_address}:{port}: {response}")
                
                # Even if we get an auth error, the response format tells us it's Bitcoin RPC
                if response or "error" in str(response):
                    return {
                        "interface_type": "RPC",
                        "network": "mainnet" if port == 8332 else "testnet"
                    }
            except Exception as post_error:
                logger.info(f"RPC POST failed on {self.ip_address}:{port}: {str(post_error)}")
                
                # Try a simple GET request to see if we get any response
                try:
                    html = await self._http_get_text("/")
                    if html:
                        logger.info(f"Got HTML response from {self.ip_address}:{port}, checking for RPC indicators")
                        html_lower = html.lower()
                        
                        # Look for Bitcoin RPC indicators in the response
                        rpc_indicators = [
                            "bitcoin",
                            "rpc",
                            "jsonrpc",
                            "unauthorized",
                            "forbidden",
                            "authentication required"
                        ]
                        
                        found_indicators = sum(1 for indicator in rpc_indicators if indicator in html_lower)
                        
                        if found_indicators >= 2:
                            logger.info(f"Found {found_indicators} RPC indicators in response from {self.ip_address}:{port}")
                            return {
                                "interface_type": "RPC",
                                "network": "mainnet" if port == 8332 else "testnet",
                                "auth_required": True
                            }
                except Exception as get_error:
                    logger.info(f"RPC GET also failed on {self.ip_address}:{port}: {str(get_error)}")
                
                # Check if the error suggests this is a Bitcoin RPC endpoint
                error_str = str(post_error).lower()
                if any(indicator in error_str for indicator in ["unauthorized", "forbidden", "rpc", "bitcoin", "authentication"]):
                    logger.info(f"Error suggests RPC interface on {self.ip_address}:{port}: {error_str}")
                    return {
                        "interface_type": "RPC",
                        "network": "mainnet" if port == 8332 else "testnet",
                        "auth_required": True
                    }
                
        except Exception as e:
            logger.info(f"RPC interface check failed on {self.ip_address}:{port}: {str(e)}")
        
        return {}
    
    async def _check_web_interface(self, port: int) -> Dict[str, Any]:
        """
        Check if there's a Bitcoin node web interface on the given port.
        
        Args:
            port (int): Port to check
            
        Returns:
            Dict[str, Any]: Web interface information if detected
        """
        try:
            logger.info(f"Testing web interface on {self.ip_address}:{port}")
            
            # Try to get the main page
            html = await self._http_get_text("/")
            if html:
                logger.info(f"Got HTML response from {self.ip_address}:{port}, length: {len(html)}")
                html_lower = html.lower()
                
                # Look for Bitcoin node indicators
                bitcoin_indicators = [
                    "bitcoin",
                    "blockchain", 
                    "block height",
                    "mempool",
                    "node",
                    "satoshi",
                    "btc",
                    "bitcoin core",
                    "bitcoind",
                    "rpc server"
                ]
                
                found_indicators = []
                for indicator in bitcoin_indicators:
                    if indicator in html_lower:
                        found_indicators.append(indicator)
                
                logger.info(f"Found Bitcoin indicators on {self.ip_address}:{port}: {found_indicators}")
                
                # If we find multiple Bitcoin-related terms, it's likely a Bitcoin node interface
                if len(found_indicators) >= 2:  # Lowered threshold for better detection
                    logger.info(f"Bitcoin web interface detected on {self.ip_address}:{port} with {len(found_indicators)} indicators")
                    return {
                        "interface_type": "Web",
                        "indicators_found": len(found_indicators),
                        "found_terms": found_indicators[:5]  # Limit to first 5 for logging
                    }
                else:
                    logger.info(f"Not enough Bitcoin indicators found on {self.ip_address}:{port} (found {len(found_indicators)}, need 2+)")
            else:
                logger.info(f"No HTML response from {self.ip_address}:{port}")
        
        except Exception as e:
            logger.info(f"Web interface check failed on {self.ip_address}:{port}: {str(e)}")
        
        return {}
    
    async def _check_p2p_port(self, port: int) -> Dict[str, Any]:
        """
        Check if there's a Bitcoin P2P port open (basic connectivity check).
        
        Args:
            port (int): Port to check
            
        Returns:
            Dict[str, Any]: P2P port information if detected
        """
        try:
            import socket
            import asyncio
            
            # Create a socket connection to test if the port is open
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            
            try:
                # Try to connect to the port
                result = sock.connect_ex((self.ip_address, port))
                if result == 0:
                    # Port is open, likely a Bitcoin P2P port
                    logger.info(f"P2P port {port} is open on {self.ip_address}")
                    return {
                        "interface_type": "P2P",
                        "network": "mainnet" if port == 8333 else "testnet",
                        "port_open": True
                    }
            finally:
                sock.close()
                
        except Exception as e:
            logger.debug(f"P2P port check failed on port {port}: {str(e)}")
        
        return {}
    
    async def _get_web_status(self) -> Dict[str, Any]:
        """Get status from web interface."""
        try:
            # Basic status for web interface
            return {
                "online": True,
                "type": "Bitcoin Node",
                "interface": "Web",
                "port": self.port
            }
        except Exception:
            return {"online": False}
    
    async def _get_rpc_status(self) -> Dict[str, Any]:
        """Get status from RPC interface."""
        try:
            # Basic status for RPC interface (would need auth for real data)
            return {
                "online": True,
                "type": "Bitcoin Node", 
                "interface": "RPC",
                "port": self.port,
                "auth_required": True
            }
        except Exception:
            return {"online": False}
    
    async def _get_rpc_metrics(self) -> Dict[str, Any]:
        """Get metrics from RPC interface."""
        # Would need authentication to get real RPC metrics
        return {
            "rpc_available": True,
            "auth_required": True
        }
    
    # Required interface methods (not applicable for Bitcoin nodes)
    async def get_pool_info(self) -> List[Dict[str, Any]]:
        """Bitcoin nodes don't have pool info."""
        return []
    
    async def restart(self) -> bool:
        """Bitcoin node restart not supported via this interface."""
        return False
    
    async def update_settings(self, settings: Dict[str, Any]) -> bool:
        """Bitcoin node settings update not supported via this interface."""
        return False
    
    def get_supported_features(self) -> List[str]:
        """
        Get a list of features supported by the Bitcoin node interface.
        
        Returns:
            List[str]: List of feature identifiers
        """
        return [
            "status_monitoring",
            "basic_metrics",
            "connection_info"
        ]
    
    def get_miner_type(self) -> str:
        """
        Get the type identifier.
        
        Returns:
            str: Type identifier
        """
        return "Bitcoin Node"
    
    def get_last_updated(self) -> Optional[datetime]:
        """
        Get the timestamp of the last successful data update.
        
        Returns:
            Optional[datetime]: Timestamp of last update or None if never updated
        """
        return self.last_updated