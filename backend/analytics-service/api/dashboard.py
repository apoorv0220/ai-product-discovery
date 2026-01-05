"""
AI Product Discovery Suite - Analytics Service Dashboard API

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, Query, HTTPException, status
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

from shared.middleware.auth import get_merchant_id
from schemas.dashboard import (
    DashboardOverviewResponse,
    MetricResponse,
    TimeSeriesDataResponse,
    TimeSeriesDataPoint,
    FilterRequest,
)
from core.dashboard_queries import DashboardQueryService
from core.dashboard_cache import DashboardCache
from core.user_segmentation import UserSegmentationService

logger = structlog.get_logger()

router = APIRouter()

# Initialize services
query_service = DashboardQueryService()
cache_service = DashboardCache()
segmentation_service = UserSegmentationService()


@router.get("/overview", response_model=DashboardOverviewResponse,
           summary="Get Dashboard Overview",
           description="""
    Get comprehensive dashboard overview with key business metrics.

    **Returns:**
    - Total events, users, and sessions
    - Page views, product views, and searches
    - Purchase metrics and conversion rates
    - Revenue and performance indicators
    """)
async def get_dashboard_overview(
    request: Request,
    date_from: Optional[datetime] = Query(None, description="Start date for data range", example="2025-01-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="End date for data range", example="2025-01-15T23:59:59Z"),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """
    Get dashboard overview data with real database queries
    """
    try:
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Default to last 30 days if no date range specified
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)
        
        # Check cache first
        cache_key_data = await cache_service.get(
            'overview',
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to
        )
        
        if cache_key_data:
            logger.debug("Returning cached overview data", merchant_id=effective_merchant_id)
            return DashboardOverviewResponse(**cache_key_data)
        
        # Query database
        metrics_data = await query_service.get_overview_metrics(
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to
        )
        
        # Calculate period-over-period changes (compare with previous period)
        previous_date_from = date_from - (date_to - date_from)
        previous_date_to = date_from
        
        previous_metrics = await query_service.get_overview_metrics(
            effective_merchant_id,
            date_from=previous_date_from,
            date_to=previous_date_to
        )
        
        # Calculate changes
        additional_metrics = []
        
        # Note: avg_session_duration and pages_per_session would come from session analytics
        # For now, we'll add basic metrics
        
        # Build response
        response_data = {
            **metrics_data,
            'metrics': additional_metrics,
            'timestamp': datetime.utcnow()
        }
        
        # Cache the result (5 minute TTL)
        ttl = cache_service.get_ttl('overview')
        await cache_service.set(
            'overview',
            effective_merchant_id,
            response_data,
            ttl,
            date_from=date_from,
            date_to=date_to
        )
        
        return DashboardOverviewResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting dashboard overview", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving dashboard overview"
        )


@router.get("/metrics", response_model=TimeSeriesDataResponse)
async def get_dashboard_metrics(
    request: Request,
    metric_name: str = Query(..., description="Name of the metric to retrieve"),
    period: str = Query("hourly", description="Time period (hourly, daily, weekly, monthly)"),
    date_from: Optional[datetime] = Query(None, description="Start date for data range"),
    date_to: Optional[datetime] = Query(None, description="End date for data range"),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """
    Get time-series metrics for dashboard with real database queries
    """
    try:
        # Validate period
        valid_periods = ['hourly', 'daily', 'weekly', 'monthly']
        if period not in valid_periods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        # Validate metric_name
        valid_metrics = ['page_views', 'product_views', 'searches', 'purchases', 'revenue', 'unique_users', 'unique_sessions']
        if metric_name not in valid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metric_name. Must be one of: {', '.join(valid_metrics)}"
            )
        
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Default date range based on period
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            if period == 'hourly':
                date_from = date_to - timedelta(hours=24)
            elif period == 'daily':
                date_from = date_to - timedelta(days=30)
            elif period == 'weekly':
                date_from = date_to - timedelta(days=90)
            else:  # monthly
                date_from = date_to - timedelta(days=365)
        
        # Check cache first
        cache_key_data = await cache_service.get(
            'metrics',
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to,
            metric_name=metric_name,
            period=period
        )
        
        if cache_key_data:
            logger.debug("Returning cached metrics data", merchant_id=effective_merchant_id, metric=metric_name)
            return TimeSeriesDataResponse(**cache_key_data)
        
        # Query database
        data_points_raw = await query_service.get_time_series_data(
            effective_merchant_id,
            metric_name=metric_name,
            period=period,
            date_from=date_from,
            date_to=date_to
        )
        
        # Convert to TimeSeriesDataPoint objects
        data_points = [
            TimeSeriesDataPoint(
                timestamp=dp['timestamp'],
                value=dp['value']
            )
            for dp in data_points_raw
        ]
        
        # Calculate total
        total = sum(dp.value for dp in data_points)
        
        response_data = {
            'metric_name': metric_name,
            'data_points': data_points,
            'period': period,
            'total': total
        }
        
        # Cache the result
        ttl = cache_service.get_ttl('metrics', period=period)
        await cache_service.set(
            'metrics',
            effective_merchant_id,
            {
                'metric_name': metric_name,
                'data_points': [{'timestamp': dp.timestamp, 'value': dp.value} for dp in data_points],
                'period': period,
                'total': total
            },
            ttl,
            date_from=date_from,
            date_to=date_to,
            metric_name=metric_name,
            period=period
        )
        
        return TimeSeriesDataResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting dashboard metrics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving dashboard metrics"
        )


@router.get("/sessions",
           summary="Get Session Analytics",
           description="""
    Get detailed session analytics including duration, bounce rates, and user journey data.

    **Returns:**
    - Session counts and duration statistics
    - Device and platform breakdown
    - Bounce rate and engagement metrics
    - Geographic distribution (when available)
    """)
async def get_dashboard_sessions(
    request: Request,
    date_from: Optional[datetime] = Query(None, description="Start date for data range", example="2025-01-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="End date for data range", example="2025-01-15T23:59:59Z"),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """
    Get session analytics data with real database queries
    """
    try:
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Default to last 30 days if no date range specified
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)
        
        # Check cache first
        cache_key_data = await cache_service.get(
            'sessions',
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to
        )
        
        if cache_key_data:
            logger.debug("Returning cached session analytics", merchant_id=effective_merchant_id)
            return cache_key_data
        
        # Query database
        session_data = await query_service.get_session_analytics(
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to
        )
        
        # Cache the result (5 minute TTL)
        ttl = cache_service.get_ttl('sessions')
        await cache_service.set(
            'sessions',
            effective_merchant_id,
            session_data,
            ttl,
            date_from=date_from,
            date_to=date_to
        )
        
        return session_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting session analytics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving session analytics"
        )


@router.get("/users",
           summary="Get User Behavior Analytics",
           description="""
    Get user behavior analytics including segmentation, engagement patterns, and behavioral trends.

    **Returns:**
    - User segmentation data
    - Behavioral patterns and preferences
    - Engagement metrics and trends
    - User lifetime value indicators
    """)
async def get_dashboard_users(
    request: Request,
    date_from: Optional[datetime] = Query(None, description="Start date for data range", example="2025-01-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="End date for data range", example="2025-01-15T23:59:59Z"),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """
    Get user behavior metrics with real database queries
    """
    try:
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Default to last 30 days if no date range specified
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)
        
        # Check cache first
        cache_key_data = await cache_service.get(
            'users',
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to
        )
        
        if cache_key_data:
            logger.debug("Returning cached user behavior data", merchant_id=effective_merchant_id)
            return cache_key_data
        
        # Query database
        user_data = await query_service.get_user_behavior_metrics(
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to
        )
        
        # Cache the result (5 minute TTL)
        ttl = cache_service.get_ttl('users')
        await cache_service.set(
            'users',
            effective_merchant_id,
            user_data,
            ttl,
            date_from=date_from,
            date_to=date_to
        )
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting user metrics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user behavior metrics"
        )


@router.get("/segments",
           summary="Get User Segments",
           description="""
    Get list of user segments with counts and metrics.
    
    **Segments:**
    - high_value: Users with revenue above threshold
    - frequent_buyers: Users with purchase count above threshold
    - engaged: Users with event count above threshold
    - new_users: Users with first activity in date range
    - returning: Users with multiple sessions
    - search_active: Users with search count above threshold
    """)
async def get_user_segments(
    request: Request,
    date_from: Optional[datetime] = Query(None, description="Start date for data range", example="2025-01-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="End date for data range", example="2025-01-15T23:59:59Z"),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """Get user segments with counts and metrics"""
    try:
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Default to last 30 days if no date range specified
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)
        
        # Get segments
        segments_data = await segmentation_service.get_segments(
            effective_merchant_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return segments_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting user segments", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user segments"
        )


@router.get("/segments/{segment_name}",
           summary="Get Segment Users",
           description="""
    Get users in a specific segment with pagination.
    
    **Supported Segments:**
    - high_value, frequent_buyers, engaged, new_users, returning, search_active
    """)
async def get_segment_users(
    request: Request,
    segment_name: str,
    date_from: Optional[datetime] = Query(None, description="Start date for data range", example="2025-01-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="End date for data range", example="2025-01-15T23:59:59Z"),
    limit: int = Query(100, description="Limit for pagination", ge=1, le=1000),
    offset: int = Query(0, description="Offset for pagination", ge=0),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """Get users in a specific segment with pagination"""
    try:
        # Validate segment name
        valid_segments = ['high_value', 'frequent_buyers', 'engaged', 'new_users', 'returning', 'search_active']
        if segment_name not in valid_segments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid segment_name. Must be one of: {', '.join(valid_segments)}"
            )
        
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Default to last 30 days if no date range specified
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)
        
        # Get segment users
        segment_users = await segmentation_service.get_segment_users(
            effective_merchant_id,
            segment_name=segment_name,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset
        )
        
        return segment_users
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting segment users", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving segment users"
        )


@router.get("/segments/{segment_name}/performance",
           summary="Get Segment Performance",
           description="""
    Get performance analysis for a specific segment.
    
    **Metrics:**
    - Revenue per user, conversion rate, engagement metrics
    - Retention rates and comparison insights
    """)
async def get_segment_performance(
    request: Request,
    segment_name: str,
    date_from: Optional[datetime] = Query(None, description="Start date for data range", example="2025-01-01T00:00:00Z"),
    date_to: Optional[datetime] = Query(None, description="End date for data range", example="2025-01-15T23:59:59Z"),
    merchant_id: Optional[int] = Query(None, description="Merchant ID (admin only, defaults to authenticated merchant)")
):
    """Get performance analysis for a specific segment"""
    try:
        # Validate segment name
        valid_segments = ['high_value', 'frequent_buyers', 'engaged', 'new_users', 'returning', 'search_active']
        if segment_name not in valid_segments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid segment_name. Must be one of: {', '.join(valid_segments)}"
            )
        
        # Get merchant_id: use query param if provided (admin), otherwise use request.state
        effective_merchant_id = merchant_id if merchant_id else get_merchant_id(request)
        
        # Default to last 30 days if no date range specified
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)
        
        # Get segment performance
        performance = await segmentation_service.analyze_segment_performance(
            effective_merchant_id,
            segment_name=segment_name,
            date_from=date_from,
            date_to=date_to
        )
        
        return performance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting segment performance", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving segment performance"
        )