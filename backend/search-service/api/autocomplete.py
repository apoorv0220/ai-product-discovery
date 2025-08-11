"""
AI Product Discovery Suite - Search Service Autocomplete API

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, Query, Body
from pydantic import BaseModel
from typing import List, Optional
import structlog
import json
import os

logger = structlog.get_logger()
router = APIRouter()

# Use the same storage as the index API
PRODUCTS_FILE = "/tmp/products_index.json"

def load_products():
    """Load products from storage"""
    try:
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error("Error loading products for autocomplete", error=str(e))
    return {}

def get_autocomplete_suggestions(query: str, limit: int = 10):
    """Get real autocomplete suggestions from indexed products"""
    # Load current products
    products = load_products()
    
    # Check if we have any products
    if not products:
        logger.warning("No products found in index for autocomplete", query=query)
        return []
        
    if not query.strip():
        return []
    
    query_lower = query.lower()
    suggestions = []
    
    for product_id, product in products.items():
        product_name = product.get('name', '')
        if query_lower in product_name.lower():
            suggestions.append({
                'suggestion': product_name,
                'type': 'product',
                'count': 1,  # In a real system, this would be stock quantity or popularity
                'product_id': product.get('id'),
                'price': product.get('price'),
                'currency': product.get('currency', 'USD'),
                'image_url': product.get('image_url', ''),
                'url': product.get('url', '')
            })
    
    # Sort by relevance (how close the match is to the beginning of the name)
    def relevance_score(item):
        name = item['suggestion'].lower()
        pos = name.find(query_lower)
        return (-pos if pos >= 0 else 999, len(name))  # Prefer matches at start, then shorter names
    
    suggestions.sort(key=relevance_score)
    return suggestions[:limit]


class AutocompleteResult(BaseModel):
    """Autocomplete result model"""
    suggestion: str
    type: str  # 'product', 'category', 'brand'
    count: int


class AutocompleteResponse(BaseModel):
    """Autocomplete response model"""
    suggestions: List[AutocompleteResult]
    query: str

class AutocompleteRequest(BaseModel):
    """Autocomplete request model for POST requests"""
    q: Optional[str] = None
    query: Optional[str] = None  # Alternative field name for compatibility
    limit: Optional[int] = 10
    
    def get_query(self) -> str:
        """Get the query value from either q or query field"""
        return self.q or self.query or ""


async def _process_autocomplete_request(q: str, limit: int = 10):
    """Internal function to process autocomplete requests"""
    try:
        logger.info("Getting autocomplete suggestions", query=q)
        
        # Get real suggestions from indexed products
        suggestions_data = get_autocomplete_suggestions(q, limit)
        
        # Convert to response format
        suggestions = [
            AutocompleteResult(
                suggestion=item['suggestion'],
                type=item['type'],
                count=item['count']
            )
            for item in suggestions_data
        ]
        
        logger.info("Returning autocomplete suggestions", query=q, count=len(suggestions))
        
        return AutocompleteResponse(
            suggestions=suggestions,
            query=q
        )
    except Exception as e:
        logger.error("Error getting autocomplete suggestions", error=str(e))
        # Return empty suggestions instead of raising to prevent API errors
        return AutocompleteResponse(
            suggestions=[],
            query=q
        )

@router.get("/", response_model=AutocompleteResponse)
async def get_autocomplete(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, description="Number of suggestions"),
    request: Request = None
):
    """Get autocomplete suggestions via GET"""
    return await _process_autocomplete_request(q, limit)

@router.post("/", response_model=AutocompleteResponse)
async def post_autocomplete(
    autocomplete_request: AutocompleteRequest = Body(...),
    request: Request = None
):
    """Get autocomplete suggestions via POST with JSON body"""
    query = autocomplete_request.get_query()
    if not query:
        # Return empty suggestions if no query provided
        return AutocompleteResponse(suggestions=[], query="")
    return await _process_autocomplete_request(query, autocomplete_request.limit)

@router.post("/form", response_model=AutocompleteResponse)
async def post_autocomplete_form(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, description="Number of suggestions"),
    request: Request = None
):
    """Get autocomplete suggestions via POST with query parameters (for form submissions)"""
    return await _process_autocomplete_request(q, limit)