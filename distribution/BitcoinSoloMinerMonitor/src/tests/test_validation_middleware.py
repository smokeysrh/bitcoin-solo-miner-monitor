"""
Tests for validation middleware implementation.

This module tests the comprehensive validation middleware including
input validation, miner configuration validation, and security features.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from src.backend.middleware.validation_middleware import (
    InputValidationMiddleware,
    MinerConfigurationValidationMiddleware
)
from src.backend.exceptions import ValidationError


class TestInputValidationMiddleware:
    """Test input validation middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with validation middleware."""
        app = FastAPI()
        app.add_middleware(InputValidationMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.post("/test")
        async def test_post_endpoint(request: Request):
            body = await request.body()
            return {"received": json.loads(body) if body else None}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_valid_get_request(self, client):
        """Test valid GET request passes through middleware."""
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
    
    def test_valid_post_request_with_json(self, client):
        """Test valid POST request with JSON data."""
        data = {"name": "test_miner", "ip": "10.0.0.100"}
        response = client.post("/test", json=data)
        assert response.status_code == 200
        assert response.json()["received"] == data
    
    def test_request_size_limit(self, client):
        """Test request size limit enforcement."""
        # Create large payload (larger than 10MB limit)
        large_data = {"data": "x" * (11 * 1024 * 1024)}  # 11MB of data
        
        response = client.post(
            "/test",
            json=large_data,
            headers={"content-length": str(11 * 1024 * 1024)}
        )
        assert response.status_code == 400
        assert "Request size" in response.json()["message"]
    
    def test_invalid_json_format(self, client):
        """Test invalid JSON format rejection."""
        response = client.post(
            "/test",
            data="invalid json {",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 400
        assert "Invalid JSON format" in response.json()["message"]
    
    def test_malicious_json_content(self, client):
        """Test malicious JSON content rejection."""
        malicious_data = {
            "name": "'; DROP TABLE miners; --",
            "script": "<script>alert('xss')</script>"
        }
        
        response = client.post("/test", json=malicious_data)
        assert response.status_code == 400
        assert "Validation Error" in response.json()["error"]
    
    def test_json_depth_limit(self, client):
        """Test JSON nesting depth limit."""
        # Create deeply nested JSON (more than 10 levels)
        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "level6": {
                                    "level7": {
                                        "level8": {
                                            "level9": {
                                                "level10": {
                                                    "level11": "too deep"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        response = client.post("/test", json=nested_data)
        assert response.status_code == 400
        assert "nesting depth" in response.json()["message"]
    
    def test_large_json_array(self, client):
        """Test large JSON array rejection."""
        large_array = list(range(1001))  # More than 1000 elements
        
        response = client.post("/test", json={"data": large_array})
        assert response.status_code == 400
        assert "array too large" in response.json()["message"]
    
    def test_long_string_rejection(self, client):
        """Test long string rejection."""
        long_string = "x" * 10001  # More than 10000 characters
        
        response = client.post("/test", json={"data": long_string})
        assert response.status_code == 400
        assert "String too long" in response.json()["message"]
    
    def test_skip_validation_for_static_files(self, client):
        """Test that validation is skipped for static files."""
        # This would normally fail validation, but should be skipped
        response = client.get("/static/test.js")
        # Should get 404 (not found) rather than validation error
        assert response.status_code == 404
    
    def test_skip_validation_for_options_requests(self, client):
        """Test that validation is skipped for OPTIONS requests."""
        response = client.options("/test")
        # Should not get validation error
        assert response.status_code in [200, 405]  # Depends on FastAPI handling
    
    def test_query_parameter_validation(self, client):
        """Test query parameter validation."""
        # Valid query parameters
        response = client.get("/test?limit=10&offset=0")
        assert response.status_code == 200
        
        # Invalid limit parameter
        response = client.get("/test?limit=invalid")
        assert response.status_code == 400
        
        # Invalid offset parameter
        response = client.get("/test?offset=-1")
        assert response.status_code == 400
    
    def test_datetime_parameter_validation(self, client):
        """Test datetime parameter validation."""
        # Valid datetime
        response = client.get("/test?start=2024-01-01T00:00:00")
        assert response.status_code == 200
        
        # Invalid datetime
        response = client.get("/test?start=invalid-date")
        assert response.status_code == 400
    
    def test_interval_parameter_validation(self, client):
        """Test interval parameter validation."""
        # Valid interval
        response = client.get("/test?interval=1h")
        assert response.status_code == 200
        
        # Invalid interval
        response = client.get("/test?interval=invalid")
        assert response.status_code == 400


class TestMinerConfigurationValidationMiddleware:
    """Test miner configuration validation middleware."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with miner validation middleware."""
        app = FastAPI()
        app.add_middleware(MinerConfigurationValidationMiddleware)
        
        @app.post("/api/miners")
        async def add_miner(request: Request):
            body = await request.body()
            return {"received": json.loads(body) if body else None}
        
        @app.post("/api/discovery")
        async def start_discovery(request: Request):
            body = await request.body()
            return {"received": json.loads(body) if body else None}
        
        @app.post("/other")
        async def other_endpoint(request: Request):
            body = await request.body()
            return {"received": json.loads(body) if body else None}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_valid_miner_configuration(self, client):
        """Test valid miner configuration passes validation."""
        data = {
            "type": "bitaxe",
            "ip_address": "10.0.0.100",
            "port": 80,
            "name": "Test Miner"
        }
        
        response = client.post("/api/miners", json=data)
        assert response.status_code == 200
        assert response.json()["received"] == data
    
    def test_invalid_ip_address_rejection(self, client):
        """Test invalid IP address rejection."""
        data = {
            "type": "bitaxe",
            "ip_address": "256.256.256.256",
            "port": 80
        }
        
        response = client.post("/api/miners", json=data)
        assert response.status_code == 400
        assert "Invalid IP address" in response.json()["message"]
    
    def test_invalid_port_rejection(self, client):
        """Test invalid port rejection."""
        data = {
            "type": "bitaxe",
            "ip_address": "10.0.0.100",
            "port": 65536  # Invalid port
        }
        
        response = client.post("/api/miners", json=data)
        assert response.status_code == 400
        assert "Invalid port" in response.json()["message"]
    
    def test_invalid_miner_type_rejection(self, client):
        """Test invalid miner type rejection."""
        data = {
            "type": "unknown_miner",
            "ip_address": "10.0.0.100",
            "port": 80
        }
        
        response = client.post("/api/miners", json=data)
        assert response.status_code == 400
        assert "Invalid miner type" in response.json()["message"]
    
    def test_valid_discovery_configuration(self, client):
        """Test valid discovery configuration."""
        data = {
            "network": "192.168.1.0/24",
            "ports": [80, 443, 4028],
            "timeout": 10
        }
        
        response = client.post("/api/discovery", json=data)
        assert response.status_code == 200
        assert response.json()["received"] == data
    
    def test_invalid_network_range_rejection(self, client):
        """Test invalid network range rejection."""
        data = {
            "network": "256.256.256.0/24",
            "ports": [80, 443]
        }
        
        response = client.post("/api/discovery", json=data)
        assert response.status_code == 400
        assert "Invalid network range" in response.json()["message"]
    
    def test_invalid_port_list_rejection(self, client):
        """Test invalid port list rejection."""
        data = {
            "network": "192.168.1.0/24",
            "ports": [80, 65536, 443]  # Contains invalid port
        }
        
        response = client.post("/api/discovery", json=data)
        assert response.status_code == 400
        assert "Invalid port list" in response.json()["message"]
    
    def test_miner_settings_validation(self, client):
        """Test miner settings validation."""
        # Valid settings
        data = {
            "type": "bitaxe",
            "ip_address": "10.0.0.100",
            "port": 80,
            "settings": {
                "frequency": 500,
                "voltage": 1.2,
                "pool_url": "stratum+tcp://pool.example.com:4444"
            }
        }
        
        response = client.post("/api/miners", json=data)
        assert response.status_code == 200
        
        # Invalid frequency
        data["settings"]["frequency"] = 3000  # Too high
        response = client.post("/api/miners", json=data)
        assert response.status_code == 400
        assert "Frequency must be between" in response.json()["message"]
        
        # Invalid voltage
        data["settings"]["frequency"] = 500  # Reset to valid
        data["settings"]["voltage"] = 3.0  # Too high
        response = client.post("/api/miners", json=data)
        assert response.status_code == 400
        assert "Voltage must be between" in response.json()["message"]
    
    def test_non_miner_endpoint_bypass(self, client):
        """Test that non-miner endpoints bypass miner validation."""
        # This would fail miner validation but should pass through
        data = {
            "ip_address": "256.256.256.256",  # Invalid IP
            "port": 65536  # Invalid port
        }
        
        response = client.post("/other", json=data)
        assert response.status_code == 200
        assert response.json()["received"] == data
    
    def test_get_request_bypass(self, client):
        """Test that GET requests bypass miner validation."""
        response = client.get("/api/miners")
        # Should not get validation error (might get 405 Method Not Allowed)
        assert response.status_code != 400


