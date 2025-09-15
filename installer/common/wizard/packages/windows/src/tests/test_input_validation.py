"""
Tests for comprehensive input validation implementation.

This module tests all aspects of input validation including IP addresses,
port numbers, data sanitization, and SQL injection prevention.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError

from src.backend.utils.validators import (
    IPAddressValidator,
    PortValidator,
    DataSanitizer,
    MinerTypeValidator,
    URLValidator,
    validate_input_data
)
from src.backend.models.validation_models import (
    MinerAddRequest,
    MinerUpdateRequest,
    DiscoveryRequest,
    AppSettingsRequest,
    MetricsQueryRequest,
    WebSocketMessage
)
from src.backend.utils.query_builder import SafeQueryBuilder
from src.backend.exceptions import ValidationError


class TestIPAddressValidator:
    """Test IP address validation."""
    
    def test_valid_ipv4_addresses(self):
        """Test valid IPv4 addresses."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "127.0.0.1",
            "8.8.8.8"
        ]
        
        for ip in valid_ips:
            result = IPAddressValidator.validate_ip_address(ip)
            assert result == ip
    
    def test_valid_ipv6_addresses(self):
        """Test valid IPv6 addresses."""
        valid_ips = [
            "::1",
            "2001:db8::1",
            "fe80::1"
        ]
        
        for ip in valid_ips:
            result = IPAddressValidator.validate_ip_address(ip)
            assert result == ip
    
    def test_invalid_ip_addresses(self):
        """Test invalid IP addresses."""
        invalid_ips = [
            "256.256.256.256",
            "192.168.1",
            "192.168.1.1.1",
            "not.an.ip.address",
            "",
            None,
            "192.168.1.-1"
        ]
        
        for ip in invalid_ips:
            with pytest.raises(ValidationError):
                IPAddressValidator.validate_ip_address(ip)
    
    def test_network_range_validation(self):
        """Test network range validation."""
        valid_ranges = [
            "192.168.1.0/24",
            "10.0.0.0/8",
            "172.16.0.0/16"
        ]
        
        for network in valid_ranges:
            result = IPAddressValidator.validate_network_range(network)
            assert result == network
        
        invalid_ranges = [
            "192.168.1.0/33",
            "256.256.256.0/24",
            "not.a.network/24",
            ""
        ]
        
        for network in invalid_ranges:
            with pytest.raises(ValidationError):
                IPAddressValidator.validate_network_range(network)


class TestPortValidator:
    """Test port number validation."""
    
    def test_valid_ports(self):
        """Test valid port numbers."""
        valid_ports = [80, 443, 8080, 4028, "80", "443"]
        
        for port in valid_ports:
            result = PortValidator.validate_port(port)
            assert isinstance(result, int)
            assert 1 <= result <= 65535
    
    def test_invalid_ports(self):
        """Test invalid port numbers."""
        invalid_ports = [0, -1, 65536, 100000, "not_a_port", None]
        
        for port in invalid_ports:
            with pytest.raises(ValidationError):
                PortValidator.validate_port(port)
    
    def test_port_type_validation(self):
        """Test port type-specific validation."""
        # System port
        result = PortValidator.validate_port(80, 'system')
        assert result == 80
        
        # Should fail for system port range
        with pytest.raises(ValidationError):
            PortValidator.validate_port(8080, 'system')
        
        # Registered port
        result = PortValidator.validate_port(8080, 'registered')
        assert result == 8080
    
    def test_port_list_validation(self):
        """Test port list validation."""
        valid_ports = [80, 443, 8080, 4028]
        result = PortValidator.validate_port_list(valid_ports)
        assert result == valid_ports
        
        invalid_ports = [80, 443, 65536]
        with pytest.raises(ValidationError):
            PortValidator.validate_port_list(invalid_ports)


