"""
AI Product Discovery Suite - Tracking Schemas

Schemas for user interaction tracking and personalization data collection.

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProductViewRequest(BaseModel):
    """Request model for tracking product views"""
    # merchant_id is extracted from API key authentication, not provided in request
    user_id: Optional[str] = Field(None, description="User ID (null for anonymous)")
    session_id: str = Field(..., description="Session ID")
    product_id: str = Field(..., description="Product ID")
    product_name: Optional[str] = Field(None, description="Product name")
    product_sku: Optional[str] = Field(None, description="Product SKU")
    categories: Optional[List[str]] = Field(None, description="Product category names")
    category_ids: Optional[List[str]] = Field(None, description="Product category IDs")
    # Platform context for better personalization (optional)
    platform: Optional[str] = Field(None, description="Platform source: magento, woocommerce, shopify, etc.")
    device_type: Optional[str] = Field(None, description="Device type: mobile, desktop, tablet")
    user_agent: Optional[str] = Field(None, description="Browser/device user agent string")
    referrer: Optional[str] = Field(None, description="Referring page URL")
    view_duration: Optional[int] = Field(0, description="Time spent viewing in seconds")
    came_from_search: Optional[bool] = Field(False, description="Did user come from search?")
    search_query: Optional[str] = Field(None, description="Search query if came from search")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "session_id": "session_abc123",
                "product_id": "158",
                "product_name": "Hero Hoodie",
                "product_sku": "MH07",
                "categories": ["Hoodies & Sweatshirts"],
                "category_ids": ["cat_123"],
                "platform": "magento",
                "device_type": "mobile",
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)",
                "referrer": "https://store.com/search?q=hoodie",
                "view_duration": 45,
                "came_from_search": True,
                "search_query": "comfortable hoodie"
            }
        }


class SearchQueryRequest(BaseModel):
    """Request model for tracking search queries"""
    # merchant_id is extracted from API key authentication, not provided in request
    user_id: Optional[str] = Field(None, description="User ID (null for anonymous)")
    session_id: str = Field(..., description="Session ID")
    query: str = Field(..., description="Search query")
    results: Optional[List[Dict[str, Any]]] = Field(None, description="Search results")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "session_id": "session_abc123",
                "query": "comfortable hoodie",
                "results": [
                    {
                        "product_id": "158",
                        "title": "Hero Hoodie",
                        "score": 0.95
                    }
                ]
            }
        }


class SearchClickRequest(BaseModel):
    """Request model for tracking search result clicks"""
    # merchant_id is extracted from API key authentication, not provided in request
    user_id: Optional[str] = Field(None, description="User ID (null for anonymous)")
    session_id: str = Field(..., description="Session ID")
    search_query: str = Field(..., description="Original search query")
    clicked_product_id: str = Field(..., description="ID of clicked product")
    clicked_product_name: Optional[str] = Field(None, description="Name of clicked product")
    position_in_results: Optional[int] = Field(None, description="Position in search results")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "session_id": "session_abc123",
                "search_query": "comfortable hoodie",
                "clicked_product_id": "158",
                "clicked_product_name": "Hero Hoodie",
                "position_in_results": 1
            }
        }


class BulkTrackingRequest(BaseModel):
    """Request model for bulk historical data ingestion"""
    # merchant_id is extracted from API key authentication, not provided in request
    product_views: Optional[List[ProductViewRequest]] = Field(default_factory=list, description="Historical product views")
    search_queries: Optional[List[SearchQueryRequest]] = Field(default_factory=list, description="Historical search queries")
    search_clicks: Optional[List[SearchClickRequest]] = Field(default_factory=list, description="Historical search clicks")

    class Config:
        json_schema_extra = {
            "example": {
                "product_views": [
                    {
                        "user_id": "user_12345",
                        "session_id": "session_abc123",
                        "product_id": "158",
                        "product_name": "Hero Hoodie",
                        "categories": ["Hoodies & Sweatshirts"],
                        "view_duration": 30
                    }
                ],
                "search_queries": [
                    {
                        "user_id": "user_12345",
                        "session_id": "session_abc123",
                        "query": "comfortable hoodie"
                    }
                ],
                "search_clicks": [
                    {
                        "user_id": "user_12345",
                        "session_id": "session_abc123",
                        "search_query": "comfortable hoodie",
                        "clicked_product_id": "158",
                        "position_in_results": 1
                    }
                ]
            }
        }


class BulkTrackingResponse(BaseModel):
    """Response model for bulk tracking endpoints"""
    success: bool = Field(..., description="Whether the bulk operation was successful")
    message: str = Field(..., description="Status message")
    processed_counts: Dict[str, int] = Field(..., description="Count of processed items by type")
    errors: List[str] = Field(default_factory=list, description="List of errors if any")
    timestamp: str = Field(..., description="Timestamp of the operation")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully processed 150 tracking events",
                "processed_counts": {
                    "product_views": 100,
                    "search_queries": 30,
                    "search_clicks": 20
                },
                "errors": [],
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class TrackingResponse(BaseModel):
    """Response model for tracking endpoints"""
    success: bool = Field(..., description="Whether the tracking was successful")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="Timestamp of the tracking event")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Product view tracked successfully",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class UserHistoryResponse(BaseModel):
    """Response model for user history endpoints"""
    user_id: str = Field(..., description="User ID")
    total_events: int = Field(..., description="Total number of tracking events")
    recent_views: List[Dict[str, Any]] = Field(default_factory=list, description="Recent product views")
    recent_searches: List[Dict[str, Any]] = Field(default_factory=list, description="Recent search queries")
    last_activity: Optional[str] = Field(None, description="Timestamp of last activity")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "total_events": 25,
                "recent_views": [
                    {
                        "product_id": "158",
                        "product_name": "Hero Hoodie",
                        "viewed_at": "2024-01-15T10:25:00Z",
                        "view_duration": 30
                    }
                ],
                "recent_searches": [
                    {
                        "query": "comfortable hoodie",
                        "searched_at": "2024-01-15T10:20:00Z"
                    }
                ],
                "last_activity": "2024-01-15T10:25:00Z"
            }
        }


class PersonalizationWeightsResponse(BaseModel):
    """Response model for personalization weights"""
    user_id: str = Field(..., description="User ID")
    weights: Dict[str, float] = Field(..., description="Personalization weights by factor")
    confidence: float = Field(..., description="Overall confidence in personalization")
    factors_used: List[str] = Field(..., description="Factors used in personalization")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "weights": {
                    "category_preference": 0.8,
                    "price_sensitivity": 0.6,
                    "brand_loyalty": 0.4
                },
                "confidence": 0.75,
                "factors_used": ["category_preference", "price_sensitivity"]
            }
        }
