"""
Pydantic models for comprehensive input validation.

This module defines Pydantic models for validating API requests and ensuring
data integrity throughout the application.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from src.backend.utils.validators import (
    IPAddressValidator, 
    PortValidator, 
    DataSanitizer, 
    MinerTypeValidator,
    URLValidator
)
from src.backend.exceptions import ValidationError as AppValidationError


class MinerAddRequest(BaseModel):
    """Validation model for adding a new miner."""
    
    type: str = Field(..., description="Type of miner (bitaxe, avalon_nano, magic_miner)")
    ip_address: str = Field(..., description="IP address of the miner")
    port: Optional[int] = Field(None, description="Port number for miner communication")
    name: Optional[str] = Field(None, description="Custom name for the miner")
    
    @field_validator('type')
    @classmethod
    def validate_miner_type(cls, v):
        """Validate miner type."""
        return MinerTypeValidator.validate_miner_type(v)
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v):
        """Validate IP address format."""
        return IPAddressValidator.validate_ip_address(v)
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        """Validate port number."""
        if v is not None:
            return PortValidator.validate_port(v, 'all')
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate miner name."""
        if v is not None:
            return DataSanitizer.sanitize_miner_name(v)
        return v
    
    @model_validator(mode='after')
    def validate_miner_config(self):
        """Validate complete miner configuration."""
        # Set default ports based on miner type if not provided
        if self.port is None:
            default_ports = {
                'bitaxe': 80,
                'avalon_nano': 4028,
                'magic_miner': 80
            }
            self.port = default_ports.get(self.type, 80)
        
        return self


class MinerUpdateRequest(BaseModel):
    """Validation model for updating a miner."""
    
    name: Optional[str] = Field(None, description="Updated name for the miner")
    settings: Optional[Dict[str, Any]] = Field(None, description="Updated settings for the miner")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate miner name."""
        if v is not None:
            return DataSanitizer.sanitize_miner_name(v)
        return v
    
    @field_validator('settings')
    @classmethod
    def validate_settings(cls, v):
        """Validate miner settings."""
        if v is not None:
            return DataSanitizer.sanitize_json_data(v)
        return v


class DiscoveryRequest(BaseModel):
    """Validation model for network discovery requests."""
    
    network: str = Field(..., description="Network range in CIDR notation (e.g., 192.168.1.0/24)")
    ports: Optional[List[int]] = Field(None, description="List of ports to scan")
    timeout: Optional[int] = Field(5, description="Timeout in seconds for each connection attempt")
    
    @field_validator('network')
    @classmethod
    def validate_network(cls, v):
        """Validate network range."""
        return IPAddressValidator.validate_network_range(v)
    
    @field_validator('ports')
    @classmethod
    def validate_ports(cls, v):
        """Validate port list."""
        if v is not None:
            if len(v) > 50:  # Limit number of ports to prevent abuse
                raise AppValidationError("Too many ports specified (maximum 50)")
            return PortValidator.validate_port_list(v, 'all')
        return v
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout value."""
        if v is not None:
            if not (1 <= v <= 60):
                raise AppValidationError("Timeout must be between 1 and 60 seconds")
        return v


class AppSettingsRequest(BaseModel):
    """Validation model for application settings updates."""
    
    polling_interval: Optional[int] = Field(None, description="Polling interval in seconds")
    theme: Optional[str] = Field(None, description="UI theme (light, dark)")
    chart_retention_days: Optional[int] = Field(None, description="Number of days to retain chart data")
    refresh_interval: Optional[int] = Field(None, description="UI refresh interval in seconds")
    
    @field_validator('polling_interval')
    @classmethod
    def validate_polling_interval(cls, v):
        """Validate polling interval."""
        if v is not None:
            if not (5 <= v <= 3600):  # 5 seconds to 1 hour
                raise AppValidationError("Polling interval must be between 5 and 3600 seconds")
        return v
    
    @field_validator('theme')
    @classmethod
    def validate_theme(cls, v):
        """Validate theme setting."""
        if v is not None:
            v = DataSanitizer.sanitize_string(v, max_length=20)
            if v not in ['light', 'dark']:
                raise AppValidationError("Theme must be 'light' or 'dark'")
        return v
    
    @field_validator('chart_retention_days')
    @classmethod
    def validate_chart_retention_days(cls, v):
        """Validate chart retention days."""
        if v is not None:
            if not (1 <= v <= 365):  # 1 day to 1 year
                raise AppValidationError("Chart retention days must be between 1 and 365")
        return v
    
    @field_validator('refresh_interval')
    @classmethod
    def validate_refresh_interval(cls, v):
        """Validate refresh interval."""
        if v is not None:
            if not (1 <= v <= 300):  # 1 second to 5 minutes
                raise AppValidationError("Refresh interval must be between 1 and 300 seconds")
        return v


