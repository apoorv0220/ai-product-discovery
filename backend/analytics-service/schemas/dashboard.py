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


class DashboardData(BaseModel):
    """Dashboard data schema"""
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