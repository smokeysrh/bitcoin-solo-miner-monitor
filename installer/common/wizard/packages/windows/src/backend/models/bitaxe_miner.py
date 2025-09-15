"""
Bitaxe Miner Implementation

This module implements the MinerInterface for Bitaxe miners.
"""

import aiohttp
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.backend.models.miner_interface import MinerInterface
from src.backend.models.http_client_mixin import HTTPClientMixin
from config.app_config import CONNECTION_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY

logger = logging.getLogger(__name__)


class BitaxeMiner(HTTPClientMixin, MinerInterface):
    """
    Implementation of the MinerInterface for Bitaxe miners.
    
    The Bitaxe miner exposes a HTTP REST API that returns JSON data.
    """
    
    def __init__(self, ip_address: str, port: int = 80):
        """
        Initialize a new BitaxeMiner instance.
        
        Args:
            ip_address (str): IP address of the Bitaxe miner
            port (int, optional): Port number. Defaults to 80.
        """
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
        self.connected = False
        self.last_updated = None
        self.device_info = {}
        
    async def connect(self) -> bool:
        """
        Establish connection to the Bitaxe miner.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Test connection by fetching system info
            system_info = await self._http_get("/api/system/info")
            if system_info:
                self.connected = True
                self.device_info = system_info
                logger.info(f"Connected to Bitaxe miner at {self.ip_address}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Bitaxe miner at {self.ip_address}: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the Bitaxe miner.
        
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
            
            logger.info(f"Disconnected from Bitaxe miner at {self.ip_address}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Bitaxe miner at {self.ip_address}: {str(e)}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Bitaxe miner.
        
        Returns:
            Dict[str, Any]: Dictionary containing miner status information
        """
        status_data = {}
        
        try:
            # Get system info
            system_info = await self._http_get("/api/system/info")
            if system_info:
                status_data.update({
                    "online": True,
                    "hashrate": system_info.get("hashRate", 0),
                    "temperature": system_info.get("temp", 0),
                    "fan_speed": system_info.get("fanspeed", 0),
                    "fan_rpm": system_info.get("fanrpm", 0),
                    "power": system_info.get("power", 0),
                    "voltage": system_info.get("voltage", 0),
                    "current": system_info.get("current", 0),
                    "uptime": system_info.get("uptimeSeconds", 0),
                    "shares_accepted": system_info.get("sharesAccepted", 0),
                    "shares_rejected": system_info.get("sharesRejected", 0),
                    "firmware_version": system_info.get("version", "unknown"),
                    "asic_count": system_info.get("asicCount", 0),
                    "frequency": system_info.get("frequency", 0),
                })
                
                # Update last updated timestamp
                self.last_updated = datetime.now()
            else:
                status_data["online"] = False
                
            return status_data
        except Exception as e:
            logger.error(f"Error getting status from Bitaxe miner at {self.ip_address}: {str(e)}")
            return {"online": False, "error": str(e)}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get the current performance metrics of the Bitaxe miner.
        
        Returns:
            Dict[str, Any]: Dictionary containing miner metrics
        """
        try:
            # For Bitaxe, we can get more detailed metrics from the statistics endpoint
            stats = await self._http_get("/api/system/statistics/dashboard")
            if not stats:
                return {}
                
            metrics = {
                "hashrate": stats.get("hashRate", 0),
                "temperature": stats.get("temp", 0),
                "power": stats.get("power", 0),
                "efficiency": stats.get("hashRate", 0) / stats.get("power", 1) if stats.get("power", 0) > 0 else 0,
                "shares": {
                    "accepted": stats.get("sharesAccepted", 0),
                    "rejected": stats.get("sharesRejected", 0),
                    "rejection_rate": stats.get("sharesRejected", 0) / (stats.get("sharesAccepted", 0) + stats.get("sharesRejected", 0)) * 100 if (stats.get("sharesAccepted", 0) + stats.get("sharesRejected", 0)) > 0 else 0
                },
                "best_share": {
                    "difficulty": stats.get("bestDiff", "0"),
                    "session_difficulty": stats.get("bestSessionDiff", "0")
                }
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting metrics from Bitaxe miner at {self.ip_address}: {str(e)}")
            return {}
    
    async def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the Bitaxe miner device.
        
        Returns:
            Dict[str, Any]: Dictionary containing device information
        """
        if not self.device_info:
            try:
                self.device_info = await self._http_get("/api/system/info")
            except Exception as e:
                logger.error(f"Error getting device info from Bitaxe miner at {self.ip_address}: {str(e)}")
                return {}
        
        # Extract relevant device information
        if self.device_info:
            return {
                "type": "Bitaxe",
                "model": self.device_info.get("ASICModel", "Unknown"),
                "firmware_version": self.device_info.get("version", "Unknown"),
                "idf_version": self.device_info.get("idfVersion", "Unknown"),
                "board_version": self.device_info.get("boardVersion", "Unknown"),
                "mac_address": self.device_info.get("macAddr", "Unknown"),
                "hostname": self.device_info.get("hostname", "Unknown"),
                "asic_count": self.device_info.get("asicCount", 0),
                "core_count": self.device_info.get("smallCoreCount", 0),
            }
        
        return {}
    
    async def get_pool_info(self) -> List[Dict[str, Any]]:
        """
        Get information about the mining pools configured on the Bitaxe miner.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing pool information
        """
        try:
            system_info = await self._http_get("/api/system/info")
            if not system_info:
                return []
                
            pools = []
            
            # Primary pool
            if "stratumURL" in system_info:
                pools.append({
                    "url": system_info.get("stratumURL", ""),
                    "port": system_info.get("stratumPort", 0),
                    "user": system_info.get("stratumUser", ""),
                    "is_active": not system_info.get("isUsingFallbackStratum", 0),
                    "difficulty": system_info.get("stratumDiff", 0),
                    "is_fallback": False
                })
            
            # Fallback pool
            if "fallbackStratumURL" in system_info:
                pools.append({
                    "url": system_info.get("fallbackStratumURL", ""),
                    "port": system_info.get("fallbackStratumPort", 0),
                    "user": system_info.get("fallbackStratumUser", ""),
                    "is_active": system_info.get("isUsingFallbackStratum", 0) == 1,
                    "difficulty": system_info.get("stratumDiff", 0),
                    "is_fallback": True
                })
                
            return pools
        except Exception as e:
            logger.error(f"Error getting pool info from Bitaxe miner at {self.ip_address}: {str(e)}")
            return []
    
    async def restart(self) -> bool:
        """
        Restart the Bitaxe miner.
        
        Returns:
            bool: True if restart command was successful, False otherwise
        """
        try:
            response = await self._http_post("/api/system/restart", {})
            return response is not None
        except Exception as e:
            logger.error(f"Error restarting Bitaxe miner at {self.ip_address}: {str(e)}")
            return False
    
    async def update_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Update Bitaxe miner settings.
        
        Args:
            settings (Dict[str, Any]): Dictionary containing settings to update
            
        Returns:
            bool: True if settings were updated successfully, False otherwise
        """
        try:
            response = await self._http_patch("/api/system", settings)
            return response is not None
        except Exception as e:
            logger.error(f"Error updating settings for Bitaxe miner at {self.ip_address}: {str(e)}")
            return False
    
    def get_supported_features(self) -> List[str]:
        """
        Get a list of features supported by the Bitaxe miner.
        
        Returns:
            List[str]: List of feature identifiers
        """
        return [
            "restart",
            "update_settings",
            "fan_control",
            "frequency_control",
            "pool_configuration",
            "detailed_metrics"
        ]
    
    def get_miner_type(self) -> str:
        """
        Get the type of miner.
        
        Returns:
            str: Miner type identifier
        """
        return "Bitaxe"
    
    def get_last_updated(self) -> Optional[datetime]:
        """
        Get the timestamp of the last successful data update.
        
        Returns:
            Optional[datetime]: Timestamp of last update or None if never updated
        """
        return self.last_updated
    
