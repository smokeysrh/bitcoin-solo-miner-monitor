"""
Demonstration of comprehensive input validation implementation.

This script demonstrates all aspects of the input validation system
including IP addresses, ports, data sanitization, and SQL injection prevention.
"""

import asyncio
import json
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
    MinerTypeValidator,
    URLValidator,
    validate_input_data
)
from src.backend.utils.query_builder import (
    SafeQueryBuilder,
    DatabaseQueryExecutor
)
from src.backend.exceptions import ValidationError


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")


def demo_ip_address_validation():
    """Demonstrate IP address validation."""
    print_section("IP Address Validation")
    
    # Valid IP addresses
    valid_ips = [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "127.0.0.1",
        "::1",
        "2001:db8::1"
    ]
    
    print("✅ Valid IP addresses:")
    for ip in valid_ips:
        try:
            validated = IPAddressValidator.validate_ip_address(ip)
            print(f"  {ip} -> {validated}")
        except ValidationError as e:
            print(f"  {ip} -> ERROR: {e}")
    
    # Invalid IP addresses
    invalid_ips = [
        "256.256.256.256",
        "192.168.1",
        "not.an.ip.address",
        "",
        "192.168.1.-1"
    ]
    
    print("\n❌ Invalid IP addresses:")
    for ip in invalid_ips:
        try:
            validated = IPAddressValidator.validate_ip_address(ip)
            print(f"  {ip} -> {validated} (UNEXPECTED SUCCESS)")
        except ValidationError as e:
            print(f"  {ip} -> BLOCKED: {e}")
    
    # Network ranges
    print_subsection("Network Range Validation")
    
    valid_networks = [
        "192.168.1.0/24",
        "10.0.0.0/8",
        "172.16.0.0/16"
    ]
    
    print("✅ Valid network ranges:")
    for network in valid_networks:
        try:
            validated = IPAddressValidator.validate_network_range(network)
            print(f"  {network} -> {validated}")
        except ValidationError as e:
            print(f"  {network} -> ERROR: {e}")


def demo_port_validation():
    """Demonstrate port number validation."""
    print_section("Port Number Validation")
    
    # Valid ports
    valid_ports = [80, 443, 8080, 4028, "22", "9999"]
    
    print("✅ Valid ports:")
    for port in valid_ports:
        try:
            validated = PortValidator.validate_port(port)
            print(f"  {port} -> {validated}")
        except ValidationError as e:
            print(f"  {port} -> ERROR: {e}")
    
    # Invalid ports
    invalid_ports = [0, -1, 65536, 100000, "not_a_port"]
    
    print("\n❌ Invalid ports:")
    for port in invalid_ports:
        try:
            validated = PortValidator.validate_port(port)
            print(f"  {port} -> {validated} (UNEXPECTED SUCCESS)")
        except ValidationError as e:
            print(f"  {port} -> BLOCKED: {e}")
    
    # Port type validation
    print_subsection("Port Type Validation")
    
    print("System ports (1-1023):")
    try:
        result = PortValidator.validate_port(80, 'system')
        print(f"  Port 80 as system port: {result}")
    except ValidationError as e:
        print(f"  Port 80 as system port: ERROR: {e}")
    
    try:
        result = PortValidator.validate_port(8080, 'system')
        print(f"  Port 8080 as system port: {result} (UNEXPECTED SUCCESS)")
    except ValidationError as e:
        print(f"  Port 8080 as system port: BLOCKED: {e}")


def demo_data_sanitization():
    """Demonstrate data sanitization."""
    print_section("Data Sanitization")
    
    # SQL injection attempts
    print_subsection("SQL Injection Prevention")
    
    sql_injection_attempts = [
        "'; DROP TABLE miners; --",
        "1 OR 1=1",
        "UNION SELECT * FROM users",
        "admin'--",
        "/* comment */ SELECT"
    ]
    
    print("❌ SQL injection attempts:")
    for attempt in sql_injection_attempts:
        try:
            sanitized = DataSanitizer.sanitize_string(attempt)
            print(f"  '{attempt}' -> '{sanitized}' (UNEXPECTED SUCCESS)")
        except ValidationError as e:
            print(f"  '{attempt}' -> BLOCKED: {e}")
    
    # XSS attempts
    print_subsection("XSS Prevention")
    
    xss_attempts = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "<iframe src='evil.com'></iframe>",
        "onclick='alert(1)'"
    ]
    
    print("❌ XSS attempts:")
    for attempt in xss_attempts:
        try:
            sanitized = DataSanitizer.sanitize_string(attempt)
            print(f"  '{attempt}' -> '{sanitized}' (UNEXPECTED SUCCESS)")
        except ValidationError as e:
            print(f"  '{attempt}' -> BLOCKED: {e}")
    
    # Valid strings
    print_subsection("Valid String Sanitization")
    
    valid_strings = [
        "normal string",
        "miner-name_123",
        "192.168.1.1",
        "valid@email.com"
    ]
    
    print("✅ Valid strings:")
    for string in valid_strings:
        try:
            sanitized = DataSanitizer.sanitize_string(string)
            print(f"  '{string}' -> '{sanitized}'")
        except ValidationError as e:
            print(f"  '{string}' -> ERROR: {e}")


