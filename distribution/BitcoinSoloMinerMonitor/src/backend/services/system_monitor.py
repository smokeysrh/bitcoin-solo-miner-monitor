"""
System Monitor Service

This module provides system monitoring functionality for the Bitcoin Solo Miner Monitoring App.
"""

import asyncio
import logging
import os
import platform
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class SystemMonitor:
    """
    System monitoring service.
    """
    
    def __init__(self):
        """
        Initialize a new SystemMonitor instance.
        """
        self.start_time = time.time()
        self.system_info = self._get_system_info()
        self.metrics_history = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": []
        }
        self.history_max_points = 1000  # Maximum number of history points to keep
        self.history_retention = timedelta(hours=24)  # Keep history for 24 hours
    
    def _get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            Dict[str, Any]: System information
        """
        try:
            return {
                "os": {
                    "name": platform.system(),
                    "version": platform.version(),
                    "platform": platform.platform(),
                    "release": platform.release(),
                    "architecture": platform.machine()
                },
                "python": {
                    "version": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "compiler": platform.python_compiler()
                },
                "cpu": {
                    "count_physical": psutil.cpu_count(logical=False),
                    "count_logical": psutil.cpu_count(logical=True),
                    "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None
                },
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "swap_total": psutil.swap_memory().total
                },
                "disk": {
                    "partitions": [
                        {
                            "device": p.device,
                            "mountpoint": p.mountpoint,
                            "fstype": p.fstype,
                            "total": psutil.disk_usage(p.mountpoint).total
                        }
                        for p in psutil.disk_partitions()
                        if os.path.exists(p.mountpoint)  # Check if mountpoint exists
                    ]
                },
                "network": {
                    "interfaces": list(psutil.net_if_addrs().keys())
                }
            }
        except Exception as e:
            logger.error(f"Error getting system information: {str(e)}")
            return {
                "os": {"name": "Unknown", "version": "Unknown"},
                "python": {"version": "Unknown"},
                "cpu": {"count_physical": 0, "count_logical": 0},
                "memory": {"total": 0, "swap_total": 0},
                "disk": {"partitions": []},
                "network": {"interfaces": []}
            }
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            Dict[str, Any]: System information
        """
        return self.system_info
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.
        
        Returns:
            Dict[str, Any]: System metrics
        """
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_times = psutil.cpu_times_percent(interval=0.1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Get disk usage
            disk_usage = {
                p.mountpoint: psutil.disk_usage(p.mountpoint)
                for p in psutil.disk_partitions()
                if os.path.exists(p.mountpoint)  # Check if mountpoint exists
            }
            
            # Get network usage
            network = psutil.net_io_counters()
            
            # Get process information
            process = psutil.Process(os.getpid())
            process_info = {
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_percent": process.memory_percent(),
                "memory_info": {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms
                },
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            }
            
            # Calculate uptime
            uptime = time.time() - self.start_time
            
            # Create metrics object
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "times": {
                        "user": cpu_times.user,
                        "system": cpu_times.system,
                        "idle": cpu_times.idle
                    }
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent,
                    "swap": {
                        "total": swap.total,
                        "used": swap.used,
                        "free": swap.free,
                        "percent": swap.percent
                    }
                },
                "disk": {
                    mountpoint: {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    }
                    for mountpoint, usage in disk_usage.items()
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                    "errin": network.errin,
                    "errout": network.errout,
                    "dropin": network.dropin,
                    "dropout": network.dropout
                },
                "process": process_info,
                "uptime": uptime
            }
            
            # Add to history
            self._add_to_history(metrics)
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {"percent": 0},
                "memory": {"percent": 0},
                "disk": {},
                "network": {},
                "process": {},
                "uptime": time.time() - self.start_time,
                "error": str(e)
            }
    
    def _add_to_history(self, metrics: Dict[str, Any]):
        """
        Add metrics to history.
        
        Args:
            metrics (Dict[str, Any]): Metrics to add
        """
        timestamp = datetime.fromisoformat(metrics["timestamp"])
        
        # Add CPU metrics
        self.metrics_history["cpu"].append({
            "timestamp": timestamp,
            "percent": metrics["cpu"]["percent"]
        })
        
        # Add memory metrics
        self.metrics_history["memory"].append({
            "timestamp": timestamp,
            "percent": metrics["memory"]["percent"]
        })
        
        # Add disk metrics
        total_disk_percent = 0
        disk_count = 0
        for usage in metrics["disk"].values():
            total_disk_percent += usage["percent"]
            disk_count += 1
        
        avg_disk_percent = total_disk_percent / disk_count if disk_count > 0 else 0
        self.metrics_history["disk"].append({
            "timestamp": timestamp,
            "percent": avg_disk_percent
        })
        
        # Add network metrics
        self.metrics_history["network"].append({
            "timestamp": timestamp,
            "bytes_sent": metrics["network"]["bytes_sent"],
            "bytes_recv": metrics["network"]["bytes_recv"]
        })
        
        # Trim history if needed
        self._trim_history()
    
    def _trim_history(self):
        """
        Trim history to keep only the maximum number of points and within retention period.
        """
        now = datetime.now()
        retention_threshold = now - self.history_retention
        
        for metric_type in self.metrics_history:
            # Trim by count
            if len(self.metrics_history[metric_type]) > self.history_max_points:
                self.metrics_history[metric_type] = self.metrics_history[metric_type][-self.history_max_points:]
            
            # Trim by age
            self.metrics_history[metric_type] = [
                point for point in self.metrics_history[metric_type]
                if point["timestamp"] >= retention_threshold
            ]
    
    async def get_metrics_history(
        self,
        metric_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get metrics history for a specific type.
        
        Args:
            metric_type (str): Metric type (cpu, memory, disk, network)
            start_time (Optional[datetime]): Start time
            end_time (Optional[datetime]): End time
            
        Returns:
            List[Dict[str, Any]]: Metrics history
        """
        if metric_type not in self.metrics_history:
            return []
        
        # Filter by time range if specified
        if start_time or end_time:
            filtered_history = self.metrics_history[metric_type]
            
            if start_time:
                filtered_history = [
                    point for point in filtered_history
                    if point["timestamp"] >= start_time
                ]
            
            if end_time:
                filtered_history = [
                    point for point in filtered_history
                    if point["timestamp"] <= end_time
                ]
            
            return filtered_history
        
        return self.metrics_history[metric_type]
    
    async def start(self):
        """
        Start the system monitor.
        """
        logger.info("System monitor started")
    
    async def stop(self):
        """
        Stop the system monitor.
        """
        logger.info("System monitor stopped")