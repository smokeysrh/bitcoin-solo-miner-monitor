"""
Tests for comprehensive endpoint validation schemas.

This module tests all the validation schemas for API endpoints including
request validation, response models, and data sanitization.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError as PydanticValidationError

from src.backend.schemas.endpoint_schemas import (
    # Base models
    BaseResponse,
    ErrorResponse,
    PaginationRequest,
    PaginationResponse,
    
    # Enums
    ResponseStatus,
    SortOrder,
    MinerStatus,
    MetricType,
    
    # Miner schemas
    MinerListRequest,
    MinerResponse,
    MinerListResponse,
    MinerDetailResponse,
    
    # Metrics schemas
    MetricsRequest,
    MetricDataPoint,
    MetricSeries,
    MetricsResponse,
    
    # Settings schemas
    SettingsRequest,
    SettingsResponse,
    
    # WebSocket schemas
    WebSocketSubscriptionRequest,
    WebSocketResponse,
    
    # Bulk operations schemas
    BulkMinerActionRequest,
    BulkActionResult,
    BulkMinerActionResponse,
    
    # Export schemas
    ExportRequest,
    ExportResponse,
    
    # Health check schemas
    HealthCheckResponse,
    
    # Validation schemas
    ValidationStatsResponse
)
from src.backend.exceptions import ValidationError as AppValidationError


class TestBaseSchemas:
    """Test base response and pagination schemas."""
    
    def test_base_response_creation(self):
        """Test base response model creation."""
        response = BaseResponse(
            status=ResponseStatus.SUCCESS,
            message="Operation completed"
        )
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.message == "Operation completed"
        assert isinstance(response.timestamp, datetime)
    
    def test_error_response_creation(self):
        """Test error response model creation."""
        response = ErrorResponse(
            message="An error occurred",
            error_code="VALIDATION_ERROR",
            details={"field": "invalid_value"}
        )
        
        assert response.status == ResponseStatus.ERROR
        assert response.message == "An error occurred"
        assert response.error_code == "VALIDATION_ERROR"
        assert response.details == {"field": "invalid_value"}
    
    def test_pagination_request_validation(self):
        """Test pagination request validation."""
        # Valid pagination request
        request = PaginationRequest(
            limit=50,
            offset=10,
            sort_by="name",
            sort_order=SortOrder.DESC
        )
        
        assert request.limit == 50
        assert request.offset == 10
        assert request.sort_by == "name"
        assert request.sort_order == SortOrder.DESC
        
        # Invalid limit (too high)
        with pytest.raises(PydanticValidationError):
            PaginationRequest(limit=20000)
        
        # Invalid offset (negative)
        with pytest.raises(PydanticValidationError):
            PaginationRequest(offset=-1)
    
    def test_pagination_response_creation(self):
        """Test pagination response creation."""
        response = PaginationResponse(
            total=100,
            limit=20,
            offset=40,
            has_more=True
        )
        
        assert response.total == 100
        assert response.limit == 20
        assert response.offset == 40
        assert response.has_more is True


class TestMinerSchemas:
    """Test miner-related schemas."""
    
    def test_miner_list_request_validation(self):
        """Test miner list request validation."""
        # Valid request
        request = MinerListRequest(
            limit=10,
            status_filter=MinerStatus.ONLINE,
            type_filter="bitaxe",
            search="test miner"
        )
        
        assert request.limit == 10
        assert request.status_filter == MinerStatus.ONLINE
        assert request.type_filter == "bitaxe"
        assert request.search == "test miner"
        
        # Invalid miner type
        with pytest.raises((PydanticValidationError, AppValidationError)):
            MinerListRequest(type_filter="unknown_miner")
    
    def test_miner_response_creation(self):
        """Test miner response model creation."""
        now = datetime.now()
        
        response = MinerResponse(
            id="miner_001",
            name="Test Miner",
            type="bitaxe",
            ip_address="10.0.0.100",
            port=80,
            status=MinerStatus.ONLINE,
            last_seen=now,
            created_at=now,
            updated_at=now
        )
        
        assert response.id == "miner_001"
        assert response.name == "Test Miner"
        assert response.type == "bitaxe"
        assert response.ip_address == "10.0.0.100"
        assert response.port == 80
        assert response.status == MinerStatus.ONLINE
    
    def test_miner_list_response_creation(self):
        """Test miner list response creation."""
        now = datetime.now()
        
        miners = [
            MinerResponse(
                id="miner_001",
                name="Test Miner 1",
                type="bitaxe",
                ip_address="10.0.0.100",
                port=80,
                status=MinerStatus.ONLINE,
                created_at=now,
                updated_at=now
            )
        ]
        
        pagination = PaginationResponse(
            total=1,
            limit=10,
            offset=0,
            has_more=False
        )
        
        response = MinerListResponse(
            status=ResponseStatus.SUCCESS,
            data=miners,
            pagination=pagination
        )
        
        assert response.status == ResponseStatus.SUCCESS
        assert len(response.data) == 1
        assert response.pagination.total == 1


class TestMetricsSchemas:
    """Test metrics-related schemas."""
    
    def test_metrics_request_validation(self):
        """Test metrics request validation."""
        now = datetime.now()
        start = now - timedelta(hours=24)
        
        # Valid request
        request = MetricsRequest(
            miner_id="miner_001",
            start=start,
            end=now,
            interval="1h",
            metric_types=[MetricType.HASHRATE, MetricType.TEMPERATURE],
            aggregation="avg"
        )
        
        assert request.miner_id == "miner_001"
        assert request.start == start
        assert request.end == now
        assert request.interval == "1h"
        assert MetricType.HASHRATE in request.metric_types
        assert request.aggregation == "avg"
        
        # Invalid interval
        with pytest.raises((PydanticValidationError, AppValidationError)):
            MetricsRequest(
                miner_id="miner_001",
                interval="invalid_interval"
            )
        
        # Invalid aggregation
        with pytest.raises((PydanticValidationError, AppValidationError)):
            MetricsRequest(
                miner_id="miner_001",
                aggregation="invalid_aggregation"
            )
        
        # Invalid time range (start after end)
        with pytest.raises((PydanticValidationError, AppValidationError)):
            MetricsRequest(
                miner_id="miner_001",
                start=now,
                end=start  # End before start
            )
    
    def test_metric_data_point_creation(self):
        """Test metric data point creation."""
        now = datetime.now()
        
        data_point = MetricDataPoint(
            timestamp=now,
            value=500.5,
            unit="GH/s"
        )
        
        assert data_point.timestamp == now
        assert data_point.value == 500.5
        assert data_point.unit == "GH/s"
    
    def test_metric_series_creation(self):
        """Test metric series creation."""
        now = datetime.now()
        
        data_points = [
            MetricDataPoint(timestamp=now, value=500.0, unit="GH/s"),
            MetricDataPoint(timestamp=now + timedelta(minutes=1), value=505.0, unit="GH/s")
        ]
        
        series = MetricSeries(
            metric_type=MetricType.HASHRATE,
            data_points=data_points,
            aggregation="avg",
            interval="1m"
        )
        
        assert series.metric_type == MetricType.HASHRATE
        assert len(series.data_points) == 2
        assert series.aggregation == "avg"
        assert series.interval == "1m"


class TestSettingsSchemas:
    """Test settings-related schemas."""
    
    def test_settings_request_validation(self):
        """Test settings request validation."""
        # Valid request
        request = SettingsRequest(
            polling_interval=30,
            theme="dark",
            chart_retention_days=30,
            refresh_interval=10,
            notifications_enabled=True,
            alert_thresholds={
                "temperature": 80.0,
                "hashrate": 400.0
            }
        )
        
        assert request.polling_interval == 30
        assert request.theme == "dark"
        assert request.chart_retention_days == 30
        assert request.refresh_interval == 10
        assert request.notifications_enabled is True
        assert request.alert_thresholds["temperature"] == 80.0
        
        # Invalid theme
        with pytest.raises((PydanticValidationError, AppValidationError)):
            SettingsRequest(theme="invalid_theme")
        
        # Invalid polling interval (too low)
        with pytest.raises(PydanticValidationError):
            SettingsRequest(polling_interval=1)
        
        # Invalid alert threshold metric
        with pytest.raises((PydanticValidationError, AppValidationError)):
            SettingsRequest(alert_thresholds={"invalid_metric": 100.0})


class TestWebSocketSchemas:
    """Test WebSocket-related schemas."""
    
    def test_websocket_subscription_request_validation(self):
        """Test WebSocket subscription request validation."""
        # Valid request
        request = WebSocketSubscriptionRequest(
            type="subscribe",
            topic="miners",
            filters={"status": "online"}
        )
        
        assert request.type == "subscribe"
        assert request.topic == "miners"
        assert request.filters == {"status": "online"}
        
        # Invalid message type
        with pytest.raises((PydanticValidationError, AppValidationError)):
            WebSocketSubscriptionRequest(
                type="invalid_type",
                topic="miners"
            )
        
        # Invalid topic
        with pytest.raises((PydanticValidationError, AppValidationError)):
            WebSocketSubscriptionRequest(
                type="subscribe",
                topic="invalid_topic"
            )
    
    def test_websocket_response_creation(self):
        """Test WebSocket response creation."""
        response = WebSocketResponse(
            type="data",
            topic="miners",
            data={"miner_id": "miner_001", "status": "online"}
        )
        
        assert response.type == "data"
        assert response.topic == "miners"
        assert response.data["miner_id"] == "miner_001"
        assert isinstance(response.timestamp, datetime)


class TestBulkOperationSchemas:
    """Test bulk operation schemas."""
    
    def test_bulk_miner_action_request_validation(self):
        """Test bulk miner action request validation."""
        # Valid request
        request = BulkMinerActionRequest(
            miner_ids=["miner_001", "miner_002"],
            action="restart",
            parameters={"force": True}
        )
        
        assert request.miner_ids == ["miner_001", "miner_002"]
        assert request.action == "restart"
        assert request.parameters == {"force": True}
        
        # Invalid action
        with pytest.raises((PydanticValidationError, AppValidationError)):
            BulkMinerActionRequest(
                miner_ids=["miner_001"],
                action="invalid_action"
            )
        
        # Too many miner IDs
        with pytest.raises(PydanticValidationError):
            BulkMinerActionRequest(
                miner_ids=[f"miner_{i:03d}" for i in range(101)],  # 101 miners
                action="restart"
            )
        
        # Empty miner IDs list
        with pytest.raises(PydanticValidationError):
            BulkMinerActionRequest(
                miner_ids=[],
                action="restart"
            )
    
    def test_bulk_action_result_creation(self):
        """Test bulk action result creation."""
        result = BulkActionResult(
            miner_id="miner_001",
            success=True,
            message="Restart successful"
        )
        
        assert result.miner_id == "miner_001"
        assert result.success is True
        assert result.message == "Restart successful"
        
        # Failed result
        failed_result = BulkActionResult(
            miner_id="miner_002",
            success=False,
            error="Connection failed"
        )
        
        assert failed_result.success is False
        assert failed_result.error == "Connection failed"


class TestExportSchemas:
    """Test export-related schemas."""
    
    def test_export_request_validation(self):
        """Test export request validation."""
        now = datetime.now()
        start = now - timedelta(days=7)
        
        # Valid request
        request = ExportRequest(
            export_type="metrics",
            format="json",
            date_range={"start": start, "end": now},
            filters={"miner_type": "bitaxe"}
        )
        
        assert request.export_type == "metrics"
        assert request.format == "json"
        assert request.date_range["start"] == start
        assert request.filters == {"miner_type": "bitaxe"}
        
        # Invalid export type
        with pytest.raises((PydanticValidationError, AppValidationError)):
            ExportRequest(export_type="invalid_type")
        
        # Invalid format
        with pytest.raises((PydanticValidationError, AppValidationError)):
            ExportRequest(
                export_type="metrics",
                format="invalid_format"
            )
    
    def test_export_response_creation(self):
        """Test export response creation."""
        response = ExportResponse(
            status=ResponseStatus.SUCCESS,
            data={"export_size": 1024, "records": 100},
            export_id="export_12345",
            download_url="/api/exports/export_12345/download"
        )
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.export_id == "export_12345"
        assert response.download_url == "/api/exports/export_12345/download"


class TestHealthCheckSchemas:
    """Test health check schemas."""
    
    def test_health_check_response_creation(self):
        """Test health check response creation."""
        response = HealthCheckResponse(
            status=ResponseStatus.SUCCESS,
            data={"uptime": 3600, "version": "0.1.0"},
            overall_status="healthy",
            checks={
                "database": {"status": "healthy", "response_time": 5},
                "miners": {"status": "healthy", "count": 3}
            }
        )
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.overall_status == "healthy"
        assert "database" in response.checks
        assert response.checks["database"]["status"] == "healthy"


class TestValidationStatsSchemas:
    """Test validation statistics schemas."""
    
    def test_validation_stats_response_creation(self):
        """Test validation stats response creation."""
        response = ValidationStatsResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "requests_processed": 1000,
                "requests_blocked": 10,
                "validation_errors": 5
            },
            middleware_stats={
                "InputValidationMiddleware": {
                    "requests_processed": 800,
                    "requests_blocked": 8
                },
                "MinerConfigurationValidationMiddleware": {
                    "requests_processed": 200,
                    "requests_blocked": 2
                }
            }
        )
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.data["requests_processed"] == 1000
        assert "InputValidationMiddleware" in response.middleware_stats


class TestEnumValidation:
    """Test enum validation in schemas."""
    
    def test_response_status_enum(self):
        """Test ResponseStatus enum validation."""
        # Valid status
        response = BaseResponse(status=ResponseStatus.SUCCESS)
        assert response.status == ResponseStatus.SUCCESS
        
        # Invalid status should raise validation error
        with pytest.raises(PydanticValidationError):
            BaseResponse(status="invalid_status")
    
    def test_miner_status_enum(self):
        """Test MinerStatus enum validation."""
        now = datetime.now()
        
        # Valid status
        miner = MinerResponse(
            id="miner_001",
            name="Test Miner",
            type="bitaxe",
            ip_address="10.0.0.100",
            port=80,
            status=MinerStatus.ONLINE,
            created_at=now,
            updated_at=now
        )
        assert miner.status == MinerStatus.ONLINE
    
    def test_metric_type_enum(self):
        """Test MetricType enum validation."""
        # Valid metric type
        request = MetricsRequest(
            miner_id="miner_001",
            metric_types=[MetricType.HASHRATE, MetricType.TEMPERATURE]
        )
        assert MetricType.HASHRATE in request.metric_types


if __name__ == "__main__":
    pytest.main([__file__])