def demo_miner_validation():
    """Demonstrate miner-specific validation."""
    print_section("Miner Validation")
    
    # Valid miner types
    print_subsection("Miner Type Validation")
    
    valid_types = ["bitaxe", "avalon_nano", "magic_miner", "BITAXE"]
    
    print("✅ Valid miner types:")
    for miner_type in valid_types:
        try:
            validated = MinerTypeValidator.validate_miner_type(miner_type)
            print(f"  {miner_type} -> {validated}")
        except ValidationError as e:
            print(f"  {miner_type} -> ERROR: {e}")
    
    # Invalid miner types
    invalid_types = ["unknown_miner", "", "invalid_type"]
    
    print("\n❌ Invalid miner types:")
    for miner_type in invalid_types:
        try:
            validated = MinerTypeValidator.validate_miner_type(miner_type)
            print(f"  {miner_type} -> {validated} (UNEXPECTED SUCCESS)")
        except ValidationError as e:
            print(f"  {miner_type} -> BLOCKED: {e}")
    
    # Miner name validation
    print_subsection("Miner Name Validation")
    
    valid_names = [
        "Miner 1",
        "bitaxe-001",
        "avalon_nano_2"
    ]
    
    print("✅ Valid miner names:")
    for name in valid_names:
        try:
            validated = DataSanitizer.sanitize_miner_name(name)
            print(f"  '{name}' -> '{validated}'")
        except ValidationError as e:
            print(f"  '{name}' -> ERROR: {e}")
    
    invalid_names = [
        "",
        "miner@#$%",
        "<script>alert(1)</script>",
        "a" * 101  # Too long
    ]
    
    print("\n❌ Invalid miner names:")
    for name in invalid_names:
        try:
            validated = DataSanitizer.sanitize_miner_name(name)
            print(f"  '{name}' -> '{validated}' (UNEXPECTED SUCCESS)")
        except ValidationError as e:
            print(f"  '{name}' -> BLOCKED: {e}")


def demo_pydantic_models():
    """Demonstrate Pydantic model validation."""
    print_section("Pydantic Model Validation")
    
    # Valid miner add request
    print_subsection("Miner Add Request")
    
    valid_miner_data = {
        "type": "bitaxe",
        "ip_address": "10.0.0.100",
        "port": 80,
        "name": "Test Bitaxe Miner"
    }
    
    try:
        miner_request = MinerAddRequest(**valid_miner_data)
        print("✅ Valid miner add request:")
        print(f"  Type: {miner_request.type}")
        print(f"  IP: {miner_request.ip_address}")
        print(f"  Port: {miner_request.port}")
        print(f"  Name: {miner_request.name}")
    except Exception as e:
        print(f"❌ Miner add request failed: {e}")
    
    # Invalid miner add request
    invalid_miner_data = {
        "type": "unknown_miner",
        "ip_address": "256.256.256.256",
        "port": 80
    }
    
    try:
        miner_request = MinerAddRequest(**invalid_miner_data)
        print(f"❌ Invalid miner request succeeded (UNEXPECTED): {miner_request}")
    except Exception as e:
        print(f"✅ Invalid miner request blocked: {e}")
    
    # Discovery request
    print_subsection("Discovery Request")
    
    valid_discovery = {
        "network": "192.168.1.0/24",
        "ports": [80, 443, 4028],
        "timeout": 10
    }
    
    try:
        discovery_request = DiscoveryRequest(**valid_discovery)
        print("✅ Valid discovery request:")
        print(f"  Network: {discovery_request.network}")
        print(f"  Ports: {discovery_request.ports}")
        print(f"  Timeout: {discovery_request.timeout}")
    except Exception as e:
        print(f"❌ Discovery request failed: {e}")


def demo_url_validation():
    """Demonstrate URL validation."""
    print_section("URL Validation")
    
    # Valid URLs
    valid_urls = [
        "http://example.com",
        "https://example.com",
        "http://192.168.1.1:8080",
        "stratum+tcp://pool.example.com:4444"
    ]
    
    print("✅ Valid URLs:")
    for url in valid_urls:
        try:
            validated = URLValidator.validate_url(url, ['http', 'https', 'stratum+tcp'])
            print(f"  {url} -> {validated}")
        except ValidationError as e:
            print(f"  {url} -> ERROR: {e}")
    
    # Invalid URLs
    invalid_urls = [
        "ftp://example.com",  # Invalid scheme
        "example.com",        # No scheme
        "",                   # Empty
        "http://",           # No hostname
    ]
    
    print("\n❌ Invalid URLs:")
    for url in invalid_urls:
        try:
            validated = URLValidator.validate_url(url)
            print(f"  {url} -> {validated} (UNEXPECTED SUCCESS)")
        except ValidationError as e:
            print(f"  {url} -> BLOCKED: {e}")