class TestValidationMiddlewareIntegration:
    """Test integration of multiple validation middlewares."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with both validation middlewares."""
        app = FastAPI()
        app.add_middleware(InputValidationMiddleware)
        app.add_middleware(MinerConfigurationValidationMiddleware)
        
        @app.post("/api/miners")
        async def add_miner(request: Request):
            body = await request.body()
            return {"received": json.loads(body) if body else None}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_both_middlewares_validation(self, client):
        """Test that both middlewares validate the request."""
        # This should fail both general validation (malicious content) 
        # and miner validation (invalid IP)
        data = {
            "type": "bitaxe",
            "ip_address": "256.256.256.256",  # Invalid IP
            "name": "'; DROP TABLE miners; --"  # Malicious content
        }
        
        response = client.post("/api/miners", json=data)
        assert response.status_code == 400
        # Should get validation error from one of the middlewares
        assert "Validation Error" in response.json()["error"] or "Invalid" in response.json()["message"]
    
    def test_valid_request_passes_both_middlewares(self, client):
        """Test that valid requests pass through both middlewares."""
        data = {
            "type": "bitaxe",
            "ip_address": "10.0.0.100",
            "port": 80,
            "name": "Valid Miner Name"
        }
        
        response = client.post("/api/miners", json=data)
        assert response.status_code == 200
        assert response.json()["received"] == data


class TestValidationStats:
    """Test validation statistics collection."""
    
    def test_validation_stats_collection(self):
        """Test that validation statistics are collected."""
        middleware = InputValidationMiddleware(None)
        
        # Initial stats should be zero
        stats = middleware.get_validation_stats()
        assert stats["requests_processed"] == 0
        assert stats["requests_blocked"] == 0
        assert stats["validation_errors"] == 0
        
        # Stats should be modifiable
        middleware.validation_stats["requests_processed"] = 10
        middleware.validation_stats["requests_blocked"] = 2
        middleware.validation_stats["validation_errors"] = 1
        
        updated_stats = middleware.get_validation_stats()
        assert updated_stats["requests_processed"] == 10
        assert updated_stats["requests_blocked"] == 2
        assert updated_stats["validation_errors"] == 1


if __name__ == "__main__":
    pytest.main([__file__])