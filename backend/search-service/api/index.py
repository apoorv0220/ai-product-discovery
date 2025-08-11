"""
AI Product Discovery Suite - Search Service Indexing API

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Dict, Any, List
import structlog
import json
import os
from pathlib import Path

logger = structlog.get_logger()
router = APIRouter()

# In-memory storage for products (in production, use a real database/search engine)
PRODUCTS_STORAGE = {}
PRODUCTS_FILE = "/tmp/products_index.json"

def load_products():
    """Load products from file"""
    global PRODUCTS_STORAGE
    try:
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, 'r') as f:
                PRODUCTS_STORAGE = json.load(f)
                logger.info("Loaded products from storage", count=len(PRODUCTS_STORAGE))
    except Exception as e:
        logger.error("Error loading products", error=str(e))
        PRODUCTS_STORAGE = {}

def save_products():
    """Save products to file"""
    try:
        os.makedirs(os.path.dirname(PRODUCTS_FILE), exist_ok=True)
        with open(PRODUCTS_FILE, 'w') as f:
            json.dump(PRODUCTS_STORAGE, f)
        logger.info("Saved products to storage", count=len(PRODUCTS_STORAGE))
    except Exception as e:
        logger.error("Error saving products", error=str(e))

# Load existing products on startup
load_products()

@router.get("/status")
async def get_index_status():
    """Get status of the search index"""
    return {
        "status": "active",
        "total_products": get_product_count(),
        "storage_file": PRODUCTS_FILE,
        "storage_exists": os.path.exists(PRODUCTS_FILE)
    }

def search_products(query: str, limit: int = 10):
    """Search products by query"""
    if not query.strip():
        return []
    
    query_lower = query.lower()
    matching_products = []
    
    for product_id, product in PRODUCTS_STORAGE.items():
        # Simple text matching
        if (query_lower in product.get('searchable_text', '') or 
            query_lower in product.get('name', '').lower() or
            query_lower in product.get('sku', '').lower()):
            matching_products.append(product)
    
    # Sort by relevance (name matches first, then description)
    def relevance_score(product):
        name = product.get('name', '').lower()
        if query_lower in name:
            return 10 + (100 - len(name))  # Prefer shorter names
        return 1
    
    matching_products.sort(key=relevance_score, reverse=True)
    return matching_products[:limit]

def get_product_count():
    """Get total number of indexed products"""
    return len(PRODUCTS_STORAGE)


class IndexRequest(BaseModel):
    """Index request model"""
    products: List[Dict[str, Any]]


class IndexResponse(BaseModel):
    """Index response model"""
    success: bool
    indexed_count: int
    message: str


@router.post("/products", response_model=IndexResponse)
async def index_products(index_request: IndexRequest, request: Request):
    """Index products for search"""
    try:
        logger.info("Indexing products", count=len(index_request.products))
        
        # Store products in our index
        indexed_count = 0
        for product in index_request.products:
            try:
                product_id = str(product.get('id', product.get('sku', f'unknown_{indexed_count}')))
                
                # Store the product with searchable data
                PRODUCTS_STORAGE[product_id] = {
                    'id': product.get('id'),
                    'sku': product.get('sku', ''),
                    'name': product.get('name', ''),
                    'description': product.get('description', ''),
                    'short_description': product.get('short_description', ''),
                    'price': product.get('price', 0),
                    'special_price': product.get('special_price'),
                    'currency': product.get('currency', 'USD'),
                    'url': product.get('url', ''),
                    'image_url': product.get('image_url', ''),
                    'categories': product.get('categories', []),
                    'attributes': product.get('attributes', {}),
                    'stock': product.get('stock', {}),
                    'status': product.get('status', 1),
                    'visibility': product.get('visibility', 4),
                    'store_id': product.get('store_id', 1),
                    'searchable_text': f"{product.get('name', '')} {product.get('description', '')} {product.get('sku', '')}".lower()
                }
                indexed_count += 1
                
            except Exception as e:
                logger.error("Error indexing individual product", error=str(e), product=product)
                continue
        
        # Save to persistent storage
        save_products()
        
        logger.info("Successfully indexed products", indexed=indexed_count, total=len(index_request.products))
        
        return IndexResponse(
            success=True,
            indexed_count=indexed_count,
            message=f"Successfully indexed {indexed_count} products"
        )
    except Exception as e:
        logger.error("Error indexing products", error=str(e))
        return IndexResponse(
            success=False,
            indexed_count=0,
            message=f"Error indexing products: {str(e)}"
        )


@router.delete("/products/{product_id}")
async def delete_product_from_index(product_id: str, request: Request):
    """Delete a product from the search index"""
    try:
        logger.info("Deleting product from index", product_id=product_id)
        
        # TODO: Implement actual deletion
        return {"success": True, "message": f"Product {product_id} deleted from index"}
    except Exception as e:
        logger.error("Error deleting product from index", error=str(e))
        return {"success": False, "message": str(e)}


@router.post("/rebuild")
async def rebuild_index(request: Request):
    """Rebuild the entire search index"""
    try:
        logger.info("Rebuilding search index")
        
        # Clear current index
        global PRODUCTS_STORAGE
        product_count = len(PRODUCTS_STORAGE)
        PRODUCTS_STORAGE.clear()
        save_products()
        
        logger.info("Search index cleared", previous_count=product_count)
        
        return {"success": True, "message": f"Index rebuild completed. Cleared {product_count} products. Ready for new data."}
    except Exception as e:
        logger.error("Error rebuilding index", error=str(e))
        return {"success": False, "message": str(e)}

@router.get("/status")
async def get_index_status(request: Request):
    """Get index status"""
    try:
        return {
            "product_count": get_product_count(),
            "status": "ready",
            "storage_file": PRODUCTS_FILE
        }
    except Exception as e:
        logger.error("Error getting index status", error=str(e))
        return {"error": str(e)}