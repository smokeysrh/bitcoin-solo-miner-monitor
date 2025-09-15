"""
Safe database query builder with parameterized queries.

This module provides utilities for building safe SQL queries with proper
parameter binding to prevent SQL injection attacks.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import logging

from src.backend.exceptions import ValidationError, DatabaseQueryError

logger = logging.getLogger(__name__)


class SafeQueryBuilder:
    """
    Safe SQL query builder that uses parameterized queries to prevent SQL injection.
    """
    
    # Allowed table names (whitelist approach)
    ALLOWED_TABLES = {
        'miners', 'settings', 'miner_metrics', 'miner_status'
    }
    
    # Allowed column names for each table
    ALLOWED_COLUMNS = {
        'miners': {'id', 'config', 'created_at', 'updated_at'},
        'settings': {'id', 'value', 'created_at', 'updated_at'},
        'miner_metrics': {
            'id', 'miner_id', 'timestamp', 'metric_type', 'value', 'unit', 'created_at'
        },
        'miner_status': {
            'id', 'miner_id', 'timestamp', 'status_data', 'created_at'
        }
    }
    
    # Allowed operators for WHERE clauses
    ALLOWED_OPERATORS = {
        '=', '!=', '<', '>', '<=', '>=', 'LIKE', 'IN', 'NOT IN', 'IS NULL', 'IS NOT NULL'
    }
    
    # Allowed ORDER BY directions
    ALLOWED_ORDER_DIRECTIONS = {'ASC', 'DESC'}
    
    @staticmethod
    def validate_table_name(table: str) -> str:
        """
        Validate table name against whitelist.
        
        Args:
            table (str): Table name to validate
            
        Returns:
            str: Validated table name
            
        Raises:
            ValidationError: If table name is not allowed
        """
        if table not in SafeQueryBuilder.ALLOWED_TABLES:
            raise ValidationError(f"Table '{table}' is not allowed")
        return table
    
    @staticmethod
    def validate_column_name(table: str, column: str) -> str:
        """
        Validate column name for a specific table.
        
        Args:
            table (str): Table name
            column (str): Column name to validate
            
        Returns:
            str: Validated column name
            
        Raises:
            ValidationError: If column name is not allowed for the table
        """
        SafeQueryBuilder.validate_table_name(table)
        
        allowed_columns = SafeQueryBuilder.ALLOWED_COLUMNS.get(table, set())
        if column not in allowed_columns:
            raise ValidationError(f"Column '{column}' is not allowed for table '{table}'")
        return column
    
    @staticmethod
    def validate_operator(operator: str) -> str:
        """
        Validate SQL operator.
        
        Args:
            operator (str): SQL operator to validate
            
        Returns:
            str: Validated operator
            
        Raises:
            ValidationError: If operator is not allowed
        """
        operator = operator.upper()
        if operator not in SafeQueryBuilder.ALLOWED_OPERATORS:
            raise ValidationError(f"Operator '{operator}' is not allowed")
        return operator
    
    @staticmethod
    def build_select_query(
        table: str,
        columns: Optional[List[str]] = None,
        where_conditions: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_direction: str = 'ASC',
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[str, List[Any]]:
        """
        Build a safe SELECT query with parameterized values.
        
        Args:
            table (str): Table name
            columns (Optional[List[str]]): Columns to select (None for all)
            where_conditions (Optional[Dict[str, Any]]): WHERE conditions
            order_by (Optional[str]): Column to order by
            order_direction (str): Order direction (ASC/DESC)
            limit (Optional[int]): LIMIT value
            offset (Optional[int]): OFFSET value
            
        Returns:
            Tuple[str, List[Any]]: Query string and parameters
            
        Raises:
            ValidationError: If any parameter is invalid
        """
        # Validate table name
        table = SafeQueryBuilder.validate_table_name(table)
        
        # Build SELECT clause
        if columns:
            # Validate each column
            validated_columns = []
            for col in columns:
                validated_columns.append(SafeQueryBuilder.validate_column_name(table, col))
            columns_str = ', '.join(validated_columns)
        else:
            columns_str = '*'
        
        query = f"SELECT {columns_str} FROM {table}"
        params = []
        
        # Build WHERE clause
        if where_conditions:
            where_parts = []
            for column, value in where_conditions.items():
                # Validate column name
                SafeQueryBuilder.validate_column_name(table, column)
                
                if isinstance(value, dict) and 'operator' in value:
                    # Handle complex conditions with operators
                    operator = SafeQueryBuilder.validate_operator(value['operator'])
                    condition_value = value['value']
                    
                    if operator in ('IS NULL', 'IS NOT NULL'):
                        where_parts.append(f"{column} {operator}")
                    elif operator == 'IN':
                        if not isinstance(condition_value, (list, tuple)):
                            raise ValidationError("IN operator requires a list of values")
                        placeholders = ', '.join(['?' for _ in condition_value])
                        where_parts.append(f"{column} IN ({placeholders})")
                        params.extend(condition_value)
                    elif operator == 'NOT IN':
                        if not isinstance(condition_value, (list, tuple)):
                            raise ValidationError("NOT IN operator requires a list of values")
                        placeholders = ', '.join(['?' for _ in condition_value])
                        where_parts.append(f"{column} NOT IN ({placeholders})")
                        params.extend(condition_value)
                    else:
                        where_parts.append(f"{column} {operator} ?")
                        params.append(condition_value)
                else:
                    # Simple equality condition
                    where_parts.append(f"{column} = ?")
                    params.append(value)
            
            if where_parts:
                query += " WHERE " + " AND ".join(where_parts)
        
        # Build ORDER BY clause
        if order_by:
            SafeQueryBuilder.validate_column_name(table, order_by)
            order_direction = order_direction.upper()
            if order_direction not in SafeQueryBuilder.ALLOWED_ORDER_DIRECTIONS:
                raise ValidationError(f"Invalid order direction: {order_direction}")
            query += f" ORDER BY {order_by} {order_direction}"
        
        # Build LIMIT clause
        if limit is not None:
            if not isinstance(limit, int) or limit <= 0:
                raise ValidationError("LIMIT must be a positive integer")
            query += " LIMIT ?"
            params.append(limit)
        
        # Build OFFSET clause
        if offset is not None:
            if not isinstance(offset, int) or offset < 0:
                raise ValidationError("OFFSET must be a non-negative integer")
            query += " OFFSET ?"
            params.append(offset)
        
        return query, params
    
    @staticmethod
    def build_insert_query(
        table: str,
        data: Dict[str, Any]
    ) -> Tuple[str, List[Any]]:
        """
        Build a safe INSERT query with parameterized values.
        
        Args:
            table (str): Table name
            data (Dict[str, Any]): Data to insert
            
        Returns:
            Tuple[str, List[Any]]: Query string and parameters
            
        Raises:
            ValidationError: If any parameter is invalid
        """
        # Validate table name
        table = SafeQueryBuilder.validate_table_name(table)
        
        if not data:
            raise ValidationError("Insert data cannot be empty")
        
        # Validate columns and build query
        columns = []
        values = []
        placeholders = []
        
        for column, value in data.items():
            SafeQueryBuilder.validate_column_name(table, column)
            columns.append(column)
            values.append(value)
            placeholders.append('?')
        
        columns_str = ', '.join(columns)
        placeholders_str = ', '.join(placeholders)
        
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders_str})"
        
        return query, values
    
    @staticmethod
    def build_update_query(
        table: str,
        data: Dict[str, Any],
        where_conditions: Dict[str, Any]
    ) -> Tuple[str, List[Any]]:
        """
        Build a safe UPDATE query with parameterized values.
        
        Args:
            table (str): Table name
            data (Dict[str, Any]): Data to update
            where_conditions (Dict[str, Any]): WHERE conditions
            
        Returns:
            Tuple[str, List[Any]]: Query string and parameters
            
        Raises:
            ValidationError: If any parameter is invalid
        """
        # Validate table name
        table = SafeQueryBuilder.validate_table_name(table)
        
        if not data:
            raise ValidationError("Update data cannot be empty")
        
        if not where_conditions:
            raise ValidationError("WHERE conditions are required for UPDATE queries")
        
        # Build SET clause
        set_parts = []
        params = []
        
        for column, value in data.items():
            SafeQueryBuilder.validate_column_name(table, column)
            set_parts.append(f"{column} = ?")
            params.append(value)
        
        query = f"UPDATE {table} SET {', '.join(set_parts)}"
        
        # Build WHERE clause
        where_parts = []
        for column, value in where_conditions.items():
            SafeQueryBuilder.validate_column_name(table, column)
            where_parts.append(f"{column} = ?")
            params.append(value)
        
        query += " WHERE " + " AND ".join(where_parts)
        
        return query, params
    
    @staticmethod
    def build_delete_query(
        table: str,
        where_conditions: Dict[str, Any]
    ) -> Tuple[str, List[Any]]:
        """
        Build a safe DELETE query with parameterized values.
        
        Args:
            table (str): Table name
            where_conditions (Dict[str, Any]): WHERE conditions
            
        Returns:
            Tuple[str, List[Any]]: Query string and parameters
            
        Raises:
            ValidationError: If any parameter is invalid
        """
        # Validate table name
        table = SafeQueryBuilder.validate_table_name(table)
        
        if not where_conditions:
            raise ValidationError("WHERE conditions are required for DELETE queries")
        
        # Build WHERE clause
        where_parts = []
        params = []
        
        for column, value in where_conditions.items():
            SafeQueryBuilder.validate_column_name(table, column)
            where_parts.append(f"{column} = ?")
            params.append(value)
        
        query = f"DELETE FROM {table} WHERE {' AND '.join(where_parts)}"
        
        return query, params
    
    @staticmethod
    def build_time_range_query(
        table: str,
        miner_id: str,
        start_time: datetime,
        end_time: datetime,
        columns: Optional[List[str]] = None,
        metric_types: Optional[List[str]] = None,
        order_by: str = 'timestamp',
        limit: Optional[int] = None
    ) -> Tuple[str, List[Any]]:
        """
        Build a time-range query for metrics data.
        
        Args:
            table (str): Table name (miner_metrics or miner_status)
            miner_id (str): Miner ID
            start_time (datetime): Start time
            end_time (datetime): End time
            columns (Optional[List[str]]): Columns to select
            metric_types (Optional[List[str]]): Specific metric types to filter
            order_by (str): Column to order by
            limit (Optional[int]): Limit number of results
            
        Returns:
            Tuple[str, List[Any]]: Query string and parameters
        """
        # Validate table name
        table = SafeQueryBuilder.validate_table_name(table)
        
        # Build WHERE conditions
        where_conditions = {
            'miner_id': miner_id,
            'timestamp': {
                'operator': '>=',
                'value': start_time.isoformat()
            }
        }
        
        # Add end time condition
        end_condition = {
            'timestamp': {
                'operator': '<=',
                'value': end_time.isoformat()
            }
        }
        
        # Build base query
        query, params = SafeQueryBuilder.build_select_query(
            table=table,
            columns=columns,
            where_conditions=where_conditions,
            order_by=order_by,
            order_direction='ASC',
            limit=limit
        )
        
        # Add end time condition manually (since we can't have duplicate keys in dict)
        if 'WHERE' in query:
            query += f" AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        # Add metric type filter for metrics table
        if table == 'miner_metrics' and metric_types:
            placeholders = ', '.join(['?' for _ in metric_types])
            query += f" AND metric_type IN ({placeholders})"
            params.extend(metric_types)
        
        return query, params
    
    @staticmethod
    def build_aggregation_query(
        miner_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1h',
        metric_types: Optional[List[str]] = None
    ) -> Tuple[str, List[Any]]:
        """
        Build an aggregation query for time-series metrics.
        
        Args:
            miner_id (str): Miner ID
            start_time (datetime): Start time
            end_time (datetime): End time
            interval (str): Aggregation interval
            metric_types (Optional[List[str]]): Specific metric types
            
        Returns:
            Tuple[str, List[Any]]: Query string and parameters
        """
        # Map intervals to SQLite date functions
        interval_mapping = {
            '1m': "strftime('%Y-%m-%d %H:%M', timestamp)",
            '5m': "strftime('%Y-%m-%d %H:', timestamp) || (CAST(strftime('%M', timestamp) AS INTEGER) / 5) * 5",
            '15m': "strftime('%Y-%m-%d %H:', timestamp) || (CAST(strftime('%M', timestamp) AS INTEGER) / 15) * 15",
            '30m': "strftime('%Y-%m-%d %H:', timestamp) || (CAST(strftime('%M', timestamp) AS INTEGER) / 30) * 30",
            '1h': "strftime('%Y-%m-%d %H:00', timestamp)",
            '6h': "strftime('%Y-%m-%d ', timestamp) || (CAST(strftime('%H', timestamp) AS INTEGER) / 6) * 6 || ':00'",
            '12h': "strftime('%Y-%m-%d ', timestamp) || (CAST(strftime('%H', timestamp) AS INTEGER) / 12) * 12 || ':00'",
            '1d': "strftime('%Y-%m-%d', timestamp)"
        }
        
        if interval not in interval_mapping:
            raise ValidationError(f"Invalid aggregation interval: {interval}")
        
        time_group = interval_mapping[interval]
        
        query = f"""
        SELECT 
            {time_group} as time_bucket,
            metric_type,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            COUNT(*) as sample_count
        FROM miner_metrics 
        WHERE miner_id = ? AND timestamp >= ? AND timestamp <= ?
        """
        
        params = [miner_id, start_time.isoformat(), end_time.isoformat()]
        
        # Add metric type filter
        if metric_types:
            placeholders = ', '.join(['?' for _ in metric_types])
            query += f" AND metric_type IN ({placeholders})"
            params.extend(metric_types)
        
        query += f" GROUP BY {time_group}, metric_type ORDER BY time_bucket ASC"
        
        return query, params


class DatabaseQueryExecutor:
    """
    Safe database query executor that uses the SafeQueryBuilder.
    """
    
    def __init__(self, connection):
        """
        Initialize with database connection.
        
        Args:
            connection: Database connection object
        """
        self.connection = connection
    
    async def execute_safe_query(self, query: str, params: List[Any]) -> List[Dict[str, Any]]:
        """
        Execute a safe parameterized query.
        
        Args:
            query (str): SQL query with parameter placeholders
            params (List[Any]): Query parameters
            
        Returns:
            List[Dict[str, Any]]: Query results
            
        Raises:
            DatabaseQueryError: If query execution fails
        """
        try:
            logger.debug(f"Executing query: {query} with params: {params}")
            
            async with self.connection.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                
                # Convert rows to dictionaries
                if rows:
                    columns = [description[0] for description in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Database query failed: {str(e)}")
            raise DatabaseQueryError(f"Query execution failed: {str(e)}")
    
    async def execute_safe_insert(self, query: str, params: List[Any]) -> bool:
        """
        Execute a safe INSERT query.
        
        Args:
            query (str): INSERT query
            params (List[Any]): Query parameters
            
        Returns:
            bool: True if successful
            
        Raises:
            DatabaseQueryError: If query execution fails
        """
        try:
            logger.debug(f"Executing insert: {query} with params: {params}")
            
            await self.connection.execute(query, params)
            await self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Database insert failed: {str(e)}")
            raise DatabaseQueryError(f"Insert execution failed: {str(e)}")
    
    async def execute_safe_update(self, query: str, params: List[Any]) -> int:
        """
        Execute a safe UPDATE query.
        
        Args:
            query (str): UPDATE query
            params (List[Any]): Query parameters
            
        Returns:
            int: Number of affected rows
            
        Raises:
            DatabaseQueryError: If query execution fails
        """
        try:
            logger.debug(f"Executing update: {query} with params: {params}")
            
            cursor = await self.connection.execute(query, params)
            await self.connection.commit()
            return cursor.rowcount
            
        except Exception as e:
            logger.error(f"Database update failed: {str(e)}")
            raise DatabaseQueryError(f"Update execution failed: {str(e)}")
    
    async def execute_safe_delete(self, query: str, params: List[Any]) -> int:
        """
        Execute a safe DELETE query.
        
        Args:
            query (str): DELETE query
            params (List[Any]): Query parameters
            
        Returns:
            int: Number of affected rows
            
        Raises:
            DatabaseQueryError: If query execution fails
        """
        try:
            logger.debug(f"Executing delete: {query} with params: {params}")
            
            cursor = await self.connection.execute(query, params)
            await self.connection.commit()
            return cursor.rowcount
            
        except Exception as e:
            logger.error(f"Database delete failed: {str(e)}")
            raise DatabaseQueryError(f"Delete execution failed: {str(e)}")