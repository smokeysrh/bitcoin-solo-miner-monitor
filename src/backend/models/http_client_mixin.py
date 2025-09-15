"""
HTTP Client Mixin

This module provides a mixin class for miners that need HTTP client functionality
with proper session lifecycle management.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, Union
from contextlib import asynccontextmanager

from src.backend.services.http_session_manager import http_session
from config.app_config import RETRY_ATTEMPTS, RETRY_DELAY

logger = logging.getLogger(__name__)


class HTTPClientMixin:
    """
    Mixin class providing HTTP client functionality with proper session management.
    
    This mixin should be used by miner classes that need to make HTTP requests.
    It provides automatic session management, retry logic, and proper error handling.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the HTTP client mixin."""
        super().__init__(*args, **kwargs)
        self._http_session_active = False
    
    @asynccontextmanager
    async def _http_session_context(self):
        """
        Context manager for HTTP session lifecycle.
        
        Yields:
            aiohttp.ClientSession: HTTP session for this miner
        """
        if not hasattr(self, 'ip_address') or not hasattr(self, 'port'):
            raise AttributeError("HTTPClientMixin requires 'ip_address' and 'port' attributes")
        
        try:
            self._http_session_active = True
            async with http_session(self.ip_address, self.port) as session:
                yield session
        finally:
            self._http_session_active = False
    
    async def _http_get(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make a GET request to the specified endpoint with retry logic.
        
        Args:
            endpoint (str): API endpoint path
            **kwargs: Additional arguments for the request
            
        Returns:
            Optional[Dict[str, Any]]: Response data as dictionary or None if request failed
        """
        return await self._http_request('GET', endpoint, **kwargs)
    
    async def _http_post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make a POST request to the specified endpoint with retry logic.
        
        Args:
            endpoint (str): API endpoint path
            data (Optional[Dict[str, Any]]): Data to send in the request body
            **kwargs: Additional arguments for the request
            
        Returns:
            Optional[Dict[str, Any]]: Response data as dictionary or None if request failed
        """
        if data is not None:
            kwargs['json'] = data
        return await self._http_request('POST', endpoint, **kwargs)
    
    async def _http_patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make a PATCH request to the specified endpoint with retry logic.
        
        Args:
            endpoint (str): API endpoint path
            data (Optional[Dict[str, Any]]): Data to send in the request body
            **kwargs: Additional arguments for the request
            
        Returns:
            Optional[Dict[str, Any]]: Response data as dictionary or None if request failed
        """
        if data is not None:
            kwargs['json'] = data
        return await self._http_request('PATCH', endpoint, **kwargs)
    
    async def _http_put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make a PUT request to the specified endpoint with retry logic.
        
        Args:
            endpoint (str): API endpoint path
            data (Optional[Dict[str, Any]]): Data to send in the request body
            **kwargs: Additional arguments for the request
            
        Returns:
            Optional[Dict[str, Any]]: Response data as dictionary or None if request failed
        """
        if data is not None:
            kwargs['json'] = data
        return await self._http_request('PUT', endpoint, **kwargs)
    
    async def _http_delete(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make a DELETE request to the specified endpoint with retry logic.
        
        Args:
            endpoint (str): API endpoint path
            **kwargs: Additional arguments for the request
            
        Returns:
            Optional[Dict[str, Any]]: Response data as dictionary or None if request failed
        """
        return await self._http_request('DELETE', endpoint, **kwargs)
    
    async def _http_post_form(self, endpoint: str, form_data: Optional[Dict[str, Any]] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make a POST request with form data to the specified endpoint with retry logic.
        
        Args:
            endpoint (str): API endpoint path
            form_data (Optional[Dict[str, Any]]): Form data to send
            **kwargs: Additional arguments for the request
            
        Returns:
            Optional[Dict[str, Any]]: Response data as dictionary or None if request failed
        """
        if form_data is not None:
            kwargs['data'] = form_data
            kwargs['headers'] = kwargs.get('headers', {})
            kwargs['headers']['Content-Type'] = 'application/x-www-form-urlencoded'
        return await self._http_request('POST', endpoint, **kwargs)
    
    async def _http_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP request with retry logic and proper error handling.
        
        Args:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): API endpoint path
            **kwargs: Additional arguments for the request
            
        Returns:
            Optional[Dict[str, Any]]: Response data as dictionary or None if request failed
        """
        if not hasattr(self, 'base_url'):
            raise AttributeError("HTTPClientMixin requires 'base_url' attribute")
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                async with self._http_session_context() as session:
                    async with session.request(method, url, **kwargs) as response:
                        # Check if response is successful
                        if response.status in (200, 201, 202, 204):
                            try:
                                # Try to parse JSON response
                                return await response.json()
                            except aiohttp.ContentTypeError:
                                # Response is not JSON, return empty dict for success
                                return {}
                            except Exception as e:
                                logger.warning(f"Error parsing JSON response from {url}: {e}")
                                return {}
                        else:
                            logger.warning(f"HTTP {method} to {url} failed with status {response.status}")
                            
                            # For client errors (4xx), don't retry
                            if 400 <= response.status < 500:
                                return None
                            
                            # For server errors (5xx), continue to retry
                            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for HTTP {method} to {url}, attempt {attempt + 1}/{RETRY_ATTEMPTS}")
            except aiohttp.ClientConnectorError as e:
                logger.warning(f"Connection error for HTTP {method} to {url}, attempt {attempt + 1}/{RETRY_ATTEMPTS}: {e}")
            except aiohttp.ClientError as e:
                logger.error(f"Client error for HTTP {method} to {url}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error for HTTP {method} to {url}: {e}")
                return None
            
            # Wait before retrying (except on last attempt)
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY)
        
        logger.error(f"All retry attempts failed for HTTP {method} to {url}")
        return None
    
    async def _http_get_text(self, endpoint: str, **kwargs) -> Optional[str]:
        """
        Make a GET request and return the response as text.
        
        Args:
            endpoint (str): API endpoint path
            **kwargs: Additional arguments for the request
            
        Returns:
            Optional[str]: Response text or None if request failed
        """
        if not hasattr(self, 'base_url'):
            raise AttributeError("HTTPClientMixin requires 'base_url' attribute")
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                async with self._http_session_context() as session:
                    async with session.get(url, **kwargs) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            logger.warning(f"HTTP GET to {url} failed with status {response.status}")
                            
                            # For client errors (4xx), don't retry
                            if 400 <= response.status < 500:
                                return None
                            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for HTTP GET to {url}, attempt {attempt + 1}/{RETRY_ATTEMPTS}")
            except aiohttp.ClientConnectorError as e:
                logger.warning(f"Connection error for HTTP GET to {url}, attempt {attempt + 1}/{RETRY_ATTEMPTS}: {e}")
            except aiohttp.ClientError as e:
                logger.error(f"Client error for HTTP GET to {url}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error for HTTP GET to {url}: {e}")
                return None
            
            # Wait before retrying (except on last attempt)
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY)
        
        logger.error(f"All retry attempts failed for HTTP GET to {url}")
        return None
    
    def is_http_session_active(self) -> bool:
        """
        Check if an HTTP session is currently active.
        
        Returns:
            bool: True if HTTP session is active
        """
        return getattr(self, '_http_session_active', False)