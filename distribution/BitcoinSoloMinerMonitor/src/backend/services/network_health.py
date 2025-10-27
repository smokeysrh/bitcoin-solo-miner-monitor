"""
Network Health Service

This module provides network health monitoring functionality for miners,
including latency measurement, packet loss detection, and connection uptime tracking.
"""

import asyncio
import logging
import platform
import socket
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from src.backend.utils.structured_logging import get_logger

logger = get_logger(__name__)


class NetworkHealthMonitor:
    """
    Service for monitoring network health metrics for miners.
    """
    
    def __init__(self, timeseries_storage=None):
        """
        Initialize a new NetworkHealthMonitor instance.
        
        Args:
            timeseries_storage: Optional TimeSeriesStorage instance for persisting health data
        """
        self.connection_start_times: Dict[str, datetime] = {}  # Track when miners first connected
        self.last_successful_ping: Dict[str, datetime] = {}  # Track last successful ping per miner
        self.is_windows = platform.system().lower() == 'windows'
        self.timeseries_storage = timeseries_storage
        self.polling_task = None
        self.polling_interval = 30  # Poll every 30 seconds
        self.is_running = False
        self.miner_manager = None  # Will be set by the API service
        logger.info(f"NetworkHealthMonitor initialized on {platform.system()}")
    
    async def measure_latency(self, host: str, count: int = 4) -> Optional[float]:
        """
        Measure network latency to a host using ping.
        
        Args:
            host (str): IP address or hostname to ping
            count (int): Number of ping packets to send (default: 4)
            
        Returns:
            Optional[float]: Average latency in milliseconds, or None if ping failed
        """
        try:
            # Build ping command based on OS
            if self.is_windows:
                # Windows: ping -n <count> <host>
                cmd = ['ping', '-n', str(count), host]
            else:
                # Linux/Mac: ping -c <count> <host>
                cmd = ['ping', '-c', str(count), host]
            
            logger.debug(f"Executing ping command: {' '.join(cmd)}")
            
            # Execute ping command with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for command to complete with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=10.0  # 10 second timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Ping timeout for host {host}")
                process.kill()
                return None
            
            # Parse output
            output = stdout.decode('utf-8', errors='ignore')
            
            if process.returncode != 0:
                logger.debug(f"Ping failed for {host}: {stderr.decode('utf-8', errors='ignore')}")
                return None
            
            # Parse average latency from output
            latency = self._parse_ping_output(output)
            
            if latency is not None:
                logger.debug(f"Measured latency for {host}: {latency:.2f}ms")
                self.last_successful_ping[host] = datetime.now()
            
            return latency
            
        except Exception as e:
            logger.error(f"Error measuring latency for {host}: {str(e)}")
            return None
    
    def _parse_ping_output(self, output: str) -> Optional[float]:
        """
        Parse ping output to extract average latency.
        
        Args:
            output (str): Ping command output
            
        Returns:
            Optional[float]: Average latency in milliseconds, or None if parsing failed
        """
        try:
            if self.is_windows:
                # Windows format: "Average = XXXms" or "Average = XXXms"
                for line in output.split('\n'):
                    if 'Average' in line or 'average' in line:
                        # Extract number before 'ms'
                        parts = line.split('=')
                        if len(parts) >= 2:
                            avg_part = parts[-1].strip()
                            # Remove 'ms' and extract number
                            avg_str = avg_part.replace('ms', '').strip()
                            return float(avg_str)
            else:
                # Linux/Mac format: "rtt min/avg/max/mdev = X.XXX/Y.YYY/Z.ZZZ/W.WWW ms"
                for line in output.split('\n'):
                    if 'rtt' in line.lower() or 'round-trip' in line.lower():
                        parts = line.split('=')
                        if len(parts) >= 2:
                            values = parts[1].strip().split('/')
                            if len(values) >= 2:
                                # Return average (second value)
                                return float(values[1])
            
            logger.debug(f"Could not parse latency from ping output: {output[:200]}")
            return None
            
        except (ValueError, IndexError) as e:
            logger.debug(f"Error parsing ping output: {str(e)}")
            return None
    
    async def measure_packet_loss(self, host: str, count: int = 10) -> Optional[float]:
        """
        Measure packet loss percentage to a host.
        
        Args:
            host (str): IP address or hostname to ping
            count (int): Number of ping packets to send (default: 10)
            
        Returns:
            Optional[float]: Packet loss percentage (0-100), or None if measurement failed
        """
        try:
            # Build ping command based on OS
            if self.is_windows:
                cmd = ['ping', '-n', str(count), host]
            else:
                cmd = ['ping', '-c', str(count), host]
            
            logger.debug(f"Measuring packet loss for {host} with {count} packets")
            
            # Execute ping command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for command to complete with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=15.0  # 15 second timeout for packet loss test
                )
            except asyncio.TimeoutError:
                logger.warning(f"Packet loss measurement timeout for host {host}")
                process.kill()
                return None
            
            # Parse output
            output = stdout.decode('utf-8', errors='ignore')
            
            # Parse packet loss from output
            packet_loss = self._parse_packet_loss(output)
            
            if packet_loss is not None:
                logger.debug(f"Measured packet loss for {host}: {packet_loss:.1f}%")
            
            return packet_loss
            
        except Exception as e:
            logger.error(f"Error measuring packet loss for {host}: {str(e)}")
            return None
    
    def _parse_packet_loss(self, output: str) -> Optional[float]:
        """
        Parse ping output to extract packet loss percentage.
        
        Args:
            output (str): Ping command output
            
        Returns:
            Optional[float]: Packet loss percentage (0-100), or None if parsing failed
        """
        try:
            # Look for packet loss line in output
            # Windows: "Packets: Sent = X, Received = Y, Lost = Z (W% loss)"
            # Linux/Mac: "X packets transmitted, Y received, Z% packet loss"
            
            for line in output.split('\n'):
                line_lower = line.lower()
                
                if 'loss' in line_lower or 'lost' in line_lower:
                    # Extract percentage
                    if '%' in line:
                        # Find the number before '%'
                        parts = line.split('%')[0].split()
                        if parts:
                            try:
                                # Get the last part before '%' which should be the percentage
                                loss_str = parts[-1].replace('(', '').replace(',', '')
                                return float(loss_str)
                            except ValueError:
                                continue
            
            logger.debug(f"Could not parse packet loss from ping output: {output[:200]}")
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing packet loss: {str(e)}")
            return None
    
    def register_connection(self, miner_id: str):
        """
        Register a miner connection to start tracking uptime.
        
        Args:
            miner_id (str): ID of the miner
        """
        if miner_id not in self.connection_start_times:
            self.connection_start_times[miner_id] = datetime.now()
            logger.info(f"Registered connection for miner {miner_id}")
    
    def unregister_connection(self, miner_id: str):
        """
        Unregister a miner connection.
        
        Args:
            miner_id (str): ID of the miner
        """
        if miner_id in self.connection_start_times:
            del self.connection_start_times[miner_id]
            logger.info(f"Unregistered connection for miner {miner_id}")
        
        if miner_id in self.last_successful_ping:
            del self.last_successful_ping[miner_id]
    
    def get_connection_uptime(self, miner_id: str) -> Optional[int]:
        """
        Get connection uptime for a miner in seconds.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Optional[int]: Uptime in seconds, or None if miner not registered
        """
        if miner_id not in self.connection_start_times:
            return None
        
        start_time = self.connection_start_times[miner_id]
        uptime_seconds = int((datetime.now() - start_time).total_seconds())
        
        return uptime_seconds
    
    async def get_network_health(self, miner_id: str, host: str) -> Dict[str, Any]:
        """
        Get comprehensive network health metrics for a miner, including pool latency.
        
        Args:
            miner_id (str): ID of the miner
            host (str): IP address or hostname of the miner
            
        Returns:
            Dict[str, Any]: Network health metrics including miner latency, packet loss, 
                           uptime, pool latency, total path latency, and status
        """
        try:
            # Register connection if not already registered
            if miner_id not in self.connection_start_times:
                self.register_connection(miner_id)
            
            # Measure miner latency (quick test with 3 pings)
            miner_latency = await self.measure_latency(host, count=3)
            
            # Measure packet loss (use 5 pings for faster results)
            packet_loss = await self.measure_packet_loss(host, count=5)
            
            # Get connection uptime
            uptime = self.get_connection_uptime(miner_id)
            
            # Calculate jitter (variation in latency) - simplified version
            # In a full implementation, this would track multiple latency measurements
            jitter = None
            if miner_latency is not None:
                # Estimate jitter as 10% of latency (simplified)
                jitter = miner_latency * 0.1
            
            # Get pool information and measure pool latency
            pool_latency_data = None
            pool_latency_value = None
            total_path_latency = None
            
            pool_info = await self.get_pool_info_from_miner(miner_id)
            
            if pool_info:
                # Find the active pool (or use the first one if none marked as active)
                active_pool = next((p for p in pool_info if p.get('is_active')), None)
                if not active_pool and pool_info:
                    active_pool = pool_info[0]
                
                if active_pool:
                    pool_url = active_pool.get('url', '')
                    pool_port = active_pool.get('port')
                    
                    if pool_url:
                        # Measure pool latency
                        pool_latency_value = await self.measure_pool_latency(pool_url, pool_port)
                        
                        # Calculate pool health status
                        pool_status = self._calculate_pool_health_status(pool_latency_value)
                        
                        pool_latency_data = {
                            "url": pool_url,
                            "port": pool_port,
                            "latency_ms": pool_latency_value,
                            "status": pool_status
                        }
                        
                        # Calculate total path latency (miner + pool)
                        if miner_latency is not None and pool_latency_value is not None:
                            total_path_latency = miner_latency + pool_latency_value
                    else:
                        logger.debug(f"Miner {miner_id} has pool configuration but no URL specified")
                else:
                    logger.debug(f"Miner {miner_id} has pool info but no active pool found")
            else:
                logger.debug(f"Miner {miner_id} has no pool configuration available")
            
            # Determine overall health status (considering both miner and pool latency)
            status = self._calculate_health_status(miner_latency, packet_loss, pool_latency_value)
            
            return {
                "miner_id": miner_id,
                "miner_latency_ms": miner_latency,
                "packet_loss_percent": packet_loss if packet_loss is not None else 0.0,
                "uptime_seconds": uptime,
                "jitter_ms": jitter,
                "pool_latency": pool_latency_data,
                "total_path_latency_ms": total_path_latency,
                "status": status,
                "last_measured": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting network health for miner {miner_id}: {str(e)}")
            return {
                "miner_id": miner_id,
                "miner_latency_ms": None,
                "packet_loss_percent": None,
                "uptime_seconds": self.get_connection_uptime(miner_id),
                "jitter_ms": None,
                "pool_latency": None,
                "total_path_latency_ms": None,
                "status": "unknown",
                "last_measured": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _calculate_health_status(
        self, 
        latency: Optional[float], 
        packet_loss: Optional[float],
        pool_latency: Optional[float] = None
    ) -> str:
        """
        Calculate overall health status based on latency and packet loss.
        
        Args:
            latency (Optional[float]): Miner latency in milliseconds
            packet_loss (Optional[float]): Packet loss percentage
            pool_latency (Optional[float]): Pool latency in milliseconds
            
        Returns:
            str: Health status ('healthy', 'degraded', 'poor', or 'unknown')
        """
        # If we can't measure, status is unknown
        if latency is None and packet_loss is None:
            return "unknown"
        
        # Check for poor health conditions
        if latency is not None and latency > 200:
            return "poor"
        if packet_loss is not None and packet_loss > 5:
            return "poor"
        if pool_latency is not None and pool_latency > 200:
            return "poor"
        
        # Check for degraded health conditions
        if latency is not None and latency > 100:
            return "degraded"
        if packet_loss is not None and packet_loss > 2:
            return "degraded"
        if pool_latency is not None and pool_latency > 100:
            return "degraded"
        
        # Otherwise, health is good
        return "healthy"
    
    def _calculate_pool_health_status(self, pool_latency: Optional[float]) -> str:
        """
        Calculate pool health status based on latency thresholds.
        
        Args:
            pool_latency (Optional[float]): Pool latency in milliseconds
            
        Returns:
            str: Pool health status ('healthy', 'warning', 'critical', or 'unreachable')
        """
        if pool_latency is None:
            return "unreachable"
        
        # Critical: latency >= 200ms
        if pool_latency >= 200:
            return "critical"
        
        # Warning: latency >= 100ms
        if pool_latency >= 100:
            return "warning"
        
        # Healthy: latency < 100ms
        return "healthy"
    
    async def get_aggregate_network_health(
        self, 
        miner_health_data: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate aggregate network health statistics from multiple miners.
        
        Args:
            miner_health_data (list[Dict[str, Any]]): List of network health data for each miner
            
        Returns:
            Dict[str, Any]: Aggregate network health statistics including pool latency
        """
        if not miner_health_data:
            return {
                "average_miner_latency_ms": None,
                "average_pool_latency_ms": None,
                "average_total_path_latency_ms": None,
                "average_packet_loss_percent": None,
                "average_jitter_ms": None,
                "healthy_count": 0,
                "degraded_count": 0,
                "poor_count": 0,
                "unknown_count": 0,
                "total_miners": 0,
                "unique_pools": []
            }
        
        # Calculate averages for miner metrics
        miner_latencies = [d["miner_latency_ms"] for d in miner_health_data if d.get("miner_latency_ms") is not None]
        packet_losses = [d["packet_loss_percent"] for d in miner_health_data if d.get("packet_loss_percent") is not None]
        jitters = [d["jitter_ms"] for d in miner_health_data if d.get("jitter_ms") is not None]
        
        # Calculate averages for pool metrics
        pool_latencies = []
        total_path_latencies = []
        unique_pools_map = {}  # Track unique pools with their latencies
        
        for data in miner_health_data:
            pool_data = data.get("pool_latency")
            if pool_data and pool_data.get("latency_ms") is not None:
                pool_latencies.append(pool_data["latency_ms"])
                
                # Track unique pools
                pool_key = f"{pool_data.get('url')}:{pool_data.get('port')}"
                if pool_key not in unique_pools_map:
                    unique_pools_map[pool_key] = {
                        "url": pool_data.get("url"),
                        "port": pool_data.get("port"),
                        "latency_ms": pool_data.get("latency_ms"),
                        "status": pool_data.get("status"),
                        "miner_count": 1
                    }
                else:
                    # Update average latency for this pool
                    existing = unique_pools_map[pool_key]
                    existing["miner_count"] += 1
                    # Keep the most recent latency measurement
                    existing["latency_ms"] = pool_data.get("latency_ms")
            
            if data.get("total_path_latency_ms") is not None:
                total_path_latencies.append(data["total_path_latency_ms"])
        
        avg_miner_latency = sum(miner_latencies) / len(miner_latencies) if miner_latencies else None
        avg_pool_latency = sum(pool_latencies) / len(pool_latencies) if pool_latencies else None
        avg_total_path_latency = sum(total_path_latencies) / len(total_path_latencies) if total_path_latencies else None
        avg_packet_loss = sum(packet_losses) / len(packet_losses) if packet_losses else None
        avg_jitter = sum(jitters) / len(jitters) if jitters else None
        
        # Count status categories
        status_counts = {
            "healthy": 0,
            "degraded": 0,
            "poor": 0,
            "unknown": 0
        }
        
        for data in miner_health_data:
            status = data.get("status", "unknown")
            if status in status_counts:
                status_counts[status] += 1
        
        return {
            "average_miner_latency_ms": round(avg_miner_latency, 2) if avg_miner_latency is not None else None,
            "average_pool_latency_ms": round(avg_pool_latency, 2) if avg_pool_latency is not None else None,
            "average_total_path_latency_ms": round(avg_total_path_latency, 2) if avg_total_path_latency is not None else None,
            "average_packet_loss_percent": round(avg_packet_loss, 2) if avg_packet_loss is not None else None,
            "average_jitter_ms": round(avg_jitter, 2) if avg_jitter is not None else None,
            "healthy_count": status_counts["healthy"],
            "degraded_count": status_counts["degraded"],
            "poor_count": status_counts["poor"],
            "unknown_count": status_counts["unknown"],
            "total_miners": len(miner_health_data),
            "unique_pools": list(unique_pools_map.values())
        }
    
    def set_timeseries_storage(self, timeseries_storage):
        """
        Set the TimeSeriesStorage instance for persisting health data.
        
        Args:
            timeseries_storage: TimeSeriesStorage instance
        """
        self.timeseries_storage = timeseries_storage
        logger.info("TimeSeriesStorage set for NetworkHealthMonitor")
    
    def set_miner_manager(self, miner_manager):
        """
        Set the MinerManager instance for accessing miner information.
        
        Args:
            miner_manager: MinerManager instance
        """
        self.miner_manager = miner_manager
        logger.info("MinerManager set for NetworkHealthMonitor")
    
    async def get_pool_info_from_miner(self, miner_id: str) -> List[Dict[str, Any]]:
        """
        Get pool configuration from a miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            List[Dict[str, Any]]: List of pool configurations with URL, port, and status
                                  Returns empty list if miner has no pool configuration
        """
        try:
            if not self.miner_manager:
                logger.warning("MinerManager not set, cannot get pool info")
                return []
            
            # Get the miner instance from the manager
            async with self.miner_manager._miners_lock:
                miner = self.miner_manager.miners.get(miner_id)
            
            if not miner:
                logger.debug(f"Miner {miner_id} not found in manager")
                return []
            
            # Get pool info from the miner
            pool_info = await miner.get_pool_info()
            
            if pool_info:
                logger.debug(f"Retrieved {len(pool_info)} pool(s) for miner {miner_id}")
            else:
                logger.debug(f"No pool configuration found for miner {miner_id}")
            
            return pool_info if pool_info else []
            
        except AttributeError as e:
            # Miner doesn't have get_pool_info method
            logger.debug(f"Miner {miner_id} does not support pool info retrieval: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error getting pool info from miner {miner_id}: {str(e)}")
            return []
    
    async def _resolve_hostname(self, hostname: str) -> Optional[str]:
        """
        Resolve a hostname to an IP address using DNS.
        
        Args:
            hostname (str): Hostname to resolve
            
        Returns:
            Optional[str]: IP address or None if resolution failed
        """
        try:
            # Validate hostname
            if not hostname or not isinstance(hostname, str) or not hostname.strip():
                logger.warning("Empty or invalid hostname provided for DNS resolution")
                return None
            
            # Use asyncio's getaddrinfo for non-blocking DNS resolution
            loop = asyncio.get_event_loop()
            result = await loop.getaddrinfo(hostname, None, family=socket.AF_INET)
            
            if result:
                ip_address = result[0][4][0]
                logger.debug(f"Resolved {hostname} to {ip_address}")
                return ip_address
            
            logger.warning(f"DNS resolution returned no results for {hostname}")
            return None
            
        except socket.gaierror as e:
            # DNS resolution failed - hostname doesn't exist or DNS server unreachable
            logger.warning(f"DNS resolution failed for {hostname}: {str(e)}")
            return None
        except OSError as e:
            # Network error during DNS resolution
            logger.warning(f"Network error resolving hostname {hostname}: {str(e)}")
            return None
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error resolving hostname {hostname}: {str(e)}")
            return None
    
    async def measure_pool_latency(self, pool_url: str, pool_port: Optional[int] = None) -> Optional[float]:
        """
        Measure network latency to a mining pool or Bitcoin node.
        
        This method handles both IP addresses and hostnames, performing DNS resolution
        when necessary. It attempts ICMP ping first, and if that fails (e.g., due to
        firewall blocking), it falls back to TCP connection timing.
        
        Args:
            pool_url (str): Pool URL or hostname (can include protocol prefix)
            pool_port (Optional[int]): Pool port number (used for TCP fallback)
            
        Returns:
            Optional[float]: Latency in milliseconds, or None if measurement failed
                            (indicates unreachable pool server)
        """
        try:
            # Validate input
            if not pool_url or not isinstance(pool_url, str):
                logger.warning(f"Invalid pool URL provided: {pool_url}")
                return None
            
            # Parse the URL to extract hostname
            # Handle URLs with or without protocol prefix
            if '://' in pool_url:
                parsed = urlparse(pool_url)
                hostname = parsed.hostname or parsed.netloc
            else:
                # No protocol, treat as hostname directly
                hostname = pool_url.split(':')[0]  # Remove port if present
            
            if not hostname:
                logger.warning(f"Could not extract hostname from pool URL: {pool_url}")
                return None
            
            # Check if hostname is already an IP address
            try:
                socket.inet_aton(hostname)
                target_host = hostname
                logger.debug(f"Pool URL {pool_url} is already an IP address: {target_host}")
            except socket.error:
                # Not an IP address, need to resolve hostname
                logger.debug(f"Resolving hostname for pool: {hostname}")
                target_host = await self._resolve_hostname(hostname)
                
                if not target_host:
                    logger.warning(f"Failed to resolve pool hostname: {hostname} (DNS resolution failed)")
                    return None
            
            # Try ICMP ping first (standard latency measurement)
            latency = await self.measure_latency(target_host, count=3)
            
            if latency is not None:
                logger.debug(f"Measured pool latency via ICMP for {pool_url}: {latency:.2f}ms")
                return latency
            
            # ICMP ping failed, try TCP connection timing as fallback
            if pool_port:
                logger.debug(f"ICMP ping failed for {pool_url}, trying TCP connection timing on port {pool_port}")
                tcp_latency = await self._measure_tcp_latency(target_host, pool_port)
                
                if tcp_latency is not None:
                    logger.debug(f"Measured pool latency via TCP for {pool_url}: {tcp_latency:.2f}ms")
                    return tcp_latency
                else:
                    logger.warning(f"TCP connection failed for {pool_url}:{pool_port} (port may be blocked or server unreachable)")
            else:
                logger.debug(f"No port provided for TCP fallback, cannot measure latency for {pool_url}")
            
            logger.warning(f"All latency measurement methods failed for pool {pool_url} - server is unreachable")
            return None
            
        except ValueError as e:
            logger.error(f"Invalid pool URL format {pool_url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error measuring pool latency for {pool_url}: {str(e)}")
            return None
    
    async def _measure_tcp_latency(self, host: str, port: int, timeout: float = 5.0) -> Optional[float]:
        """
        Measure latency using TCP connection timing.
        
        This is a fallback method when ICMP ping is blocked by firewalls.
        
        Args:
            host (str): IP address or hostname
            port (int): Port number to connect to
            timeout (float): Connection timeout in seconds
            
        Returns:
            Optional[float]: Latency in milliseconds, or None if connection failed
        """
        try:
            start_time = time.time()
            
            # Attempt TCP connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            return latency_ms
            
        except asyncio.TimeoutError:
            logger.debug(f"TCP connection timeout for {host}:{port} (server may be unreachable or port blocked)")
            return None
        except ConnectionRefusedError:
            logger.debug(f"TCP connection refused for {host}:{port} (port is closed or service not running)")
            return None
        except OSError as e:
            logger.debug(f"TCP connection failed for {host}:{port}: {str(e)} (network error or firewall blocking)")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during TCP latency measurement for {host}:{port}: {str(e)}")
            return None
    
    async def start_polling(self):
        """
        Start the background polling task for network health monitoring.
        """
        if self.is_running:
            logger.warning("Network health polling is already running")
            return
        
        self.is_running = True
        self.polling_task = asyncio.create_task(self._polling_loop())
        logger.info(f"Network health polling started (interval: {self.polling_interval}s)")
    
    async def stop_polling(self):
        """
        Stop the background polling task.
        """
        if not self.is_running:
            return
        
        self.is_running = False
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Network health polling stopped")
    
    async def _polling_loop(self):
        """
        Background polling loop that measures network health for all miners.
        """
        logger.info("Network health polling loop started")
        
        while self.is_running:
            try:
                # Get all miners from the miner manager
                if not self.miner_manager:
                    logger.debug("MinerManager not set, skipping network health poll")
                    await asyncio.sleep(self.polling_interval)
                    continue
                
                miners = await self.miner_manager.get_miners()
                
                if not miners:
                    logger.debug("No miners to poll for network health")
                    await asyncio.sleep(self.polling_interval)
                    continue
                
                # Poll network health for each miner
                for miner in miners:
                    try:
                        miner_id = miner.get('id')
                        ip_address = miner.get('ip_address')
                        
                        if not miner_id or not ip_address:
                            logger.debug(f"Skipping miner with missing id or ip_address: {miner}")
                            continue
                        
                        # Get network health for this miner
                        health_data = await self.get_network_health(miner_id, ip_address)
                        
                        # Save to database if timeseries storage is available
                        if self.timeseries_storage:
                            await self.timeseries_storage.save_network_health(miner_id, health_data)
                            logger.debug(f"Saved network health for miner {miner_id}")
                        
                    except Exception as e:
                        logger.error(f"Error polling network health for miner {miner.get('id', 'unknown')}: {str(e)}")
                
                # Wait for next polling interval
                await asyncio.sleep(self.polling_interval)
                
            except asyncio.CancelledError:
                logger.info("Network health polling loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in network health polling loop: {str(e)}")
                await asyncio.sleep(self.polling_interval)
