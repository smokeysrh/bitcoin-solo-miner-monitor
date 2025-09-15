"""
Comprehensive API Endpoint Validation Schemas

This module provides validation schemas for all API endpoints, ensuring
consistent and comprehensive input validation across the entire application.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

from src.backend.utils.validators import (
    IPAddressValidator,
    PortValidator,
    DataSanitizer,
    MinerTypeValidator,
    URLValidator
)
from src.backend.exceptions import ValidationError as AppValidationError


class ResponseStatus(str, Enum):
    """Enumeration for API response statuses."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class SortOrder(str, Enum):
    """Enumeration for sort orders."""
    ASC = "asc"
    DESC = "desc"


class MinerStatus(str, Enum):
    """Enumeration for miner statuses."""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    CONNECTING = "connecting"


class MetricType(str, Enum):
    """Enumeration for metric types."""
    HASHRATE = "hashrate"
    TEMPERATURE = "temperature"
    POWER = "power"
    VOLTAGE = "voltage"
    FREQUENCY = "frequency"
    SHARES_ACCEPTED = "shares_accepted"
    SHARES_REJECTED = "shares_rejected"
    UPTIME = "uptime"
    EFFICIENCY = "efficiency"


# Base Response Models
class BaseResponse(BaseModel):
    """Base response model for all API endpoints."""
    
    status: ResponseStatus = Field(..., description="Response status")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ErrorResponse(BaseResponse):
    """Error response model."""
    
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="Error status")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


class PaginationRequest(BaseModel):
    """Request model for paginated endpoints."""
    
    limit: int = Field(100, ge=1, le=10000, description="Maximum number of items to return")
    offset: int = Field(0, ge=0, description="Number of items to skip")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: SortOrder = Field(SortOrder.ASC, description="Sort order")
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        if v is not None:
            return DataSanitizer.sanitize_string(v, max_length=50)
        return v


class PaginationResponse(BaseModel):
    """Response model for paginated data."""
    
    total: int = Field(..., ge=0, description="Total number of items")
    limit: int = Field(..., ge=1, description="Items per page")
    offset: int = Field(..., ge=0, description="Items skipped")
    has_more: bool = Field(..., description="Whether there are more items")


# Miner Management Schemas
class MinerListRequest(PaginationRequest):
    """Request model for listing miners."""
    
    status_filter: Optional[MinerStatus] = Field(None, description="Filter by miner status")
    type_filter: Optional[str] = Field(None, description="Filter by miner type")
    search: Optional[str] = Field(None, description="Search term for miner names")
    
    @field_validator('type_filter')
    @classmethod
    def validate_type_filter(cls, v):
        """Validate miner type filter."""
        if v is not None:
            return MinerTypeValidator.validate_miner_type(v)
        return v
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, v):
        """Validate search term."""
        if v is not None:
            return DataSanitizer.sanitize_string(v, max_length=100)
        return v


class MinerResponse(BaseModel):
    """Response model for miner data."""
    
    id: str = Field(..., description="Miner ID")
    name: str = Field(..., description="Miner name")
    type: str = Field(..., description="Miner type")
    ip_address: str = Field(..., description="IP address")
    port: int = Field(..., description="Port number")
    status: MinerStatus = Field(..., description="Current status")
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class MinerListResponse(BaseResponse):
    """Response model for miner list."""
    
    data: List[MinerResponse] = Field(..., description="List of miners")
    pagination: PaginationResponse = Field(..., description="Pagination information")


class MinerDetailResponse(BaseResponse):
    """Response model for detailed miner information."""
    
    data: MinerResponse = Field(..., description="Miner details")
    device_info: Optional[Dict[str, Any]] = Field(None, description="Device information")
    pool_info: Optional[List[Dict[str, Any]]] = Field(None, description="Pool information")
    supported_features: List[str] = Field(default_factory=list, description="Supported features")


# Metrics Schemas
class MetricsRequest(BaseModel):
    """Request model for metrics queries."""
    
    miner_id: str = Field(..., description="Miner ID")
    start: Optional[datetime] = Field(None, description="Start time")
    end: Optional[datetime] = Field(None, description="End time")
    interval: str = Field("1h", description="Aggregation interval")
    metric_types: Optional[List[MetricType]] = Field(None, description="Specific metric types")
    aggregation: str = Field("avg", description="Aggregation function")
    
    @field_validator('miner_id')
    @classmethod
    def validate_miner_id(cls, v):
        """Validate miner ID."""
        return DataSanitizer.sanitize_string(v, max_length=100)
    
    @field_validator('interval')
    @classmethod
    def validate_interval(cls, v):
        """Validate aggregation interval."""
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '6h', '12h', '1d']
        if v not in valid_intervals:
            raise AppValidationError(f"Invalid interval: {v}. Valid intervals: {', '.join(valid_intervals)}")
        return v
    
    @field_validator('aggregation')
    @classmethod
    def validate_aggregation(cls, v):
        """Validate aggregation function."""
        valid_aggregations = ['avg', 'min', 'max', 'sum', 'count']
        if v not in valid_aggregations:
            raise AppValidationError(f"Invalid aggregation: {v}. Valid aggregations: {', '.join(valid_aggregations)}")
        return v
    
    @model_validator(mode='after')
    def validate_time_range(self):
        """Validate time range consistency."""
        if self.start and self.end:
            if self.start >= self.end:
                raise AppValidationError("Start time must be before end time")
            
            # Limit query range to prevent excessive data retrieval
            max_days = 90
            if (self.end - self.start).days > max_days:
                raise AppValidationError(f"Query range cannot exceed {max_days} days")
        
        return self