class MetricsQueryRequest(BaseModel):
    """Validation model for metrics query requests."""
    
    miner_id: str = Field(..., description="ID of the miner")
    start: Optional[str] = Field(None, description="Start time in ISO format")
    end: Optional[str] = Field(None, description="End time in ISO format")
    interval: str = Field("1h", description="Aggregation interval (1m, 5m, 1h, 1d)")
    metric_types: Optional[List[str]] = Field(None, description="Specific metric types to query")
    
    @field_validator('miner_id')
    @classmethod
    def validate_miner_id(cls, v):
        """Validate miner ID."""
        return DataSanitizer.sanitize_string(v, max_length=100)
    
    @field_validator('start', 'end')
    @classmethod
    def validate_datetime(cls, v):
        """Validate datetime strings."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise AppValidationError(f"Invalid datetime format: {v}. Use ISO format.")
        return v
    
    @field_validator('interval')
    @classmethod
    def validate_interval(cls, v):
        """Validate aggregation interval."""
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '6h', '12h', '1d']
        if v not in valid_intervals:
            raise AppValidationError(f"Invalid interval: {v}. Valid intervals: {', '.join(valid_intervals)}")
        return v
    
    @field_validator('metric_types')
    @classmethod
    def validate_metric_types(cls, v):
        """Validate metric types."""
        if v is not None:
            valid_metrics = [
                'hashrate', 'temperature', 'power', 'voltage', 'frequency',
                'shares_accepted', 'shares_rejected', 'uptime', 'efficiency'
            ]
            for metric in v:
                if metric not in valid_metrics:
                    raise AppValidationError(f"Invalid metric type: {metric}")
        return v
    
    @model_validator(mode='after')
    def validate_time_range(self):
        """Validate time range consistency."""
        if self.start and self.end:
            try:
                start_dt = datetime.fromisoformat(self.start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(self.end.replace('Z', '+00:00'))
                
                if start_dt >= end_dt:
                    raise AppValidationError("Start time must be before end time")
                
                # Limit query range to prevent excessive data retrieval
                max_days = 90
                if (end_dt - start_dt).days > max_days:
                    raise AppValidationError(f"Query range cannot exceed {max_days} days")
                    
            except ValueError as e:
                raise AppValidationError(f"Invalid datetime format: {str(e)}")
        
        return self


class WebSocketMessage(BaseModel):
    """Validation model for WebSocket messages."""
    
    type: str = Field(..., description="Message type")
    data: Optional[Dict[str, Any]] = Field(None, description="Message data")
    topic: Optional[str] = Field(None, description="Topic to subscribe/unsubscribe")
    
    @field_validator('type')
    @classmethod
    def validate_message_type(cls, v):
        """Validate message type."""
        valid_types = ['subscribe', 'unsubscribe', 'ping', 'pong', 'data', 'heartbeat', 'status']
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if v not in valid_types:
            raise AppValidationError(f"Invalid message type: {v}")
        return v
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v):
        """Validate topic name."""
        if v is not None:
            valid_topics = ['miners', 'alerts', 'system', 'metrics']
            v = DataSanitizer.sanitize_string(v, max_length=50)
            if v not in valid_topics:
                raise AppValidationError(f"Invalid topic: {v}")
        return v
    
    @field_validator('data')
    @classmethod
    def validate_data(cls, v):
        """Validate message data."""
        if v is not None:
            return DataSanitizer.sanitize_json_data(v)
        return v


class SystemMetricsRequest(BaseModel):
    """Validation model for system metrics requests."""
    
    metric_type: str = Field("cpu", description="Type of system metric")
    start: Optional[str] = Field(None, description="Start time in ISO format")
    end: Optional[str] = Field(None, description="End time in ISO format")
    
    @field_validator('metric_type')
    @classmethod
    def validate_metric_type(cls, v):
        """Validate system metric type."""
        valid_types = ['cpu', 'memory', 'disk', 'network', 'temperature']
        v = DataSanitizer.sanitize_string(v, max_length=20)
        if v not in valid_types:
            raise AppValidationError(f"Invalid metric type: {v}")
        return v
    
    @field_validator('start', 'end')
    @classmethod
    def validate_datetime(cls, v):
        """Validate datetime strings."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise AppValidationError(f"Invalid datetime format: {v}")
        return v


