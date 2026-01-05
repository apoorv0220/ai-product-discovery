"""
AI Product Discovery Suite - Analytics Service Reports API

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, Query, HTTPException, status, Body
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import structlog

from shared.middleware.auth import get_merchant_id
from core.report_generator import ReportGenerator
from core.export_service import ExportService

logger = structlog.get_logger()

router = APIRouter()

# Initialize services
report_generator = ReportGenerator()
export_service = ExportService()


class ExportRequest(BaseModel):
    """Request schema for export"""
    export_type: str = Field(..., description="Type of export: events, time_series, or report")
    format: str = Field(..., description="Export format: csv or json")
    date_from: Optional[datetime] = Field(None, description="Start date for data range")
    date_to: Optional[datetime] = Field(None, description="End date for data range")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional filters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "export_type": "events",
                "format": "csv",
                "date_from": "2025-01-01T00:00:00Z",
                "date_to": "2025-01-15T23:59:59Z",
                "filters": {
                    "event_types": ["product_view", "purchase"]
                }
            }
        }


@router.get("/performance",
           summary="Get Performance Report",
           description="""
    Generate comprehensive performance report with business metrics.

    **Includes:**
    - Traffic and engagement metrics
    - Conversion funnel analysis
    - Revenue and sales performance
    - User behavior insights
    - Time-based comparisons
    """)
async def get_performance_report(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", example="2025-01-01"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", example="2025-01-15"),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """Get performance report with real data"""
    try:
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Parse dates
        date_from = None
        date_to = None
        
        if start_date:
            try:
                date_from = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                # Try YYYY-MM-DD format
                date_from = datetime.strptime(start_date, '%Y-%m-%d')
        
        if end_date:
            try:
                date_to = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                # Try YYYY-MM-DD format
                date_to = datetime.strptime(end_date, '%Y-%m-%d')
                # Set to end of day
                date_to = date_to.replace(hour=23, minute=59, second=59)
        
        # Generate report
        report = await report_generator.generate_performance_report(
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating performance report", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating performance report"
        )


@router.get("/user-behavior",
           summary="Get User Behavior Report",
           description="""
    Generate detailed user behavior analysis report.

    **Includes:**
    - User segmentation analysis
    - Behavioral patterns and trends
    - Engagement and retention metrics
    - Personalized insights
    """)
async def get_user_behavior_report(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", example="2025-01-01"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", example="2025-01-15"),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """Get user behavior report with real data"""
    try:
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Parse dates
        date_from = None
        date_to = None
        
        if start_date:
            try:
                date_from = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                # Try YYYY-MM-DD format
                date_from = datetime.strptime(start_date, '%Y-%m-%d')
        
        if end_date:
            try:
                date_to = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                # Try YYYY-MM-DD format
                date_to = datetime.strptime(end_date, '%Y-%m-%d')
                # Set to end of day
                date_to = date_to.replace(hour=23, minute=59, second=59)
        
        # Generate report
        report = await report_generator.generate_user_behavior_report(
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating user behavior report", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating user behavior report"
        )


@router.post("/export",
           summary="Export Analytics Data",
           description="""
    Export analytics data in CSV or JSON format.
    
    **Supported Export Types:**
    - `events`: Export raw analytics events
    - `time_series`: Export time-series metrics data
    - `report`: Export performance or user behavior reports
    
    **Supported Formats:**
    - `csv`: Comma-separated values format
    - `json`: JSON format (JSONL for streaming events)
    """)
async def export_data(
    request: Request,
    export_request: ExportRequest = Body(...),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """Export analytics data in CSV or JSON format"""
    try:
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Validate export_type
        valid_export_types = ['events', 'time_series', 'report']
        if export_request.export_type not in valid_export_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid export_type. Must be one of: {', '.join(valid_export_types)}"
            )
        
        # Validate format
        valid_formats = ['csv', 'json']
        if export_request.format not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )
        
        # Extract filters
        event_types = export_request.filters.get('event_types') if export_request.filters else None
        limit = export_request.filters.get('limit') if export_request.filters else None
        metric_name = export_request.filters.get('metric_name') if export_request.filters else None
        period = export_request.filters.get('period', 'daily') if export_request.filters else 'daily'
        report_type = export_request.filters.get('report_type', 'performance') if export_request.filters else 'performance'
        
        # Generate export based on type and format
        if export_request.export_type == 'events':
            if export_request.format == 'csv':
                generator = export_service.export_events_csv(
                    effective_merchant_id,
                    date_from=export_request.date_from,
                    date_to=export_request.date_to,
                    event_types=event_types,
                    limit=limit
                )
                return StreamingResponse(
                    generator,
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename=events_{effective_merchant_id}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
                    }
                )
            else:  # json
                streaming = limit is None or limit > 1000  # Use streaming for large datasets
                generator = export_service.export_events_json(
                    effective_merchant_id,
                    date_from=export_request.date_from,
                    date_to=export_request.date_to,
                    event_types=event_types,
                    limit=limit,
                    streaming=streaming
                )
                if streaming:
                    return StreamingResponse(
                        generator,
                        media_type="application/x-ndjson",
                        headers={
                            "Content-Disposition": f"attachment; filename=events_{effective_merchant_id}_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
                        }
                    )
                else:
                    # Collect all chunks for non-streaming JSON
                    chunks = []
                    async for chunk in generator:
                        chunks.append(chunk)
                    json_data = ''.join(chunks)
                    return StreamingResponse(
                        iter([json_data]),
                        media_type="application/json",
                        headers={
                            "Content-Disposition": f"attachment; filename=events_{effective_merchant_id}_{datetime.utcnow().strftime('%Y%m%d')}.json"
                        }
                    )
        
        elif export_request.export_type == 'time_series':
            if not metric_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="metric_name is required in filters for time_series export"
                )
            
            if export_request.format == 'csv':
                generator = export_service.export_time_series_csv(
                    effective_merchant_id,
                    metric_name=metric_name,
                    period=period,
                    date_from=export_request.date_from,
                    date_to=export_request.date_to
                )
                return StreamingResponse(
                    generator,
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename=timeseries_{metric_name}_{period}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
                    }
                )
            else:  # json
                json_data = await export_service.export_time_series_json(
                    effective_merchant_id,
                    metric_name=metric_name,
                    period=period,
                    date_from=export_request.date_from,
                    date_to=export_request.date_to
                )
                return StreamingResponse(
                    iter([json_data]),
                    media_type="application/json",
                    headers={
                        "Content-Disposition": f"attachment; filename=timeseries_{metric_name}_{period}_{datetime.utcnow().strftime('%Y%m%d')}.json"
                    }
                )
        
        else:  # report
            if export_request.format == 'csv':
                generator = export_service.export_report_csv(
                    effective_merchant_id,
                    report_type=report_type,
                    date_from=export_request.date_from,
                    date_to=export_request.date_to
                )
                return StreamingResponse(
                    generator,
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename=report_{report_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
                    }
                )
            else:  # json
                json_data = await export_service.export_report_json(
                    effective_merchant_id,
                    report_type=report_type,
                    date_from=export_request.date_from,
                    date_to=export_request.date_to
                )
                return StreamingResponse(
                    iter([json_data]),
                    media_type="application/json",
                    headers={
                        "Content-Disposition": f"attachment; filename=report_{report_type}_{datetime.utcnow().strftime('%Y%m%d')}.json"
                    }
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exporting data", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error exporting data"
        )