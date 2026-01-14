"""
AI Product Discovery Suite - Analytics Service Tracking Schemas

Tracking request/response schemas for analytics service endpoints.
Supports hybrid user/session tracking (at least one of user_id or session_id required).

@category    Backend
@package     AnalyticsService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProductViewRequest(BaseModel):
    """Request model for tracking product views"""
    # merchant_id is extracted from API key authentication, not provided in request
    user_id: Optional[str] = Field(None, description="User ID (optional, supports string user IDs)")
    session_id: Optional[str] = Field(None, description="Session ID (optional, at least one of user_id or session_id required)")
    product_id: int = Field(..., description="Product ID")
    product_name: Optional[str] = Field(None, description="Product name")
    product_sku: Optional[str] = Field(None, description="Product SKU")
    categories: Optional[List[str]] = Field(None, description="Product category names")
    category_ids: Optional[List[str]] = Field(None, description="Product category IDs")
    platform: Optional[str] = Field(None, description="Platform source: magento, woocommerce, shopify, etc.")
    device_type: Optional[str] = Field(None, description="Device type: mobile, desktop, tablet")
    user_agent: Optional[str] = Field(None, description="Browser/device user agent string")
    referrer: Optional[str] = Field(None, description="Referring page URL")
    view_duration: Optional[int] = Field(0, description="Time spent viewing in seconds")
    came_from_search: Optional[bool] = Field(False, description="Did user come from search?")
    search_query: Optional[str] = Field(None, description="Search query if came from search")
    ip_address: Optional[str] = Field(None, description="IP address")

    @model_validator(mode='after')
    def validate_identifiers(self):
        """Validate that at least one of user_id or session_id is provided"""
        if not self.user_id and not self.session_id:
            raise ValueError('Either user_id or session_id must be provided')
        return self

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "Product View with User ID and Session",
                    "description": "Complete product view tracking with all fields",
                    "value": {
                        "user_id": "user_12345",
                        "session_id": "sess_abc123def456",
                        "product_id": 158,
                        "product_name": "Hero Hoodie",
                        "product_sku": "MH07",
                        "categories": ["Hoodies & Sweatshirts", "Men"],
                        "category_ids": ["cat_123", "cat_456"],
                        "platform": "magento",
                        "device_type": "mobile",
                        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15",
                        "referrer": "https://store.example.com/search?q=hoodie",
                        "view_duration": 45,
                        "came_from_search": True,
                        "search_query": "comfortable hoodie",
                        "ip_address": "192.168.1.100"
                    }
                },
                {
                    "summary": "Product View with Session Only",
                    "description": "Anonymous user tracking with session ID only",
                    "value": {
                        "session_id": "sess_anonymous_xyz789",
                        "product_id": 158,
                        "product_name": "Hero Hoodie",
                        "platform": "magento",
                        "device_type": "desktop"
                    }
                },
                {
                    "summary": "Product View with User ID Only",
                    "description": "Authenticated user tracking without session",
                    "value": {
                        "user_id": "user_67890",
                        "product_id": 158,
                        "platform": "magento",
                        "device_type": "tablet"
                    }
                }
            ]
        }


class SearchQueryRequest(BaseModel):
    """Request model for tracking search queries (manual fallback)"""
    # merchant_id is extracted from API key authentication, not provided in request
    user_id: Optional[str] = Field(None, description="User ID (optional, supports string user IDs)")
    session_id: Optional[str] = Field(None, description="Session ID (optional, at least one of user_id or session_id required)")
    query: str = Field(..., description="Search query")
    results: Optional[List[Dict[str, Any]]] = Field(None, description="Search results (list of product dicts)")
    results_count: Optional[int] = Field(None, description="Number of search results")
    platform: Optional[str] = Field(None, description="Platform source: magento, woocommerce, shopify, etc.")
    device_type: Optional[str] = Field(None, description="Device type: mobile, desktop, tablet")
    user_agent: Optional[str] = Field(None, description="Browser/device user agent string")
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    referrer: Optional[str] = Field(None, description="Referring page URL")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional event properties")

    @model_validator(mode='after')
    def validate_identifiers(self):
        """Validate that at least one of user_id or session_id is provided"""
        if not self.user_id and not self.session_id:
            raise ValueError('Either user_id or session_id must be provided')
        return self

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "Search Query with Results",
                    "description": "Complete search query tracking with results",
                    "value": {
                        "user_id": "user_12345",
                        "session_id": "sess_abc123def456",
                        "query": "comfortable hoodie",
                        "results_count": 25,
                        "platform": "magento",
                        "device_type": "desktop",
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "ip_address": "192.168.1.100",
                        "referrer": "https://store.example.com/",
                        "results": [
                            {"product_id": 158, "product_name": "Hero Hoodie", "score": 0.95},
                            {"product_id": 159, "product_name": "Classic Hoodie", "score": 0.87}
                        ]
                    }
                },
                {
                    "summary": "Search Query Minimal",
                    "description": "Minimal search query tracking (auto-tracking typically handles this)",
                    "value": {
                        "session_id": "sess_xyz789",
                        "query": "wireless headphones",
                        "results_count": 12
                    }
                }
            ]
        }


class SearchClickRequest(BaseModel):
    """Request model for tracking search result clicks"""
    # merchant_id is extracted from API key authentication, not provided in request
    user_id: Optional[str] = Field(None, description="User ID (optional, supports string user IDs)")
    session_id: Optional[str] = Field(None, description="Session ID (optional, at least one of user_id or session_id required)")
    search_query: str = Field(..., description="Original search query")
    clicked_product_id: int = Field(..., description="ID of clicked product")
    clicked_product_name: Optional[str] = Field(None, description="Name of clicked product")
    position_in_results: Optional[int] = Field(None, description="Position in search results")
    platform: Optional[str] = Field(None, description="Platform source: magento, woocommerce, shopify, etc.")
    device_type: Optional[str] = Field(None, description="Device type: mobile, desktop, tablet")
    user_agent: Optional[str] = Field(None, description="Browser/device user agent string")
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    referrer: Optional[str] = Field(None, description="Referring page URL")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional event properties")

    @model_validator(mode='after')
    def validate_identifiers(self):
        """Validate that at least one of user_id or session_id is provided"""
        if not self.user_id and not self.session_id:
            raise ValueError('Either user_id or session_id must be provided')
        return self

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "Search Click Complete",
                    "description": "Complete search click tracking with all fields",
                    "value": {
                        "user_id": "user_12345",
                        "session_id": "sess_abc123def456",
                        "search_query": "comfortable hoodie",
                        "clicked_product_id": 158,
                        "clicked_product_name": "Hero Hoodie",
                        "position_in_results": 1,
                        "platform": "magento",
                        "device_type": "mobile",
                        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)",
                        "ip_address": "192.168.1.100",
                        "referrer": "https://store.example.com/search?q=hoodie"
                    }
                },
                {
                    "summary": "Search Click Minimal",
                    "description": "Minimal search click tracking",
                    "value": {
                        "session_id": "sess_xyz789",
                        "search_query": "wireless headphones",
                        "clicked_product_id": 456,
                        "position_in_results": 3
                    }
                }
            ]
        }


class TrackingResponse(BaseModel):
    """Response model for tracking endpoints"""
    success: bool = Field(..., description="Whether the tracking was successful")
    event_id: str = Field(..., description="Unique event ID")
    message: str = Field(..., description="Status message")
    timestamp: datetime = Field(..., description="Timestamp of the tracking event")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "event_id": "evt_1234567890abcdef",
                "message": "Product view tracked successfully",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }

