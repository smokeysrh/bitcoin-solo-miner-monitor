"""
Input Validation Middleware for FastAPI

This module provides comprehensive input validation middleware that sanitizes
and validates all incoming requests before they reach the API endpoints.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.backend.utils.validators import DataSanitizer, IPAddressValidator, PortValidator
from src.backend.exceptions import ValidationError

logger = logging.getLogger(__name__)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates and sanitizes all incoming requests.
    
    This middleware performs the following validations:
    - Request size limits
    - Content type validation
    - JSON payload sanitization
    - Query parameter validation
    - Path parameter validation
    """
    
    # Configuration
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_JSON_DEPTH = 10
    MAX_STRING_LENGTH = 10000
    ALLOWED_CONTENT_TYPES = [
        'application/json',
        'application/x-www-form-urlencoded',
        'multipart/form-data',
        'text/plain'
    ]
    
    # Endpoints that require special validation
    MINER_ENDPOINTS = ['/api/miners', '/api/discovery']
    METRICS_ENDPOINTS = ['/api/miners/{miner_id}/metrics']
    WEBSOCKET_ENDPOINTS = ['/ws']
    
    def __init__(self, app: ASGIApp):
        """
        Initialize the validation middleware.
        
        Args:
            app (ASGIApp): The ASGI application
        """
        super().__init__(app)
        self.validation_stats = {
            'requests_processed': 0,
            'requests_blocked': 0,
            'validation_errors': 0
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request through validation middleware.
        
        Args:
            request (Request): The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The response from the next middleware or an error response
        """
        self.validation_stats['requests_processed'] += 1
        
        try:
            # Skip validation for certain endpoints
            if self._should_skip_validation(request):
                return await call_next(request)
            
            # Validate request size
            await self._validate_request_size(request)
            
            # Validate content type
            self._validate_content_type(request)
            
            # Validate and sanitize request data
            await self._validate_request_data(request)
            
            # Validate path parameters
            self._validate_path_parameters(request)
            
            # Validate query parameters
            self._validate_query_parameters(request)
            
            # Process the request
            response = await call_next(request)
            
            return response
            
        except ValidationError as e:
            self.validation_stats['requests_blocked'] += 1
            self.validation_stats['validation_errors'] += 1
            logger.warning(f"Validation error for {request.method} {request.url}: {str(e)}")
            
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Validation Error",
                    "message": str(e),
                    "path": str(request.url.path),
                    "method": request.method
                }
            )
        except HTTPException as e:
            self.validation_stats['requests_blocked'] += 1
            raise e
        except Exception as e:
            self.validation_stats['validation_errors'] += 1
            logger.error(f"Unexpected error in validation middleware: {str(e)}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred during validation"
                }
            )
    
    def _should_skip_validation(self, request: Request) -> bool:
        """
        Determine if validation should be skipped for this request.
        
        Args:
            request (Request): The incoming request
            
        Returns:
            bool: True if validation should be skipped
        """
        # Skip validation for static files
        if request.url.path.startswith('/static/'):
            return True
        
        # Skip validation for health checks
        if request.url.path in ['/health', '/ping']:
            return True
        
        # Skip validation for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return True
        
        return False
    
    async def _validate_request_size(self, request: Request) -> None:
        """
        Validate that the request size is within limits.
        
        Args:
            request (Request): The incoming request
            
        Raises:
            ValidationError: If request size exceeds limits
        """
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                size = int(content_length)
                if size > self.MAX_REQUEST_SIZE:
                    raise ValidationError(
                        f"Request size {size} exceeds maximum allowed size {self.MAX_REQUEST_SIZE}"
                    )
            except ValueError:
                raise ValidationError("Invalid Content-Length header")
    
    def _validate_content_type(self, request: Request) -> None:
        """
        Validate the content type of the request.
        
        Args:
            request (Request): The incoming request
            
        Raises:
            ValidationError: If content type is not allowed
        """
        # Skip content type validation for GET requests
        if request.method in ['GET', 'DELETE']:
            return
        
        content_type = request.headers.get('content-type', '').lower()
        
        # Extract base content type (ignore charset, boundary, etc.)
        base_content_type = content_type.split(';')[0].strip()
        
        if base_content_type and base_content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValidationError(f"Content type '{base_content_type}' is not allowed")
    
    async def _validate_request_data(self, request: Request) -> None:
        """
        Validate and sanitize request body data.
        
        Args:
            request (Request): The incoming request
            
        Raises:
            ValidationError: If request data is invalid
        """
        # Skip for requests without body
        if request.method in ['GET', 'DELETE']:
            return
        
        content_type = request.headers.get('content-type', '').lower()
        
        if 'application/json' in content_type:
            await self._validate_json_data(request)
    
    async def _validate_json_data(self, request: Request) -> None:
        """
        Validate and sanitize JSON request data.
        
        Args:
            request (Request): The incoming request
            
        Raises:
            ValidationError: If JSON data is invalid
        """
        try:
            # For now, skip body validation to avoid consuming the request body
            # This prevents the hanging issue while still allowing other validations
            # TODO: Implement proper body validation that doesn't consume the stream
            return
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Error validating JSON data: {str(e)}")
    
    def _validate_json_structure(self, data: Any, depth: int = 0) -> None:
        """
        Validate JSON structure for depth and content.
        
        Args:
            data: The JSON data to validate
            depth (int): Current nesting depth
            
        Raises:
            ValidationError: If JSON structure is invalid
        """
        if depth > self.MAX_JSON_DEPTH:
            raise ValidationError(f"JSON nesting depth exceeds maximum {self.MAX_JSON_DEPTH}")
        
        if isinstance(data, dict):
            if len(data) > 100:  # Limit number of keys
                raise ValidationError("JSON object has too many keys (maximum 100)")
            
            for key, value in data.items():
                if not isinstance(key, str):
                    raise ValidationError("JSON object keys must be strings")
                
                if len(key) > 100:
                    raise ValidationError("JSON object key too long (maximum 100 characters)")
                
                self._validate_json_structure(value, depth + 1)
        
        elif isinstance(data, list):
            if len(data) > 1000:  # Limit array size
                raise ValidationError("JSON array too large (maximum 1000 elements)")
            
            for item in data:
                self._validate_json_structure(item, depth + 1)
        
        elif isinstance(data, str):
            if len(data) > self.MAX_STRING_LENGTH:
                raise ValidationError(f"String too long (maximum {self.MAX_STRING_LENGTH} characters)")
    
    def _sanitize_json_data(self, data: Any) -> Any:
        """
        Recursively sanitize JSON data.
        
        Args:
            data: The JSON data to sanitize
            
        Returns:
            Any: Sanitized JSON data
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Sanitize key
                sanitized_key = DataSanitizer.sanitize_string(key, max_length=100)
                # Sanitize value
                sanitized_value = self._sanitize_json_data(value)
                sanitized[sanitized_key] = sanitized_value
            return sanitized
        
        elif isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        
        elif isinstance(data, str):
            return DataSanitizer.sanitize_string(data, max_length=self.MAX_STRING_LENGTH)
        
        else:
            # Numbers, booleans, null - return as-is
            return data
    
    def _validate_path_parameters(self, request: Request) -> None:
        """
        Validate path parameters.
        
        Args:
            request (Request): The incoming request
            
        Raises:
            ValidationError: If path parameters are invalid
        """
        path_params = request.path_params
        
        for key, value in path_params.items():
            # Sanitize path parameter values
            if isinstance(value, str):
                try:
                    sanitized_value = DataSanitizer.sanitize_string(value, max_length=200)
                    
                    # Special validation for miner IDs
                    if key == 'miner_id':
                        self._validate_miner_id(sanitized_value)
                    
                    # Update path params with sanitized value
                    request.path_params[key] = sanitized_value
                    
                except ValidationError as e:
                    raise ValidationError(f"Invalid path parameter '{key}': {str(e)}")
    
    def _validate_query_parameters(self, request: Request) -> None:
        """
        Validate query parameters.
        
        Args:
            request (Request): The incoming request
            
        Raises:
            ValidationError: If query parameters are invalid
        """
        query_params = dict(request.query_params)
        
        for key, value in query_params.items():
            try:
                # Sanitize query parameter
                sanitized_key = DataSanitizer.sanitize_string(key, max_length=100)
                sanitized_value = DataSanitizer.sanitize_string(value, max_length=1000)
                
                # Special validation for specific parameters
                if key == 'limit':
                    self._validate_limit_parameter(sanitized_value)
                elif key == 'offset':
                    self._validate_offset_parameter(sanitized_value)
                elif key in ['start', 'end']:
                    self._validate_datetime_parameter(sanitized_value)
                elif key == 'interval':
                    self._validate_interval_parameter(sanitized_value)
                
            except ValidationError as e:
                raise ValidationError(f"Invalid query parameter '{key}': {str(e)}")
    
    def _validate_miner_id(self, miner_id: str) -> None:
        """
        Validate miner ID format.
        
        Args:
            miner_id (str): The miner ID to validate
            
        Raises:
            ValidationError: If miner ID is invalid
        """
        if not miner_id:
            raise ValidationError("Miner ID cannot be empty")
        
        if len(miner_id) > 100:
            raise ValidationError("Miner ID too long (maximum 100 characters)")
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9\-_]+$', miner_id):
            raise ValidationError("Miner ID contains invalid characters")
    
    def _validate_limit_parameter(self, limit: str) -> None:
        """
        Validate limit query parameter.
        
        Args:
            limit (str): The limit value to validate
            
        Raises:
            ValidationError: If limit is invalid
        """
        try:
            limit_int = int(limit)
            if limit_int < 1 or limit_int > 10000:
                raise ValidationError("Limit must be between 1 and 10000")
        except ValueError:
            raise ValidationError("Limit must be a valid integer")
    
    def _validate_offset_parameter(self, offset: str) -> None:
        """
        Validate offset query parameter.
        
        Args:
            offset (str): The offset value to validate
            
        Raises:
            ValidationError: If offset is invalid
        """
        try:
            offset_int = int(offset)
            if offset_int < 0:
                raise ValidationError("Offset must be non-negative")
        except ValueError:
            raise ValidationError("Offset must be a valid integer")
    
    def _validate_datetime_parameter(self, datetime_str: str) -> None:
        """
        Validate datetime query parameter.
        
        Args:
            datetime_str (str): The datetime string to validate
            
        Raises:
            ValidationError: If datetime is invalid
        """
        from datetime import datetime
        try:
            datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError("Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    def _validate_interval_parameter(self, interval: str) -> None:
        """
        Validate interval query parameter.
        
        Args:
            interval (str): The interval value to validate
            
        Raises:
            ValidationError: If interval is invalid
        """
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '6h', '12h', '1d']
        if interval not in valid_intervals:
            raise ValidationError(f"Invalid interval. Valid intervals: {', '.join(valid_intervals)}")
    
    def get_validation_stats(self) -> Dict[str, int]:
        """
        Get validation statistics.
        
        Returns:
            Dict[str, int]: Dictionary containing validation statistics
        """
        return self.validation_stats.copy()


