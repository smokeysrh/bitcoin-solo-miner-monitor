"""
Input validation utilities for the Bitcoin Solo Miner Monitoring App.

This module provides comprehensive input validation including IP addresses,
port numbers, and data sanitization to prevent security vulnerabilities.
"""

import ipaddress
import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field, validator, ValidationError
from src.backend.exceptions import ValidationError as AppValidationError


class IPAddressValidator:
    """Utility class for IP address validation."""
    
    @staticmethod
    def validate_ip_address(ip: str) -> str:
        """
        Validate IP address format and return normalized version.
        
        Args:
            ip (str): IP address to validate
            
        Returns:
            str: Normalized IP address
            
        Raises:
            AppValidationError: If IP address is invalid
        """
        if not ip or not isinstance(ip, str):
            raise AppValidationError("IP address must be a non-empty string")
        
        # Remove whitespace
        ip = ip.strip()
        
        try:
            # Parse and validate IP address
            ip_obj = ipaddress.ip_address(ip)
            
            # Check if it's a valid IPv4 or IPv6 address
            if isinstance(ip_obj, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
                return str(ip_obj)
            else:
                raise AppValidationError(f"Invalid IP address format: {ip}")
                
        except ipaddress.AddressValueError as e:
            raise AppValidationError(f"Invalid IP address: {ip} - {str(e)}")
        except Exception as e:
            raise AppValidationError(f"IP address validation failed: {str(e)}")
    
    @staticmethod
    def validate_network_range(network: str) -> str:
        """
        Validate network range in CIDR notation.
        
        Args:
            network (str): Network range to validate (e.g., "192.168.1.0/24")
            
        Returns:
            str: Normalized network range
            
        Raises:
            AppValidationError: If network range is invalid
        """
        if not network or not isinstance(network, str):
            raise AppValidationError("Network range must be a non-empty string")
        
        network = network.strip()
        
        try:
            # Parse and validate network range
            network_obj = ipaddress.ip_network(network, strict=False)
            return str(network_obj)
        except ipaddress.AddressValueError as e:
            raise AppValidationError(f"Invalid network range: {network} - {str(e)}")
        except Exception as e:
            raise AppValidationError(f"Network range validation failed: {str(e)}")


class PortValidator:
    """Utility class for port number validation."""
    
    # Valid port ranges for different services
    VALID_PORT_RANGES = {
        'system': (1, 1023),          # System/privileged ports
        'registered': (1024, 49151),   # Registered ports
        'dynamic': (49152, 65535),     # Dynamic/private ports
        'all': (1, 65535)              # All valid ports
    }
    
    # Common miner ports
    COMMON_MINER_PORTS = [80, 443, 4028, 4029, 8080, 8081, 8888, 9999]
    
    @staticmethod
    def validate_port(port: Union[int, str], port_type: str = 'all') -> int:
        """
        Validate port number and return as integer.
        
        Args:
            port (Union[int, str]): Port number to validate
            port_type (str): Type of port validation ('system', 'registered', 'dynamic', 'all')
            
        Returns:
            int: Validated port number
            
        Raises:
            AppValidationError: If port is invalid
        """
        # Convert to integer if string
        try:
            if isinstance(port, str):
                port = int(port.strip())
            elif not isinstance(port, int):
                raise AppValidationError("Port must be an integer or string representation of integer")
        except ValueError:
            raise AppValidationError(f"Invalid port format: {port}")
        
        # Check port range
        if port_type not in PortValidator.VALID_PORT_RANGES:
            raise AppValidationError(f"Invalid port type: {port_type}")
        
        min_port, max_port = PortValidator.VALID_PORT_RANGES[port_type]
        
        if not (min_port <= port <= max_port):
            raise AppValidationError(
                f"Port {port} is outside valid range {min_port}-{max_port} for type '{port_type}'"
            )
        
        return port
    
    @staticmethod
    def validate_port_list(ports: List[Union[int, str]], port_type: str = 'all') -> List[int]:
        """
        Validate a list of port numbers.
        
        Args:
            ports (List[Union[int, str]]): List of ports to validate
            port_type (str): Type of port validation
            
        Returns:
            List[int]: List of validated port numbers
            
        Raises:
            AppValidationError: If any port is invalid
        """
        if not isinstance(ports, list):
            raise AppValidationError("Ports must be provided as a list")
        
        validated_ports = []
        for i, port in enumerate(ports):
            try:
                validated_port = PortValidator.validate_port(port, port_type)
                validated_ports.append(validated_port)
            except AppValidationError as e:
                raise AppValidationError(f"Invalid port at index {i}: {str(e)}")
        
        return validated_ports


class DataSanitizer:
    """Utility class for data sanitization."""
    
    # Patterns for potentially dangerous content
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\bUNION\s+SELECT\b)",
        r"(\b(SCRIPT|JAVASCRIPT|VBSCRIPT)\b)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
    ]
    
    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize string input by removing potentially dangerous content.
        
        Args:
            value (str): String to sanitize
            max_length (Optional[int]): Maximum allowed length
            
        Returns:
            str: Sanitized string
            
        Raises:
            AppValidationError: If string contains dangerous content
        """
        if not isinstance(value, str):
            raise AppValidationError("Value must be a string")
        
        # Check for SQL injection patterns
        for pattern in DataSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise AppValidationError("String contains potentially dangerous SQL content")
        
        # Check for XSS patterns
        for pattern in DataSanitizer.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise AppValidationError("String contains potentially dangerous script content")
        
        # Trim whitespace
        value = value.strip()
        
        # Check length
        if max_length and len(value) > max_length:
            raise AppValidationError(f"String length {len(value)} exceeds maximum {max_length}")
        
        return value
    
    @staticmethod
    def sanitize_miner_name(name: str) -> str:
        """
        Sanitize miner name with specific rules.
        
        Args:
            name (str): Miner name to sanitize
            
        Returns:
            str: Sanitized miner name
            
        Raises:
            AppValidationError: If name is invalid
        """
        if not name:
            raise AppValidationError("Miner name cannot be empty")
        
        # Sanitize basic string
        name = DataSanitizer.sanitize_string(name, max_length=100)
        
        # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
            raise AppValidationError("Miner name can only contain letters, numbers, spaces, hyphens, and underscores")
        
        return name
    
    @staticmethod
    def sanitize_json_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize JSON data.
        
        Args:
            data (Dict[str, Any]): JSON data to sanitize
            
        Returns:
            Dict[str, Any]: Sanitized JSON data
        """
        if not isinstance(data, dict):
            raise AppValidationError("Data must be a dictionary")
        
        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            if not isinstance(key, str):
                raise AppValidationError(f"Dictionary key must be string, got {type(key)}")
            
            sanitized_key = DataSanitizer.sanitize_string(key, max_length=100)
            
            # Sanitize value based on type
            if isinstance(value, str):
                sanitized_value = DataSanitizer.sanitize_string(value, max_length=1000)
            elif isinstance(value, dict):
                sanitized_value = DataSanitizer.sanitize_json_data(value)
            elif isinstance(value, list):
                sanitized_value = [
                    DataSanitizer.sanitize_string(item, max_length=1000) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized_value = value
            
            sanitized[sanitized_key] = sanitized_value
        
        return sanitized


class MinerTypeValidator:
    """Validator for miner types."""
    
    VALID_MINER_TYPES = ['bitaxe', 'avalon_nano', 'magic_miner']
    
    @staticmethod
    def validate_miner_type(miner_type: str) -> str:
        """
        Validate miner type.
        
        Args:
            miner_type (str): Miner type to validate
            
        Returns:
            str: Validated miner type
            
        Raises:
            AppValidationError: If miner type is invalid
        """
        if not miner_type or not isinstance(miner_type, str):
            raise AppValidationError("Miner type must be a non-empty string")
        
        miner_type = miner_type.strip().lower()
        
        if miner_type not in MinerTypeValidator.VALID_MINER_TYPES:
            raise AppValidationError(
                f"Invalid miner type: {miner_type}. "
                f"Valid types are: {', '.join(MinerTypeValidator.VALID_MINER_TYPES)}"
            )
        
        return miner_type


class URLValidator:
    """Validator for URLs and endpoints."""
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> str:
        """
        Validate URL format and scheme.
        
        Args:
            url (str): URL to validate
            allowed_schemes (Optional[List[str]]): List of allowed schemes (default: ['http', 'https'])
            
        Returns:
            str: Validated URL
            
        Raises:
            AppValidationError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise AppValidationError("URL must be a non-empty string")
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        try:
            parsed = urlparse(url.strip())
            
            if not parsed.scheme:
                raise AppValidationError("URL must include a scheme (http/https)")
            
            if parsed.scheme.lower() not in allowed_schemes:
                raise AppValidationError(
                    f"URL scheme '{parsed.scheme}' not allowed. "
                    f"Allowed schemes: {', '.join(allowed_schemes)}"
                )
            
            if not parsed.netloc:
                raise AppValidationError("URL must include a hostname")
            
            return url.strip()
            
        except Exception as e:
            if isinstance(e, AppValidationError):
                raise
            raise AppValidationError(f"Invalid URL format: {str(e)}")


def validate_input_data(data: Dict[str, Any], validation_rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic input validation function.
    
    Args:
        data (Dict[str, Any]): Data to validate
        validation_rules (Dict[str, Any]): Validation rules
        
    Returns:
        Dict[str, Any]: Validated and sanitized data
        
    Raises:
        AppValidationError: If validation fails
    """
    if not isinstance(data, dict):
        raise AppValidationError("Input data must be a dictionary")
    
    validated_data = {}
    
    for field, rules in validation_rules.items():
        value = data.get(field)
        
        # Check required fields
        if rules.get('required', False) and value is None:
            raise AppValidationError(f"Required field '{field}' is missing")
        
        # Skip validation for optional fields that are None
        if value is None:
            continue
        
        # Apply type validation
        expected_type = rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            raise AppValidationError(f"Field '{field}' must be of type {expected_type.__name__}")
        
        # Apply custom validator
        validator_func = rules.get('validator')
        if validator_func:
            try:
                value = validator_func(value)
            except Exception as e:
                raise AppValidationError(f"Validation failed for field '{field}': {str(e)}")
        
        validated_data[field] = value
    
    return validated_data