async def demo_safe_query_builder():
    """Demonstrate safe query builder."""
    print_section("Safe Query Builder")
    
    # Create temporary database
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    
    try:
        import aiosqlite
        conn = await aiosqlite.connect(temp_file.name)
        
        # Create test table
        await conn.execute("""
            CREATE TABLE miners (
                id TEXT PRIMARY KEY,
                config TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await conn.commit()
        
        executor = DatabaseQueryExecutor(conn)
        
        # Safe insert
        print_subsection("Safe Insert Query")
        
        insert_data = {
            "id": "test_miner_001",
            "config": json.dumps({"type": "bitaxe", "ip": "10.0.0.100"}),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        insert_query, insert_params = SafeQueryBuilder.build_insert_query("miners", insert_data)
        print(f"Query: {insert_query}")
        print(f"Params: {insert_params}")
        
        success = await executor.execute_safe_insert(insert_query, insert_params)
        print(f"✅ Insert successful: {success}")
        
        # Safe select
        print_subsection("Safe Select Query")
        
        select_query, select_params = SafeQueryBuilder.build_select_query(
            table="miners",
            columns=["id", "config"],
            where_conditions={"id": "test_miner_001"}
        )
        
        print(f"Query: {select_query}")
        print(f"Params: {select_params}")
        
        results = await executor.execute_safe_query(select_query, select_params)
        print(f"✅ Results: {results}")
        
        # Test malicious table name
        print_subsection("Malicious Input Prevention")
        
        try:
            malicious_query, _ = SafeQueryBuilder.build_select_query(
                table="miners; DROP TABLE miners; --",
                columns=["id"]
            )
            print(f"❌ Malicious query succeeded (UNEXPECTED): {malicious_query}")
        except ValidationError as e:
            print(f"✅ Malicious table name blocked: {e}")
        
        # Test malicious column name
        try:
            malicious_query, _ = SafeQueryBuilder.build_select_query(
                table="miners",
                columns=["id; DROP TABLE miners; --"]
            )
            print(f"❌ Malicious query succeeded (UNEXPECTED): {malicious_query}")
        except ValidationError as e:
            print(f"✅ Malicious column name blocked: {e}")
        
        await conn.close()
        
    finally:
        # Cleanup
        os.unlink(temp_file.name)


def demo_generic_validation():
    """Demonstrate generic validation framework."""
    print_section("Generic Validation Framework")
    
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
    
    # Valid data
    print_subsection("Valid Data Validation")
    
    valid_data = {
        'miner_name': 'Test Miner',
        'ip_address': '10.0.0.100',
        'port': 80
    }
    
    try:
        validated_data = validate_input_data(valid_data, validation_rules)
        print("✅ Valid data validation successful:")
        for key, value in validated_data.items():
            print(f"  {key}: {value}")
    except ValidationError as e:
        print(f"❌ Valid data validation failed: {e}")
    
    # Invalid data
    print_subsection("Invalid Data Validation")
    
    invalid_data = {
        'miner_name': "'; DROP TABLE miners; --",
        'ip_address': '256.256.256.256',
        'port': 'not_a_port'
    }
    
    try:
        validated_data = validate_input_data(invalid_data, validation_rules)
        print(f"❌ Invalid data validation succeeded (UNEXPECTED): {validated_data}")
    except ValidationError as e:
        print(f"✅ Invalid data validation blocked: {e}")


async def main():
    """Run all validation demonstrations."""
    print("🔒 Comprehensive Input Validation Demonstration")
    print("This demo shows all aspects of the input validation system.")
    
    # Run all demonstrations
    demo_ip_address_validation()
    demo_port_validation()
    demo_data_sanitization()
    demo_miner_validation()
    demo_pydantic_models()
    demo_url_validation()
    await demo_safe_query_builder()
    demo_generic_validation()
    
    print_section("Summary")
    print("✅ All validation components demonstrated successfully!")
    print("🔒 The system provides comprehensive protection against:")
    print("   • SQL injection attacks")
    print("   • XSS attacks")
    print("   • Invalid IP addresses and ports")
    print("   • Malicious input data")
    print("   • Unauthorized database operations")
    print("   • Invalid miner configurations")
    print("   • Malformed network requests")


if __name__ == "__main__":
    asyncio.run(main())