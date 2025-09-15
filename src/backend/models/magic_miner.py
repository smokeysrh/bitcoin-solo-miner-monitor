"""
Magic Miner Implementation

This module implements the MinerInterface for Magic Miner BG02 miners.
Since there's no documented API, this implementation uses web scraping
and request interception to extract data from the web interface.
"""

import aiohttp
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

from src.backend.models.miner_interface import MinerInterface
from src.backend.models.http_client_mixin import HTTPClientMixin
from src.backend.exceptions import (
    MinerConnectionError, MinerDataError, MinerTimeoutError,
    HTTPSessionError, ValidationError
)
from src.backend.utils.structured_logging import get_logger
from config.app_config import CONNECTION_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY

logger = get_logger(__name__)


class MagicMiner(HTTPClientMixin, MinerInterface):
    """
    Implementation of the MinerInterface for Magic Miner BG02 miners.
    
    The Magic Miner provides a web-based management interface. This implementation
    uses web scraping and request interception to extract data.
    """
    
    def __init__(self, ip_address: str, port: int = 80):
        """
        Initialize a new MagicMiner instance.
        
        Args:
            ip_address (str): IP address of the Magic Miner
            port (int, optional): Port number. Defaults to 80.
        """
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
        self.connected = False
        self.last_updated = None
        self.device_info = {}
        self.auth_token = None
        
    async def connect(self) -> bool:
        """
        Establish connection to the Magic Miner.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Test connection by accessing the main page
            html = await self._http_get_text("")
            if html:
                # Extract any necessary tokens or cookies for future requests
                self.auth_token = self._extract_auth_token(html)
                
                # Get initial device info
                self.device_info = await self._extract_device_info(html)
                
                self.connected = True
                logger.info(f"Connected to Magic Miner", {
                    'ip_address': self.ip_address,
                    'port': self.port,
                    'device_model': self.device_info.get('model', 'unknown')
                })
                return True
            else:
                raise MinerConnectionError("Failed to retrieve main page", 
                                         ip_address=self.ip_address,
                                         context={'port': self.port})
        except aiohttp.ClientConnectorError as e:
            raise MinerConnectionError("Connection refused or network unreachable", 
                                     ip_address=self.ip_address,
                                     context={'port': self.port, 'original_error': str(e)})
        except aiohttp.ServerTimeoutError as e:
            raise MinerTimeoutError("Connection timeout", 
                                  ip_address=self.ip_address,
                                  context={'port': self.port, 'timeout': CONNECTION_TIMEOUT})
        except MinerConnectionError:
            # Re-raise specific connection errors
            raise
        except (RuntimeError, MemoryError, SystemError) as e:
            raise MinerConnectionError("System error during connection", 
                                     ip_address=self.ip_address,
                                     context={'port': self.port, 'original_error': str(e)})
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the Magic Miner.
        
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
            
            logger.info(f"Disconnected from Magic Miner", {
                'ip_address': self.ip_address,
                'port': self.port
            })
            return True
        except HTTPSessionError as e:
            logger.error(f"HTTP session error during disconnect", {
                'ip_address': self.ip_address,
                'port': self.port,
                'error_type': 'session_error'
            })
            return False
        except (RuntimeError, OSError) as e:
            logger.error(f"System error disconnecting from Magic Miner", {
                'ip_address': self.ip_address,
                'port': self.port,
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Magic Miner.
        
        Returns:
            Dict[str, Any]: Dictionary containing miner status information
        """
        status_data = {}
        
        try:
            # Get the main status page
            html = await self._http_get_text("/status")
            if html:
                status_data = await self._extract_status_data(html)
                status_data["online"] = True
                
                # Update last updated timestamp
                self.last_updated = datetime.now()
            else:
                status_data["online"] = False
                
            return status_data
        except MinerConnectionError as e:
            logger.error(f"Connection error getting status from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'connection_error'
            })
            return {"online": False, "error": "Connection failed"}
        except MinerTimeoutError as e:
            logger.error(f"Timeout error getting status from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'timeout_error'
            })
            return {"online": False, "error": "Request timeout"}
        except MinerDataError as e:
            logger.error(f"Data parsing error getting status from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
            return {"online": True, "error": "Data parsing failed"}
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error getting status from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'system_error',
                'error': str(e)
            })
            return {"online": False, "error": "System error"}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get the current performance metrics of the Magic Miner.
        
        Returns:
            Dict[str, Any]: Dictionary containing miner metrics
        """
        try:
            # For Magic Miner, we'll try to get metrics from the stats page
            html = await self._http_get_text("/stats")
            if html:
                return await self._extract_metrics_data(html)
            else:
                # Fall back to status page if stats page doesn't exist
                return await self.get_status()
        except MinerConnectionError as e:
            logger.error(f"Connection error getting metrics from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'connection_error'
            })
            return {}
        except MinerTimeoutError as e:
            logger.error(f"Timeout error getting metrics from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'timeout_error'
            })
            return {}
        except MinerDataError as e:
            logger.error(f"Data parsing error getting metrics from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
            return {}
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error getting metrics from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'system_error',
                'error': str(e)
            })
            return {}
    
    async def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the Magic Miner device.
        
        Returns:
            Dict[str, Any]: Dictionary containing device information
        """
        if not self.device_info:
            try:
                html = await self._http_get_text("/system")
                if html:
                    self.device_info = await self._extract_device_info(html)
            except MinerConnectionError as e:
                logger.error(f"Connection error getting device info from Magic Miner", {
                    'ip_address': self.ip_address,
                    'error_type': 'connection_error'
                })
                return {}
            except MinerDataError as e:
                logger.error(f"Data parsing error getting device info from Magic Miner", {
                    'ip_address': self.ip_address,
                    'error_type': 'data_error'
                })
                return {}
            except (RuntimeError, MemoryError) as e:
                logger.error(f"System error getting device info from Magic Miner", {
                    'ip_address': self.ip_address,
                    'error_type': 'system_error',
                    'error': str(e)
                })
                return {}
        
        # Add basic device type information
        device_info = {
            "type": "Magic Miner",
            "model": "BG02",  # Default model, will be updated if available in device details
        }
        
        # Add any additional details from device_info
        device_info.update(self.device_info)
        
        return device_info
    
    async def get_pool_info(self) -> List[Dict[str, Any]]:
        """
        Get information about the mining pools configured on the Magic Miner.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing pool information
        """
        try:
            # Get the pool configuration page
            html = await self._http_get_text("/pool")
            if html:
                return await self._extract_pool_info(html)
            else:
                return []
        except MinerConnectionError as e:
            logger.error(f"Connection error getting pool info from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'connection_error'
            })
            return []
        except MinerDataError as e:
            logger.error(f"Data parsing error getting pool info from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
            return []
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error getting pool info from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'system_error',
                'error': str(e)
            })
            return []
    
    async def restart(self) -> bool:
        """
        Restart the Magic Miner.
        
        Returns:
            bool: True if restart command was successful, False otherwise
        """
        try:
            # Send restart command
            form_data = {"token": self.auth_token} if self.auth_token else {}
            response = await self._http_post_form("/restart", form_data)
            return response is not None
        except MinerConnectionError as e:
            logger.error(f"Connection error restarting Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'connection_error'
            })
            return False
        except HTTPSessionError as e:
            logger.error(f"HTTP session error restarting Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'session_error'
            })
            return False
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error restarting Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
    
    async def update_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Update Magic Miner settings.
        
        Args:
            settings (Dict[str, Any]): Dictionary containing settings to update
            
        Returns:
            bool: True if settings were updated successfully, False otherwise
        """
        try:
            # Determine what settings are being updated
            if "pool" in settings:
                return await self._update_pool_settings(settings["pool"])
            elif "fan" in settings:
                return await self._update_fan_settings(settings["fan"])
            elif "system" in settings:
                return await self._update_system_settings(settings["system"])
            else:
                logger.warning(f"No recognized settings to update for Magic Miner at {self.ip_address}")
                return False
        except MinerConnectionError as e:
            logger.error(f"Connection error updating settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'connection_error'
            })
            return False
        except ValidationError as e:
            logger.error(f"Validation error updating settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'validation_error'
            })
            return False
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error updating settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'system_error',
                'error': str(e)
            })
            return False
    
    def get_supported_features(self) -> List[str]:
        """
        Get a list of features supported by the Magic Miner.
        
        Returns:
            List[str]: List of feature identifiers
        """
        return [
            "restart",
            "update_settings",
            "fan_control",
            "pool_configuration",
            "basic_metrics"
        ]
    
    def get_miner_type(self) -> str:
        """
        Get the type of miner.
        
        Returns:
            str: Miner type identifier
        """
        return "Magic Miner"
    
    def get_last_updated(self) -> Optional[datetime]:
        """
        Get the timestamp of the last successful data update.
        
        Returns:
            Optional[datetime]: Timestamp of last update or None if never updated
        """
        return self.last_updated
    
    async def _extract_status_data(self, html: str) -> Dict[str, Any]:
        """
        Extract status data from the HTML of the status page.
        
        Args:
            html (str): HTML content of the status page
            
        Returns:
            Dict[str, Any]: Extracted status data
        """
        status_data = {}
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract hashrate
            hashrate_element = soup.select_one('.hashrate, #hashrate, [data-id="hashrate"]')
            if hashrate_element:
                hashrate_text = hashrate_element.text.strip()
                hashrate_value = self._parse_hashrate(hashrate_text)
                status_data["hashrate"] = hashrate_value
            
            # Extract temperature
            temp_element = soup.select_one('.temperature, #temperature, [data-id="temperature"]')
            if temp_element:
                temp_text = temp_element.text.strip()
                temp_value = self._parse_temperature(temp_text)
                status_data["temperature"] = temp_value
            
            # Extract fan speed
            fan_element = soup.select_one('.fan, #fan, [data-id="fan"]')
            if fan_element:
                fan_text = fan_element.text.strip()
                fan_value = self._parse_percentage(fan_text)
                status_data["fan_speed"] = fan_value
            
            # Extract shares information
            shares_element = soup.select_one('.shares, #shares, [data-id="shares"]')
            if shares_element:
                shares_text = shares_element.text.strip()
                accepted, rejected = self._parse_shares(shares_text)
                status_data["shares_accepted"] = accepted
                status_data["shares_rejected"] = rejected
            
            # Extract uptime if available
            uptime_element = soup.select_one('.uptime, #uptime, [data-id="uptime"]')
            if uptime_element:
                uptime_text = uptime_element.text.strip()
                uptime_value = self._parse_uptime(uptime_text)
                status_data["uptime"] = uptime_value
        except MinerDataError as e:
            logger.error(f"Data parsing error extracting status data from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
        except Exception as e:
            logger.error(f"Unexpected error extracting status data from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'unexpected_error',
                'error': str(e)
            })
        
        return status_data
    
    async def _extract_metrics_data(self, html: str) -> Dict[str, Any]:
        """
        Extract metrics data from the HTML of the stats page.
        
        Args:
            html (str): HTML content of the stats page
            
        Returns:
            Dict[str, Any]: Extracted metrics data
        """
        metrics = {}
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract detailed metrics if available
            # This is highly dependent on the actual structure of the Magic Miner web interface
            
            # Extract hashrate metrics
            hashrate_elements = soup.select('.hashrate-item, .hashrate-data')
            if hashrate_elements:
                hashrate_data = {}
                for element in hashrate_elements:
                    label = element.select_one('.label, .name')
                    value = element.select_one('.value, .data')
                    if label and value:
                        key = label.text.strip().lower().replace(' ', '_')
                        hashrate_data[key] = self._parse_hashrate(value.text.strip())
                
                metrics["hashrate_details"] = hashrate_data
            
            # Extract temperature metrics
            temp_elements = soup.select('.temp-item, .temperature-data')
            if temp_elements:
                temp_data = {}
                for element in temp_elements:
                    label = element.select_one('.label, .name')
                    value = element.select_one('.value, .data')
                    if label and value:
                        key = label.text.strip().lower().replace(' ', '_')
                        temp_data[key] = self._parse_temperature(value.text.strip())
                
                metrics["temperature_details"] = temp_data
            
            # Extract power metrics
            power_elements = soup.select('.power-item, .power-data')
            if power_elements:
                power_data = {}
                for element in power_elements:
                    label = element.select_one('.label, .name')
                    value = element.select_one('.value, .data')
                    if label and value:
                        key = label.text.strip().lower().replace(' ', '_')
                        power_data[key] = self._parse_power(value.text.strip())
                
                metrics["power_details"] = power_data
            
            # Extract shares metrics
            shares_elements = soup.select('.shares-item, .shares-data')
            if shares_elements:
                shares_data = {}
                for element in shares_elements:
                    label = element.select_one('.label, .name')
                    value = element.select_one('.value, .data')
                    if label and value:
                        key = label.text.strip().lower().replace(' ', '_')
                        if "accepted" in key:
                            shares_data["accepted"] = int(self._extract_number(value.text.strip()))
                        elif "rejected" in key:
                            shares_data["rejected"] = int(self._extract_number(value.text.strip()))
                        elif "rate" in key:
                            shares_data["rate"] = self._parse_percentage(value.text.strip())
                
                metrics["shares_details"] = shares_data
        except MinerDataError as e:
            logger.error(f"Data parsing error extracting metrics data from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
        except Exception as e:
            logger.error(f"Unexpected error extracting metrics data from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'unexpected_error',
                'error': str(e)
            })
        
        # If we couldn't extract detailed metrics, fall back to basic status data
        if not metrics:
            basic_status = await self._extract_status_data(html)
            metrics.update(basic_status)
        
        return metrics
    
    async def _extract_device_info(self, html: str) -> Dict[str, Any]:
        """
        Extract device information from the HTML.
        
        Args:
            html (str): HTML content
            
        Returns:
            Dict[str, Any]: Extracted device information
        """
        device_info = {
            "type": "Magic Miner",
            "model": "BG02"  # Default model
        }
        
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract model information
            model_element = soup.select_one('.model, #model, [data-id="model"]')
            if model_element:
                model_text = model_element.text.strip()
                if "BG02" in model_text:
                    device_info["model"] = "BG02"
                else:
                    device_info["model"] = model_text
            
            # Extract firmware version
            firmware_element = soup.select_one('.firmware, #firmware, [data-id="firmware"]')
            if firmware_element:
                device_info["firmware_version"] = firmware_element.text.strip()
            
            # Extract MAC address if available
            mac_element = soup.select_one('.mac, #mac, [data-id="mac"]')
            if mac_element:
                device_info["mac_address"] = mac_element.text.strip()
            
            # Extract hostname if available
            hostname_element = soup.select_one('.hostname, #hostname, [data-id="hostname"]')
            if hostname_element:
                device_info["hostname"] = hostname_element.text.strip()
        except MinerDataError as e:
            logger.error(f"Data parsing error extracting device info from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
        except Exception as e:
            logger.error(f"Unexpected error extracting device info from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'unexpected_error',
                'error': str(e)
            })
        
        return device_info
    
    async def _extract_pool_info(self, html: str) -> List[Dict[str, Any]]:
        """
        Extract pool information from the HTML of the pool configuration page.
        
        Args:
            html (str): HTML content of the pool page
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing pool information
        """
        pools = []
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Look for pool configuration forms or tables
            pool_forms = soup.select('form[action*="pool"], #pool-config, .pool-config')
            
            if pool_forms:
                for form in pool_forms:
                    pool_info = {}
                    
                    # Extract URL
                    url_input = form.select_one('input[name*="url"], input[name*="pool"], #pool-url')
                    if url_input and url_input.get('value'):
                        pool_info["url"] = url_input.get('value')
                    
                    # Extract user
                    user_input = form.select_one('input[name*="user"], input[name*="worker"], #pool-user')
                    if user_input and user_input.get('value'):
                        pool_info["user"] = user_input.get('value')
                    
                    # Extract password if available
                    pass_input = form.select_one('input[name*="pass"], #pool-pass')
                    if pass_input and pass_input.get('value'):
                        pool_info["pass"] = pass_input.get('value')
                    
                    # Extract status if available
                    status_element = form.select_one('.status, #status, [data-id="status"]')
                    if status_element:
                        pool_info["status"] = status_element.text.strip()
                    
                    if "url" in pool_info:  # Only add if we have at least a URL
                        pools.append(pool_info)
            
            # If no forms found, look for pool information in tables
            if not pools:
                pool_tables = soup.select('table.pools, #pools-table, .pools-table')
                if pool_tables:
                    for table in pool_tables:
                        rows = table.select('tr')
                        for row in rows[1:]:  # Skip header row
                            cells = row.select('td')
                            if len(cells) >= 2:
                                pool_info = {
                                    "url": cells[0].text.strip() if len(cells) > 0 else "",
                                    "user": cells[1].text.strip() if len(cells) > 1 else "",
                                    "status": cells[2].text.strip() if len(cells) > 2 else ""
                                }
                                if pool_info["url"]:  # Only add if we have a URL
                                    pools.append(pool_info)
        except MinerDataError as e:
            logger.error(f"Data parsing error extracting pool info from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
        except Exception as e:
            logger.error(f"Unexpected error extracting pool info from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'unexpected_error',
                'error': str(e)
            })
        
        return pools
    
    async def _update_pool_settings(self, pool_settings: Dict[str, Any]) -> bool:
        """
        Update pool settings on the Magic Miner.
        
        Args:
            pool_settings (Dict[str, Any]): Pool settings to update
            
        Returns:
            bool: True if settings were updated successfully, False otherwise
        """
        try:
            # First get the pool configuration page to extract form details
            html = await self._http_get_text("/pool")
            if not html:
                return False
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the pool configuration form
            form = soup.select_one('form[action*="pool"]')
            if not form:
                logger.error(f"Could not find pool configuration form for Magic Miner at {self.ip_address}")
                return False
            
            # Extract form action and method
            form_action = form.get('action', '/pool')
            form_method = form.get('method', 'post').lower()
            
            # Prepare form data
            form_data = {}
            
            # Add auth token if available
            if self.auth_token:
                form_data["token"] = self.auth_token
            
            # Add pool settings
            if "url" in pool_settings:
                form_data["pool_url"] = pool_settings["url"]
            if "user" in pool_settings:
                form_data["pool_user"] = pool_settings["user"]
            if "pass" in pool_settings:
                form_data["pool_pass"] = pool_settings["pass"]
            
            # Submit form
            if form_method == "post":
                response = await self._http_post_form(form_action, form_data)
                return response is not None
            else:
                response = await self._http_get(form_action, params=form_data)
                return response is not None
        except MinerConnectionError as e:
            logger.error(f"Connection error updating pool settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'connection_error'
            })
            return False
        except MinerDataError as e:
            logger.error(f"Data parsing error updating pool settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating pool settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'unexpected_error',
                'error': str(e)
            })
            return False
    
    async def _update_fan_settings(self, fan_settings: Dict[str, Any]) -> bool:
        """
        Update fan settings on the Magic Miner.
        
        Args:
            fan_settings (Dict[str, Any]): Fan settings to update
            
        Returns:
            bool: True if settings were updated successfully, False otherwise
        """
        try:
            # First get the fan configuration page to extract form details
            html = await self._http_get_text("/fan")
            if not html:
                return False
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the fan configuration form
            form = soup.select_one('form[action*="fan"]')
            if not form:
                logger.error(f"Could not find fan configuration form for Magic Miner at {self.ip_address}")
                return False
            
            # Extract form action and method
            form_action = form.get('action', '/fan')
            form_method = form.get('method', 'post').lower()
            
            # Prepare form data
            form_data = {}
            
            # Add auth token if available
            if self.auth_token:
                form_data["token"] = self.auth_token
            
            # Add fan settings
            if "speed" in fan_settings:
                form_data["fan_speed"] = str(fan_settings["speed"])
            if "mode" in fan_settings:
                form_data["fan_mode"] = fan_settings["mode"]
            
            # Submit form
            if form_method == "post":
                response = await self._http_post_form(form_action, form_data)
                return response is not None
            else:
                response = await self._http_get(form_action, params=form_data)
                return response is not None
        except MinerConnectionError as e:
            logger.error(f"Connection error updating fan settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'connection_error'
            })
            return False
        except MinerDataError as e:
            logger.error(f"Data parsing error updating fan settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating fan settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'unexpected_error',
                'error': str(e)
            })
            return False
    
    async def _update_system_settings(self, system_settings: Dict[str, Any]) -> bool:
        """
        Update system settings on the Magic Miner.
        
        Args:
            system_settings (Dict[str, Any]): System settings to update
            
        Returns:
            bool: True if settings were updated successfully, False otherwise
        """
        try:
            # First get the system configuration page to extract form details
            html = await self._http_get_text("/system")
            if not html:
                return False
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the system configuration form
            form = soup.select_one('form[action*="system"]')
            if not form:
                logger.error(f"Could not find system configuration form for Magic Miner at {self.ip_address}")
                return False
            
            # Extract form action and method
            form_action = form.get('action', '/system')
            form_method = form.get('method', 'post').lower()
            
            # Prepare form data
            form_data = {}
            
            # Add auth token if available
            if self.auth_token:
                form_data["token"] = self.auth_token
            
            # Add system settings
            for key, value in system_settings.items():
                form_data[key] = str(value)
            
            # Submit form
            if form_method == "post":
                response = await self._http_post_form(form_action, form_data)
                return response is not None
            else:
                response = await self._http_get(form_action, params=form_data)
                return response is not None
        except MinerConnectionError as e:
            logger.error(f"Connection error updating system settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'connection_error'
            })
            return False
        except MinerDataError as e:
            logger.error(f"Data parsing error updating system settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating system settings for Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'unexpected_error',
                'error': str(e)
            })
            return False
    
    def _extract_auth_token(self, html: str) -> Optional[str]:
        """
        Extract authentication token from HTML.
        
        Args:
            html (str): HTML content
            
        Returns:
            Optional[str]: Authentication token or None if not found
        """
        try:
            # Look for token in meta tags
            soup = BeautifulSoup(html, 'html.parser')
            meta_token = soup.select_one('meta[name="csrf-token"]')
            if meta_token and meta_token.get('content'):
                return meta_token.get('content')
            
            # Look for token in hidden form fields
            hidden_token = soup.select_one('input[name="token"], input[name="csrf_token"], input[name="_token"]')
            if hidden_token and hidden_token.get('value'):
                return hidden_token.get('value')
            
            # Look for token in JavaScript
            token_match = re.search(r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
            if token_match:
                return token_match.group(1)
            
            return None
        except MinerDataError as e:
            logger.error(f"Data parsing error extracting auth token from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'data_error'
            })
            return None
        except (RuntimeError, MemoryError) as e:
            logger.error(f"System error extracting auth token from Magic Miner", {
                'ip_address': self.ip_address,
                'error_type': 'system_error',
                'error': str(e)
            })
            return None
    
    def _parse_hashrate(self, text: str) -> float:
        """
        Parse hashrate from text.
        
        Args:
            text (str): Text containing hashrate
            
        Returns:
            float: Hashrate in H/s
        """
        try:
            # Extract number and unit
            match = re.search(r'([\d.]+)\s*([KMGT]?H/s)', text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).upper()
                
                # Convert to H/s
                if unit.startswith('K'):
                    return value * 1000
                elif unit.startswith('M'):
                    return value * 1000000
                elif unit.startswith('G'):
                    return value * 1000000000
                elif unit.startswith('T'):
                    return value * 1000000000000
                else:
                    return value
            
            # If no unit, just extract number
            return float(self._extract_number(text))
        except Exception:
            return 0.0
    
    def _parse_temperature(self, text: str) -> float:
        """
        Parse temperature from text.
        
        Args:
            text (str): Text containing temperature
            
        Returns:
            float: Temperature in Celsius
        """
        try:
            # Extract number and unit
            match = re.search(r'([\d.]+)\s*([CF°])', text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).upper()
                
                # Convert to Celsius if needed
                if unit == 'F':
                    return (value - 32) * 5/9
                else:
                    return value
            
            # If no unit, just extract number and assume Celsius
            return float(self._extract_number(text))
        except Exception:
            return 0.0
    
    def _parse_percentage(self, text: str) -> float:
        """
        Parse percentage from text.
        
        Args:
            text (str): Text containing percentage
            
        Returns:
            float: Percentage as float
        """
        try:
            # Extract number and percentage sign
            match = re.search(r'([\d.]+)\s*%', text)
            if match:
                return float(match.group(1))
            
            # If no percentage sign, just extract number
            return float(self._extract_number(text))
        except Exception:
            return 0.0
    
    def _parse_shares(self, text: str) -> tuple:
        """
        Parse shares information from text.
        
        Args:
            text (str): Text containing shares information
            
        Returns:
            tuple: (accepted_shares, rejected_shares)
        """
        try:
            # Look for pattern like "123/4" or "Accepted: 123, Rejected: 4"
            ratio_match = re.search(r'(\d+)\s*\/\s*(\d+)', text)
            if ratio_match:
                return int(ratio_match.group(1)), int(ratio_match.group(2))
            
            # Look for separate accepted and rejected values
            accepted_match = re.search(r'accepted:?\s*(\d+)', text, re.IGNORECASE)
            rejected_match = re.search(r'rejected:?\s*(\d+)', text, re.IGNORECASE)
            
            accepted = int(accepted_match.group(1)) if accepted_match else 0
            rejected = int(rejected_match.group(1)) if rejected_match else 0
            
            return accepted, rejected
        except Exception:
            return 0, 0
    
    def _parse_uptime(self, text: str) -> int:
        """
        Parse uptime from text.
        
        Args:
            text (str): Text containing uptime
            
        Returns:
            int: Uptime in seconds
        """
        try:
            # Look for days, hours, minutes, seconds
            days = hours = minutes = seconds = 0
            
            days_match = re.search(r'(\d+)\s*d', text, re.IGNORECASE)
            if days_match:
                days = int(days_match.group(1))
            
            hours_match = re.search(r'(\d+)\s*h', text, re.IGNORECASE)
            if hours_match:
                hours = int(hours_match.group(1))
            
            minutes_match = re.search(r'(\d+)\s*m(?!s)', text, re.IGNORECASE)
            if minutes_match:
                minutes = int(minutes_match.group(1))
            
            seconds_match = re.search(r'(\d+)\s*s', text, re.IGNORECASE)
            if seconds_match:
                seconds = int(seconds_match.group(1))
            
            return days * 86400 + hours * 3600 + minutes * 60 + seconds
        except Exception:
            return 0
    
    def _parse_power(self, text: str) -> float:
        """
        Parse power from text.
        
        Args:
            text (str): Text containing power
            
        Returns:
            float: Power in watts
        """
        try:
            # Extract number and unit
            match = re.search(r'([\d.]+)\s*([KM]?W)', text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).upper()
                
                # Convert to watts
                if unit.startswith('K'):
                    return value * 1000
                elif unit.startswith('M'):
                    return value * 1000000
                else:
                    return value
            
            # If no unit, just extract number and assume watts
            return float(self._extract_number(text))
        except Exception:
            return 0.0
    
    def _extract_number(self, text: str) -> str:
        """
        Extract the first number from text.
        
        Args:
            text (str): Text containing a number
            
        Returns:
            str: Extracted number as string
        """
        match = re.search(r'[\d.]+', text)
        if match:
            return match.group(0)
        return "0"