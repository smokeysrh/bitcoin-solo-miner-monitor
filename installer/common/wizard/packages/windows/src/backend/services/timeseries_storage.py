"""
Time-Series Storage Service

This module provides specialized methods for storing and querying time-series data
in SQLite, replacing the InfluxDB dependency.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import aiosqlite

logger = logging.getLogger(__name__)


class TimeSeriesStorage:
    """
    Service for time-series data operations in SQLite.
    """
    
    def __init__(self, db_connection: aiosqlite.Connection):
        """
        Initialize TimeSeriesStorage with a database connection.
        
        Args:
            db_connection: Active SQLite database connection
        """
        self.conn = db_connection
    
    async def save_metrics(self, miner_id: str, metrics: Dict[str, Any], timestamp: Optional[datetime] = None) -> bool:
        """
        Save miner metrics to the time-series table.
        
        Args:
            miner_id: ID of the miner
            metrics: Dictionary of metric name -> value pairs
            timestamp: Optional timestamp, defaults to current time
            
        Returns:
            bool: True if successful, False otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        timestamp_str = timestamp.isoformat()
        
        try:
            # Prepare batch insert data
            insert_data = []
            
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, dict):
                    # Handle nested metrics (flatten with underscore)
                    for sub_name, sub_value in metric_value.items():
                        if isinstance(sub_value, (int, float)):
                            full_name = f"{metric_name}_{sub_name}"
                            unit = self._get_metric_unit(full_name)
                            insert_data.append((miner_id, timestamp_str, full_name, float(sub_value), unit))
                elif isinstance(metric_value, (int, float, bool)):
                    # Handle simple numeric metrics
                    unit = self._get_metric_unit(metric_name)
                    value = float(metric_value) if not isinstance(metric_value, bool) else (1.0 if metric_value else 0.0)
                    insert_data.append((miner_id, timestamp_str, metric_name, value, unit))
                elif isinstance(metric_value, str):
                    # Try to convert string to number
                    try:
                        value = float(metric_value)
                        unit = self._get_metric_unit(metric_name)
                        insert_data.append((miner_id, timestamp_str, metric_name, value, unit))
                    except ValueError:
                        # Skip non-numeric string values
                        logger.debug(f"Skipping non-numeric metric {metric_name}: {metric_value}")
                        continue
            
            if not insert_data:
                logger.warning(f"No valid metrics to save for miner {miner_id}")
                return True
            
            # Batch insert all metrics
            await self.conn.executemany("""
                INSERT INTO miner_metrics (miner_id, timestamp, metric_type, value, unit)
                VALUES (?, ?, ?, ?, ?)
            """, insert_data)
            
            await self.conn.commit()
            logger.debug(f"Saved {len(insert_data)} metrics for miner {miner_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving metrics for miner {miner_id}: {str(e)}")
            return False
    
    async def save_status(self, miner_id: str, status_data: Dict[str, Any], timestamp: Optional[datetime] = None) -> bool:
        """
        Save miner status snapshot to the time-series table.
        
        Args:
            miner_id: ID of the miner
            status_data: Complete status data as dictionary
            timestamp: Optional timestamp, defaults to current time
            
        Returns:
            bool: True if successful, False otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        timestamp_str = timestamp.isoformat()
        
        try:
            # Convert status data to JSON
            status_json = json.dumps(status_data, default=str)
            
            await self.conn.execute("""
                INSERT INTO miner_status (miner_id, timestamp, status_data)
                VALUES (?, ?, ?)
            """, (miner_id, timestamp_str, status_json))
            
            await self.conn.commit()
            logger.debug(f"Saved status snapshot for miner {miner_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving status for miner {miner_id}: {str(e)}")
            return False
    
    async def get_metrics(self, miner_id: str, start_time: datetime, end_time: datetime, 
                         metric_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get metrics for a miner within a time range.
        
        Args:
            miner_id: ID of the miner
            start_time: Start of time range
            end_time: End of time range
            metric_types: Optional list of specific metric types to retrieve
            
        Returns:
            List of metric records
        """
        try:
            query = """
                SELECT timestamp, metric_type, value, unit
                FROM miner_metrics
                WHERE miner_id = ? AND timestamp BETWEEN ? AND ?
            """
            params = [miner_id, start_time.isoformat(), end_time.isoformat()]
            
            if metric_types:
                placeholders = ','.join(['?' for _ in metric_types])
                query += f" AND metric_type IN ({placeholders})"
                params.extend(metric_types)
            
            query += " ORDER BY timestamp, metric_type"
            
            cursor = await self.conn.execute(query, params)
            rows = await cursor.fetchall()
            
            # Convert to list of dictionaries
            results = []
            for row in rows:
                results.append({
                    'timestamp': row[0],
                    'metric_type': row[1],
                    'value': row[2],
                    'unit': row[3]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting metrics for miner {miner_id}: {str(e)}")
            return []
    
    async def get_latest_metrics(self, miner_id: str) -> Dict[str, Any]:
        """
        Get the latest metrics for a miner.
        
        Args:
            miner_id: ID of the miner
            
        Returns:
            Dictionary of latest metric values
        """
        try:
            # Get the latest timestamp for this miner
            cursor = await self.conn.execute("""
                SELECT MAX(timestamp) FROM miner_metrics WHERE miner_id = ?
            """, (miner_id,))
            
            latest_timestamp = await cursor.fetchone()
            if not latest_timestamp or not latest_timestamp[0]:
                return {}
            
            # Get all metrics for the latest timestamp
            cursor = await self.conn.execute("""
                SELECT metric_type, value, unit
                FROM miner_metrics
                WHERE miner_id = ? AND timestamp = ?
                ORDER BY metric_type
            """, (miner_id, latest_timestamp[0]))
            
            rows = await cursor.fetchall()
            
            # Convert to dictionary
            metrics = {}
            for row in rows:
                metric_type, value, unit = row
                metrics[metric_type] = {
                    'value': value,
                    'unit': unit,
                    'timestamp': latest_timestamp[0]
                }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting latest metrics for miner {miner_id}: {str(e)}")
            return {}
    
    async def get_aggregated_metrics(self, miner_id: str, start_time: datetime, end_time: datetime,
                                   interval: str = "1h", metric_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get aggregated metrics for a miner within a time range.
        
        Args:
            miner_id: ID of the miner
            start_time: Start of time range
            end_time: End of time range
            interval: Aggregation interval ('1m', '5m', '1h', '1d')
            metric_types: Optional list of specific metric types to retrieve
            
        Returns:
            List of aggregated metric records
        """
        try:
            if interval == '5m':
                # Special handling for 5-minute intervals
                query = """
                    SELECT 
                        CASE 
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 5 THEN strftime('%Y-%m-%d %H:0', timestamp) || '0'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 10 THEN strftime('%Y-%m-%d %H:0', timestamp) || '5'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 15 THEN strftime('%Y-%m-%d %H:', timestamp) || '10'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 20 THEN strftime('%Y-%m-%d %H:', timestamp) || '15'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 25 THEN strftime('%Y-%m-%d %H:', timestamp) || '20'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 30 THEN strftime('%Y-%m-%d %H:', timestamp) || '25'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 35 THEN strftime('%Y-%m-%d %H:', timestamp) || '30'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 40 THEN strftime('%Y-%m-%d %H:', timestamp) || '35'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 45 THEN strftime('%Y-%m-%d %H:', timestamp) || '40'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 50 THEN strftime('%Y-%m-%d %H:', timestamp) || '45'
                            WHEN CAST(strftime('%M', timestamp) AS INTEGER) < 55 THEN strftime('%Y-%m-%d %H:', timestamp) || '50'
                            ELSE strftime('%Y-%m-%d %H:', timestamp) || '55'
                        END as time_bucket,
                        metric_type,
                        AVG(value) as avg_value,
                        MIN(value) as min_value,
                        MAX(value) as max_value,
                        COUNT(*) as sample_count,
                        MAX(unit) as unit
                    FROM miner_metrics
                    WHERE miner_id = ? AND timestamp BETWEEN ? AND ?
                """
            else:
                # Standard time grouping for other intervals
                time_format = self._get_time_format(interval)
                query = f"""
                    SELECT 
                        strftime('{time_format}', timestamp) as time_bucket,
                        metric_type,
                        AVG(value) as avg_value,
                        MIN(value) as min_value,
                        MAX(value) as max_value,
                        COUNT(*) as sample_count,
                        MAX(unit) as unit
                    FROM miner_metrics
                    WHERE miner_id = ? AND timestamp BETWEEN ? AND ?
                """
            
            params = [miner_id, start_time.isoformat(), end_time.isoformat()]
            
            if metric_types:
                placeholders = ','.join(['?' for _ in metric_types])
                query += f" AND metric_type IN ({placeholders})"
                params.extend(metric_types)
            
            query += " GROUP BY time_bucket, metric_type ORDER BY time_bucket, metric_type"
            
            cursor = await self.conn.execute(query, params)
            rows = await cursor.fetchall()
            
            # Convert to list of dictionaries
            results = []
            for row in rows:
                results.append({
                    'time_bucket': row[0],
                    'metric_type': row[1],
                    'avg_value': row[2],
                    'min_value': row[3],
                    'max_value': row[4],
                    'sample_count': row[5],
                    'unit': row[6]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting aggregated metrics for miner {miner_id}: {str(e)}")
            return []
    
    async def get_latest_status(self, miner_id: str) -> Dict[str, Any]:
        """
        Get the latest status for a miner.
        
        Args:
            miner_id: ID of the miner
            
        Returns:
            Dictionary of latest status data
        """
        try:
            cursor = await self.conn.execute("""
                SELECT status_data, timestamp
                FROM miner_status
                WHERE miner_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (miner_id,))
            
            row = await cursor.fetchone()
            if not row:
                return {}
            
            status_data = json.loads(row[0])
            status_data['timestamp'] = row[1]
            
            return status_data
            
        except Exception as e:
            logger.error(f"Error getting latest status for miner {miner_id}: {str(e)}")
            return {}
    
    async def cleanup_old_data(self, retention_days: int = 30) -> bool:
        """
        Clean up old time-series data beyond retention period.
        
        Args:
            retention_days: Number of days to retain data
            
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            cutoff_str = cutoff_date.isoformat()
            
            # Clean up old metrics
            cursor = await self.conn.execute("""
                DELETE FROM miner_metrics WHERE timestamp < ?
            """, (cutoff_str,))
            metrics_deleted = cursor.rowcount
            
            # Clean up old status records
            cursor = await self.conn.execute("""
                DELETE FROM miner_status WHERE timestamp < ?
            """, (cutoff_str,))
            status_deleted = cursor.rowcount
            
            await self.conn.commit()
            
            logger.info(f"Cleaned up {metrics_deleted} old metric records and {status_deleted} old status records")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
            return False
    
    async def apply_retention_policy(self, detailed_retention_days: int = 7, 
                                   aggregated_retention_days: int = 30,
                                   status_retention_days: int = 30) -> bool:
        """
        Apply tiered data retention policy for optimal storage usage.
        
        This implements a tiered retention strategy:
        - Keep detailed metrics (all data points) for detailed_retention_days
        - Keep hourly aggregates for aggregated_retention_days  
        - Keep status snapshots for status_retention_days
        
        Args:
            detailed_retention_days: Days to keep all detailed metric data points
            aggregated_retention_days: Days to keep aggregated data
            status_retention_days: Days to keep status snapshots
            
        Returns:
            bool: True if retention policy applied successfully
        """
        try:
            now = datetime.now()
            detailed_cutoff = now - timedelta(days=detailed_retention_days)
            aggregated_cutoff = now - timedelta(days=aggregated_retention_days)
            status_cutoff = now - timedelta(days=status_retention_days)
            
            # Step 1: Create hourly aggregates for data older than detailed retention
            # but newer than aggregated retention (if they don't exist)
            await self._create_hourly_aggregates(detailed_cutoff, aggregated_cutoff)
            
            # Step 2: Delete detailed metrics older than detailed retention period
            cursor = await self.conn.execute("""
                DELETE FROM miner_metrics WHERE timestamp < ?
            """, (detailed_cutoff.isoformat(),))
            detailed_deleted = cursor.rowcount
            
            # Step 3: Delete status records older than status retention period
            cursor = await self.conn.execute("""
                DELETE FROM miner_status WHERE timestamp < ?
            """, (status_cutoff.isoformat(),))
            status_deleted = cursor.rowcount
            
            await self.conn.commit()
            
            logger.info(f"Retention policy applied: deleted {detailed_deleted} detailed metrics, "
                       f"{status_deleted} status records")
            return True
            
        except Exception as e:
            logger.error(f"Error applying retention policy: {str(e)}")
            return False
    
    async def _create_hourly_aggregates(self, start_time: datetime, end_time: datetime) -> bool:
        """
        Create hourly aggregates for the specified time range.
        
        This is used by the retention policy to preserve aggregated data
        while removing detailed data points.
        
        Args:
            start_time: Start of time range to aggregate
            end_time: End of time range to aggregate
            
        Returns:
            bool: True if aggregates created successfully
        """
        try:
            # Create a temporary table for hourly aggregates
            await self.conn.execute("""
                CREATE TEMPORARY TABLE IF NOT EXISTS hourly_aggregates AS
                SELECT 
                    miner_id,
                    strftime('%Y-%m-%d %H:00', timestamp) as hour_bucket,
                    metric_type,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    COUNT(*) as sample_count,
                    MAX(unit) as unit
                FROM miner_metrics
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY miner_id, hour_bucket, metric_type
            """, (start_time.isoformat(), end_time.isoformat()))
            
            # Insert aggregated data back as new metric records with special naming
            await self.conn.execute("""
                INSERT INTO miner_metrics (miner_id, timestamp, metric_type, value, unit)
                SELECT 
                    miner_id,
                    hour_bucket || ':00',
                    metric_type || '_hourly_avg',
                    avg_value,
                    unit
                FROM hourly_aggregates
            """)
            
            # Also insert min/max values
            await self.conn.execute("""
                INSERT INTO miner_metrics (miner_id, timestamp, metric_type, value, unit)
                SELECT 
                    miner_id,
                    hour_bucket || ':00',
                    metric_type || '_hourly_min',
                    min_value,
                    unit
                FROM hourly_aggregates
            """)
            
            await self.conn.execute("""
                INSERT INTO miner_metrics (miner_id, timestamp, metric_type, value, unit)
                SELECT 
                    miner_id,
                    hour_bucket || ':00',
                    metric_type || '_hourly_max',
                    max_value,
                    unit
                FROM hourly_aggregates
            """)
            
            # Drop temporary table
            await self.conn.execute("DROP TABLE IF EXISTS hourly_aggregates")
            
            await self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error creating hourly aggregates: {str(e)}")
            return False
    
    def _get_metric_unit(self, metric_name: str) -> Optional[str]:
        """
        Get the appropriate unit for a metric based on its name.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Unit string or None
        """
        unit_mapping = {
            'hashrate': 'TH/s',
            'temperature': '°C',
            'temp': '°C',
            'power': 'W',
            'voltage': 'V',
            'current': 'A',
            'frequency': 'MHz',
            'shares_accepted': 'count',
            'shares_rejected': 'count',
            'shares_total': 'count',
            'uptime': 'seconds',
            'difficulty': 'count',
            'fan_speed': 'RPM',
            'efficiency': 'W/TH'
        }
        
        # Check for exact match first
        if metric_name in unit_mapping:
            return unit_mapping[metric_name]
        
        # Check for partial matches
        for key, unit in unit_mapping.items():
            if key in metric_name.lower():
                return unit
        
        return None
    
    def _get_time_format(self, interval: str) -> str:
        """
        Get SQLite time format string for aggregation interval.
        
        Args:
            interval: Interval string ('1m', '5m', '1h', '1d')
            
        Returns:
            SQLite strftime format string
        """
        format_mapping = {
            '1m': '%Y-%m-%d %H:%M',
            '5m': '%Y-%m-%d %H:%M',  # Will use custom logic for 5-minute grouping
            '1h': '%Y-%m-%d %H:00',
            '1d': '%Y-%m-%d'
        }
        
        return format_mapping.get(interval, '%Y-%m-%d %H:00')
    
    def _get_5min_bucket(self, timestamp_str: str) -> str:
        """
        Get 5-minute time bucket for a timestamp.
        
        Args:
            timestamp_str: ISO timestamp string
            
        Returns:
            5-minute bucket timestamp string
        """
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Round down to nearest 5-minute interval
            minute = (dt.minute // 5) * 5
            bucket_dt = dt.replace(minute=minute, second=0, microsecond=0)
            return bucket_dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            return timestamp_str