class MinerConfigurationRequest(BaseModel):
    """Validation model for miner configuration updates."""
    
    frequency: Optional[int] = Field(None, description="Mining frequency in MHz")
    voltage: Optional[float] = Field(None, description="Core voltage in volts")
    pool_url: Optional[str] = Field(None, description="Mining pool URL")
    pool_user: Optional[str] = Field(None, description="Mining pool username")
    pool_password: Optional[str] = Field(None, description="Mining pool password")
    fan_speed: Optional[int] = Field(None, description="Fan speed percentage")
    auto_fan: Optional[bool] = Field(None, description="Enable automatic fan control")
    temperature_target: Optional[float] = Field(None, description="Target temperature in Celsius")
    power_limit: Optional[int] = Field(None, description="Power limit in watts")
    
    @field_validator('frequency')
    @classmethod
    def validate_frequency(cls, v):
        """Validate mining frequency."""
        if v is not None:
            if not (100 <= v <= 2000):  # Reasonable frequency range in MHz
                raise AppValidationError("Frequency must be between 100 and 2000 MHz")
        return v
    
    @field_validator('voltage')
    @classmethod
    def validate_voltage(cls, v):
        """Validate core voltage."""
        if v is not None:
            if not (0.5 <= v <= 2.0):  # Reasonable voltage range
                raise AppValidationError("Voltage must be between 0.5 and 2.0 volts")
        return v
    
    @field_validator('pool_url')
    @classmethod
    def validate_pool_url(cls, v):
        """Validate mining pool URL."""
        if v is not None:
            return URLValidator.validate_url(v, ['stratum+tcp', 'stratum+ssl', 'http', 'https'])
        return v
    
    @field_validator('pool_user')
    @classmethod
    def validate_pool_user(cls, v):
        """Validate pool username."""
        if v is not None:
            return DataSanitizer.sanitize_string(v, max_length=200)
        return v
    
    @field_validator('pool_password')
    @classmethod
    def validate_pool_password(cls, v):
        """Validate pool password."""
        if v is not None:
            return DataSanitizer.sanitize_string(v, max_length=200)
        return v
    
    @field_validator('fan_speed')
    @classmethod
    def validate_fan_speed(cls, v):
        """Validate fan speed percentage."""
        if v is not None:
            if not (0 <= v <= 100):
                raise AppValidationError("Fan speed must be between 0 and 100 percent")
        return v
    
    @field_validator('temperature_target')
    @classmethod
    def validate_temperature_target(cls, v):
        """Validate target temperature."""
        if v is not None:
            if not (30 <= v <= 100):  # Reasonable temperature range in Celsius
                raise AppValidationError("Temperature target must be between 30 and 100 degrees Celsius")
        return v
    
    @field_validator('power_limit')
    @classmethod
    def validate_power_limit(cls, v):
        """Validate power limit."""
        if v is not None:
            if not (10 <= v <= 1000):  # Reasonable power range in watts
                raise AppValidationError("Power limit must be between 10 and 1000 watts")
        return v


