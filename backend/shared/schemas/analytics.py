"""
Shared Analytics Schemas
Standardized event schemas for analytics service
"""

from enum import Enum
from typing import Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, model_validator
import uuid


class EventType(str, Enum):
    """Analytics event types"""
    PAGE_VIEW = "page_view"
    PRODUCT_VIEW = "product_view"
    SEARCH = "search"
    SEARCH_QUERY = "search_query"  # Alias for search, used for auto-tracking
    SEARCH_CLICK = "search_click"  # Click on search result
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    PURCHASE = "purchase"
    WISHLIST_ADD = "wishlist_add"
    RECOMMENDATION_CLICK = "recommendation_click"
    FILTER_APPLY = "filter_apply"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


class AnalyticsEventSchema(BaseModel):
    """Standardized analytics event schema"""

    event_type: EventType = Field(..., description="Type of event")
    merchant_id: int = Field(..., description="Merchant ID (required)")
    user_id: Optional[Union[str, int]] = Field(None, description="User ID (string or int, optional)")
    session_id: Optional[str] = Field(None, description="Session identifier (optional)")
    product_id: Optional[int] = Field(None, description="Product ID (optional)")

    # Context fields
    platform: Optional[str] = Field(None, max_length=50, description="Platform (e.g., magento, woocommerce)")
    device_type: Optional[str] = Field(None, max_length=50, description="Device type (mobile, desktop, tablet)")
    ip_address: Optional[str] = Field(None, max_length=45, description="IP address")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent string")
    referrer: Optional[str] = Field(None, max_length=500, description="Referrer URL")
    revenue: Optional[float] = Field(None, ge=0, description="Revenue amount (for purchase events)")

    # Additional properties
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional event properties")

    # Metadata
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Event timestamp")
    event_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event ID")
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('session_id cannot be empty if provided')
            if len(v) > 255:
                raise ValueError('session_id cannot exceed 255 characters')
            return v.strip()
        return v
    
    @validator('properties')
    def validate_properties_size(cls, v):
        if v and len(str(v)) > 10000:  # 10KB limit for properties
            raise ValueError('properties JSON size cannot exceed 10KB')
        return v
    
    @validator('platform')
    def validate_platform(cls, v):
        if v and len(v) > 50:
            raise ValueError('platform cannot exceed 50 characters')
        return v.lower() if v else v

    @validator('device_type')
    def validate_device_type(cls, v):
        if v:
            v = v.lower()
            allowed = ['mobile', 'desktop', 'tablet', 'other']
            if v not in allowed:
                # Default to 'other' if not in allowed list
                return 'other'
        return v

    @model_validator(mode='after')
    def validate_identifiers(self):
        """Validate that at least one of user_id or session_id is provided"""
        if not self.user_id and not self.session_id:
            raise ValueError('Either user_id or session_id must be provided')
        return self

    @model_validator(mode='after')
    def validate_event_specific_fields(self):
        """Validate event-specific required fields"""
        # Product-related events should have product_id (optional but recommended)
        # Purchase events should have revenue (optional but should be >= 0 if provided)
        # These are just warnings/recommendations, not strict requirements
        return self
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EventValidationResult(BaseModel):
    """Event validation result"""
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    sanitized_event: Optional[AnalyticsEventSchema] = None


class EventDeduplicationKey(BaseModel):
    """Key for event deduplication"""
    event_id: str
    merchant_id: int
    session_id: str
    timestamp: datetime
    event_type: EventType
    
    def to_redis_key(self) -> str:
        """Convert to Redis key format"""
        # Use a short timestamp to avoid very long keys
        timestamp_str = self.timestamp.strftime('%Y%m%d%H%M%S')
        return f"event:{self.merchant_id}:{self.event_type}:{self.session_id}:{timestamp_str}:{self.event_id}"