class TestDataSanitizer:
    """Test data sanitization."""
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        malicious_strings = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "UNION SELECT * FROM users",
            "/* comment */ SELECT",
            "admin'--"
        ]
        
        for malicious in malicious_strings:
            with pytest.raises(ValidationError):
                DataSanitizer.sanitize_string(malicious)
    
    def test_xss_detection(self):
        """Test XSS pattern detection."""
        malicious_strings = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<iframe src='evil.com'></iframe>",
            "onclick='alert(1)'"
        ]
        
        for malicious in malicious_strings:
            with pytest.raises(ValidationError):
                DataSanitizer.sanitize_string(malicious)
    
    def test_valid_string_sanitization(self):
        """Test valid string sanitization."""
        valid_strings = [
            "normal string",
            "miner-name_123",
            "192.168.1.1",
            "valid@email.com"
        ]
        
        for valid in valid_strings:
            result = DataSanitizer.sanitize_string(valid)
            assert result == valid.strip()
    
    def test_miner_name_validation(self):
        """Test miner name specific validation."""
        valid_names = [
            "Miner 1",
            "bitaxe-001",
            "avalon_nano_2"
        ]
        
        for name in valid_names:
            result = DataSanitizer.sanitize_miner_name(name)
            assert result == name
        
        invalid_names = [
            "",
            "miner@#$%",
            "<script>alert(1)</script>",
            "a" * 101  # Too long
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError):
                DataSanitizer.sanitize_miner_name(name)
    
    def test_json_data_sanitization(self):
        """Test JSON data sanitization."""
        valid_data = {
            "name": "miner1",
            "ip": "192.168.1.1",
            "port": 80,
            "settings": {
                "frequency": 500,
                "voltage": 1.2
            }
        }
        
        result = DataSanitizer.sanitize_json_data(valid_data)
        assert result["name"] == "miner1"
        assert result["ip"] == "192.168.1.1"
        
        malicious_data = {
            "name": "'; DROP TABLE miners; --",
            "script": "<script>alert(1)</script>"
        }
        
        with pytest.raises(ValidationError):
            DataSanitizer.sanitize_json_data(malicious_data)


class TestMinerTypeValidator:
    """Test miner type validation."""
    
    def test_valid_miner_types(self):
        """Test valid miner types."""
        valid_types = ["bitaxe", "avalon_nano", "magic_miner"]
        
        for miner_type in valid_types:
            result = MinerTypeValidator.validate_miner_type(miner_type)
            assert result == miner_type
    
    def test_invalid_miner_types(self):
        """Test invalid miner types."""
        invalid_types = ["unknown_miner", "", None]
        
        for miner_type in invalid_types:
            with pytest.raises(ValidationError):
                MinerTypeValidator.validate_miner_type(miner_type)
        
        # Test case-insensitive validation (should work)
        result = MinerTypeValidator.validate_miner_type("BITAXE")
        assert result == "bitaxe"