class MetricDataPoint(BaseModel):
    """Model for a single metric data point."""
    
    timestamp: datetime = Field(..., description="Metric timestamp")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit")


class MetricSeries(BaseModel):
    """Model for a metric time series."""
    
    metric_type: MetricType = Field(..., description="Type of metric")
    data_points: List[MetricDataPoint] = Field(..., description="Metric data points")
    aggregation: str = Field(..., description="Aggregation function used")
    interval: str = Field(..., description="Time interval")


class MetricsResponse(BaseResponse):
    """Response model for metrics data."""
    
    data: List[MetricSeries] = Field(..., description="Metric time series")
    miner_id: str = Field(..., description="Miner ID")
    time_range: Dict[str, datetime] = Field(..., description="Query time range")


# Discovery Schemas
class DiscoveryProgressResponse(BaseResponse):
    """Response model for discovery progress."""
    
    data: Dict[str, Any] = Field(..., description="Discovery progress data")
    is_running: bool = Field(..., description="Whether discovery is running")
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress percentage")
    discovered_miners: List[Dict[str, Any]] = Field(default_factory=list, description="Discovered miners")


# Settings Schemas
class SettingsRequest(BaseModel):
    """Request model for application settings."""
    
    polling_interval: Optional[int] = Field(None, ge=5, le=3600, description="Polling interval in seconds")
    theme: Optional[str] = Field(None, description="UI theme")
    chart_retention_days: Optional[int] = Field(None, ge=1, le=365, description="Chart data retention days")
    refresh_interval: Optional[int] = Field(None, ge=1, le=300, description="UI refresh interval")
    notifications_enabled: Optional[bool] = Field(None, description="Enable notifications")
    alert_thresholds: Optional[Dict[str, float]] = Field(None, description="Alert thresholds")
    
    @field_validator('theme')
    @classmethod
    def validate_theme(cls, v):
        """Validate theme setting."""
        if v is not None:
            v = DataSanitizer.sanitize_string(v, max_length=20)
            if v not in ['light', 'dark', 'auto']:
                raise AppValidationError("Theme must be 'light', 'dark', or 'auto'")
        return v
    
    @field_validator('alert_thresholds')
    @classmethod
    def validate_alert_thresholds(cls, v):
        """Validate alert thresholds."""
        if v is not None:
            if not isinstance(v, dict):
                raise AppValidationError("Alert thresholds must be a dictionary")
            
            valid_metrics = ['temperature', 'hashrate', 'power', 'rejection_rate']
            for metric, threshold in v.items():
                if metric not in valid_metrics:
                    raise AppValidationError(f"Invalid alert metric: {metric}")
                if not isinstance(threshold, (int, float)):
                    raise AppValidationError(f"Alert threshold for {metric} must be a number")
        return v


class SettingsResponse(BaseResponse):
    """Response model for application settings."""
    
    data: Dict[str, Any] = Field(..., description="Application settings")


# System Monitoring Schemas
class SystemInfoResponse(BaseResponse):
    """Response model for system information."""
    
    data: Dict[str, Any] = Field(..., description="System information")
    version: str = Field(..., description="Application version")
    uptime: int = Field(..., description="System uptime in seconds")


class SystemMetricsResponse(BaseResponse):
    """Response model for system metrics."""
    
    data: Dict[str, Any] = Field(..., description="System metrics")
    timestamp: datetime = Field(..., description="Metrics timestamp")


# WebSocket Schemas
class WebSocketSubscriptionRequest(BaseModel):
    """Request model for WebSocket subscriptions."""
    
    type: str = Field(..., description="Message type")
    topic: str = Field(..., description="Topic to subscribe to")
    filters: Optional[Dict[str, Any]] = Field(None, description="Subscription filters")
    
    @field_validator('type')
    @classmethod
    def validate_message_type(cls, v):
        """Validate WebSocket message type."""
        valid_types = ['subscribe', 'unsubscribe', 'ping', 'pong']
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if v not in valid_types:
            raise AppValidationError(f"Invalid message type: {v}")
        return v
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v):
        """Validate WebSocket topic."""
        valid_topics = ['miners', 'metrics', 'alerts', 'system', 'discovery']
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if v not in valid_topics:
            raise AppValidationError(f"Invalid topic: {v}")
        return v
    
    @field_validator('filters')
    @classmethod
    def validate_filters(cls, v):
        """Validate subscription filters."""
        if v is not None:
            return DataSanitizer.sanitize_json_data(v)
        return v


