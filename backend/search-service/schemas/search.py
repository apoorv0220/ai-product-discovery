"""
Updated Search Schemas for AI Product Discovery Suite
Reflects actual API response formats with OpenAI integration and personalization

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator


class SearchResultItem(BaseModel):
    """Individual search result with enhanced metadata"""
    product_id: str = Field(..., description="Product ID as string")
    title: str = Field(..., description="Product title/name")
    score: float = Field(..., ge=0.0, description="Relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Product metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "158",
                "title": "Hero Hoodie",
                "score": 0.95,
                "metadata": {
                    "price": 59.99,
                    "currency": "USD",
                    "image_url": "https://example-store.com/media/product/hero-hoodie.jpg",
                    "url": "https://example-store.com/products/hero-hoodie.html",
                    "categories": ["Hoodies & Sweatshirts"],
                    "sku": "MH07",
                    "description": "Premium quality hero themed hoodie"
                }
            }
        }


class SearchCorrection(BaseModel):
    """Search query correction information"""
    original: str = Field(..., description="Original text")
    corrected: str = Field(..., description="Corrected text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Correction confidence")
    type: str = Field(..., description="Correction type: 'openai_correction', 'basic_correction'")

    class Config:
        json_schema_extra = {
            "example": {
                "original": "Hro Hoodie",
                "corrected": "Hero Hoodie",
                "confidence": 0.9,
                "type": "openai_correction"
            }
        }


class SearchMetadata(BaseModel):
    """Search processing metadata with personalization info"""
    nlp_enabled: bool = Field(default=False, description="Whether NLP processing was enabled")
    semantic_search: bool = Field(default=False, description="Whether semantic search was used")
    typo_corrected: bool = Field(default=False, description="Whether typo correction was applied")
    ai_enhanced: bool = Field(default=False, description="Whether AI enhancement was used")
    intent_type: str = Field(default="", description="Detected search intent")
    processing_time: float = Field(default=0.0, ge=0.0, description="Processing time in seconds")
    corrections: List[SearchCorrection] = Field(default_factory=list, description="Applied corrections")
    fallback_used: Optional[bool] = Field(default=None, description="Whether fallback search was used")
    error: Optional[str] = Field(default=None, description="Error message if processing failed")

    # Personalization metadata
    personalization_applied: bool = Field(default=False, description="Whether personalization was applied")
    user_id: Optional[str] = Field(default=None, description="User ID used for personalization")
    session_id: Optional[str] = Field(default=None, description="Session ID used for personalization")
    personalization_profile_used: bool = Field(default=False, description="Whether user profile was found and used")
    personalization_processing_time: float = Field(default=0.0, ge=0.0, description="Time spent on personalization")

    class Config:
        json_schema_extra = {
            "example": {
                "nlp_enabled": True,
                "semantic_search": True,
                "typo_corrected": True,
                "ai_enhanced": True,
                "intent_type": "buy",
                "processing_time": 0.45,
                "corrections": [
                    {
                        "original": "Hro Hoodie",
                        "corrected": "Hero Hoodie",
                        "confidence": 0.9,
                        "type": "openai_correction"
                    }
                ],
                "personalization_applied": True,
                "user_id": "user_12345",
                "session_id": "session_abc123",
                "personalization_profile_used": True,
                "personalization_processing_time": 0.02
            }
        }


class SearchResponse(BaseModel):
    """Complete search response format"""
    results: List[SearchResultItem] = Field(default_factory=list, description="Search results")
    total: int = Field(default=0, ge=0, description="Total number of results")
    query: str = Field(..., description="Original search query")
    took: float = Field(..., ge=0.0, description="Total response time in seconds")
    facets: Optional[Dict[str, Any]] = Field(default=None, description="Search facets for filtering")
    search_metadata: SearchMetadata = Field(description="Search processing metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "product_id": "158",
                        "title": "Hero Hoodie",
                        "score": 0.95,
                        "metadata": {
                            "price": 59.99,
                            "currency": "USD",
                            "image_url": "https://example-store.com/media/product/hero-hoodie.jpg",
                            "url": "https://example-store.com/products/hero-hoodie.html",
                            "categories": ["Hoodies & Sweatshirts"],
                            "sku": "MH07",
                            "description": "Premium quality hero themed hoodie"
                        }
                    }
                ],
                "total": 1,
                "query": "Hro Hoodie",
                "took": 0.45,
                "search_metadata": {
                    "nlp_enabled": True,
                    "semantic_search": True,
                    "typo_corrected": True,
                    "ai_enhanced": True,
                    "intent_type": "buy",
                    "processing_time": 0.45,
                    "corrections": [
                        {
                            "original": "Hro Hoodie",
                            "corrected": "Hero Hoodie",
                            "confidence": 0.9,
                            "type": "openai_correction"
                        }
                    ]
                }
            }
        }


class SearchRequest(BaseModel):
    """Search request schema with personalization support"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Result offset for pagination")
    filters: Optional[Union[Dict[str, Any], List]] = Field(default_factory=dict, description="Search filters")

    # Personalization parameters
    user_id: Optional[str] = Field(None, description="Platform user ID for personalization")
    session_id: Optional[str] = Field(None, description="Session ID for anonymous user personalization")
    user_context: Optional[Dict[str, Any]] = Field(None, description="Platform-specific user context data")
    personalize: bool = Field(False, description="Enable/disable personalization")

    @validator('filters', pre=True)
    def normalize_filters(cls, v):
        """Convert filters array to dict if needed"""
        if isinstance(v, list):
            return {}
        return v or {}

    class Config:
        json_schema_extra = {
            "example": {
                "query": "comfortable hoodie",
                "limit": 20,
                "offset": 0,
                "filters": {
                    "category": "hoodies",
                    "price_range": {"min": 20, "max": 100}
                },
                "user_id": "user_12345",
                "session_id": "session_abc123",
                "user_context": {
                    "cart_items": ["prod_1", "prod_2"],
                    "recently_viewed": ["prod_3"],
                    "purchase_history": ["prod_4"],
                    "device_type": "mobile"
                },
                "personalize": False
            }
        }


class SearchErrorResponse(BaseModel):
    """Error response for search API"""
    results: List[SearchResultItem] = Field(default_factory=list, description="Empty results list")
    total: int = Field(default=0, description="Zero total results")
    query: str = Field(..., description="Original query")
    took: float = Field(..., ge=0.0, description="Processing time")
    search_metadata: SearchMetadata = Field(description="Metadata indicating error")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [],
                "total": 0,
                "query": "search term",
                "took": 0.1,
                "search_metadata": {
                    "nlp_enabled": False,
                    "semantic_search": False,
                    "typo_corrected": False,
                    "ai_enhanced": False,
                    "intent_type": "error",
                    "processing_time": 0.1,
                    "corrections": [],
                    "error": "Search service unavailable"
                }
            }
        }