class BitaxeConfigurationRequest(MinerConfigurationRequest):
    """Validation model for Bitaxe-specific configuration."""
    
    asic_frequency: Optional[int] = Field(None, description="ASIC frequency in MHz")
    asic_voltage: Optional[float] = Field(None, description="ASIC voltage in volts")
    flip_screen: Optional[bool] = Field(None, description="Flip screen orientation")
    invert_screen: Optional[bool] = Field(None, description="Invert screen colors")
    
    @field_validator('asic_frequency')
    @classmethod
    def validate_asic_frequency(cls, v):
        """Validate ASIC frequency for Bitaxe."""
        if v is not None:
            if not (400 <= v <= 600):  # Bitaxe-specific frequency range
                raise AppValidationError("ASIC frequency must be between 400 and 600 MHz for Bitaxe")
        return v
    
    @field_validator('asic_voltage')
    @classmethod
    def validate_asic_voltage(cls, v):
        """Validate ASIC voltage for Bitaxe."""
        if v is not None:
            if not (1.0 <= v <= 1.3):  # Bitaxe-specific voltage range
                raise AppValidationError("ASIC voltage must be between 1.0 and 1.3 volts for Bitaxe")
        return v


class AvalonNanoConfigurationRequest(MinerConfigurationRequest):
    """Validation model for Avalon Nano-specific configuration."""
    
    led_brightness: Optional[int] = Field(None, description="LED brightness percentage")
    mining_mode: Optional[str] = Field(None, description="Mining mode")
    
    @field_validator('led_brightness')
    @classmethod
    def validate_led_brightness(cls, v):
        """Validate LED brightness."""
        if v is not None:
            if not (0 <= v <= 100):
                raise AppValidationError("LED brightness must be between 0 and 100 percent")
        return v
    
    @field_validator('mining_mode')
    @classmethod
    def validate_mining_mode(cls, v):
        """Validate mining mode for Avalon Nano."""
        if v is not None:
            valid_modes = ['eco', 'normal', 'turbo']
            v = DataSanitizer.sanitize_string(v, max_length=20).lower()
            if v not in valid_modes:
                raise AppValidationError(f"Mining mode must be one of: {', '.join(valid_modes)}")
        return v


class MagicMinerConfigurationRequest(MinerConfigurationRequest):
    """Validation model for Magic Miner-specific configuration."""
    
    overclock_profile: Optional[str] = Field(None, description="Overclock profile")
    cooling_mode: Optional[str] = Field(None, description="Cooling mode")
    
    @field_validator('overclock_profile')
    @classmethod
    def validate_overclock_profile(cls, v):
        """Validate overclock profile."""
        if v is not None:
            valid_profiles = ['conservative', 'balanced', 'aggressive', 'custom']
            v = DataSanitizer.sanitize_string(v, max_length=20).lower()
            if v not in valid_profiles:
                raise AppValidationError(f"Overclock profile must be one of: {', '.join(valid_profiles)}")
        return v
    
    @field_validator('cooling_mode')
    @classmethod
    def validate_cooling_mode(cls, v):
        """Validate cooling mode."""
        if v is not None:
            valid_modes = ['silent', 'auto', 'performance']
            v = DataSanitizer.sanitize_string(v, max_length=20).lower()
            if v not in valid_modes:
                raise AppValidationError(f"Cooling mode must be one of: {', '.join(valid_modes)}")
        return v


class DatabaseQueryRequest(BaseModel):
    """Validation model for database query parameters."""
    
    table: str = Field(..., description="Database table name")
    filters: Optional[Dict[str, Any]] = Field(None, description="Query filters")
    limit: Optional[int] = Field(None, description="Maximum number of results")
    offset: Optional[int] = Field(None, description="Query offset for pagination")
    order_by: Optional[str] = Field(None, description="Field to order results by")
    
    @field_validator('table')
    @classmethod
    def validate_table(cls, v):
        """Validate table name to prevent SQL injection."""
        # Only allow specific table names
        valid_tables = ['miners', 'settings', 'miner_metrics', 'miner_status']
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if v not in valid_tables:
            raise AppValidationError(f"Invalid table name: {v}")
        return v
    
    @field_validator('filters')
    @classmethod
    def validate_filters(cls, v):
        """Validate query filters."""
        if v is not None:
            return DataSanitizer.sanitize_json_data(v)
        return v
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v):
        """Validate query limit."""
        if v is not None:
            if not (1 <= v <= 10000):  # Prevent excessive data retrieval
                raise AppValidationError("Limit must be between 1 and 10000")
        return v
    
    @field_validator('offset')
    @classmethod
    def validate_offset(cls, v):
        """Validate query offset."""
        if v is not None:
            if v < 0:
                raise AppValidationError("Offset must be non-negative")
        return v
    
    @field_validator('order_by')
    @classmethod
    def validate_order_by(cls, v):
        """Validate order by field."""
        if v is not None:
            # Only allow specific field names to prevent SQL injection
            valid_fields = [
                'id', 'created_at', 'updated_at', 'timestamp', 
                'miner_id', 'metric_type', 'value'
            ]
            v = DataSanitizer.sanitize_string(v, max_length=50)
            if v not in valid_fields:
                raise AppValidationError(f"Invalid order by field: {v}")
        return v


