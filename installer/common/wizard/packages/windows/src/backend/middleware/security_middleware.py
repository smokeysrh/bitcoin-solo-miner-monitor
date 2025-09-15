"""
Security Middleware

This module provides security middleware for API authentication and rate limiting.
"""

import time
import logging
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse of API endpoints.
    """
    
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Store request timestamps per IP
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Cleanup interval
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.
        """
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Periodic cleanup of old entries
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
            self.last_cleanup = current_time
        
        # Check rate limits
        if self._is_rate_limited(client_ip, current_time):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Rate limit exceeded",
                    "retry_after": 60,
                    "limits": {
                        "per_minute": self.requests_per_minute,
                        "per_hour": self.requests_per_hour
                    }
                }
            )
        
        # Record this request
        self.request_history[client_ip].append(current_time)
        
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        """
        # Check for forwarded headers (proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """
        Check if client IP is rate limited.
        """
        history = self.request_history[client_ip]
        
        # Remove old entries
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        # Count requests in the last minute and hour
        minute_requests = sum(1 for timestamp in history if timestamp > minute_ago)
        hour_requests = sum(1 for timestamp in history if timestamp > hour_ago)
        
        return (minute_requests >= self.requests_per_minute or 
                hour_requests >= self.requests_per_hour)
    
    def _cleanup_old_entries(self, current_time: float):
        """
        Clean up old request history entries.
        """
        hour_ago = current_time - 3600
        
        for client_ip in list(self.request_history.keys()):
            history = self.request_history[client_ip]
            
            # Remove entries older than 1 hour
            while history and history[0] < hour_ago:
                history.popleft()
            
            # Remove empty histories
            if not history:
                del self.request_history[client_ip]


class APIKeyAuth:
    """
    Simple API key authentication for sensitive endpoints.
    """
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
        
        # In production, these should be loaded from environment variables
        # or a secure configuration system
        import os
        self.valid_api_keys: Set[str] = set()
        
        # Load API keys from environment
        api_keys_env = os.getenv("API_KEYS", "")
        if api_keys_env:
            self.valid_api_keys.update(key.strip() for key in api_keys_env.split(",") if key.strip())
        
        # Development fallback (should be removed in production)
        if not self.valid_api_keys and os.getenv("DEBUG", "false").lower() == "true":
            logger.warning("No API keys configured, using development fallback")
            self.valid_api_keys.add("dev-key-12345")
    
    async def __call__(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> bool:
        """
        Validate API key authentication.
        """
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Authentication required",
                    "type": "missing_credentials"
                }
            )
        
        if credentials.credentials not in self.valid_api_keys:
            logger.warning(f"Invalid API key attempted: {credentials.credentials[:10]}...")
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Invalid API key",
                    "type": "invalid_credentials"
                }
            )
        
        return True


class DevelopmentEndpointAuth:
    """
    Authentication for development-only endpoints.
    These endpoints should be disabled in production or require special authentication.
    """
    
    def __init__(self):
        import os
        self.is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        
        # Development endpoints are only available in debug mode or non-production
        self.allow_dev_endpoints = self.debug_mode or not self.is_production
    
    async def __call__(self) -> bool:
        """
        Check if development endpoints are allowed.
        """
        if not self.allow_dev_endpoints:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Endpoint not available in production",
                    "type": "production_disabled"
                }
            )
        
        return True


# Global instances
api_key_auth = APIKeyAuth()
dev_endpoint_auth = DevelopmentEndpointAuth()