"""
AI Product Discovery Suite - Analytics Service Events API

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, model_validator
from typing import Dict, Any, Optional, Union
from datetime import datetime
import structlog
import uuid

from shared.middleware.auth import get_merchant_id
from shared.schemas.analytics import AnalyticsEventSchema, EventType
from shared.utils.event_validator import event_validator
from core.processor import EventProcessor

logger = structlog.get_logger()

router = APIRouter()


class EventRequest(BaseModel):
    """Event tracking request model"""
    event_type: str
    user_id: Optional[Union[str, int]] = None  # Support both string and int user IDs
    session_id: Optional[str] = None  # Made optional
    product_id: Optional[int] = None
    platform: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referrer: Optional[str] = None
    revenue: Optional[float] = None
    properties: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def validate_identifiers(self):
        """Validate that at least one of user_id or session_id is provided"""
        if not self.user_id and not self.session_id:
            raise ValueError('Either user_id or session_id must be provided')
        return self

    class Config:
        json_schema_extra = {
            "examples": [
                # Session-based tracking (existing behavior)
                {
                    "event_type": "product_view",
                    "session_id": "sess_123456789",
                    "product_id": 158,
                    "platform": "magento",
                    "device_type": "desktop",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "referrer": "https://store.example.com/search?q=laptop",
                    "properties": {
                        "page_url": "/products/hero-hoodie.html",
                        "categories": ["Hoodies & Sweatshirts"],
                        "price": 59.99
                    }
                },
                # User-based tracking (new capability)
                {
                    "event_type": "purchase",
                    "user_id": "user_12345",  # String user ID from search service
                    "product_id": 158,
                    "revenue": 59.99,
                    "platform": "magento",
                    "properties": {
                        "order_id": "ORD-12345",
                        "currency": "USD"
                    }
                },
                # Mixed tracking (user + session)
                {
                    "event_type": "search",
                    "user_id": 123,  # Integer user ID
                    "session_id": "sess_987654321",
                    "properties": {
                        "query": "wireless headphones",
                        "results_count": 25
                    }
                }
            ]
        }


class EventResponse(BaseModel):
    """Event tracking response model"""
    success: bool
    event_id: str
    message: str
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "event_id": "evt_prod_view_123456789_abcdef12",
                "message": "Event tracked successfully",
                "timestamp": "2025-01-15T10:30:45.123456"
            }
        }


@router.post("/track", response_model=EventResponse,
           summary="Track Analytics Event",
           description="""
    Track an analytics event for business intelligence and reporting.

    **Supported Event Types:**
    - `page_view` - User views a page
    - `product_view` - User views a product detail page
    - `search` - User performs a search query
    - `add_to_cart` - User adds item to cart
    - `remove_from_cart` - User removes item from cart
    - `purchase` - User completes a purchase
    - `wishlist_add` - User adds item to wishlist
    - `recommendation_click` - User clicks a recommendation
    - `filter_apply` - User applies search filters
    - `session_start` - User session begins
    - `session_end` - User session ends

    **Processing:**
    - Events are validated and enriched with context
    - Stored in database for analytics
    - Queued for batch aggregation processing
    - Returns immediately (async processing)
    """)
async def track_event(event: EventRequest, request: Request):
    """
    Track an analytics event

    Validates, enriches, and processes the event asynchronously.
    Returns immediately with event_id for async processing.
    """
    try:
        # Extract merchant_id from authenticated request
        merchant_id = get_merchant_id(request)
        
        logger.info(
            "Tracking event",
            event_type=event.event_type,
            merchant_id=merchant_id,
            user_id=event.user_id,
            session_id=event.session_id
        )
        
        # Validate event_type
        try:
            event_type = EventType(event.event_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event_type: {event.event_type}. Valid types: {[e.value for e in EventType]}"
            )
        
        # Build event data dictionary
        event_data = {
            "event_type": event_type.value,
            "merchant_id": merchant_id,
            "user_id": event.user_id,  # Can be string or int
            "session_id": event.session_id,
            "product_id": event.product_id,
            "platform": event.platform,
            "device_type": event.device_type,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "referrer": event.referrer,
            "revenue": event.revenue,
            "properties": event.properties or {},
            "timestamp": datetime.utcnow(),
            "event_id": str(uuid.uuid4())
        }
        
        # Validate event using EventValidator
        validation_result = event_validator.validate_event(event_data)
        
        if not validation_result.is_valid:
            logger.warning(
                "Event validation failed",
                errors=validation_result.errors,
                merchant_id=merchant_id,
                event_type=event.event_type
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
        if not hasattr(request.app.state, 'event_processor'):
            logger.error("EventProcessor not initialized in app state")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analytics service not ready"
            )
        
        event_processor: EventProcessor = request.app.state.event_processor
        
        # Process event asynchronously (non-blocking)
        # This will validate, enrich, store, and queue for aggregation
        event_id = sanitized_event.event_id
        await event_processor.process_event(sanitized_event.dict())
        
        logger.info(
            "Event tracked successfully",
            event_id=event_id,
            event_type=event.event_type,
            merchant_id=merchant_id
        )
        
        return EventResponse(
            success=True,
            event_id=event_id,
            message="Event tracked successfully",
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error tracking event", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track event: {str(e)}"
        )


@router.get("/health")
async def events_health():
    """Events API health check"""
    return {"status": "healthy", "component": "events"}
