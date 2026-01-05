"""
AI Product Discovery Suite - Analytics Dashboard Schemas

@category    Backend
@package     Analytics Service
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class FilterRequest(BaseModel):
    """Filter request for dashboard queries"""
    merchant_id: Optional[int] = Field(None, description="Merchant ID filter")
    date_from: Optional[datetime] = Field(None, description="Start date for data range")
    date_to: Optional[datetime] = Field(None, description="End date for data range")
    event_types: Optional[List[str]] = Field(default_factory=list, description="Filter by event types")

    class Config:
        json_schema_extra = {
            "example": {
                "merchant_id": 1,
                "date_from": "2025-01-01T00:00:00Z",
                "date_to": "2025-01-15T23:59:59Z",
                "event_types": ["product_view", "purchase", "search"]
            }
        }


class MetricResponse(BaseModel):
    """Single metric response"""
    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit (e.g., 'percent', 'seconds')")
    change_percent: Optional[float] = Field(None, description="Percentage change from previous period")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "conversion_rate",
                "value": 3.45,
                "unit": "percent",
                "change_percent": 12.5
            }
        }


class TimeSeriesDataPoint(BaseModel):
    """Single time series data point"""
    timestamp: datetime = Field(..., description="Timestamp for this data point")
    value: float = Field(..., description="Value at this timestamp")
    label: Optional[str] = Field(None, description="Optional label for this point")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-15T10:00:00Z",
                "value": 145.67,
                "label": "Daily Revenue"
            }
        }


class TimeSeriesDataResponse(BaseModel):
    """Time series data response"""
    metric_name: str = Field(..., description="Name of the metric")
    data_points: List[TimeSeriesDataPoint] = Field(..., description="Time series data points")
    period: str = Field(..., description="Time period (e.g., 'hourly', 'daily', 'weekly')")
    total: Optional[float] = Field(None, description="Total value for the period")

    class Config:
        json_schema_extra = {
            "example": {
                "metric_name": "daily_revenue",
                "data_points": [
                    {
                        "timestamp": "2025-01-14T00:00:00Z",
                        "value": 1250.50,
                        "label": "Revenue"
                    },
                    {
                        "timestamp": "2025-01-15T00:00:00Z",
                        "value": 1450.75,
                        "label": "Revenue"
                    }
                ],
                "period": "daily",
                "total": 2701.25
            }
        }


class DashboardOverviewResponse(BaseModel):
    """Dashboard overview response"""
    total_events: int = Field(..., description="Total number of events")
    unique_users: int = Field(..., description="Number of unique users")
    unique_sessions: int = Field(..., description="Number of unique sessions")
    page_views: int = Field(..., description="Total page views")
    product_views: int = Field(..., description="Total product views")
    searches: int = Field(..., description="Total searches")
    purchases: int = Field(..., description="Total purchases")
    revenue: float = Field(..., description="Total revenue")
    conversion_rate: float = Field(..., description="Conversion rate (0-1)")
    metrics: List[MetricResponse] = Field(default_factory=list, description="Additional metrics")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 15432,
                "unique_users": 1247,
                "unique_sessions": 3456,
                "page_views": 8920,
                "product_views": 5678,
                "searches": 2341,
                "purchases": 156,
                "revenue": 45678.90,
                "conversion_rate": 0.0345,
                "metrics": [
                    {
                        "name": "avg_session_duration",
                        "value": 180.5,
                        "unit": "seconds",
                        "change_percent": 5.2
                    },
                    {
                        "name": "bounce_rate",
                        "value": 0.32,
                        "unit": "percent",
                        "change_percent": -2.1
                    }
                ],
                "timestamp": "2025-01-15T10:30:45.123456"
            }
        }


class DashboardData(BaseModel):
    """Dashboard data schema (legacy - for backward compatibility)"""
    total_searches: int = Field(..., description="Total number of searches")
    total_clicks: int = Field(..., description="Total number of clicks")
    conversion_rate: float = Field(..., description="Conversion rate percentage")
    top_queries: List[Dict[str, Any]] = Field(..., description="Top search queries")
    zero_results_queries: List[Dict[str, Any]] = Field(..., description="Queries with zero results")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")


class DashboardRequest(BaseModel):
    """Request schema for dashboard data"""
    store_id: Optional[str] = Field(None, description="Store identifier")
    date_from: Optional[datetime] = Field(None, description="Start date for data")
    date_to: Optional[datetime] = Field(None, description="End date for data")
    metrics: Optional[List[str]] = Field(default_factory=list, description="Specific metrics to fetch")
    
    class Config:
        json_schema_extra = {
            "example": {
                "store_id": "store_1",
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-31T23:59:59Z",
                "metrics": ["searches", "clicks", "conversions"]
            }
        }


class DashboardResponse(BaseModel):
    """Response schema for dashboard data"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[DashboardData] = Field(None, description="Dashboard data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total_searches": 1250,
                    "total_clicks": 890,
                    "conversion_rate": 12.5,
                    "top_queries": [
                        {"query": "running shoes", "count": 45},
                        {"query": "laptop", "count": 32}
                    ],
                    "zero_results_queries": [
                        {"query": "xyz product", "count": 5}
                    ],
                    "performance_metrics": {
                        "avg_response_time": 150,
                        "search_success_rate": 95.2
                    }
                }
            }
        }