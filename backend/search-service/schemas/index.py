"""
AI Product Discovery Suite - Index Schemas

Schemas for product indexing operations and index management.

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from .product import DataQualityMetrics


class IndexRequest(BaseModel):
    """Index request model for product indexing"""
    products: List[Dict[str, Any]] = Field(..., description="List of products to index")

    class Config:
        json_schema_extra = {
            "example": {
                "products": [
                    {
                        "id": "158",
                        "sku": "MH07",
                        "name": "Hero Hoodie",
                        "description": "Premium quality hero themed hoodie with comfort fit",
                        "price": 59.99,
                        "special_price": 49.99,
                        "currency": "USD",
                        "categories": ["Hoodies & Sweatshirts"],
                        "brand": "Magento",
                        "image_url": "https://example-store.com/media/product/hero-hoodie.jpg",
                        "url": "https://example-store.com/products/hero-hoodie.html",
                        "stock": {
                            "qty": 25,
                            "is_in_stock": True
                        },
                        "attributes": {
                            "color": "Blue",
                            "size": "M",
                            "material": "Cotton"
                        },
                        "status": 1,
                        "visibility": 4
                    }
                ]
            }
        }


class IndexResponse(BaseModel):
    """Index response model with data quality metrics"""
    success: bool = Field(..., description="Whether indexing was successful")
    indexed_count: int = Field(..., description="Number of products successfully indexed")
    message: str = Field(..., description="Status message")
    data_quality: Optional[DataQualityMetrics] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "indexed_count": 1,
                "message": "Successfully indexed 1 product(s)",
                "data_quality": {
                    "total_products": 1,
                    "products_with_price": 1,
                    "products_with_image": 1,
                    "products_with_categories": 1,
                    "products_with_description": 1,
                    "completeness_score": 100.0
                }
            }
        }


class IndexStatusResponse(BaseModel):
    """Response model for index status endpoint"""
    index: str = Field(..., description="Index name")
    exists: bool = Field(..., description="Whether the index exists")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Index statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "index": "ai_discovery_products_merchant_1",
                "exists": True,
                "stats": {
                    "indices": {
                        "ai_discovery_products_merchant_1": {
                            "total": {
                                "docs": {
                                    "count": 150,
                                    "deleted": 0
                                },
                                "store": {
                                    "size_in_bytes": 245760
                                }
                            }
                        }
                    }
                }
            }
        }


class EnsureIndexResponse(BaseModel):
    """Response model for ensure index endpoint"""
    success: bool = Field(..., description="Whether index creation/update was successful")
    index: str = Field(..., description="Index name")
    message: str = Field(..., description="Status message")
    created: bool = Field(..., description="Whether a new index was created")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "index": "ai_discovery_products_merchant_1",
                "message": "Index created successfully",
                "created": True
            }
        }


class DeleteProductResponse(BaseModel):
    """Response model for delete product endpoint"""
    success: bool = Field(..., description="Whether deletion was successful")
    product_id: str = Field(..., description="ID of the deleted product")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "product_id": "158",
                "message": "Product deleted successfully from search index"
            }
        }