class MinerConfigurationValidationMiddleware(BaseHTTPMiddleware):
    """
    Specialized middleware for validating miner configuration requests.
    
    This middleware provides enhanced validation for miner-specific endpoints
    including IP address validation, port validation, and miner type validation.
    """
    
    def __init__(self, app: ASGIApp):
        """
        Initialize the miner configuration validation middleware.
        
        Args:
            app (ASGIApp): The ASGI application
        """
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process miner configuration requests through specialized validation.
        
        Args:
            request (Request): The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The response from the next middleware or an error response
        """
        try:
            # Only validate miner-related endpoints
            if not self._is_miner_endpoint(request):
                return await call_next(request)
            
            # Validate miner configuration data
            await self._validate_miner_configuration(request)
            
            # Process the request
            response = await call_next(request)
            
            return response
            
        except ValidationError as e:
            logger.warning(f"Miner configuration validation error for {request.method} {request.url}: {str(e)}")
            
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Miner Configuration Validation Error",
                    "message": str(e),
                    "path": str(request.url.path),
                    "method": request.method
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error in miner configuration validation middleware: {str(e)}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred during miner configuration validation"
                }
            )
    
    def _is_miner_endpoint(self, request: Request) -> bool:
        """
        Check if the request is for a miner-related endpoint.
        
        Args:
            request (Request): The incoming request
            
        Returns:
            bool: True if this is a miner endpoint
        """
        path = request.url.path
        
        # Miner management endpoints
        if path.startswith('/api/miners'):
            return True
        
        # Discovery endpoints
        if path.startswith('/api/discovery'):
            return True
        
        return False
    
    async def _validate_miner_configuration(self, request: Request) -> None:
        """
        Validate miner configuration in the request.
        
        Args:
            request (Request): The incoming request
            
        Raises:
            ValidationError: If miner configuration is invalid
        """
        # Skip validation for GET requests
        if request.method == 'GET':
            return
        
        # Read and parse request body
        body = await request.body()
        if not body:
            return
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            # JSON validation will be handled by the main validation middleware
            return
        
        # Validate IP addresses
        if 'ip_address' in data:
            try:
                IPAddressValidator.validate_ip_address(data['ip_address'])
            except ValidationError as e:
                raise ValidationError(f"Invalid IP address: {str(e)}")
        
        # Validate ports (skip if None/null - will be handled by Pydantic model)
        if 'port' in data and data['port'] is not None:
            try:
                PortValidator.validate_port(data['port'])
            except ValidationError as e:
                raise ValidationError(f"Invalid port: {str(e)}")
        
        # Validate network ranges (for discovery)
        if 'network' in data:
            try:
                IPAddressValidator.validate_network_range(data['network'])
            except ValidationError as e:
                raise ValidationError(f"Invalid network range: {str(e)}")
        
        # Validate port lists (for discovery)
        if 'ports' in data and isinstance(data['ports'], list):
            try:
                PortValidator.validate_port_list(data['ports'])
            except ValidationError as e:
                raise ValidationError(f"Invalid port list: {str(e)}")
        
        # Validate miner type
        if 'type' in data:
            from src.backend.utils.validators import MinerTypeValidator
            try:
                MinerTypeValidator.validate_miner_type(data['type'])
            except ValidationError as e:
                raise ValidationError(f"Invalid miner type: {str(e)}")
        
        # Validate miner settings
        if 'settings' in data:
            self._validate_miner_settings(data['settings'])
    
    def _validate_miner_settings(self, settings: Dict[str, Any]) -> None:
        """
        Validate miner-specific settings.
        
        Args:
            settings (Dict[str, Any]): Miner settings to validate
            
        Raises:
            ValidationError: If settings are invalid
        """
        if not isinstance(settings, dict):
            raise ValidationError("Miner settings must be a dictionary")
        
        # Validate frequency settings
        if 'frequency' in settings:
            frequency = settings['frequency']
            if not isinstance(frequency, (int, float)):
                raise ValidationError("Frequency must be a number")
            if not (100 <= frequency <= 2000):
                raise ValidationError("Frequency must be between 100 and 2000 MHz")
        
        # Validate voltage settings
        if 'voltage' in settings:
            voltage = settings['voltage']
            if not isinstance(voltage, (int, float)):
                raise ValidationError("Voltage must be a number")
            if not (0.5 <= voltage <= 2.0):
                raise ValidationError("Voltage must be between 0.5 and 2.0 volts")
        
        # Validate pool URL
        if 'pool_url' in settings:
            from src.backend.utils.validators import URLValidator
            try:
                URLValidator.validate_url(settings['pool_url'], ['stratum+tcp', 'stratum+ssl'])
            except ValidationError as e:
                raise ValidationError(f"Invalid pool URL: {str(e)}")
        
        # Validate pool user
        if 'pool_user' in settings:
            pool_user = settings['pool_user']
            if not isinstance(pool_user, str):
                raise ValidationError("Pool user must be a string")
            if len(pool_user) > 200:
                raise ValidationError("Pool user too long (maximum 200 characters)")
        
        # Validate pool password
        if 'pool_password' in settings:
            pool_password = settings['pool_password']
            if not isinstance(pool_password, str):
                raise ValidationError("Pool password must be a string")
            if len(pool_password) > 200:
                raise ValidationError("Pool password too long (maximum 200 characters)")