class EmailConfigRequest(BaseModel):
    """Validation model for email configuration updates."""
    
    enabled: Optional[bool] = Field(None, description="Enable/disable email notifications")
    smtp_server: Optional[str] = Field(None, description="SMTP server hostname")
    smtp_port: Optional[int] = Field(None, description="SMTP server port")
    username: Optional[str] = Field(None, description="SMTP username")
    password: Optional[str] = Field(None, description="SMTP password")
    use_tls: Optional[bool] = Field(None, description="Use TLS encryption")
    from_address: Optional[str] = Field(None, description="From email address")
    from_name: Optional[str] = Field(None, description="From name")
    
    @field_validator('smtp_server')
    @classmethod
    def validate_smtp_server(cls, v):
        """Validate SMTP server hostname."""
        if v is not None:
            v = DataSanitizer.sanitize_string(v, max_length=255)
            if not v:
                raise AppValidationError("SMTP server cannot be empty")
        return v
    
    @field_validator('smtp_port')
    @classmethod
    def validate_smtp_port(cls, v):
        """Validate SMTP port."""
        if v is not None:
            return PortValidator.validate_port(v, 'all')
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate SMTP username."""
        if v is not None:
            v = DataSanitizer.sanitize_string(v, max_length=255)
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate SMTP password."""
        if v is not None:
            # Don't sanitize password as it might contain special characters
            if len(v) > 255:
                raise AppValidationError("Password too long")
        return v
    
    @field_validator('from_address')
    @classmethod
    def validate_from_address(cls, v):
        """Validate from email address."""
        if v is not None:
            v = DataSanitizer.sanitize_string(v, max_length=255)
            # Basic email format validation
            if v and '@' not in v:
                raise AppValidationError("Invalid email address format")
        return v
    
    @field_validator('from_name')
    @classmethod
    def validate_from_name(cls, v):
        """Validate from name."""
        if v is not None:
            v = DataSanitizer.sanitize_string(v, max_length=100)
        return v


class EmailTestRequest(BaseModel):
    """Validation model for email test requests."""
    
    to_email: str = Field(..., description="Recipient email address")
    
    @field_validator('to_email')
    @classmethod
    def validate_to_email(cls, v):
        """Validate recipient email address."""
        v = DataSanitizer.sanitize_string(v, max_length=255)
        if not v or '@' not in v:
            raise AppValidationError("Invalid email address format")
        return v


class EmailNotificationRequest(BaseModel):
    """Validation model for sending email notifications."""
    
    to_email: str = Field(..., description="Recipient email address")
    notification_type: str = Field(..., description="Type of notification")
    data: Dict[str, Any] = Field(..., description="Notification data")
    
    @field_validator('to_email')
    @classmethod
    def validate_to_email(cls, v):
        """Validate recipient email address."""
        v = DataSanitizer.sanitize_string(v, max_length=255)
        if not v or '@' not in v:
            raise AppValidationError("Invalid email address format")
        return v
    
    @field_validator('notification_type')
    @classmethod
    def validate_notification_type(cls, v):
        """Validate notification type."""
        valid_types = [
            'miner_offline', 'temperature_alert', 'hashrate_drop', 'new_miner'
        ]
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if v not in valid_types:
            raise AppValidationError(f"Invalid notification type: {v}")
        return v
    
    @field_validator('data')
    @classmethod
    def validate_data(cls, v):
        """Validate notification data."""
        return DataSanitizer.sanitize_json_data(v)


