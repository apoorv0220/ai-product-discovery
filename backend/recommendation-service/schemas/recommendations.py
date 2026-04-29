"""
AI Product Discovery Suite - Recommendation Service Schemas

@category    Backend
@package     RecommendationService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class RecommendationContext(str, Enum):
    """Recommendation context types"""
    HOME = "home"
    PRODUCT_DETAIL = "product_detail"
    PRODUCT_VIEW = "product_view"  # Alternative for product_detail
    SIMILAR_PRODUCTS = "similar_products"  # For similar product recommendations
    CART = "cart"
    CHECKOUT = "checkout"
    CATEGORY = "category"
    CATEGORY_VIEW = "category_view"  # Alternative for category
    SEARCH = "search"
    WISHLIST = "wishlist"
    RECENTLY_VIEWED = "recently_viewed"


class EventType(str, Enum):
    """Tracking event types"""
    VIEW = "view"
    CLICK = "click"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"
    WISHLIST_ADD = "wishlist_add"
    SHARE = "share"
    IMPRESSION = "impression"


class RecommendationRequest(BaseModel):
    """Request model for getting recommendations"""
    user_id: Optional[str] = Field(None, description="User ID for personalized recommendations")
    context: RecommendationContext = Field(..., description="Context where recommendations are requested")
    product_ids: Optional[List[str]] = Field(None, description="Product IDs for context-based recommendations")
    category_ids: Optional[List[str]] = Field(None, description="Category IDs to filter recommendations")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of recommendations to return")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters for recommendations")
    exclude_viewed: bool = Field(True, description="Exclude products already viewed by user")
    exclude_purchased: bool = Field(True, description="Exclude products already purchased by user")
    session_id: Optional[str] = Field(None, description="Session ID for anonymous users")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "context": "home",
                "limit": 10,
                "filters": {
                    "price_range": {"min": 10, "max": 100},
                    "brand": ["Nike", "Adidas"]
                },
                "exclude_viewed": True,
                "exclude_purchased": True
            }
        }


class RecommendationItem(BaseModel):
    """Individual recommendation item"""
    product_id: str = Field(..., description="Product ID")
    score: float = Field(..., description="Recommendation score (0-1)")
    reason: str = Field(..., description="Explanation for why this product is recommended")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "prod_456",
                "score": 0.85,
                "reason": "Frequently bought together",
                "metadata": {
                    "algorithm": "collaborative_filtering",
                    "category": "electronics"
                }
            }
        }


class RecommendationResponse(BaseModel):
    """Response model for recommendations"""
    recommendations: List[RecommendationItem] = Field(..., description="List of recommended products")
    user_id: Optional[str] = Field(None, description="User ID")
    context: RecommendationContext = Field(..., description="Recommendation context")
    total_count: int = Field(..., description="Total number of recommendations returned")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "recommendations": [
                    {
                        "product_id": "prod_456",
                        "score": 0.85,
                        "reason": "Frequently bought together",
                        "metadata": {"algorithm": "collaborative_filtering"}
                    }
                ],
                "user_id": "user_123",
                "context": "home",
                "total_count": 1,
                "metadata": {
                    "algorithm": "collaborative_filtering_v2",
                    "model_version": "1.0.0"
                }
            }
        }


class TrackingRequest(BaseModel):
    """Request model for tracking recommendation events"""
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID for anonymous users")
    event_type: EventType = Field(..., description="Type of event being tracked")
    product_id: str = Field(..., description="Product ID that was interacted with")
    recommendation_id: Optional[str] = Field(None, description="ID of the recommendation that led to this event")
    position: Optional[int] = Field(None, description="Position of the product in the recommendation list")
    context: Optional[RecommendationContext] = Field(None, description="Context where the event occurred")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional event metadata")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "event_type": "click",
                "product_id": "prod_456",
                "recommendation_id": "rec_789",
                "position": 1,
                "context": "home",
                "metadata": {
                    "page": "homepage",
                    "widget": "trending_now"
                }
            }
        }


class TrackingResponse(BaseModel):
    """Response model for tracking events"""
    success: bool = Field(..., description="Whether the event was successfully tracked")
    event_id: str = Field(..., description="Unique ID for the tracked event")
    message: str = Field(..., description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "event_id": "event_abc123",
                "message": "Event tracked successfully"
            }
        }


class SimilarProductsRequest(BaseModel):
    """Request model for similar products"""
    product_id: str = Field(..., description="Reference product ID")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of similar products to return")
    category_filter: Optional[str] = Field(None, description="Filter by category")
    brand_filter: Optional[str] = Field(None, description="Filter by brand")
    price_range: Optional[Dict[str, float]] = Field(None, description="Filter by price range")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "prod_123",
                "limit": 10,
                "category_filter": "electronics",
                "price_range": {"min": 50, "max": 200}
            }
        }


class UserPreferencesRequest(BaseModel):
    """Request model for updating user preferences"""
    user_id: str = Field(..., description="User ID")
    preferences: Dict[str, Any] = Field(..., description="User preferences")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "preferences": {
                    "categories": ["electronics", "books"],
                    "brands": ["Apple", "Samsung"],
                    "price_range": {"min": 0, "max": 1000}
                }
            }
        }


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences"""
    user_id: str = Field(..., description="User ID")
    preferences: Dict[str, Any] = Field(..., description="Updated user preferences")
    updated_at: datetime = Field(..., description="Timestamp when preferences were updated")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "preferences": {
                    "categories": ["electronics", "books"],
                    "brands": ["Apple", "Samsung"]
                },
                "updated_at": "2024-01-01T12:00:00Z"
            }
        }