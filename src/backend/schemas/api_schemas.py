"""
API Schema definitions for comprehensive input validation.

This module provides centralized schema definitions for all API endpoints,
ensuring consistent validation across the application.
"""

# Re-export validation models for centralized access
from src.backend.models.validation_models import (
    MinerAddRequest,
    MinerUpdateRequest,
    DiscoveryRequest,
    AppSettingsRequest,
    MetricsQueryRequest,
    WebSocketMessage,
    SystemMetricsRequest,
    MinerConfigurationRequest,
    DatabaseQueryRequest
)

# Re-export validators for easy access
from src.backend.utils.validators import (
    IPAddressValidator,
    PortValidator,
    DataSanitizer,
    MinerTypeValidator,
    URLValidator,
    validate_input_data
)

# Re-export query builder for safe database operations
from src.backend.utils.query_builder import (
    SafeQueryBuilder,
    DatabaseQueryExecutor
)

__all__ = [
    # Request models
    'MinerAddRequest',
    'MinerUpdateRequest', 
    'DiscoveryRequest',
    'AppSettingsRequest',
    'MetricsQueryRequest',
    'WebSocketMessage',
    'SystemMetricsRequest',
    'MinerConfigurationRequest',
    'DatabaseQueryRequest',
    
    # Validators
    'IPAddressValidator',
    'PortValidator',
    'DataSanitizer',
    'MinerTypeValidator',
    'URLValidator',
    'validate_input_data',
    
    # Query builders
    'SafeQueryBuilder',
    'DatabaseQueryExecutor'
]