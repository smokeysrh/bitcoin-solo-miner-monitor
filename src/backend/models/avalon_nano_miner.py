"""
Avalon Nano Miner Implementation

This module implements the MinerInterface for Avalon Nano miners using the cgminer API.
"""

import asyncio
import json
import logging
import re
import socket
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.backend.models.miner_interface import MinerInterface
from config.app_config import CONNECTION_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY

logger = logging.getLogger(__name__)


class AvalonNanoMiner(MinerInterface):
    """
    Implementation of the MinerInterface for Avalon Nano miners.
    
    The Avalon Nano miner uses the cgminer API over TCP port 4028.
    """
    
    def __init__(self, ip_address: str, port: int = 4028):
        """
        Initialize a new AvalonNanoMiner instance.
        
        Args:
            ip_address (str): IP address of the Avalon Nano miner
            port (int, optional): Port number for cgminer API. Defaults to 4028.
        """
        self.ip_address = ip_address
        self.port = port
        self.connected = False
        self.last_updated = None
        self.device_info = {}
        
    async def connect(self) -> bool:
        """
        Establish connection to the Avalon Nano miner.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Test connection by fetching summary
            summary = await self._send_command("summary")
            if summary and "STATUS" in summary and summary["STATUS"][0]["STATUS"] == "S":
                self.connected = True
                # Get device info
                self.device_info = await self._get_device_details()
                logger.info(f"Connected to Avalon Nano miner at {self.ip_address}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Avalon Nano miner at {self.ip_address}: {str(e)}")
            return False
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the Avalon Nano miner.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        self.connected = False
        logger.info(f"Disconnected from Avalon Nano miner at {self.ip_address}")
        return True
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Avalon Nano miner.
        
        Returns:
            Dict[str, Any]: Dictionary containing miner status information
        """
        status_data = {}
        
        try:
            # Get summary data
            summary = await self._send_command("summary")
            if summary and "SUMMARY" in summary:
                summary_data = summary["SUMMARY"][0]
                status_data.update({
                    "online": True,
                    "hashrate": summary_data.get("MHS av", 0) * 1000000,  # Convert to H/s
                    "uptime": summary_data.get("Elapsed", 0),
                    "shares_accepted": summary_data.get("Accepted", 0),
                    "shares_rejected": summary_data.get("Rejected", 0),
                    "hardware_errors": summary_data.get("Hardware Errors", 0),
                    "utility": summary_data.get("Utility", 0),
                })
                
                # Get device details for temperature and other info
                device_details = await self._get_device_details()
                if device_details:
                    status_data.update(device_details)
                
                # Update last updated timestamp
                self.last_updated = datetime.now()
            else:
                status_data["online"] = False
                
            return status_data
        except Exception as e:
            logger.error(f"Error getting status from Avalon Nano miner at {self.ip_address}: {str(e)}")
            return {"online": False, "error": str(e)}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get the current performance metrics of the Avalon Nano miner.
        
        Returns:
            Dict[str, Any]: Dictionary containing miner metrics
        """
        try:
            # Get detailed metrics
            stats = await self._send_command("stats")
            summary = await self._send_command("summary")
            
            if not stats or not summary:
                return {}
            
            metrics = {}
            
            # Extract metrics from summary
            if "SUMMARY" in summary:
                summary_data = summary["SUMMARY"][0]
                metrics.update({
                    "hashrate": {
                        "current": summary_data.get("MHS 5s", 0) * 1000000,  # Convert to H/s
                        "average": summary_data.get("MHS av", 0) * 1000000,   # Convert to H/s
                    },
                    "shares": {
                        "accepted": summary_data.get("Accepted", 0),
                        "rejected": summary_data.get("Rejected", 0),
                        "hardware_errors": summary_data.get("Hardware Errors", 0),
                        "utility": summary_data.get("Utility", 0),
                        "work_utility": summary_data.get("Work Utility", 0),
                    },
                    "difficulty_accepted": summary_data.get("Difficulty Accepted", 0),
                    "difficulty_rejected": summary_data.get("Difficulty Rejected", 0),
                    "best_share": summary_data.get("Best Share", 0),
                })
            
            # Extract additional metrics from stats by parsing MM ID0 string
            if "STATS" in stats:
                for stat in stats["STATS"]:
                    # Parse the MM ID0 string for temperature, fan, and other metrics
                    if "MM ID0" in stat:
                        parsed_metrics = self._parse_mm_id_string(stat["MM ID0"])
                        if "temperature" in parsed_metrics:
                            metrics["temperature"] = parsed_metrics["temperature"]
                        if "fan_speed" in parsed_metrics:
                            metrics["fan_speed"] = parsed_metrics["fan_speed"]
                        if "fan_rpm" in parsed_metrics:
                            metrics["fan_rpm"] = parsed_metrics["fan_rpm"]
                        if "frequency" in parsed_metrics:
                            metrics["frequency"] = parsed_metrics["frequency"]
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting metrics from Avalon Nano miner at {self.ip_address}: {str(e)}")
            return {}
    
    async def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the Avalon Nano miner device.
        
        Returns:
            Dict[str, Any]: Dictionary containing device information
        """
        if not self.device_info:
            self.device_info = await self._get_device_details()
        
        # Get version info to identify device type
        try:
            version = await self._send_command("version")
            if version and "VERSION" in version:
                version_data = version["VERSION"][0]
                
                # Use correct field names from cgminer API
                product = version_data.get("PROD", "")      # e.g., "Avalonnano"
                model_name = version_data.get("MODEL", "")  # e.g., "nano3"
                hw_type = version_data.get("HWTYPE", "")    # e.g., "PMMv1_X1"
                
                # Check if this is actually an Avalon device
                if "avalon" in product.lower():
                    device_type = "Avalon Nano"
                    # Build a descriptive model name
                    if model_name:
                        model = f"Avalon Nano {model_name.upper()}"
                    else:
                        model = "Avalon Nano"
                    logger.info(f"Detected {model} at {self.ip_address}")
                else:
                    # It's a cgminer device, but not Avalon
                    device_type = "cgminer Device"
                    model = product if product else "Unknown"
                    logger.info(f"Detected cgminer device (not Avalon): {product} at {self.ip_address}")
            else:
                device_type = "cgminer Device"
                model = "Unknown"
        except Exception as e:
            logger.debug(f"Error getting version info: {e}")
            device_type = "cgminer Device"
            model = "Unknown"
        
        # Build device info
        device_info = {
            "type": device_type,
            "model": model,
            "api": "cgminer",
            "cgminer_version": self.device_info.get("cgminer_version", "Unknown"),
            "api_version": self.device_info.get("api_version", "Unknown"),
            "firmware_version": self.device_info.get("firmware_version", "Unknown"),
        }
        
        # Add additional details from device_info
        device_info.update(self.device_info)
        
        return device_info
    
    async def get_pool_info(self) -> List[Dict[str, Any]]:
        """
        Get information about the mining pools configured on the Avalon Nano miner.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing pool information
        """
        try:
            pools = await self._send_command("pools")
            if not pools or "POOLS" not in pools:
                return []
                
            pool_info = []
            for pool in pools["POOLS"]:
                pool_info.append({
                    "url": pool.get("URL", ""),
                    "user": pool.get("User", ""),
                    "status": pool.get("Status", ""),
                    "priority": pool.get("Priority", 0),
                    "quota": pool.get("Quota", 0),
                    "accepted": pool.get("Accepted", 0),
                    "rejected": pool.get("Rejected", 0),
                    "works": pool.get("Works", 0),
                    "difficulty": pool.get("Diff", 0),
                    "is_active": pool.get("Stratum Active", False),
                    "last_share_time": pool.get("Last Share Time", 0),
                })
                
            return pool_info
        except Exception as e:
            logger.error(f"Error getting pool info from Avalon Nano miner at {self.ip_address}: {str(e)}")
            return []
    
    async def restart(self) -> bool:
        """
        Restart the Avalon Nano miner.
        
        Returns:
            bool: True if restart command was successful, False otherwise
        """
        try:
            response = await self._send_command("restart")
            return response is not None and "STATUS" in response and response["STATUS"][0]["STATUS"] == "S"
        except Exception as e:
            logger.error(f"Error restarting Avalon Nano miner at {self.ip_address}: {str(e)}")
            return False
    
    async def update_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Update Avalon Nano miner settings.
        
        Args:
            settings (Dict[str, Any]): Dictionary containing settings to update
            
        Returns:
            bool: True if settings were updated successfully, False otherwise
        """
        try:
            success = True
            
            # Handle different settings
            if "fan" in settings:
                fan_response = await self._send_command(f"setfan,{settings['fan']}")
                success = success and fan_response is not None
                
            if "frequency" in settings:
                freq_response = await self._send_command(f"setfreq,{settings['frequency']}")
                success = success and freq_response is not None
            
            # Add pool if provided
            if "pool_url" in settings and "pool_user" in settings:
                pool_url = settings["pool_url"]
                pool_user = settings["pool_user"]
                pool_pass = settings.get("pool_pass", "x")
                pool_response = await self._send_command(f"addpool,{pool_url},{pool_user},{pool_pass}")
                success = success and pool_response is not None
            
            return success
        except Exception as e:
            logger.error(f"Error updating settings for Avalon Nano miner at {self.ip_address}: {str(e)}")
            return False
    
    def get_supported_features(self) -> List[str]:
        """
        Get a list of features supported by the Avalon Nano miner.
        
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
        return "Avalon Nano"
    
    def get_last_updated(self) -> Optional[datetime]:
        """
        Get the timestamp of the last successful data update.
        
        Returns:
            Optional[datetime]: Timestamp of last update or None if never updated
        """
        return self.last_updated
    
    def _parse_mm_id_string(self, mm_id_string: str) -> Dict[str, Any]:
        """
        Parse the MM ID0 string from Avalon Nano stats to extract metrics.
        
        Avalon Nano miners embed critical metrics in a proprietary string format
        within the "MM ID0" field. This method extracts temperature, fan speed,
        frequency, and other metrics using regex patterns.
        
        Example string:
        "...Temp[38] OTemp[38] TMax[87] TAvg[85]...Fan1[2430] FanR[32%]...MGHS[3090.53]..."
        
        Args:
            mm_id_string (str): The MM ID0 string from cgminer stats response
            
        Returns:
            Dict[str, Any]: Dictionary containing parsed metrics
        """
        parsed_data = {}
        
        try:
            # Extract current temperature (Temp[XX])
            temp_match = re.search(r'Temp\[(\d+)\]', mm_id_string)
            if temp_match:
                parsed_data['temperature'] = int(temp_match.group(1))
            
            # Extract average temperature (TAvg[XX])
            tavg_match = re.search(r'TAvg\[(\d+)\]', mm_id_string)
            if tavg_match:
                parsed_data['temperature_avg'] = int(tavg_match.group(1))
            
            # Extract max temperature (TMax[XX])
            tmax_match = re.search(r'TMax\[(\d+)\]', mm_id_string)
            if tmax_match:
                parsed_data['temperature_max'] = int(tmax_match.group(1))
            
            # Extract fan RPM (Fan1[XXXX])
            fan_rpm_match = re.search(r'Fan1\[(\d+)\]', mm_id_string)
            if fan_rpm_match:
                parsed_data['fan_rpm'] = int(fan_rpm_match.group(1))
            
            # Extract fan percentage (FanR[XX%])
            fan_percent_match = re.search(r'FanR\[(\d+)%\]', mm_id_string)
            if fan_percent_match:
                parsed_data['fan_speed'] = int(fan_percent_match.group(1))
            
            # Extract average hashrate in MH/s (MGHS[XXXX.XX])
            mghs_match = re.search(r'MGHS\[(\d+\.?\d*)\]', mm_id_string)
            if mghs_match:
                parsed_data['hashrate_mghs'] = float(mghs_match.group(1))
            
            # Extract frequency (Freq[XXX.XX])
            freq_match = re.search(r'Freq\[(\d+\.?\d*)\]', mm_id_string)
            if freq_match:
                parsed_data['frequency'] = float(freq_match.group(1))
            
            # Extract hardware version (HVer[...])
            hver_match = re.search(r'HVer\[([^\]]+)\]', mm_id_string)
            if hver_match:
                parsed_data['hardware_version'] = hver_match.group(1)
            
            # Extract DNA/serial (DNA[...])
            dna_match = re.search(r'DNA\[([^\]]+)\]', mm_id_string)
            if dna_match:
                parsed_data['dna'] = dna_match.group(1)
                
        except Exception as e:
            logger.debug(f"Error parsing MM ID string: {e}")
        
        return parsed_data
    
    async def _send_command(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Send a command to the cgminer API and get the response.
        
        Args:
            command (str): Command to send
            
        Returns:
            Optional[Dict[str, Any]]: Response data as dictionary or None if request failed
        """
        for attempt in range(RETRY_ATTEMPTS):
            try:
                # Create socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(CONNECTION_TIMEOUT)
                
                # Connect to the miner
                sock.connect((self.ip_address, self.port))
                
                # Prepare command
                if "," in command:
                    # This is a command with parameters
                    cmd_parts = command.split(",")
                    base_cmd = cmd_parts[0]
                    params = cmd_parts[1:]
                    payload = {"command": base_cmd, "parameter": params}
                else:
                    # Simple command without parameters
                    payload = {"command": command}
                
                # Send command
                sock.send(json.dumps(payload).encode('utf-8'))
                
                # Receive response
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if response.endswith(b'\x00'):
                        break
                
                # Close socket
                sock.close()
                
                # Parse response
                if response:
                    # Remove null bytes and decode
                    response_str = response.decode('utf-8').replace('\x00', '')
                    return json.loads(response_str)
                
                return None
            except socket.timeout:
                logger.warning(f"Timeout connecting to {self.ip_address}:{self.port}, attempt {attempt + 1}/{RETRY_ATTEMPTS}")
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response from {self.ip_address}: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Error connecting to {self.ip_address}: {str(e)}")
                
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY)
                
        return None
    
    async def _get_device_details(self) -> Dict[str, Any]:
        """
        Get detailed information about the Avalon Nano device.
        
        Returns:
            Dict[str, Any]: Dictionary containing device details
        """
        try:
            # Get device details from stats
            stats = await self._send_command("stats")
            if not stats or "STATS" not in stats:
                return {}
            
            device_details = {}
            
            # Extract relevant information from stats
            for stat in stats["STATS"]:
                # Skip summary stats
                if "ID" in stat and stat["ID"] == "STATS":
                    continue
                
                # Parse the MM ID0 string which contains temperature, fan, and other metrics
                if "MM ID0" in stat:
                    parsed_metrics = self._parse_mm_id_string(stat["MM ID0"])
                    device_details.update(parsed_metrics)
                
                # Extract device information from standard fields
                if "Type" in stat:
                    device_details["model"] = stat["Type"]
                if "Elapsed" in stat:
                    device_details["uptime"] = stat["Elapsed"]
                if "Hardware Errors" in stat:
                    device_details["hardware_errors"] = stat["Hardware Errors"]
                if "Device Hardware%" in stat:
                    device_details["hardware_error_rate"] = stat["Device Hardware%"]
            
            # Get version information
            version = await self._send_command("version")
            if version and "VERSION" in version:
                version_data = version["VERSION"][0]
                device_details["cgminer_version"] = version_data.get("CGMiner", "Unknown")
                device_details["api_version"] = version_data.get("API", "Unknown")
                device_details["firmware_version"] = version_data.get("VERSION", "Unknown")
            
            return device_details
        except Exception as e:
            logger.error(f"Error getting device details from Avalon Nano miner at {self.ip_address}: {str(e)}")
            return {}