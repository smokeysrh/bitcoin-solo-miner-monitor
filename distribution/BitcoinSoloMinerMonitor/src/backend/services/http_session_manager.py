"""
HTTP Session Manager

This module provides centralized HTTP session management with proper lifecycle,
pooling, and cleanup mechanisms for miner communications.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from config.app_config import CONNECTION_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY
from src.backend.utils.retry_logic import retry_http_request, RetryConfig

logger = logging.getLogger(__name__)


class HTTPSessionManager:
    """
    Centralized HTTP session manager with proper lifecycle management,
    session pooling, and automatic cleanup.
    """
    
    def __init__(self, 
                 max_sessions: int = 10,
                 session_timeout: int = 300,  # 5 minutes
                 cleanup_interval: int = 60):  # 1 minute
        """
        Initialize the HTTP session manager.
        
        Args:
            max_sessions (int): Maximum number of concurrent sessions
            session_timeout (int): Session timeout in seconds
            cleanup_interval (int): Cleanup interval in seconds
        """
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        
        # Session pool: key is (ip_address, port), value is session info
        self._sessions: Dict[tuple, Dict[str, Any]] = {}
        self._session_lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
    async def start(self):
        """Start the session manager and cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("HTTP Session Manager started")
    
    async def stop(self):
        """Stop the session manager and cleanup all sessions."""
        self._shutdown = True
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all sessions
        async with self._session_lock:
            for session_info in self._sessions.values():
                session = session_info.get('session')
                if session and not session.closed:
                    try:
                        await session.close()
                    except Exception as e:
                        logger.error(f"Error closing session: {e}")
            
            self._sessions.clear()
        
        logger.info("HTTP Session Manager stopped")
    
    @asynccontextmanager
    async def get_session(self, ip_address: str, port: int = 80):
        """
        Get or create an HTTP session for the specified endpoint.
        
        Args:
            ip_address (str): IP address of the endpoint
            port (int): Port number of the endpoint
            
        Yields:
            aiohttp.ClientSession: HTTP session for the endpoint
        """
        session_key = (ip_address, port)
        session = None
        
        try:
            async with self._session_lock:
                # Check if we have an existing session
                if session_key in self._sessions:
                    session_info = self._sessions[session_key]
                    session = session_info['session']
                    
                    # Check if session is still valid
                    if session.closed or self._is_session_expired(session_info):
                        # Session is invalid, remove it
                        try:
                            if not session.closed:
                                await session.close()
                        except Exception as e:
                            logger.error(f"Error closing expired session for {ip_address}:{port}: {e}")
                        
                        del self._sessions[session_key]
                        session = None
                
                # Create new session if needed
                if session is None:
                    # Check session pool limit
                    if len(self._sessions) >= self.max_sessions:
                        # Remove oldest session
                        await self._remove_oldest_session()
                    
                    # Create new session with production-appropriate settings
                    session = aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(
                            total=CONNECTION_TIMEOUT,
                            connect=CONNECTION_TIMEOUT // 2,  # Connection timeout
                            sock_read=CONNECTION_TIMEOUT,     # Socket read timeout
                            sock_connect=CONNECTION_TIMEOUT // 2  # Socket connect timeout
                        ),
                        connector=aiohttp.TCPConnector(
                            limit=20,  # Increased connection pool limit for production
                            limit_per_host=10,  # Increased per-host limit for production
                            ttl_dns_cache=300,  # DNS cache TTL
                            use_dns_cache=True,
                            enable_cleanup_closed=True,  # Enable cleanup of closed connections
                            keepalive_timeout=30,  # Keep-alive timeout for connection reuse
                            force_close=False,  # Allow connection reuse
                        )
                    )
                    
                    # Store session info
                    self._sessions[session_key] = {
                        'session': session,
                        'created_at': datetime.now(),
                        'last_used': datetime.now(),
                        'ip_address': ip_address,
                        'port': port
                    }
                    
                    logger.debug(f"Created new HTTP session for {ip_address}:{port}")
                else:
                    # Update last used timestamp
                    self._sessions[session_key]['last_used'] = datetime.now()
            
            # Yield the session for use
            yield session
            
        except Exception as e:
            logger.error(f"Error managing HTTP session for {ip_address}:{port}: {e}")
            # If there's an error, ensure session is cleaned up
            if session and not session.closed:
                try:
                    await session.close()
                except Exception as cleanup_error:
                    logger.error(f"Error during session cleanup: {cleanup_error}")
            
            # Remove from pool if it exists
            async with self._session_lock:
                if session_key in self._sessions:
                    del self._sessions[session_key]
            
            raise
    
    async def close_session(self, ip_address: str, port: int = 80):
        """
        Explicitly close a session for the specified endpoint.
        
        Args:
            ip_address (str): IP address of the endpoint
            port (int): Port number of the endpoint
        """
        session_key = (ip_address, port)
        
        async with self._session_lock:
            if session_key in self._sessions:
                session_info = self._sessions[session_key]
                session = session_info['session']
                
                try:
                    if not session.closed:
                        await session.close()
                except Exception as e:
                    logger.error(f"Error closing session for {ip_address}:{port}: {e}")
                
                del self._sessions[session_key]
                logger.debug(f"Closed HTTP session for {ip_address}:{port}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current sessions.
        
        Returns:
            Dict[str, Any]: Session statistics
        """
        return {
            'active_sessions': len(self._sessions),
            'max_sessions': self.max_sessions,
            'session_timeout': self.session_timeout,
            'sessions': [
                {
                    'endpoint': f"{info['ip_address']}:{info['port']}",
                    'created_at': info['created_at'].isoformat(),
                    'last_used': info['last_used'].isoformat(),
                    'age_seconds': (datetime.now() - info['created_at']).total_seconds(),
                    'idle_seconds': (datetime.now() - info['last_used']).total_seconds()
                }
                for info in self._sessions.values()
            ]
        }
    
    @retry_http_request(max_attempts=3, base_delay=1.0, max_delay=30.0)
    async def make_request(self, method: str, ip_address: str, port: int, 
                          path: str = "/", **kwargs) -> aiohttp.ClientResponse:
        """
        Make an HTTP request with retry logic and session management.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            ip_address: Target IP address
            port: Target port
            path: Request path
            **kwargs: Additional arguments for the request
            
        Returns:
            aiohttp.ClientResponse: HTTP response
        """
        async with self.get_session(ip_address, port) as session:
            url = f"http://{ip_address}:{port}{path}"
            
            # Set default timeout if not provided
            if 'timeout' not in kwargs:
                kwargs['timeout'] = aiohttp.ClientTimeout(total=CONNECTION_TIMEOUT)
            
            async with session.request(method, url, **kwargs) as response:
                return response
    
    def _is_session_expired(self, session_info: Dict[str, Any]) -> bool:
        """
        Check if a session has expired.
        
        Args:
            session_info (Dict[str, Any]): Session information
            
        Returns:
            bool: True if session is expired
        """
        last_used = session_info['last_used']
        return datetime.now() - last_used > timedelta(seconds=self.session_timeout)
    
    async def _remove_oldest_session(self):
        """Remove the oldest session from the pool."""
        if not self._sessions:
            return
        
        # Find oldest session by creation time
        oldest_key = min(self._sessions.keys(), 
                        key=lambda k: self._sessions[k]['created_at'])
        
        session_info = self._sessions[oldest_key]
        session = session_info['session']
        
        try:
            if not session.closed:
                await session.close()
        except Exception as e:
            logger.error(f"Error closing oldest session: {e}")
        
        del self._sessions[oldest_key]
        logger.debug(f"Removed oldest session for {session_info['ip_address']}:{session_info['port']}")
    
    async def _cleanup_loop(self):
        """Background task to cleanup expired sessions."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        expired_keys = []
        
        async with self._session_lock:
            for key, session_info in self._sessions.items():
                if self._is_session_expired(session_info):
                    expired_keys.append(key)
        
        # Close expired sessions
        for key in expired_keys:
            async with self._session_lock:
                if key in self._sessions:  # Double-check in case it was removed
                    session_info = self._sessions[key]
                    session = session_info['session']
                    
                    try:
                        if not session.closed:
                            await session.close()
                    except Exception as e:
                        logger.error(f"Error closing expired session: {e}")
                    
                    del self._sessions[key]
                    logger.debug(f"Cleaned up expired session for {session_info['ip_address']}:{session_info['port']}")


# Global session manager instance
_session_manager: Optional[HTTPSessionManager] = None


async def get_session_manager() -> HTTPSessionManager:
    """
    Get the global HTTP session manager instance.
    
    Returns:
        HTTPSessionManager: Global session manager instance
    """
    global _session_manager
    
    if _session_manager is None:
        _session_manager = HTTPSessionManager()
        await _session_manager.start()
    
    return _session_manager


async def shutdown_session_manager():
    """Shutdown the global session manager."""
    global _session_manager
    
    if _session_manager:
        await _session_manager.stop()
        _session_manager = None


@asynccontextmanager
async def http_session(ip_address: str, port: int = 80):
    """
    Convenience context manager for getting HTTP sessions.
    
    Args:
        ip_address (str): IP address of the endpoint
        port (int): Port number of the endpoint
        
    Yields:
        aiohttp.ClientSession: HTTP session for the endpoint
    """
    session_manager = await get_session_manager()
    async with session_manager.get_session(ip_address, port) as session:
        yield session