"""
HTTP Client Utilities with Retry Logic

This module provides HTTP client utilities with built-in retry logic,
exponential backoff, and circuit breaker patterns for miner communications.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, Union
from contextlib import asynccontextmanager

from src.backend.utils.retry_logic import retry_http_request, RetryConfig
from src.backend.services.http_session_manager import get_session_manager
from src.backend.exceptions import MinerConnectionError, MinerTimeoutError, NetworkError
from config.app_config import CONNECTION_TIMEOUT

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    HTTP client with retry logic and session management for miner communications.
    """
    
    def __init__(self, ip_address: str, port: int = 80, 
                 retry_config: Optional[RetryConfig] = None):
        """
        Initialize HTTP client.
        
        Args:
            ip_address: Target IP address
            port: Target port
            retry_config: Optional retry configuration
        """
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
        
        # Use default retry config if not provided
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True
            )
        self.retry_config = retry_config
    
    @retry_http_request(max_attempts=3, base_delay=1.0, max_delay=30.0)
    async def get(self, path: str = "/", params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None, 
                  timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Make a GET request with retry logic.
        
        Args:
            path: Request path
            params: Query parameters
            headers: Request headers
            timeout: Request timeout
            
        Returns:
            Response data as dictionary
            
        Raises:
            MinerConnectionError: If connection fails
            MinerTimeoutError: If request times out
            NetworkError: If network error occurs
        """
        return await self._make_request("GET", path, params=params, 
                                      headers=headers, timeout=timeout)
    
    @retry_http_request(max_attempts=3, base_delay=1.0, max_delay=30.0)
    async def post(self, path: str = "/", data: Optional[Dict[str, Any]] = None,
                   json: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None,
                   timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Make a POST request with retry logic.
        
        Args:
            path: Request path
            data: Form data
            json: JSON data
            headers: Request headers
            timeout: Request timeout
            
        Returns:
            Response data as dictionary
            
        Raises:
            MinerConnectionError: If connection fails
            MinerTimeoutError: If request times out
            NetworkError: If network error occurs
        """
        return await self._make_request("POST", path, data=data, json=json,
                                      headers=headers, timeout=timeout)
    
    @retry_http_request(max_attempts=3, base_delay=1.0, max_delay=30.0)
    async def put(self, path: str = "/", data: Optional[Dict[str, Any]] = None,
                  json: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None,
                  timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Make a PUT request with retry logic.
        
        Args:
            path: Request path
            data: Form data
            json: JSON data
            headers: Request headers
            timeout: Request timeout
            
        Returns:
            Response data as dictionary
            
        Raises:
            MinerConnectionError: If connection fails
            MinerTimeoutError: If request times out
            NetworkError: If network error occurs
        """
        return await self._make_request("PUT", path, data=data, json=json,
                                      headers=headers, timeout=timeout)
    
    async def _make_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request with proper error handling.
        
        Args:
            method: HTTP method
            path: Request path
            **kwargs: Request arguments
            
        Returns:
            Response data as dictionary
            
        Raises:
            MinerConnectionError: If connection fails
            MinerTimeoutError: If request times out
            NetworkError: If network error occurs
        """
        session_manager = await get_session_manager()
        
        # Set default timeout
        timeout = kwargs.get('timeout', CONNECTION_TIMEOUT)
        kwargs['timeout'] = aiohttp.ClientTimeout(total=timeout)
        
        try:
            async with session_manager.get_session(self.ip_address, self.port) as session:
                url = f"{self.base_url}{path}"
                
                async with session.request(method, url, **kwargs) as response:
                    # Check for HTTP errors
                    if response.status >= 400:
                        error_text = await response.text()
                        if response.status >= 500:
                            # Server errors are retryable
                            raise NetworkError(
                                f"Server error {response.status}: {error_text}",
                                context={
                                    'status_code': response.status,
                                    'url': url,
                                    'method': method
                                }
                            )
                        else:
                            # Client errors are not retryable
                            raise MinerConnectionError(
                                f"Client error {response.status}: {error_text}",
                                context={
                                    'status_code': response.status,
                                    'url': url,
                                    'method': method
                                }
                            )
                    
                    # Try to parse JSON response
                    try:
                        return await response.json()
                    except aiohttp.ContentTypeError:
                        # If not JSON, return text
                        text = await response.text()
                        return {'response': text, 'status': response.status}
        
        except asyncio.TimeoutError as e:
            raise MinerTimeoutError(
                f"Request timeout for {method} {self.base_url}{path}",
                ip_address=self.ip_address,
                context={'timeout': timeout, 'method': method, 'path': path}
            )
        
        except aiohttp.ClientConnectorError as e:
            raise MinerConnectionError(
                f"Connection failed to {self.ip_address}:{self.port}",
                ip_address=self.ip_address,
                context={'method': method, 'path': path, 'error': str(e)}
            )
        
        except aiohttp.ClientError as e:
            raise NetworkError(
                f"HTTP client error for {method} {self.base_url}{path}: {str(e)}",
                context={'method': method, 'path': path, 'error': str(e)}
            )
        
        except Exception as e:
            # Catch-all for unexpected errors
            raise NetworkError(
                f"Unexpected error for {method} {self.base_url}{path}: {str(e)}",
                context={'method': method, 'path': path, 'error': str(e)}
            )
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the endpoint.
        
        Returns:
            True if endpoint is healthy, False otherwise
        """
        try:
            from config.app_config import CONNECTION_TIMEOUT
            await self.get("/", timeout=CONNECTION_TIMEOUT)
            return True
        except Exception as e:
            logger.debug(f"Health check failed for {self.ip_address}:{self.port}: {e}")
            return False
    
    def get_endpoint_info(self) -> Dict[str, Any]:
        """
        Get information about this HTTP client endpoint.
        
        Returns:
            Dictionary with endpoint information
        """
        return {
            'ip_address': self.ip_address,
            'port': self.port,
            'base_url': self.base_url,
            'retry_config': {
                'max_attempts': self.retry_config.max_attempts,
                'base_delay': self.retry_config.base_delay,
                'max_delay': self.retry_config.max_delay,
                'exponential_base': self.retry_config.exponential_base,
                'jitter': self.retry_config.jitter
            }
        }


@asynccontextmanager
async def http_client(ip_address: str, port: int = 80, 
                     retry_config: Optional[RetryConfig] = None):
    """
    Context manager for HTTP client with automatic cleanup.
    
    Args:
        ip_address: Target IP address
        port: Target port
        retry_config: Optional retry configuration
        
    Yields:
        HTTPClient: HTTP client instance
    """
    client = HTTPClient(ip_address, port, retry_config)
    try:
        yield client
    finally:
        # Cleanup is handled by the session manager
        pass


# Convenience functions for quick HTTP requests

@retry_http_request(max_attempts=3, base_delay=1.0, max_delay=30.0)
async def get_json(ip_address: str, port: int = 80, path: str = "/",
                   params: Optional[Dict[str, Any]] = None,
                   timeout: Optional[float] = None) -> Dict[str, Any]:
    """
    Make a GET request and return JSON response with retry logic.
    
    Args:
        ip_address: Target IP address
        port: Target port
        path: Request path
        params: Query parameters
        timeout: Request timeout
        
    Returns:
        JSON response as dictionary
    """
    async with http_client(ip_address, port) as client:
        return await client.get(path, params=params, timeout=timeout)


@retry_http_request(max_attempts=3, base_delay=1.0, max_delay=30.0)
async def post_json(ip_address: str, port: int = 80, path: str = "/",
                    json_data: Optional[Dict[str, Any]] = None,
                    timeout: Optional[float] = None) -> Dict[str, Any]:
    """
    Make a POST request with JSON data and return JSON response with retry logic.
    
    Args:
        ip_address: Target IP address
        port: Target port
        path: Request path
        json_data: JSON data to send
        timeout: Request timeout
        
    Returns:
        JSON response as dictionary
    """
    async with http_client(ip_address, port) as client:
        return await client.post(path, json=json_data, timeout=timeout)


async def check_endpoint_health(ip_address: str, port: int = 80) -> bool:
    """
    Check if an endpoint is healthy (responds to requests).
    
    Args:
        ip_address: Target IP address
        port: Target port
        
    Returns:
        True if endpoint is healthy, False otherwise
    """
    try:
        async with http_client(ip_address, port) as client:
            return await client.health_check()
    except Exception:
        return False