"""
AI Product Discovery Suite - Analytics Reports Schemas

@category    Backend
@package     Analytics Service
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ReportType(str, Enum):
    """Report type enumeration"""
    SEARCH_PERFORMANCE = "search_performance"
    PRODUCT_PERFORMANCE = "product_performance"
    USER_BEHAVIOR = "user_behavior"
    CONVERSION_FUNNEL = "conversion_funnel"
    AB_TEST_RESULTS = "ab_test_results"


class ReportData(BaseModel):
    """Report data schema"""
    report_type: ReportType = Field(..., description="Type of report")
    data: Dict[str, Any] = Field(..., description="Report data")
    summary: Dict[str, Any] = Field(..., description="Report summary")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")


class ReportRequest(BaseModel):
    """Request schema for report generation"""
    report_type: ReportType = Field(..., description="Type of report to generate")
    store_id: Optional[str] = Field(None, description="Store identifier")
    date_from: Optional[datetime] = Field(None, description="Start date for report")
    date_to: Optional[datetime] = Field(None, description="End date for report")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional filters")
    format: Optional[str] = Field("json", description="Report format (json, csv, pdf)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_type": "search_performance",
                "store_id": "store_1",
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-31T23:59:59Z",
                "filters": {
                    "category": "electronics",
                    "min_queries": 10
                },
                "format": "json"
            }
        }


class ReportResponse(BaseModel):
    """Response schema for report generation"""
    success: bool = Field(..., description="Whether the report was generated successfully")
    report_id: Optional[str] = Field(None, description="Report identifier")
    download_url: Optional[str] = Field(None, description="URL to download the report")
    data: Optional[ReportData] = Field(None, description="Report data (for JSON format)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "report_id": "report_12345",
                "download_url": "/api/v1/reports/download/report_12345",
                "data": {
                    "report_type": "search_performance",
                    "data": {
                        "total_searches": 1250,
                        "unique_queries": 890,
                        "avg_results_per_query": 15.3
                    },
                    "summary": {
                        "top_performing_query": "running shoes",
                        "improvement_suggestions": ["Add more product variants"]
                    }
                }
            }
        }