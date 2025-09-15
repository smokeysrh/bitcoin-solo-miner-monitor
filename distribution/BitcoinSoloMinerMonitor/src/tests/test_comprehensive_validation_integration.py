"""
Comprehensive integration tests for input validation implementation.

This module tests the complete input validation system including all
validation components working together in realistic scenarios.
"""

import pytest
import asyncio
import aiosqlite
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from src.backend.models.validation_models import (
    MinerAddRequest,
    MinerUpdateRequest,
    DiscoveryRequest,
    MetricsQueryRequest,
    WebSocketMessage
)
from src.backend.utils.validators import (
    IPAddressValidator,
    PortValidator,
    DataSanitizer,
    validate_input_data
)
from src.backend.utils.query_builder import (
    SafeQueryBuilder,
    DatabaseQueryExecutor
)
from src.backend.exceptions import ValidationError


class TestComprehensiveValidationIntegration:
    """Test comprehensive validation integration scenarios."""
    
    @pytest.fixture
    @pytest.mark.asyncio
    async def temp_database(self):
        """Create a temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        # Create database connection
        conn = await aiosqlite.connect(temp_file.name)
        
        # Create test tables
        await conn.execute("""
            CREATE TABLE miners (
                id TEXT PRIMARY KEY,
                config TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        await conn.execute("""
            CREATE TABLE miner_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                miner_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (miner_id) REFERENCES miners (id)
            )
        """)
        
        await conn.commit()
        
        yield conn
        
        # Cleanup
        await conn.close()
        os.unlink(temp_file.name)
    
    def test_end_to_end_miner_validation(self):
        """Test complete miner validation workflow."""
        # Test valid miner creation
        valid_miner_data = {
            "type": "bitaxe",
            "ip_address": "10.0.0.100",
            "port": 80,
            "name": "Test Bitaxe Miner"
        }
        
        # Should validate successfully
        miner_request = MinerAddRequest(**valid_miner_data)
        assert miner_request.type == "bitaxe"
        assert miner_request.ip_address == "10.0.0.100"
        assert miner_request.port == 80
        assert miner_request.name == "Test Bitaxe Miner"
        
        # Test miner update validation
        update_data = {
            "name": "Updated Miner Name",
            "settings": {
                "frequency": 500,
                "voltage": 1.2
            }
        }
        
        update_request = MinerUpdateRequest(**update_data)
        assert update_request.name == "Updated Miner Name"
        assert update_request.settings["frequency"] == 500
    
    def test_network_discovery_validation_workflow(self):
        """Test network discovery validation workflow."""
        # Test valid discovery request
        valid_discovery = {
            "network": "192.168.1.0/24",
            "ports": [80, 443, 4028, 8080],
            "timeout": 10
        }
        
        discovery_request = DiscoveryRequest(**valid_discovery)
        assert discovery_request.network == "192.168.1.0/24"
        assert len(discovery_request.ports) == 4
        assert discovery_request.timeout == 10
        
        # Test edge cases
        minimal_discovery = {
            "network": "10.0.0.0/8"
        }
        
        minimal_request = DiscoveryRequest(**minimal_discovery)
        assert minimal_request.network == "10.0.0.0/8"
        assert minimal_request.ports is None  # Should use defaults
        assert minimal_request.timeout == 5   # Default timeout
    
    def test_metrics_query_validation_workflow(self):
        """Test metrics query validation workflow."""
        # Test comprehensive metrics query
        metrics_query = {
            "miner_id": "test_miner_001",
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-02T00:00:00",
            "interval": "1h",
            "metric_types": ["hashrate", "temperature", "power"]
        }
        
        query_request = MetricsQueryRequest(**metrics_query)
        assert query_request.miner_id == "test_miner_001"
        assert query_request.interval == "1h"
        assert len(query_request.metric_types) == 3
        
        # Test time range validation
        now = datetime.now()
        start_time = now - timedelta(hours=24)
        
        time_range_query = {
            "miner_id": "test_miner_002",
            "start": start_time.isoformat(),
            "end": now.isoformat(),
            "interval": "15m"
        }
        
        time_request = MetricsQueryRequest(**time_range_query)
        assert time_request.interval == "15m"
    
    def test_websocket_message_validation_workflow(self):
        """Test WebSocket message validation workflow."""
        # Test subscription message
        subscribe_msg = {
            "type": "subscribe",
            "topic": "miners",
            "data": {"filter": "active"}
        }
        
        ws_message = WebSocketMessage(**subscribe_msg)
        assert ws_message.type == "subscribe"
        assert ws_message.topic == "miners"
        assert ws_message.data["filter"] == "active"
        
        # Test ping message
        ping_msg = {
            "type": "ping"
        }
        
        ping_message = WebSocketMessage(**ping_msg)
        assert ping_message.type == "ping"
        assert ping_message.data is None
    
    @pytest.mark.asyncio
    async def test_database_query_validation_integration(self, temp_database):
        """Test database query validation integration."""
        conn = temp_database
        executor = DatabaseQueryExecutor(conn)
        
        # Test safe insert
        insert_query, insert_params = SafeQueryBuilder.build_insert_query(
            table="miners",
            data={
                "id": "test_miner_001",
                "config": '{"type": "bitaxe", "ip": "10.0.0.100"}',
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        )
        
        success = await executor.execute_safe_insert(insert_query, insert_params)
        assert success is True
        
        # Test safe select
        select_query, select_params = SafeQueryBuilder.build_select_query(
            table="miners",
            columns=["id", "config"],
            where_conditions={"id": "test_miner_001"}
        )
        
        results = await executor.execute_safe_query(select_query, select_params)
        assert len(results) == 1
        assert results[0]["id"] == "test_miner_001"
        
        # Test metrics insertion
        metrics_insert_query, metrics_params = SafeQueryBuilder.build_insert_query(
            table="miner_metrics",
            data={
                "miner_id": "test_miner_001",
                "timestamp": datetime.now().isoformat(),
                "metric_type": "hashrate",
                "value": 500.5,
                "unit": "GH/s"
            }
        )
        
        metrics_success = await executor.execute_safe_insert(metrics_insert_query, metrics_params)
        assert metrics_success is True
    
    def test_malicious_input_prevention(self):
        """Test prevention of malicious inputs across all validation layers."""
        # Test SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE miners; --",
            "1 OR 1=1",
            "UNION SELECT * FROM users",
            "admin'--",
            "/* comment */ SELECT"
        ]
        
        for malicious_input in malicious_inputs:
            # Should fail at string sanitization level
            with pytest.raises(ValidationError):
                DataSanitizer.sanitize_string(malicious_input)
            
            # Should fail at miner name validation
            with pytest.raises(ValidationError):
                DataSanitizer.sanitize_miner_name(malicious_input)
        
        # Test XSS attempts
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<iframe src='evil.com'></iframe>",
            "onclick='alert(1)'"
        ]
        
        for xss_input in xss_inputs:
            with pytest.raises(ValidationError):
                DataSanitizer.sanitize_string(xss_input)
    
    def test_ip_address_validation_comprehensive(self):
        """Test comprehensive IP address validation scenarios."""
        # Valid IP addresses
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1", 
            "172.16.0.1",
            "127.0.0.1",
            "::1",
            "2001:db8::1"
        ]
        
        for ip in valid_ips:
            validated_ip = IPAddressValidator.validate_ip_address(ip)
            assert validated_ip == ip
        
        # Invalid IP addresses
        invalid_ips = [
            "256.256.256.256",
            "192.168.1",
            "not.an.ip",
            "",
            "192.168.1.-1"
        ]
        
        for ip in invalid_ips:
            with pytest.raises(ValidationError):
                IPAddressValidator.validate_ip_address(ip)
    
    def test_port_validation_comprehensive(self):
        """Test comprehensive port validation scenarios."""
        # Test different port types
        system_ports = [22, 80, 443]
        for port in system_ports:
            validated_port = PortValidator.validate_port(port, 'system')
            assert validated_port == port
        
        registered_ports = [8080, 4028, 9999]
        for port in registered_ports:
            validated_port = PortValidator.validate_port(port, 'registered')
            assert validated_port == port
        
        # Test port list validation
        port_list = [80, 443, 8080, 4028]
        validated_ports = PortValidator.validate_port_list(port_list)
        assert validated_ports == port_list
        
        # Test invalid ports
        invalid_ports = [0, -1, 65536, 100000]
        for port in invalid_ports:
            with pytest.raises(ValidationError):
                PortValidator.validate_port(port)
    
    def test_data_sanitization_comprehensive(self):
        """Test comprehensive data sanitization scenarios."""
        # Test valid JSON data sanitization
        valid_data = {
            "miner_name": "Bitaxe Miner 1",
            "ip_address": "10.0.0.100",
            "port": 80,
            "settings": {
                "frequency": 500,
                "voltage": 1.2,
                "pool_url": "stratum+tcp://pool.example.com:4444"
            }
        }
        
        sanitized_data = DataSanitizer.sanitize_json_data(valid_data)
        assert sanitized_data["miner_name"] == "Bitaxe Miner 1"
        assert sanitized_data["ip_address"] == "10.0.0.100"
        assert sanitized_data["settings"]["frequency"] == 500
        
        # Test malicious JSON data
        malicious_data = {
            "name": "'; DROP TABLE miners; --",
            "script": "<script>alert(1)</script>",
            "injection": "1 OR 1=1"
        }
        
        with pytest.raises(ValidationError):
            DataSanitizer.sanitize_json_data(malicious_data)
    
    def test_query_builder_security_comprehensive(self):
        """Test comprehensive query builder security."""
        # Test table name validation
        valid_tables = ["miners", "settings", "miner_metrics", "miner_status"]
        for table in valid_tables:
            validated_table = SafeQueryBuilder.validate_table_name(table)
            assert validated_table == table
        
        # Test malicious table names
        malicious_tables = [
            "users; DROP TABLE miners; --",
            "admin",
            "'; SELECT * FROM users; --"
        ]
        
        for table in malicious_tables:
            with pytest.raises(ValidationError):
                SafeQueryBuilder.validate_table_name(table)
        
        # Test column validation
        for table in valid_tables:
            allowed_columns = SafeQueryBuilder.ALLOWED_COLUMNS[table]
            for column in allowed_columns:
                validated_column = SafeQueryBuilder.validate_column_name(table, column)
                assert validated_column == column
        
        # Test malicious column names
        malicious_columns = [
            "id; DROP TABLE miners; --",
            "* FROM users; --",
            "password"
        ]
        
        for column in malicious_columns:
            with pytest.raises(ValidationError):
                SafeQueryBuilder.validate_column_name("miners", column)
    
    def test_generic_validation_framework(self):
        """Test the generic validation framework."""
        # Define validation rules
        validation_rules = {
            'miner_name': {
                'required': True,
                'type': str,
                'validator': DataSanitizer.sanitize_miner_name
            },
            'ip_address': {
                'required': True,
                'type': str,
                'validator': IPAddressValidator.validate_ip_address
            },
            'port': {
                'required': False,
                'type': int,
                'validator': lambda x: PortValidator.validate_port(x, 'all')
            }
        }
        
        # Test valid data
        valid_input = {
            'miner_name': 'Test Miner',
            'ip_address': '10.0.0.100',
            'port': 80
        }
        
        validated_data = validate_input_data(valid_input, validation_rules)
        assert validated_data['miner_name'] == 'Test Miner'
        assert validated_data['ip_address'] == '10.0.0.100'
        assert validated_data['port'] == 80
        
        # Test missing required field
        invalid_input = {
            'port': 80
        }
        
        with pytest.raises(ValidationError):
            validate_input_data(invalid_input, validation_rules)
        
        # Test invalid data type
        invalid_type_input = {
            'miner_name': 123,  # Should be string
            'ip_address': '10.0.0.100'
        }
        
        with pytest.raises(ValidationError):
            validate_input_data(invalid_type_input, validation_rules)
    
    def test_performance_with_large_datasets(self):
        """Test validation performance with larger datasets."""
        # Test validation of many IP addresses
        ip_addresses = [f"192.168.1.{i}" for i in range(1, 255)]
        
        for ip in ip_addresses:
            validated_ip = IPAddressValidator.validate_ip_address(ip)
            assert validated_ip == ip
        
        # Test validation of many port numbers
        ports = list(range(1024, 2048))  # 1024 ports
        
        validated_ports = PortValidator.validate_port_list(ports, 'registered')
        assert len(validated_ports) == len(ports)
        
        # Test sanitization of many strings
        test_strings = [f"miner_{i:04d}" for i in range(1000)]
        
        for test_string in test_strings:
            sanitized = DataSanitizer.sanitize_string(test_string)
            assert sanitized == test_string


if __name__ == "__main__":
    pytest.main([__file__])