"""
Bitcoin Solo Miner Monitoring App

Main application entry point.
"""

import asyncio
import logging
import sys
import os
import uvicorn
from typing import Optional

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backend.services.miner_manager import MinerManager
from src.backend.services.data_storage import DataStorage
from src.backend.services.http_session_manager import shutdown_session_manager
from src.backend.api.api_service import APIService
from src.backend.utils.app_paths import get_app_paths
from src.backend.utils.config_validator import ConfigValidator
from src.backend.utils.structured_logging import setup_structured_logging, get_logger
from src.backend.exceptions import (
    ConfigurationError, DatabaseError, MinerManagerError, 
    DataStorageError, AppError
)
from config.app_config import HOST, PORT
import config.app_config as app_config

# Initialize application paths
app_paths = get_app_paths()

# Configure structured logging
setup_structured_logging(
    log_level="INFO",
    log_file=app_paths.log_file_path,
    enable_console=True,
    enable_structured=False  # Keep simple format for now
)

logger = get_logger(__name__)


class Application:
    """
    Main application class.
    """
    
    def __init__(self):
        """
        Initialize a new Application instance.
        """
        # Validate configuration before starting
        self._validate_configuration()
        
        # Ensure required directories exist
        app_paths.ensure_directories()
        
        # Create services
        self.data_storage = DataStorage()
        self.miner_manager = MinerManager()
        self.api_service = APIService(self.miner_manager, self.data_storage)
    
    async def start(self):
        """
        Start the application.
        """
        logger.info("Starting Bitcoin Solo Miner Monitoring App")
        
        # Start services
        await self.data_storage.initialize()
        await self.miner_manager.start()
        await self.api_service.start()
        
        # Load saved miners
        await self._load_saved_miners()
        
        # Start API server
        config = uvicorn.Config(
            app=self.api_service.app,
            host=HOST,
            port=PORT,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """
        Stop the application.
        """
        logger.info("Stopping Bitcoin Solo Miner Monitoring App")
        
        # Stop services
        await self.api_service.stop()
        await self.miner_manager.stop()
        await self.data_storage.close()
        
        # Shutdown HTTP session manager
        await shutdown_session_manager()
    
    async def _load_saved_miners(self):
        """
        Load saved miners from the database.
        """
        try:
            # Get all miner configurations
            configs = await self.data_storage.get_all_miner_configs()
            
            # Add each miner
            for config in configs:
                miner_id = config.get("id")
                miner_type = config.get("type")
                ip_address = config.get("ip_address")
                port = config.get("port")
                name = config.get("name")
                
                if miner_id and miner_type and ip_address:
                    logger.info(f"Loading saved miner: {miner_id}")
                    await self.miner_manager.add_miner(miner_type, ip_address, port, name)
        except DatabaseError as e:
            logger.error(f"Database error loading saved miners", {
                'error_type': 'database_error',
                'operation': 'load_saved_miners'
            })
            # Don't fail startup for this - just log the error
        except MinerManagerError as e:
            logger.error(f"Miner manager error loading saved miners", {
                'error_type': 'miner_manager_error',
                'operation': 'load_saved_miners'
            })
            # Don't fail startup for this - just log the error
        except AppError as e:
            logger.error(f"Application error loading saved miners", {
                'error_type': 'app_error',
                'operation': 'load_saved_miners'
            })
            # Don't fail startup for this - just log the error
    
    def _validate_configuration(self):
        """
        Validate application configuration.
        """
        logger.info("Validating application configuration...")
        
        # Create configuration dictionary from app_config module
        config = {
            'HOST': getattr(app_config, 'HOST', None),
            'PORT': getattr(app_config, 'PORT', None),
            'DB_CONFIG': getattr(app_config, 'DB_CONFIG', None),
            'DEFAULT_POLLING_INTERVAL': getattr(app_config, 'DEFAULT_POLLING_INTERVAL', None),
            'CONNECTION_TIMEOUT': getattr(app_config, 'CONNECTION_TIMEOUT', None),
            'RETRY_ATTEMPTS': getattr(app_config, 'RETRY_ATTEMPTS', None),
            'RETRY_DELAY': getattr(app_config, 'RETRY_DELAY', None),
            'LOG_LEVEL': getattr(app_config, 'LOG_LEVEL', None),
            'LOG_FILE': getattr(app_config, 'LOG_FILE', None),
            'THEME': getattr(app_config, 'THEME', None),
            'CHART_RETENTION_DAYS': getattr(app_config, 'CHART_RETENTION_DAYS', None),
            'DEFAULT_REFRESH_INTERVAL': getattr(app_config, 'DEFAULT_REFRESH_INTERVAL', None),
        }
        
        # Validate configuration
        validator = ConfigValidator()
        result = validator.validate_all(config)
        
        # Log validation results
        if result.has_errors():
            logger.error("Configuration validation failed", {
                'validation_errors': result.errors,
                'operation': 'configuration_validation'
            })
            
            # Print errors to console as well
            print("\nConfiguration validation failed:")
            for error in result.errors:
                print(f"  ERROR: {error}")
            
            raise ConfigurationError("Configuration validation failed. Please fix the errors above.", {
                'errors': result.errors
            })
        
        if result.has_warnings():
            logger.warning("Configuration validation warnings:")
            for warning in result.warnings:
                logger.warning(f"  WARNING: {warning}")
            
            # Print warnings to console
            print("\nConfiguration validation warnings:")
            for warning in result.warnings:
                print(f"  WARNING: {warning}")
        
        # Validate startup requirements
        startup_result = validator.validate_startup_requirements()
        
        if startup_result.has_errors():
            logger.error("Startup requirements validation failed", {
                'startup_errors': startup_result.errors,
                'operation': 'startup_validation'
            })
            
            # Print errors to console as well
            print("\nStartup requirements validation failed:")
            for error in startup_result.errors:
                print(f"  ERROR: {error}")
            
            raise ConfigurationError("Startup requirements validation failed. Please fix the errors above.", {
                'errors': startup_result.errors
            })
        
        if startup_result.has_warnings():
            logger.warning("Startup requirements warnings:")
            for warning in startup_result.warnings:
                logger.warning(f"  WARNING: {warning}")
        
        logger.info("Configuration validation passed")
        
        # Log configuration summary
        summary = validator.get_configuration_summary(config)
        logger.info("Configuration summary:")
        logger.info(f"  Server: {summary['server']['host']}:{summary['server']['port']}")
        logger.info(f"  Database: {summary['database']['type']} at {summary['database']['path']}")
        logger.info(f"  Polling interval: {summary['miner_settings']['polling_interval']}s")
        logger.info(f"  Log level: {summary['logging']['level']}")


async def main():
    """
    Main entry point.
    """
    app = Application()
    
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())