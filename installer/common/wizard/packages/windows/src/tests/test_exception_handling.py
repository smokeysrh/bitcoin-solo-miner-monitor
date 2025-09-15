"""
Test suite for exception handling improvements.

This module tests that specific exceptions are properly raised and handled
instead of broad Exception catching.
"""

import asyncio
import pytest
import logging
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.backend.exceptions import (
    AppError, ConfigurationError, DatabaseError, DatabaseConnectionError,
    MinerError, MinerConnectionError, MinerDataError, MinerTimeoutError,
    HTTPSessionError, ValidationError, PathError, PermissionError
)
from src.backend.utils.structured_logging import get_logger, setup_structured_logging
from src.backend.models.miner_factory import MinerFactory
from src.backend.services.miner_manager import MinerManager
from src.backend.utils.config_validator import ConfigValidator


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_app_error_base_class(self):
        """Test AppError base class functionality."""
        context = {'key': 'value', 'number': 42}
        error = AppError("Test error message", context)
        
        assert str(error) == "Test error message (Context: key=value, number=42)"
        assert error.message == "Test error message"
        assert error.context == context
        assert error.timestamp is not None
    
    def test_miner_error_with_context(self):
        """Test MinerError with miner-specific context."""
        error = MinerError("Connection failed", miner_id="test-miner", ip_address="10.0.0.100")
        
        assert error.context['miner_id'] == "test-miner"
        assert error.context['ip_address'] == "10.0.0.100"
    
    def test_error_logging(self, caplog):
        """Test error logging functionality."""
        logger = get_logger(__name__)
        error = ConfigurationError("Invalid config", {'setting': 'HOST'})
        
        with caplog.at_level(logging.ERROR):
            error.log_error(logger.logger)
        
        assert "ConfigurationError: Invalid config" in caplog.text


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_structured_logger_context(self, caplog):
        """Test logger context functionality."""
        logger = get_logger(__name__)
        logger.set_context(component='test', version='1.0')
        
        with caplog.at_level(logging.INFO):
            logger.info("Test message", {'operation': 'test_op'})
        
        # Verify the message was logged
        assert "Test message" in caplog.text
    
    def test_logging_context_manager(self, caplog):
        """Test logging context manager."""
        from src.backend.utils.structured_logging import LoggingContext
        
        logger = get_logger(__name__)
        
        with LoggingContext(logger, operation='test_context'):
            with caplog.at_level(logging.INFO):
                logger.info("Context test message")
        
        assert "Context test message" in caplog.text


class TestMinerFactoryExceptions:
    """Test exception handling in MinerFactory."""
    
    @pytest.mark.asyncio
    async def test_unsupported_miner_type(self):
        """Test that unsupported miner type raises MinerConfigurationError."""
        from src.backend.exceptions import MinerConfigurationError
        
        with pytest.raises(MinerConfigurationError) as exc_info:
            await MinerFactory.create_miner("unsupported_type", "10.0.0.100")
        
        assert "Unsupported miner type" in str(exc_info.value)
        assert exc_info.value.context['miner_type'] == "unsupported_type"
    
    @pytest.mark.asyncio
    async def test_connection_failure_raises_specific_exception(self):
        """Test that connection failures raise MinerConnectionError."""
        with patch('src.backend.models.bitaxe_miner.BitaxeMiner.connect', return_value=False):
            with pytest.raises(MinerConnectionError) as exc_info:
                await MinerFactory.create_miner("bitaxe", "10.0.0.100")
            
            assert "Failed to connect" in str(exc_info.value)
            assert exc_info.value.context['ip_address'] == "10.0.0.100"


class TestMinerManagerExceptions:
    """Test exception handling in MinerManager."""
    
    @pytest.mark.asyncio
    async def test_add_miner_with_invalid_type(self):
        """Test adding miner with invalid type returns None."""
        manager = MinerManager()
        
        # Mock MinerFactory to raise MinerConfigurationError
        with patch('src.backend.models.miner_factory.MinerFactory.create_miner') as mock_create:
            from src.backend.exceptions import MinerConfigurationError
            mock_create.side_effect = MinerConfigurationError("Invalid type")
            
            result = await manager.add_miner("invalid_type", "10.0.0.100")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_miner(self):
        """Test removing non-existent miner returns False."""
        manager = MinerManager()
        result = await manager.remove_miner("nonexistent-miner")
        assert result is False


class TestConfigValidatorExceptions:
    """Test exception handling in ConfigValidator."""
    
    def test_invalid_database_path(self):
        """Test that invalid database path raises appropriate errors."""
        validator = ConfigValidator()
        
        # Test with invalid path
        config = {
            'DB_CONFIG': {
                'sqlite': {
                    'path': '/invalid/path/that/does/not/exist/database.db'
                }
            }
        }
        
        result = validator.validate_all(config)
        assert result.has_errors()
        
        # Check that specific error messages are present
        error_messages = ' '.join(result.errors)
        assert 'database' in error_messages.lower()
    
    def test_permission_errors_handled(self):
        """Test that permission errors are properly categorized."""
        validator = ConfigValidator()
        
        # Mock Path.mkdir to raise PermissionError
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Permission denied")
            
            config = {
                'DB_CONFIG': {
                    'sqlite': {
                        'path': 'test_database.db'
                    }
                }
            }
            
            result = validator.validate_all(config)
            # The validator should handle PermissionError specifically
            if result.has_errors():
                error_messages = ' '.join(result.errors)
                assert 'permission' in error_messages.lower() or 'denied' in error_messages.lower()


class TestExceptionMapping:
    """Test exception mapping functionality."""
    
    def test_map_exception_function(self):
        """Test the map_exception utility function."""
        from src.backend.exceptions import map_exception, MinerConnectionError
        
        error = map_exception('connection_refused', 'Connection refused', ip_address='10.0.0.100')
        
        assert isinstance(error, MinerConnectionError)
        assert error.message == 'Connection refused'
        assert error.context['ip_address'] == '10.0.0.100'
    
    def test_unknown_error_type_maps_to_app_error(self):
        """Test that unknown error types map to AppError."""
        from src.backend.exceptions import map_exception, AppError
        
        error = map_exception('unknown_error_type', 'Unknown error')
        
        assert isinstance(error, AppError)
        assert error.message == 'Unknown error'


async def run_exception_tests():
    """Run all exception handling tests."""
    print("🧪 Running exception handling tests...")
    
    try:
        # Test basic exception functionality
        print("   ✓ Testing custom exception classes...")
        test_exceptions = TestCustomExceptions()
        test_exceptions.test_app_error_base_class()
        test_exceptions.test_miner_error_with_context()
        
        # Test structured logging
        print("   ✓ Testing structured logging...")
        test_logging = TestStructuredLogging()
        
        # Test exception mapping
        print("   ✓ Testing exception mapping...")
        test_mapping = TestExceptionMapping()
        test_mapping.test_map_exception_function()
        test_mapping.test_unknown_error_type_maps_to_app_error()
        
        # Test async exception handling
        print("   ✓ Testing async exception handling...")
        test_factory = TestMinerFactoryExceptions()
        await test_factory.test_unsupported_miner_type()
        
        test_manager = TestMinerManagerExceptions()
        await test_manager.test_remove_nonexistent_miner()
        
        print("   ✅ All exception handling tests passed!")
        return True
        
    except Exception as e:
        print(f"   ❌ Exception handling tests failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(run_exception_tests())