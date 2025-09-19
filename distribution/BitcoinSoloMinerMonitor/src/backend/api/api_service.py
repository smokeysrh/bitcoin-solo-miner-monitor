"""
API Service

This module provides a FastAPI service for the Bitcoin Solo Miner Monitoring App.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError as PydanticValidationError

from src.backend.services.miner_manager import MinerManager
from src.backend.services.data_storage import DataStorage
from src.backend.services.websocket_manager import WebSocketManager
from src.backend.services.system_monitor import SystemMonitor
from src.backend.services.email_service import EmailService
from src.backend.utils.app_paths import get_app_paths
from src.backend.models.validation_models import (
    MinerAddRequest,
    MinerUpdateRequest,
    DiscoveryRequest,
    AppSettingsRequest,
    MetricsQueryRequest,
    WebSocketMessage,
    SystemMetricsRequest,
    EmailConfigRequest,
    EmailTestRequest,
    EmailNotificationRequest
)
from src.backend.exceptions import ValidationError as AppValidationError
from src.backend.middleware.validation_middleware import (
    InputValidationMiddleware,
    MinerConfigurationValidationMiddleware
)
from src.backend.middleware.security_middleware import (
    RateLimitMiddleware,
    api_key_auth,
    dev_endpoint_auth
)
from config.app_config import HOST, PORT

logger = logging.getLogger(__name__)


class APIService:
    """
    FastAPI service for the Bitcoin Solo Miner Monitoring App.
    """
    
    def __init__(self, miner_manager: MinerManager, data_storage: DataStorage):
        """
        Initialize a new APIService instance.
        
        Args:
            miner_manager (MinerManager): Miner manager service
            data_storage (DataStorage): Data storage service
        """
        self.miner_manager = miner_manager
        self.data_storage = data_storage
        self.app = FastAPI(title="Bitcoin Solo Miner Monitoring API")
        
        # Initialize WebSocket manager
        self.websocket_manager = WebSocketManager()
        
        # Initialize System Monitor
        self.system_monitor = SystemMonitor()
        
        # Initialize Email Service
        self.email_service = EmailService()
        
        # Configure CORS for production security
        # Allow specific origins for production deployment using configurable host/port
        allowed_origins = [
            "http://localhost:3000",  # Development frontend
            f"http://localhost:{PORT}",  # Production frontend served by API
            "http://127.0.0.1:3000",  # Local development
            f"http://127.0.0.1:{PORT}",  # Local production
        ]
        
        # Add host-specific origins if HOST is not localhost/127.0.0.1
        if HOST not in ["localhost", "127.0.0.1", "0.0.0.0"]:
            allowed_origins.extend([
                f"http://{HOST}:3000",  # Development on specific host
                f"http://{HOST}:{PORT}",  # Production on specific host
            ])
        
        # Add environment-specific origins if configured
        import os
        additional_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        if additional_origins and additional_origins[0]:  # Check if not empty
            allowed_origins.extend([origin.strip() for origin in additional_origins if origin.strip()])
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Restrict to necessary methods
            allow_headers=["Content-Type", "Authorization", "X-Requested-With"],  # Restrict headers
        )
        
        # Add security middleware
        self.app.add_middleware(RateLimitMiddleware, requests_per_minute=120, requests_per_hour=2000)
        
        # Add input validation middleware
        self.app.add_middleware(InputValidationMiddleware)
        self.app.add_middleware(MinerConfigurationValidationMiddleware)
        
        # Add validation error handler
        self._add_exception_handlers()
        
        # Register routes
        self._register_routes()
    
    def _add_exception_handlers(self):
        """Add exception handlers for validation errors."""
        
        @self.app.exception_handler(PydanticValidationError)
        async def pydantic_validation_exception_handler(request, exc):
            """Handle Pydantic validation errors."""
            logger.warning(f"Pydantic validation error: {exc}")
            return HTTPException(
                status_code=422,
                detail={
                    "message": "Input validation failed",
                    "errors": exc.errors()
                }
            )
        
        @self.app.exception_handler(AppValidationError)
        async def app_validation_exception_handler(request, exc):
            """Handle application validation errors."""
            logger.warning(f"Application validation error: {exc}")
            return HTTPException(
                status_code=400,
                detail={
                    "message": str(exc),
                    "context": getattr(exc, 'context', {})
                }
            )
    
    def _register_routes(self):
        """
        Register API routes.
        """
        # Miners
        self.app.get(
            "/api/miners", 
            response_model=List[Dict[str, Any]]
        )(self.get_miners)
        
        self.app.get(
            "/api/miners/{miner_id}", 
            response_model=Dict[str, Any]
        )(self.get_miner)
        
        self.app.post(
            "/api/miners", 
            response_model=Dict[str, Any],
            dependencies=[Depends(api_key_auth)]
        )(self.add_miner)
        
        self.app.put(
            "/api/miners/{miner_id}", 
            response_model=Dict[str, Any],
            dependencies=[Depends(api_key_auth)]
        )(self.update_miner)
        
        self.app.delete(
            "/api/miners/{miner_id}", 
            response_model=Dict[str, str],
            dependencies=[Depends(api_key_auth)]
        )(self.remove_miner)
        
        self.app.post(
            "/api/miners/{miner_id}/restart", 
            response_model=Dict[str, bool],
            dependencies=[Depends(api_key_auth)]
        )(self.restart_miner)
        
        # Metrics
        self.app.get(
            "/api/miners/{miner_id}/metrics", 
            response_model=List[Dict[str, Any]]
        )(self.get_miner_metrics)
        
        self.app.get(
            "/api/miners/{miner_id}/metrics/latest", 
            response_model=Dict[str, Any]
        )(self.get_latest_metrics)
        
        # Discovery
        self.app.post(
            "/api/discovery", 
            response_model=Dict[str, Any]
        )(self.start_discovery)
        
        self.app.get(
            "/api/discovery/status", 
            response_model=Dict[str, Any]
        )(self.get_discovery_status)
        
        # Settings
        self.app.get(
            "/api/settings", 
            response_model=Dict[str, Any]
        )(self.get_settings)
        
        self.app.put(
            "/api/settings", 
            response_model=Dict[str, Any],
            dependencies=[Depends(api_key_auth)]
        )(self.update_settings)
        
        # System monitoring
        self.app.get(
            "/api/system/info", 
            response_model=Dict[str, Any]
        )(self.get_system_info)
        
        self.app.get(
            "/api/system/metrics", 
            response_model=Dict[str, Any]
        )(self.get_system_metrics)
        
        self.app.get(
            "/api/system/metrics/history", 
            response_model=List[Dict[str, Any]]
        )(self.get_system_metrics_history)
        
        # Setup status endpoint
        self.app.get(
            "/api/setup-status",
            response_model=Dict[str, Any]
        )(self.get_setup_status)
        
        # Validation and health endpoints
        self.app.get(
            "/api/validation/stats",
            response_model=Dict[str, Any]
        )(self.get_validation_stats)
        
        self.app.get(
            "/api/health",
            response_model=Dict[str, Any]
        )(self.health_check)
        
        # Reload miners endpoint for development/testing - secured
        self.app.post(
            "/api/reload-miners",
            response_model=Dict[str, Any],
            dependencies=[Depends(dev_endpoint_auth), Depends(api_key_auth)]
        )(self.reload_miners)
        
        # Bulk operations - secured for production
        self.app.post(
            "/api/miners/bulk",
            response_model=Dict[str, Any],
            dependencies=[Depends(api_key_auth)]
        )(self.bulk_miner_action)
        
        # Email endpoints
        self.app.get(
            "/api/email/config",
            response_model=Dict[str, Any]
        )(self.get_email_config)
        
        self.app.put(
            "/api/email/config",
            response_model=Dict[str, Any],
            dependencies=[Depends(api_key_auth)]
        )(self.update_email_config)
        
        self.app.post(
            "/api/email/test",
            response_model=Dict[str, Any],
            dependencies=[Depends(api_key_auth)]
        )(self.send_test_email)
        
        self.app.post(
            "/api/email/send",
            response_model=Dict[str, Any],
            dependencies=[Depends(api_key_auth)]
        )(self.send_notification_email)
        
        # WebSocket for real-time updates - authentication handled in the endpoint
        self.app.websocket("/ws")(self.websocket_endpoint)
        
        # Serve static files (frontend) with proper SPA support
        self._setup_spa_routing()
    
    def _setup_spa_routing(self):
        """
        Set up SPA (Single Page Application) routing.
        This properly handles client-side routes by serving index.html.
        """
        from fastapi import Request
        from fastapi.responses import FileResponse
        
        app_paths = get_app_paths()
        frontend_dir = app_paths.frontend_dist_path
        index_file = frontend_dir / "index.html"
        
        if not frontend_dir.exists():
            logger.warning(f"Frontend directory not found at {frontend_dir}")
            return
            
        if not index_file.exists():
            logger.warning(f"Frontend index.html not found at {index_file}")
            return
        
        # First, mount static assets (JS, CSS, etc.)
        assets_dir = frontend_dir / "assets"
        if assets_dir.exists():
            self.app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        
        # Handle favicon and other root-level static files
        @self.app.get("/favicon.ico")
        async def favicon():
            favicon_path = frontend_dir / "favicon.ico"
            if favicon_path.exists():
                return FileResponse(str(favicon_path))
            raise HTTPException(status_code=404, detail="Favicon not found")
        
        # Bitcoin logo endpoints
        @self.app.get("/bitcoin-symbol.svg")
        async def bitcoin_symbol_svg():
            """Serve the official Bitcoin symbol SVG."""
            app_paths = get_app_paths()
            bitcoin_svg_path = app_paths.base_path / "assets" / "bitcoin-symbol.svg"
            if bitcoin_svg_path.exists():
                return FileResponse(
                    str(bitcoin_svg_path), 
                    media_type="image/svg+xml",
                    headers={
                        "Cache-Control": "public, max-age=31536000",  # 1 year
                        "ETag": f'"{bitcoin_svg_path.stat().st_mtime}"'
                    }
                )
            raise HTTPException(status_code=404, detail="Bitcoin symbol SVG not found")
        
        @self.app.get("/bitcoin-symbol.png")
        async def bitcoin_symbol_png():
            """Serve the official Bitcoin symbol PNG."""
            app_paths = get_app_paths()
            bitcoin_png_path = app_paths.base_path / "assets" / "bitcoin-symbol.png"
            if bitcoin_png_path.exists():
                return FileResponse(
                    str(bitcoin_png_path),
                    media_type="image/png", 
                    headers={
                        "Cache-Control": "public, max-age=31536000",  # 1 year
                        "ETag": f'"{bitcoin_png_path.stat().st_mtime}"'
                    }
                )
            raise HTTPException(status_code=404, detail="Bitcoin symbol PNG not found")
        
        # Handle root route specifically
        @self.app.get("/")
        async def root_handler():
            """Serve the SPA index.html for the root route."""
            return FileResponse(str(index_file), media_type="text/html")
        
        # Handle all other routes (SPA routes) - this must be last
        @self.app.get("/{full_path:path}")
        async def spa_handler(request: Request, full_path: str):
            """
            Handle SPA routes by serving index.html for non-API routes.
            """
            # Skip API routes
            if full_path.startswith('api/'):
                raise HTTPException(status_code=404, detail="API endpoint not found")
            
            # If it's a request for a static file that doesn't exist, return 404
            if (full_path.endswith(('.js', '.css', '.ico', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.html')) or
                full_path.startswith('assets/')):
                # Check if the HTML file actually exists in the frontend dist directory
                if full_path.endswith('.html'):
                    html_file_path = frontend_dir / full_path
                    if html_file_path.exists():
                        return FileResponse(str(html_file_path), media_type="text/html")
                raise HTTPException(status_code=404, detail="Static file not found")
            
            # For all other routes, serve the SPA index.html
            logger.debug(f"Serving SPA route: /{full_path}")
            return FileResponse(str(index_file), media_type="text/html")
    
    async def start(self):
        """
        Start the API service.
        """
        # Initialize services
        await self.data_storage.initialize()
        await self.miner_manager.start()
        await self.system_monitor.start()
        
        # Start background task for broadcasting updates
        await self._broadcast_updates()
        
        logger.info(f"API service started on {HOST}:{PORT}")
    
    async def stop(self):
        """
        Stop the API service.
        """
        # Stop services
        await self.miner_manager.stop()
        await self.data_storage.close()
        await self.websocket_manager.stop()
        await self.system_monitor.stop()
        
        logger.info("API service stopped")
    
    async def get_miners(self) -> List[Dict[str, Any]]:
        """
        Get all miners.
        
        Returns:
            List[Dict[str, Any]]: List of miners
        """
        # First try to get active miners from the manager
        active_miners = await self.miner_manager.get_miners()
        
        # If no active miners, return saved configurations from database
        if not active_miners:
            try:
                saved_configs = await self.data_storage.get_all_miner_configs()
                return saved_configs
            except Exception as e:
                logger.warning(f"Failed to get saved miner configs: {e}")
                return []
        
        return active_miners
    
    async def get_miner(self, miner_id: str) -> Dict[str, Any]:
        """
        Get a specific miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Dict[str, Any]: Miner information
        """
        miner = await self.miner_manager.get_miner(miner_id)
        if not miner:
            raise HTTPException(status_code=404, detail=f"Miner {miner_id} not found")
        return miner
    
    async def add_miner(self, request: MinerAddRequest) -> Dict[str, Any]:
        """
        Add a new miner with comprehensive input validation.
        
        Args:
            request (MinerAddRequest): Validated miner information
            
        Returns:
            Dict[str, Any]: Added miner information
        """
        try:
            # The request is already validated by Pydantic
            logger.info(f"Adding miner: type={request.type}, ip={request.ip_address}, port={request.port}")
            
            miner_id = await self.miner_manager.add_miner(
                request.type,
                request.ip_address,
                request.port,
                request.name
            )
            
            if not miner_id:
                raise HTTPException(status_code=400, detail="Failed to add miner")
            
            # Save miner configuration
            miner = await self.miner_manager.get_miner(miner_id)
            await self.data_storage.save_miner_config(miner_id, miner)
            
            logger.info(f"Successfully added miner {miner_id}")
            return miner
            
        except AppValidationError as e:
            logger.error(f"Validation error adding miner: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error adding miner: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_miner(self, miner_id: str, request: MinerUpdateRequest) -> Dict[str, Any]:
        """
        Update a miner with input validation.
        
        Args:
            miner_id (str): ID of the miner
            request (MinerUpdateRequest): Validated miner information to update
            
        Returns:
            Dict[str, Any]: Updated miner information
        """
        try:
            # Validate miner_id
            from src.backend.utils.validators import DataSanitizer
            miner_id = DataSanitizer.sanitize_string(miner_id, max_length=100)
            
            # Check if miner exists
            miner = await self.miner_manager.get_miner(miner_id)
            if not miner:
                raise HTTPException(status_code=404, detail=f"Miner {miner_id} not found")
            
            # Prepare updates (request is already validated by Pydantic)
            updates = {}
            if request.name is not None:
                updates["name"] = request.name
            if request.settings is not None:
                updates["settings"] = request.settings
            
            logger.info(f"Updating miner {miner_id} with: {updates}")
            
            # Update miner
            success = await self.miner_manager.update_miner(miner_id, updates)
            if not success:
                raise HTTPException(status_code=400, detail="Failed to update miner")
            
            # Get updated miner information
            miner = await self.miner_manager.get_miner(miner_id)
            
            # Save miner configuration
            await self.data_storage.save_miner_config(miner_id, miner)
            
            logger.info(f"Successfully updated miner {miner_id}")
            return miner
            
        except AppValidationError as e:
            logger.error(f"Validation error updating miner: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating miner: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def remove_miner(self, miner_id: str) -> Dict[str, str]:
        """
        Remove a miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Dict[str, str]: Success message
        """
        # Check if miner exists
        miner = await self.miner_manager.get_miner(miner_id)
        if not miner:
            raise HTTPException(status_code=404, detail=f"Miner {miner_id} not found")
        
        # Remove miner
        success = await self.miner_manager.remove_miner(miner_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove miner")
        
        # Delete miner configuration
        await self.data_storage.delete_miner_config(miner_id)
        
        return {"message": f"Miner {miner_id} removed successfully"}
    
    async def restart_miner(self, miner_id: str) -> Dict[str, bool]:
        """
        Restart a miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Dict[str, bool]: Success status
        """
        # Check if miner exists
        miner = await self.miner_manager.get_miner(miner_id)
        if not miner:
            raise HTTPException(status_code=404, detail=f"Miner {miner_id} not found")
        
        # Restart miner
        success = await self.miner_manager.restart_miner(miner_id)
        
        return {"success": success}
    
    async def get_miner_metrics(
        self,
        miner_id: str,
        start: Optional[str] = Query(None),
        end: Optional[str] = Query(None),
        interval: str = Query("1h"),
        metric_types: Optional[str] = Query(None)
    ) -> List[Dict[str, Any]]:
        """
        Get metrics for a specific miner with comprehensive validation.
        
        Args:
            miner_id (str): ID of the miner
            start (Optional[str]): Start time (ISO format)
            end (Optional[str]): End time (ISO format)
            interval (str): Aggregation interval
            metric_types (Optional[str]): Comma-separated list of metric types
            
        Returns:
            List[Dict[str, Any]]: List of metrics
        """
        try:
            # Parse metric_types if provided
            parsed_metric_types = None
            if metric_types:
                parsed_metric_types = [mt.strip() for mt in metric_types.split(',')]
            
            # Create and validate request using Pydantic model
            request = MetricsQueryRequest(
                miner_id=miner_id,
                start=start,
                end=end,
                interval=interval,
                metric_types=parsed_metric_types
            )
            
            # Check if miner exists
            miner = await self.miner_manager.get_miner(request.miner_id)
            if not miner:
                raise HTTPException(status_code=404, detail=f"Miner {request.miner_id} not found")
            
            # Parse start and end times
            if request.start:
                start_time = datetime.fromisoformat(request.start.replace('Z', '+00:00'))
            else:
                start_time = datetime.now() - timedelta(hours=24)
            
            if request.end:
                end_time = datetime.fromisoformat(request.end.replace('Z', '+00:00'))
            else:
                end_time = datetime.now()
            
            logger.info(f"Getting metrics for miner {request.miner_id} from {start_time} to {end_time}")
            
            # Get metrics
            metrics = await self.data_storage.get_metrics(
                request.miner_id, 
                start_time, 
                end_time, 
                request.interval,
                request.metric_types
            )
            
            return metrics
            
        except PydanticValidationError as e:
            logger.error(f"Validation error in get_miner_metrics: {e}")
            raise HTTPException(status_code=422, detail={"message": "Input validation failed", "errors": e.errors()})
        except AppValidationError as e:
            logger.error(f"Application validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting metrics: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_latest_metrics(self, miner_id: str) -> Dict[str, Any]:
        """
        Get latest metrics for a specific miner.
        
        Args:
            miner_id (str): ID of the miner
            
        Returns:
            Dict[str, Any]: Latest metrics
        """
        # Check if miner exists
        miner = await self.miner_manager.get_miner(miner_id)
        if not miner:
            raise HTTPException(status_code=404, detail=f"Miner {miner_id} not found")
        
        # Get latest metrics
        metrics = await self.data_storage.get_latest_metrics(miner_id)
        
        return metrics
    
    async def start_discovery(self, request: DiscoveryRequest) -> Dict[str, Any]:
        """
        Start discovery of miners on the network with input validation.
        
        Args:
            request (DiscoveryRequest): Validated discovery request
            
        Returns:
            Dict[str, Any]: Discovery status
        """
        try:
            # Request is already validated by Pydantic
            logger.info(f"Starting discovery on network {request.network} with ports {request.ports}")
            
            # Start discovery
            success = await self.miner_manager.start_discovery(
                request.network, 
                request.ports,
                getattr(request, 'timeout', 5)
            )
            if not success:
                raise HTTPException(status_code=400, detail="Failed to start discovery")
            
            # Get discovery status
            status = await self.miner_manager.get_discovery_status()
            
            logger.info("Discovery started successfully")
            return status
            
        except AppValidationError as e:
            logger.error(f"Validation error starting discovery: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error starting discovery: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_discovery_status(self) -> Dict[str, Any]:
        """
        Get the status of the discovery process.
        
        Returns:
            Dict[str, Any]: Discovery status
        """
        return await self.miner_manager.get_discovery_status()
    
    async def get_setup_status(self) -> Dict[str, Any]:
        """
        Get setup status from installer.
        
        Returns:
            Dict[str, Any]: Setup status information
        """
        import os
        import json
        from pathlib import Path
        
        try:
            # Check for setup completion file from installer
            # This would be in the data directory
            app_paths = get_app_paths()
            setup_file = app_paths.data_path / "setup-complete.json"
            
            if setup_file.exists():
                with open(setup_file, 'r') as f:
                    setup_data = json.load(f)
                logger.info(f"Found installer setup data: {setup_data}")
                return setup_data
            else:
                logger.debug(f"No setup file found at {setup_file}")
                return {"installationComplete": False}
                
        except Exception as e:
            logger.error(f"Error reading setup status: {e}")
            return {"installationComplete": False}

    async def get_settings(self) -> Dict[str, Any]:
        """
        Get application settings.
        
        Returns:
            Dict[str, Any]: Application settings
        """
        return await self.data_storage.get_app_settings()
    
    async def update_settings(self, request: AppSettingsRequest) -> Dict[str, Any]:
        """
        Update application settings.
        
        Args:
            request (AppSettingsRequest): Settings to update
            
        Returns:
            Dict[str, Any]: Updated settings
        """
        # Get current settings
        current_settings = await self.data_storage.get_app_settings()
        
        # Update settings
        if request.polling_interval is not None:
            current_settings["polling_interval"] = request.polling_interval
            # Update miner manager polling interval
            await self.miner_manager.set_polling_interval(request.polling_interval)
        
        if request.theme is not None:
            current_settings["theme"] = request.theme
        
        if request.chart_retention_days is not None:
            current_settings["chart_retention_days"] = request.chart_retention_days
        
        if request.refresh_interval is not None:
            current_settings["refresh_interval"] = request.refresh_interval
        
        # Save settings
        await self.data_storage.save_app_settings(current_settings)
        
        return current_settings
    
    async def websocket_endpoint(self, websocket: WebSocket):
        """
        WebSocket endpoint for real-time updates without authentication.
        Provides open access for local network monitoring with comprehensive error handling.
        
        Args:
            websocket (WebSocket): WebSocket connection
        """
        client_id = None
        connection_start_time = datetime.now()
        
        try:
            # Connect client to WebSocket manager (no authentication required)
            client_id = await self.websocket_manager.connect(websocket)
            logger.info(f"WebSocket client {client_id} connected from {getattr(websocket, 'client', {}).host if hasattr(websocket, 'client') else 'unknown'}")
            
            # Subscribe to miners topic by default for immediate updates
            await self.websocket_manager.subscribe(websocket, ["miners"])
            
            # Message handling loop with enhanced error recovery
            message_count = 0
            try:
                while True:
                    try:
                        # Receive message with timeout to prevent hanging
                        raw_message = await asyncio.wait_for(websocket.receive_json(), timeout=60.0)
                        message_count += 1
                        
                        # Validate message using Pydantic model
                        try:
                            validated_message = WebSocketMessage(**raw_message)
                            message = validated_message.dict()
                            
                            logger.debug(f"Client {client_id} sent valid message #{message_count}: {message.get('type', 'unknown')}")
                            await self.websocket_manager.handle_message(websocket, message)
                            
                        except PydanticValidationError as e:
                            logger.warning(f"Client {client_id} sent invalid message #{message_count}: {e}")
                            
                            # Send detailed error response to help client fix the issue
                            error_response = {
                                "type": "validation_error",
                                "data": {
                                    "message": "Invalid message format",
                                    "errors": [
                                        {
                                            "field": error.get("loc", ["unknown"])[0] if error.get("loc") else "unknown",
                                            "message": error.get("msg", "Validation failed"),
                                            "type": error.get("type", "unknown")
                                        }
                                        for error in e.errors()
                                    ],
                                    "received_message": raw_message,
                                    "valid_message_types": ["subscribe", "unsubscribe", "ping", "pong", "get_status", "get_topics"],
                                    "valid_topics": ["miners", "alerts", "system", "metrics"],
                                    "timestamp": datetime.now().isoformat()
                                }
                            }
                            
                            try:
                                await websocket.send_json(error_response)
                            except Exception as send_error:
                                logger.error(f"Failed to send validation error response to client {client_id}: {send_error}")
                                break  # Connection might be closed
                        
                    except asyncio.TimeoutError:
                        # No message received within timeout - this is normal, continue
                        logger.debug(f"No message from client {client_id} within timeout period")
                        continue
                        
                    except WebSocketDisconnect:
                        logger.info(f"WebSocket client {client_id} disconnected normally after {message_count} messages")
                        break
                        
                    except Exception as message_error:
                        logger.error(f"Error processing message from client {client_id}: {message_error}")
                        
                        # Try to send error notification to client
                        try:
                            await websocket.send_json({
                                "type": "processing_error",
                                "data": {
                                    "message": "Error processing your message",
                                    "error_type": type(message_error).__name__,
                                    "timestamp": datetime.now().isoformat()
                                }
                            })
                        except Exception:
                            # If we can't send error response, connection is likely broken
                            logger.error(f"Cannot send error response to client {client_id}, disconnecting")
                            break
                        
            except Exception as loop_error:
                logger.error(f"WebSocket message loop error for client {client_id}: {loop_error}")
                
            finally:
                # Calculate connection statistics
                connection_duration = (datetime.now() - connection_start_time).total_seconds()
                logger.info(f"WebSocket client {client_id} session ended - Duration: {connection_duration:.1f}s, Messages: {message_count}")
                
                # Ensure proper cleanup
                await self.websocket_manager.disconnect(websocket)
                
        except Exception as connection_error:
            logger.error(f"WebSocket connection error for client {client_id or 'unknown'}: {connection_error}")
            
            # Try to close connection gracefully
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except Exception as close_error:
                logger.debug(f"Error closing WebSocket for client {client_id}: {close_error}")
            
            # Ensure cleanup even if connection failed
            if client_id:
                try:
                    await self.websocket_manager.disconnect(websocket)
                except Exception as cleanup_error:
                    logger.error(f"Error during emergency cleanup for client {client_id}: {cleanup_error}")
    
    async def _broadcast_updates(self):
        """
        Set up data providers and start broadcast tasks.
        """
        # Define data providers
        data_providers = {
            "miners": self._get_miners_data,
            "alerts": self._get_alerts_data,
            "system": self._get_system_data,
        }
        
        # Start broadcast tasks
        await self.websocket_manager.start_broadcast_tasks(data_providers)
    
    async def _get_miners_data(self):
        """
        Get miners data for broadcasting.
        
        Returns:
            List[Dict[str, Any]]: Miners data
        """
        # First try to get active miners from the manager
        active_miners = await self.miner_manager.get_miners()
        
        # If no active miners, return saved configurations from database
        if not active_miners:
            try:
                saved_configs = await self.data_storage.get_all_miner_configs()
                return saved_configs
            except Exception as e:
                logger.warning(f"Failed to get saved miner configs for broadcast: {e}")
                return []
        
        return active_miners
    
    async def _get_alerts_data(self):
        """
        Get alerts data for broadcasting.
        
        Returns:
            List[Dict[str, Any]]: Alerts data
        """
        # TODO: Implement alerts service
        return []
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            Dict[str, Any]: System information
        """
        return await self.system_monitor.get_system_info()
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.
        
        Returns:
            Dict[str, Any]: System metrics
        """
        return await self.system_monitor.get_system_metrics()
    
    async def get_system_metrics_history(
        self,
        metric_type: str = Query("cpu", description="Metric type (cpu, memory, disk, network)"),
        start: Optional[str] = Query(None, description="Start time (ISO format)"),
        end: Optional[str] = Query(None, description="End time (ISO format)")
    ) -> List[Dict[str, Any]]:
        """
        Get system metrics history.
        
        Args:
            metric_type (str): Metric type (cpu, memory, disk, network)
            start (Optional[str]): Start time (ISO format)
            end (Optional[str]): End time (ISO format)
            
        Returns:
            List[Dict[str, Any]]: System metrics history
        """
        # Parse start and end times
        start_time = datetime.fromisoformat(start) if start else None
        end_time = datetime.fromisoformat(end) if end else None
        
        return await self.system_monitor.get_metrics_history(metric_type, start_time, end_time)
    
    async def _get_system_data(self):
        """
        Get system data for broadcasting.
        
        Returns:
            Dict[str, Any]: System data
        """
        return await self.system_monitor.get_system_metrics()
    
    async def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics from middleware.
        
        Returns:
            Dict[str, Any]: Validation statistics
        """
        try:
            # Get stats from validation middleware
            validation_stats = {}
            
            # Find validation middleware instances
            for middleware in self.app.user_middleware:
                if hasattr(middleware.cls, 'get_validation_stats'):
                    middleware_name = middleware.cls.__name__
                    # Create temporary instance to get stats
                    temp_instance = middleware.cls(None)
                    if hasattr(temp_instance, 'validation_stats'):
                        validation_stats[middleware_name] = temp_instance.validation_stats
            
            return {
                "status": "success",
                "data": validation_stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting validation stats: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to retrieve validation statistics",
                "timestamp": datetime.now().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            health_checks = {}
            overall_status = "healthy"
            
            # Database health check
            try:
                await self.data_storage.get_app_settings()
                health_checks["database"] = {
                    "status": "healthy",
                    "message": "Database connection successful"
                }
            except Exception as e:
                health_checks["database"] = {
                    "status": "unhealthy",
                    "message": f"Database connection failed: {str(e)}"
                }
                overall_status = "unhealthy"
            
            # Miner manager health check
            try:
                miners = await self.miner_manager.get_miners()
                health_checks["miner_manager"] = {
                    "status": "healthy",
                    "message": f"Managing {len(miners)} miners"
                }
            except Exception as e:
                health_checks["miner_manager"] = {
                    "status": "unhealthy",
                    "message": f"Miner manager error: {str(e)}"
                }
                overall_status = "unhealthy"
            
            # WebSocket manager health check
            try:
                stats = await self.websocket_manager.get_connection_stats()
                connection_count = stats.get("total_connections", 0)
                health_checks["websocket_manager"] = {
                    "status": "healthy",
                    "message": f"{connection_count} active WebSocket connections",
                    "details": stats["connections_by_topic"]
                }
            except Exception as e:
                health_checks["websocket_manager"] = {
                    "status": "unhealthy",
                    "message": f"WebSocket manager error: {str(e)}"
                }
                overall_status = "degraded"
            
            # System monitor health check
            try:
                system_metrics = await self.system_monitor.get_system_metrics()
                health_checks["system_monitor"] = {
                    "status": "healthy",
                    "message": "System monitoring active"
                }
            except Exception as e:
                health_checks["system_monitor"] = {
                    "status": "unhealthy",
                    "message": f"System monitor error: {str(e)}"
                }
                overall_status = "degraded"
            
            return {
                "status": "success",
                "data": {
                    "overall_status": overall_status,
                    "checks": health_checks,
                    "timestamp": datetime.now().isoformat(),
                    "version": "0.1.0"  # TODO: Get from config
                }
            }
        except Exception as e:
            logger.error(f"Error performing health check: {str(e)}")
            return {
                "status": "error",
                "message": "Health check failed",
                "timestamp": datetime.now().isoformat()
            }
    
    async def reload_miners(self) -> Dict[str, Any]:
        """
        Reload miners from database configurations.
        This is useful for development/testing when miners have been added directly to the database.
        
        Returns:
            Dict[str, Any]: Reload result
        """
        try:
            # Get saved configurations from database
            saved_configs = await self.data_storage.get_all_miner_configs()
            
            # Add them to the miner data manager
            from src.backend.utils.thread_safety import miner_data_manager
            
            for config in saved_configs:
                miner_id = config.get('id')
                if miner_id:
                    await miner_data_manager.set_miner(miner_id, config)
            
            logger.info(f"Reloaded {len(saved_configs)} miners from database")
            
            return {
                "success": True,
                "message": f"Successfully reloaded {len(saved_configs)} miners from database",
                "miners_count": len(saved_configs),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to reload miners: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to reload miners: {str(e)}")
    
    async def bulk_miner_action(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform bulk actions on multiple miners.
        
        Args:
            request (Dict[str, Any]): Bulk action request
            
        Returns:
            Dict[str, Any]: Bulk action results
        """
        try:
            # Import and validate using the bulk action schema
            from src.backend.schemas.endpoint_schemas import BulkMinerActionRequest
            
            # Validate request
            validated_request = BulkMinerActionRequest(**request)
            
            results = []
            success_count = 0
            failure_count = 0
            
            # Process each miner
            for miner_id in validated_request.miner_ids:
                try:
                    # Check if miner exists
                    miner = await self.miner_manager.get_miner(miner_id)
                    if not miner:
                        results.append({
                            "miner_id": miner_id,
                            "success": False,
                            "error": "Miner not found"
                        })
                        failure_count += 1
                        continue
                    
                    # Perform action based on type
                    if validated_request.action == "restart":
                        success = await self.miner_manager.restart_miner(miner_id)
                        message = "Restart command sent" if success else "Restart failed"
                    
                    elif validated_request.action == "update_settings":
                        if not validated_request.parameters:
                            raise ValueError("Settings parameters required for update_settings action")
                        success = await self.miner_manager.update_miner(miner_id, validated_request.parameters)
                        message = "Settings updated" if success else "Settings update failed"
                    
                    elif validated_request.action == "delete":
                        success = await self.miner_manager.remove_miner(miner_id)
                        message = "Miner deleted" if success else "Delete failed"
                    
                    else:
                        success = False
                        message = f"Unsupported action: {validated_request.action}"
                    
                    results.append({
                        "miner_id": miner_id,
                        "success": success,
                        "message": message
                    })
                    
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
                        
                except Exception as e:
                    results.append({
                        "miner_id": miner_id,
                        "success": False,
                        "error": str(e)
                    })
                    failure_count += 1
            
            return {
                "status": "success",
                "data": results,
                "summary": {
                    "total": len(validated_request.miner_ids),
                    "success": success_count,
                    "failure": failure_count
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error performing bulk miner action: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))    
 
    async def get_email_config(self) -> Dict[str, Any]:
        """
        Get email configuration (without sensitive data).
        
        Returns:
            Dict[str, Any]: Email configuration
        """
        try:
            config = await self.email_service.get_config()
            return {
                "status": "success",
                "data": config,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting email config: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def update_email_config(self, request: EmailConfigRequest) -> Dict[str, Any]:
        """
        Update email configuration.
        
        Args:
            request (EmailConfigRequest): Email configuration update request
            
        Returns:
            Dict[str, Any]: Updated configuration
        """
        try:
            # Convert request to dict, excluding None values
            config_data = {k: v for k, v in request.model_dump().items() if v is not None}
            
            # Update configuration
            updated_config = await self.email_service.update_config(config_data)
            
            return {
                "status": "success",
                "data": updated_config,
                "message": "Email configuration updated successfully",
                "timestamp": datetime.now().isoformat()
            }
            
        except ValueError as e:
            logger.warning(f"Email config validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating email config: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def send_test_email(self, request: EmailTestRequest) -> Dict[str, Any]:
        """
        Send a test email.
        
        Args:
            request (EmailTestRequest): Test email request
            
        Returns:
            Dict[str, Any]: Test result
        """
        try:
            result = await self.email_service.send_test_email(request.to_email)
            
            if result["success"]:
                return {
                    "status": "success",
                    "data": result,
                    "message": "Test email sent successfully",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "data": result,
                    "message": result.get("error", "Failed to send test email"),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error sending test email: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def send_notification_email(self, request: EmailNotificationRequest) -> Dict[str, Any]:
        """
        Send a notification email.
        
        Args:
            request (EmailNotificationRequest): Notification email request
            
        Returns:
            Dict[str, Any]: Send result
        """
        try:
            result = await self.email_service.send_notification_email(
                request.to_email,
                request.notification_type,
                request.data
            )
            
            if result["success"]:
                return {
                    "status": "success",
                    "data": result,
                    "message": "Notification email sent successfully",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "data": result,
                    "message": result.get("error", "Failed to send notification email"),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error sending notification email: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")