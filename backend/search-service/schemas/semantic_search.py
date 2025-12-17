"""
AI Product Discovery Suite - Semantic Search Schemas

Schemas for semantic search operations using vector similarity.

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SemanticSearchRequest(BaseModel):
    """Semantic search request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(20, ge=1, le=100, description="Number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "comfortable hoodie for running",
                "limit": 10,
                "offset": 0,
                "filters": {
                    "category": "hoodies",
                    "in_stock": True
                },
                "min_score": 0.7
            }
        }


class SemanticSearchResult(BaseModel):
    """Semantic search result item"""
    product_id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional product metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "158",
                "name": "Hero Hoodie",
                "score": 0.89,
                "metadata": {
                    "sku": "MH07",
                    "price": 59.99,
                    "special_price": 49.99,
                    "image_url": "https://example-store.com/media/product/hero-hoodie.jpg",
                    "category_name": "Hoodies & Sweatshirts",
                    "is_in_stock": True
                }
            }
        }


class SemanticSearchResponse(BaseModel):
    """Semantic search response model"""
    results: List[SemanticSearchResult] = Field(..., description="Search results")
    total: int = Field(..., ge=0, description="Total number of results returned")
    query: str = Field(..., description="Original search query")
    took: float = Field(..., ge=0.0, description="Response time in seconds")
    search_mode: str = Field("semantic", description="Search mode used")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "product_id": "158",
                        "name": "Hero Hoodie",
                        "score": 0.89,
                        "metadata": {
                            "sku": "MH07",
                            "price": 59.99,
                            "image_url": "https://example-store.com/media/product/hero-hoodie.jpg",
                            "category_name": "Hoodies & Sweatshirts",
                            "is_in_stock": True
                        }
                    }
                ],
                "total": 1,
                "query": "comfortable hoodie for running",
                "took": 0.45,
                "search_mode": "semantic"
            }
        }