class FeedbackSubmissionRequest(BaseModel):
    """Validation model for community feedback submissions."""
    
    category: str = Field(..., description="Feedback category")
    message: str = Field(..., description="Feedback message")
    user_id: str = Field(..., description="User identifier")
    installer_version: Optional[str] = Field(None, description="Installer version")
    system_info: Optional[Dict[str, Any]] = Field(None, description="System information")
    severity: Optional[str] = Field("medium", description="Feedback severity level")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        """Validate feedback category."""
        valid_categories = [
            'installation', 'verification', 'security', 'usability', 'bugs', 'suggestions'
        ]
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if v not in valid_categories:
            raise AppValidationError(f"Invalid feedback category: {v}")
        return v
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        """Validate feedback message."""
        v = DataSanitizer.sanitize_string(v, max_length=5000)
        if not v or len(v.strip()) < 10:
            raise AppValidationError("Feedback message must be at least 10 characters long")
        return v
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        """Validate user identifier."""
        v = DataSanitizer.sanitize_string(v, max_length=100)
        if not v:
            raise AppValidationError("User ID is required")
        return v
    
    @field_validator('installer_version')
    @classmethod
    def validate_installer_version(cls, v):
        """Validate installer version."""
        if v is not None:
            v = DataSanitizer.sanitize_string(v, max_length=50)
        return v
    
    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v):
        """Validate feedback severity."""
        valid_severities = ['low', 'medium', 'high', 'critical']
        v = DataSanitizer.sanitize_string(v, max_length=20)
        if v not in valid_severities:
            raise AppValidationError(f"Invalid severity level: {v}")
        return v
    
    @field_validator('system_info')
    @classmethod
    def validate_system_info(cls, v):
        """Validate system information."""
        if v is not None:
            return DataSanitizer.sanitize_json_data(v)
        return v


class FeedbackStatusUpdateRequest(BaseModel):
    """Validation model for updating feedback status."""
    
    status: str = Field(..., description="New feedback status")
    notes: Optional[str] = Field(None, description="Status update notes")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate feedback status."""
        valid_statuses = ['submitted', 'reviewed', 'in_progress', 'resolved', 'closed']
        v = DataSanitizer.sanitize_string(v, max_length=50)
        if v not in valid_statuses:
            raise AppValidationError(f"Invalid feedback status: {v}")
        return v
    
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v):
        """Validate status update notes."""
        if v is not None:
            v = DataSanitizer.sanitize_string(v, max_length=1000)
        return v


class FeedbackQueryRequest(BaseModel):
    """Validation model for feedback query requests."""
    
    category: Optional[str] = Field(None, description="Filter by category")
    status: Optional[str] = Field(None, description="Filter by status")
    severity: Optional[str] = Field(None, description="Filter by severity")
    limit: Optional[int] = Field(50, description="Maximum number of results")
    offset: Optional[int] = Field(0, description="Results offset for pagination")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        """Validate feedback category filter."""
        if v is not None:
            valid_categories = [
                'installation', 'verification', 'security', 'usability', 'bugs', 'suggestions'
            ]
            v = DataSanitizer.sanitize_string(v, max_length=50)
            if v not in valid_categories:
                raise AppValidationError(f"Invalid feedback category: {v}")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate feedback status filter."""
        if v is not None:
            valid_statuses = ['submitted', 'reviewed', 'in_progress', 'resolved', 'closed']
            v = DataSanitizer.sanitize_string(v, max_length=50)
            if v not in valid_statuses:
                raise AppValidationError(f"Invalid feedback status: {v}")
        return v
    
    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v):
        """Validate feedback severity filter."""
        if v is not None:
            valid_severities = ['low', 'medium', 'high', 'critical']
            v = DataSanitizer.sanitize_string(v, max_length=20)
            if v not in valid_severities:
                raise AppValidationError(f"Invalid severity level: {v}")
        return v
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v):
        """Validate query limit."""
        if v is not None:
            if v < 1 or v > 1000:
                raise AppValidationError("Limit must be between 1 and 1000")
        return v
    
    @field_validator('offset')
    @classmethod
    def validate_offset(cls, v):
        """Validate query offset."""
        if v is not None:
            if v < 0:
                raise AppValidationError("Offset must be non-negative")
        return v