class WebSocketResponse(BaseModel):
    """Response model for WebSocket messages."""
    
    type: str = Field(..., description="Message type")
    topic: str = Field(..., description="Message topic")
    data: Any = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")


# Bulk Operations Schemas
class BulkMinerActionRequest(BaseModel):
    """Request model for bulk miner actions."""
    
    miner_ids: List[str] = Field(..., min_length=1, max_length=100, description="List of miner IDs")
    action: str = Field(..., description="Action to perform")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Action parameters")
    
    @field_validator('miner_ids')
    @classmethod
    def validate_miner_ids(cls, v):
        """Validate miner ID list."""
        validated_ids = []
        for miner_id in v:
            validated_id = DataSanitizer.sanitize_string(miner_id, max_length=100)
            validated_ids.append(validated_id)
        return validated_ids
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        """Validate bulk action."""
        valid_actions = ['restart', 'update_settings', 'delete', 'enable', 'disable']
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if v not in valid_actions:
            raise AppValidationError(f"Invalid action: {v}")
        return v
    
    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v):
        """Validate action parameters."""
        if v is not None:
            return DataSanitizer.sanitize_json_data(v)
        return v


class BulkActionResult(BaseModel):
    """Model for individual bulk action result."""
    
    miner_id: str = Field(..., description="Miner ID")
    success: bool = Field(..., description="Whether action succeeded")
    message: Optional[str] = Field(None, description="Result message")
    error: Optional[str] = Field(None, description="Error message if failed")


class BulkMinerActionResponse(BaseResponse):
    """Response model for bulk miner actions."""
    
    data: List[BulkActionResult] = Field(..., description="Action results")
    summary: Dict[str, int] = Field(..., description="Summary statistics")


# Export Management Schemas
class ExportRequest(BaseModel):
    """Request model for data export."""
    
    export_type: str = Field(..., description="Type of data to export")
    format: str = Field("json", description="Export format")
    date_range: Optional[Dict[str, datetime]] = Field(None, description="Date range for export")
    filters: Optional[Dict[str, Any]] = Field(None, description="Export filters")
    
    @field_validator('export_type')
    @classmethod
    def validate_export_type(cls, v):
        """Validate export type."""
        valid_types = ['miners', 'metrics', 'settings', 'logs', 'all']
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if v not in valid_types:
            raise AppValidationError(f"Invalid export type: {v}")
        return v
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        """Validate export format."""
        valid_formats = ['json', 'csv', 'xlsx']
        v = DataSanitizer.sanitize_string(v, max_length=10)
        if v not in valid_formats:
            raise AppValidationError(f"Invalid export format: {v}")
        return v
    
    @field_validator('filters')
    @classmethod
    def validate_filters(cls, v):
        """Validate export filters."""
        if v is not None:
            return DataSanitizer.sanitize_json_data(v)
        return v


class ExportResponse(BaseResponse):
    """Response model for data export."""
    
    data: Dict[str, Any] = Field(..., description="Export data or download information")
    export_id: str = Field(..., description="Export job ID")
    download_url: Optional[str] = Field(None, description="Download URL if applicable")


# Health Check Schemas
class HealthCheckResponse(BaseResponse):
    """Response model for health checks."""
    
    data: Dict[str, Any] = Field(..., description="Health check results")
    overall_status: str = Field(..., description="Overall system health")
    checks: Dict[str, Dict[str, Any]] = Field(..., description="Individual health checks")


# Validation Statistics Schemas
class ValidationStatsResponse(BaseResponse):
    """Response model for validation statistics."""
    
    data: Dict[str, int] = Field(..., description="Validation statistics")
    middleware_stats: Dict[str, Dict[str, int]] = Field(..., description="Middleware statistics")


# All schemas for easy import
__all__ = [
    # Base models
    'BaseResponse',
    'ErrorResponse',
    'PaginationRequest',
    'PaginationResponse',
    
    # Enums
    'ResponseStatus',
    'SortOrder',
    'MinerStatus',
    'MetricType',
    
    # Miner schemas
    'MinerListRequest',
    'MinerResponse',
    'MinerListResponse',
    'MinerDetailResponse',
    
    # Metrics schemas
    'MetricsRequest',
    'MetricDataPoint',
    'MetricSeries',
    'MetricsResponse',
    
    # Discovery schemas
    'DiscoveryProgressResponse',
    
    # Settings schemas
    'SettingsRequest',
    'SettingsResponse',
    
    # System schemas
    'SystemInfoResponse',
    'SystemMetricsResponse',
    
    # WebSocket schemas
    'WebSocketSubscriptionRequest',
    'WebSocketResponse',
    
    # Bulk operations schemas
    'BulkMinerActionRequest',
    'BulkActionResult',
    'BulkMinerActionResponse',
    
    # Export schemas
    'ExportRequest',
    'ExportResponse',
    
    # Health check schemas
    'HealthCheckResponse',
    
    # Validation schemas
    'ValidationStatsResponse'
]