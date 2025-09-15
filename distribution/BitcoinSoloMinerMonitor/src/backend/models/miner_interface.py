"""
Miner Interface - Abstract Base Class

This module defines the interface that all miner implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class MinerInterface(ABC):
    """
    Abstract base class defining the interface for all miner implementations.
    """
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the miner.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the miner.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the miner.
        
        Returns:
            Dict[str, Any]: Dictionary containing miner status information
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get the current performance metrics of the miner.
        
        Returns:
            Dict[str, Any]: Dictionary containing miner metrics
        """
        pass
    
    @abstractmethod
    async def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the miner device.
        
        Returns:
            Dict[str, Any]: Dictionary containing device information
        """
        pass
    
    @abstractmethod
    async def get_pool_info(self) -> List[Dict[str, Any]]:
        """
        Get information about the mining pools configured on the miner.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing pool information
        """
        pass
    
    @abstractmethod
    async def restart(self) -> bool:
        """
        Restart the miner.
        
        Returns:
            bool: True if restart command was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def update_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Update miner settings.
        
        Args:
            settings (Dict[str, Any]): Dictionary containing settings to update
            
        Returns:
            bool: True if settings were updated successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_supported_features(self) -> List[str]:
        """
        Get a list of features supported by this miner.
        
        Returns:
            List[str]: List of feature identifiers
        """
        pass
    
    @abstractmethod
    def get_miner_type(self) -> str:
        """
        Get the type of miner.
        
        Returns:
            str: Miner type identifier
        """
        pass
    
    @abstractmethod
    def get_last_updated(self) -> Optional[datetime]:
        """
        Get the timestamp of the last successful data update.
        
        Returns:
            Optional[datetime]: Timestamp of last update or None if never updated
        """
        pass