class TestURLValidator:
    """Test URL validation."""
    
    def test_valid_urls(self):
        """Test valid URLs."""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "http://192.168.1.1:8080",
            "https://pool.example.com/path"
        ]
        
        for url in valid_urls:
            result = URLValidator.validate_url(url)
            assert result == url
    
    def test_invalid_urls(self):
        """Test invalid URLs."""
        invalid_urls = [
            "ftp://example.com",  # Invalid scheme
            "example.com",        # No scheme
            "",                   # Empty
            "http://",           # No hostname
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                URLValidator.validate_url(url)


class TestPydanticModels:
    """Test Pydantic validation models."""
    
    def test_miner_add_request_validation(self):
        """Test MinerAddRequest validation."""
        # Valid request
        valid_request = {
            "type": "bitaxe",
            "ip_address": "10.0.0.100",
            "port": 80,
            "name": "Bitaxe Miner 1"
        }
        
        request = MinerAddRequest(**valid_request)
        assert request.type == "bitaxe"
        assert request.ip_address == "10.0.0.100"
        assert request.port == 80
        assert request.name == "Bitaxe Miner 1"
        
        # Invalid IP address
        invalid_request = {
            "type": "bitaxe",
            "ip_address": "256.256.256.256",
            "port": 80
        }
        
        with pytest.raises((PydanticValidationError, ValidationError)):
            MinerAddRequest(**invalid_request)
        
        # Invalid miner type
        invalid_request = {
            "type": "unknown_miner",
            "ip_address": "10.0.0.100",
            "port": 80
        }
        
        with pytest.raises((PydanticValidationError, ValidationError)):
            MinerAddRequest(**invalid_request)
    
    def test_discovery_request_validation(self):
        """Test DiscoveryRequest validation."""
        # Valid request
        valid_request = {
            "network": "192.168.1.0/24",
            "ports": [80, 443, 8080],
            "timeout": 5
        }
        
        request = DiscoveryRequest(**valid_request)
        assert request.network == "192.168.1.0/24"
        assert request.ports == [80, 443, 8080]
        assert request.timeout == 5
        
        # Invalid network
        invalid_request = {
            "network": "256.256.256.0/24"
        }
        
        with pytest.raises((PydanticValidationError, ValidationError)):
            DiscoveryRequest(**invalid_request)
        
        # Too many ports
        invalid_request = {
            "network": "192.168.1.0/24",
            "ports": list(range(1, 52))  # 51 ports
        }
        
        with pytest.raises((PydanticValidationError, ValidationError)):
            DiscoveryRequest(**invalid_request)
    
    def test_metrics_query_request_validation(self):
        """Test MetricsQueryRequest validation."""
        # Valid request
        valid_request = {
            "miner_id": "miner_001",
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-02T00:00:00",
            "interval": "1h",
            "metric_types": ["hashrate", "temperature"]
        }
        
        request = MetricsQueryRequest(**valid_request)
        assert request.miner_id == "miner_001"
        assert request.interval == "1h"
        
        # Invalid interval
        invalid_request = {
            "miner_id": "miner_001",
            "interval": "invalid_interval"
        }
        
        with pytest.raises((PydanticValidationError, ValidationError)):
            MetricsQueryRequest(**invalid_request)
        
        # Invalid time range (start after end)
        invalid_request = {
            "miner_id": "miner_001",
            "start": "2024-01-02T00:00:00",
            "end": "2024-01-01T00:00:00"
        }
        
        with pytest.raises((PydanticValidationError, ValidationError)):
            MetricsQueryRequest(**invalid_request)
    
    def test_websocket_message_validation(self):
        """Test WebSocketMessage validation."""
        # Valid message
        valid_message = {
            "type": "subscribe",
            "topic": "miners",
            "data": {"filter": "active"}
        }
        
        message = WebSocketMessage(**valid_message)
        assert message.type == "subscribe"
        assert message.topic == "miners"
        
        # Invalid message type
        invalid_message = {
            "type": "invalid_type"
        }
        
        with pytest.raises((PydanticValidationError, ValidationError)):
            WebSocketMessage(**invalid_message)


class TestSafeQueryBuilder:
    """Test safe query builder."""
    
    def test_table_name_validation(self):
        """Test table name validation."""
        valid_tables = ["miners", "settings", "miner_metrics", "miner_status"]
        
        for table in valid_tables:
            result = SafeQueryBuilder.validate_table_name(table)
            assert result == table
        
        invalid_tables = ["users", "admin", "'; DROP TABLE miners; --"]
        
        for table in invalid_tables:
            with pytest.raises(ValidationError):
                SafeQueryBuilder.validate_table_name(table)
    
    def test_column_name_validation(self):
        """Test column name validation."""
        # Valid columns for miners table
        valid_columns = ["id", "config", "created_at", "updated_at"]
        
        for column in valid_columns:
            result = SafeQueryBuilder.validate_column_name("miners", column)
            assert result == column
        
        # Invalid column
        with pytest.raises(ValidationError):
            SafeQueryBuilder.validate_column_name("miners", "invalid_column")
    
    def test_select_query_building(self):
        """Test SELECT query building."""
        query, params = SafeQueryBuilder.build_select_query(
            table="miners",
            columns=["id", "config"],
            where_conditions={"id": "miner_001"},
            order_by="created_at",
            limit=10
        )
        
        assert "SELECT id, config FROM miners" in query
        assert "WHERE id = ?" in query
        assert "ORDER BY created_at ASC" in query
        assert "LIMIT ?" in query
        assert params == ["miner_001", 10]
    
    def test_insert_query_building(self):
        """Test INSERT query building."""
        data = {
            "id": "miner_001",
            "config": '{"type": "bitaxe"}',
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        query, params = SafeQueryBuilder.build_insert_query("miners", data)
        
        assert "INSERT INTO miners" in query
        assert "VALUES (?, ?, ?, ?)" in query
        assert len(params) == 4
    
    def test_update_query_building(self):
        """Test UPDATE query building."""
        data = {"config": '{"updated": true}', "updated_at": "2024-01-01T01:00:00"}
        where_conditions = {"id": "miner_001"}
        
        query, params = SafeQueryBuilder.build_update_query("miners", data, where_conditions)
        
        assert "UPDATE miners SET" in query
        assert "WHERE id = ?" in query
        assert len(params) == 3
    
    def test_delete_query_building(self):
        """Test DELETE query building."""
        where_conditions = {"id": "miner_001"}
        
        query, params = SafeQueryBuilder.build_delete_query("miners", where_conditions)
        
        assert "DELETE FROM miners WHERE id = ?" in query
        assert params == ["miner_001"]
    
    def test_time_range_query_building(self):
        """Test time range query building."""
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 2, 0, 0, 0)
        
        query, params = SafeQueryBuilder.build_time_range_query(
            table="miner_metrics",
            miner_id="miner_001",
            start_time=start_time,
            end_time=end_time,
            metric_types=["hashrate", "temperature"]
        )
        
        assert "SELECT * FROM miner_metrics" in query
        assert "WHERE miner_id = ?" in query
        assert "timestamp >= ?" in query
        assert "timestamp <= ?" in query
        assert "metric_type IN (?, ?)" in query
        assert len(params) == 5
    
    def test_aggregation_query_building(self):
        """Test aggregation query building."""
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 2, 0, 0, 0)
        
        query, params = SafeQueryBuilder.build_aggregation_query(
            miner_id="miner_001",
            start_time=start_time,
            end_time=end_time,
            interval="1h",
            metric_types=["hashrate"]
        )
        
        assert "SELECT" in query
        assert "AVG(value) as avg_value" in query
        assert "GROUP BY" in query
        assert "ORDER BY time_bucket ASC" in query
        assert len(params) == 4


class TestGenericInputValidation:
    """Test generic input validation function."""
    
    def test_generic_validation(self):
        """Test generic input validation."""
        validation_rules = {
            'name': {
                'required': True,
                'type': str,
                'validator': DataSanitizer.sanitize_miner_name
            },
            'port': {
                'required': False,
                'type': int,
                'validator': lambda x: PortValidator.validate_port(x)
            }
        }
        
        # Valid data
        valid_data = {'name': 'miner1', 'port': 80}
        result = validate_input_data(valid_data, validation_rules)
        assert result['name'] == 'miner1'
        assert result['port'] == 80
        
        # Missing required field
        invalid_data = {'port': 80}
        with pytest.raises(ValidationError):
            validate_input_data(invalid_data, validation_rules)
        
        # Invalid type
        invalid_data = {'name': 123, 'port': 80}
        with pytest.raises(ValidationError):
            validate_input_data(invalid_data, validation_rules)


if __name__ == "__main__":
    pytest.main([__file__])