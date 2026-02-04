"""
AI Product Discovery Suite - Analytics Service Tracking API

Tracking endpoints for product views, search clicks, and search queries.
These endpoints are moved from search-service to analytics-service for SOLID compliance.

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, HTTPException, status, Body
from typing import Dict, Any
from datetime import datetime
import structlog
import uuid

from shared.middleware.auth import get_merchant_id
from shared.schemas.analytics import EventType
from shared.utils.event_validator import event_validator
from core.processor import EventProcessor
from schemas.tracking import (
    ProductViewRequest,
    SearchQueryRequest,
    SearchClickRequest,
    TrackingResponse
)

logger = structlog.get_logger()

router = APIRouter()


@router.post("/product-view", response_model=TrackingResponse,
           summary="Track Product View",
           description="""
    Track a product view event for analytics.
    
    **Event Details:**
    - Event type: `product_view`
    - Supports hybrid user/session tracking (at least one of user_id or session_id required)
    - Automatically enriches with context (IP, device, etc.)
    - Returns immediately (async processing)
    """)
async def track_product_view(
    request: ProductViewRequest = Body(...),
    http_request: Request = None
):
    """Track a product page view for analytics"""
    try:
        # Extract merchant_id from authenticated request
        merchant_id = get_merchant_id(http_request)
        
        logger.info(
            "Tracking product view",
            merchant_id=merchant_id,
            product_id=request.product_id,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        # Build event data dictionary
        event_data = {
            "event_type": EventType.PRODUCT_VIEW.value,
            "merchant_id": merchant_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "product_id": request.product_id,
            "platform": request.platform,
            "device_type": request.device_type,
            "ip_address": request.ip_address,
            "user_agent": request.user_agent,
            "referrer": request.referrer,
            "properties": {
                "product_name": request.product_name,
                "product_sku": request.product_sku,
                "categories": request.categories,
                "category_ids": request.category_ids,
                "view_duration": request.view_duration,
                "came_from_search": request.came_from_search,
                "search_query": request.search_query
            },
            "timestamp": datetime.utcnow(),
            "event_id": str(uuid.uuid4())
        }
        
        # Validate event using EventValidator
        validation_result = event_validator.validate_event(event_data)
        
        if not validation_result.is_valid:
            logger.warning(
                "Product view validation failed",
                errors=validation_result.errors,
                merchant_id=merchant_id,
                product_id=request.product_id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Get sanitized event
        sanitized_event = validation_result.sanitized_event
        if not sanitized_event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event validation failed: no sanitized event returned"
            )
        
        # Get EventProcessor from app state
        if not hasattr(http_request.app.state, 'event_processor'):
            logger.error("EventProcessor not initialized in app state")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analytics service not ready"
            )
        
        event_processor: EventProcessor = http_request.app.state.event_processor
        
        # Process event asynchronously
        event_id = sanitized_event.event_id
        await event_processor.process_event(sanitized_event.dict())
        
        logger.info(
            "Product view tracked successfully",
            event_id=event_id,
            merchant_id=merchant_id,
            product_id=request.product_id
        )
        
        return TrackingResponse(
            success=True,
            event_id=event_id,
            message="Product view tracked successfully",
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error tracking product view", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track product view: {str(e)}"
        )


@router.post("/search-click", response_model=TrackingResponse,
           summary="Track Search Click",
           description="""
    Track a click on a search result for analytics.
    
    **Event Details:**
    - Event type: `search_click`
    - Supports hybrid user/session tracking (at least one of user_id or session_id required)
    - Automatically enriches with context
    - Returns immediately (async processing)
    """)
async def track_search_click(
    request: SearchClickRequest = Body(...),
    http_request: Request = None
):
    """Track a click on search result for analytics"""
    try:
        # Extract merchant_id from authenticated request
        merchant_id = get_merchant_id(http_request)
        
        logger.info(
            "Tracking search click",
            merchant_id=merchant_id,
            search_query=request.search_query,
            clicked_product_id=request.clicked_product_id,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        # Build event data dictionary
        # Merge additional properties
        properties = request.properties.copy() if request.properties else {}
        properties.update({
            "search_query": request.search_query,
            "clicked_product_name": request.clicked_product_name,
            "position_in_results": request.position_in_results
        })
        
        event_data = {
            "event_type": EventType.SEARCH_CLICK.value,
            "merchant_id": merchant_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "product_id": request.clicked_product_id,
            "platform": request.platform,
            "device_type": request.device_type,
            "user_agent": request.user_agent,
            "ip_address": request.ip_address,
            "referrer": request.referrer,
            "properties": properties,
            "timestamp": datetime.utcnow(),
            "event_id": str(uuid.uuid4())
        }
        
        # Validate event using EventValidator
        validation_result = event_validator.validate_event(event_data)
        
        if not validation_result.is_valid:
            logger.warning(
                "Search click validation failed",
                errors=validation_result.errors,
                merchant_id=merchant_id,
                search_query=request.search_query
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Get sanitized event
        sanitized_event = validation_result.sanitized_event
        if not sanitized_event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event validation failed: no sanitized event returned"
            )
        
        # Get EventProcessor from app state
        if not hasattr(http_request.app.state, 'event_processor'):
            logger.error("EventProcessor not initialized in app state")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analytics service not ready"
            )
        
        event_processor: EventProcessor = http_request.app.state.event_processor
        
        # Process event asynchronously
        event_id = sanitized_event.event_id
        await event_processor.process_event(sanitized_event.dict())
        
        logger.info(
            "Search click tracked successfully",
            event_id=event_id,
            merchant_id=merchant_id,
            search_query=request.search_query
        )
        
        return TrackingResponse(
            success=True,
            event_id=event_id,
            message="Search click tracked successfully",
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error tracking search click", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track search click: {str(e)}"
        )


@router.post("/search-query", response_model=TrackingResponse,
           summary="Track Search Query (Manual Fallback)",
           description="""
    Track a search query event for analytics (manual fallback).
    
    **Note:** Search queries are typically auto-tracked via Redis pub/sub when using the search endpoint.
    This endpoint is provided as a manual fallback for cases where auto-tracking is not available.
    
    **Event Details:**
    - Event type: `search_query`
    - Supports hybrid user/session tracking (at least one of user_id or session_id required)
    - Automatically enriches with context
    - Returns immediately (async processing)
    """)
async def track_search_query(
    request: SearchQueryRequest = Body(...),
    http_request: Request = None
):
    """Track a search query for analytics (manual fallback)"""
    try:
        # Extract merchant_id from authenticated request
        merchant_id = get_merchant_id(http_request)
        
        logger.info(
            "Tracking search query",
            merchant_id=merchant_id,
            query=request.query,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        # Build event data dictionary
        results_count = request.results_count
        if results_count is None and request.results:
            results_count = len(request.results)
        
        # Merge additional properties
        properties = request.properties.copy() if request.properties else {}
        properties.update({
            "query": request.query,
            "results_count": results_count,
            "results": request.results if request.results else None
        })
        
        event_data = {
            "event_type": EventType.SEARCH_QUERY.value,
            "merchant_id": merchant_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "platform": request.platform,
            "device_type": request.device_type,
            "user_agent": request.user_agent,
            "ip_address": request.ip_address,
            "referrer": request.referrer,
            "properties": properties,
            "timestamp": datetime.utcnow(),
            "event_id": str(uuid.uuid4())
        }
        
        # Validate event using EventValidator
        validation_result = event_validator.validate_event(event_data)
        
        if not validation_result.is_valid:
            logger.warning(
                "Search query validation failed",
                errors=validation_result.errors,
                merchant_id=merchant_id,
                query=request.query
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Get sanitized event
        sanitized_event = validation_result.sanitized_event
        if not sanitized_event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event validation failed: no sanitized event returned"
            )
        
        # Get EventProcessor from app state
        if not hasattr(http_request.app.state, 'event_processor'):
            logger.error("EventProcessor not initialized in app state")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analytics service not ready"
            )
        
        event_processor: EventProcessor = http_request.app.state.event_processor
        
        # Process event asynchronously
        event_id = sanitized_event.event_id
        await event_processor.process_event(sanitized_event.dict())
        
        logger.info(
            "Search query tracked successfully",
            event_id=event_id,
            merchant_id=merchant_id,
            query=request.query
        )
        
        return TrackingResponse(
            success=True,
            event_id=event_id,
            message="Search query tracked successfully",
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error tracking search query", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track search query: {str(e)}"
        )


@router.get("/health")
async def tracking_health():
    """Tracking API health check"""
    return {"status": "healthy", "component": "tracking"}

