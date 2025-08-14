"""
AI Product Discovery Suite - Search Service API

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from pydantic import validator
import structlog

# Import updated schemas
try:
    from ..schemas.search_updated import (
        SearchResultItem,
        SearchMetadata,
        SearchResponse as UpdatedSearchResponse,
        SearchRequest as UpdatedSearchRequest,
        SearchCorrection,
        SearchErrorResponse
    )
    USE_UPDATED_SCHEMAS = True
except ImportError:
    # Fallback to existing schemas if new ones aren't available
    USE_UPDATED_SCHEMAS = False

logger = structlog.get_logger()

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request model"""
    query: str
    filters: Optional[Union[Dict[str, Any], List]] = None
    limit: int = 20
    offset: int = 0
    
    @validator('filters', pre=True)
    def normalize_filters(cls, v):
        """Convert filters array to dict if needed"""
        if isinstance(v, list):
            return {}
        return v or {}


class SearchResult(BaseModel):
    """Search result model"""
    product_id: str
    title: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response model"""
    results: List[SearchResult]
    total: int
    query: str
    took: float


@router.post("/")
async def search_products(search_request: SearchRequest, request: Request):
    """Advanced semantic search with NLP processing"""
    import time
    start_time = time.time()
    
    logger.info("Processing semantic search request", query=search_request.query)
    
    try:
        # Use OpenAI-enhanced search
        import sys
        import os
        # Add the search-service directory to Python path
        search_service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, search_service_dir)
        from core.openai_nlp import process_query_with_openai
        from ..api.index import search_products as search_indexed_products
        
        # Process query with OpenAI for better understanding
        intent, corrections = await process_query_with_openai(search_request.query)
        
        # Use corrected/processed query for search
        processed_query = intent.processed_query if intent else search_request.query
        
        # Search indexed products (using the function from index.py)
        raw_results = search_indexed_products(
            query=processed_query,
            limit=search_request.limit
        )
        
        # Convert to SearchResult objects
        results = []
        for product in raw_results:
            results.append(SearchResult(
                product_id=str(product.get('id', '')),
                title=product.get('name', ''),
                score=1.0,  # Default score, could be enhanced with relevance scoring
                metadata={
                    'price': product.get('price', 0),
                    'currency': product.get('currency', 'USD'),
                    'image_url': product.get('image_url', ''),
                    'url': product.get('url', ''),
                    'categories': product.get('categories', []),
                    'sku': product.get('sku', ''),
                    'description': product.get('description', '')
                }
            ))
        
        took = time.time() - start_time
        
        logger.info("Semantic search completed", 
                   query=search_request.query,
                   intent=intent.intent_type,
                   results=len(results),
                   corrections=len(corrections),
                   took=took)
        
        # Enhanced response with NLP insights
        response = SearchResponse(
            results=results,
            total=len(results),
            query=search_request.query,
            took=took
        )
        
        # Add NLP metadata in format Magento expects
        search_metadata = {
            'nlp_enabled': True,
            'semantic_search': True,
            'typo_corrected': len(corrections) > 0,
            'ai_enhanced': True,
            'intent_type': intent.intent_type,
            'processing_time': took,
            'corrections': [
                {
                    'original': c.original,
                    'corrected': c.corrected,
                    'confidence': c.confidence,
                    'type': c.correction_type
                } for c in corrections
            ] if corrections else []
        }
        
        # Add search_metadata to response dict
        response_dict = response.dict()
        response_dict['search_metadata'] = search_metadata
        
        return response_dict
        
    except Exception as e:
        logger.warning("Semantic search failed, falling back to basic search", error=str(e))
        
        # Fallback to basic search
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(__file__))
            from index import search_products as search_indexed_products
            
            # Search real products using basic method
            matching_products = search_indexed_products(
                search_request.query, 
                search_request.limit
            )
            
            # Convert to SearchResult format
            results = []
            for i, product in enumerate(matching_products):
                results.append(SearchResult(
                    product_id=str(product.get('id', product.get('sku', f'unknown_{i}'))),
                    title=product.get('name', 'Unknown Product'),
                    score=1.0 - (i * 0.1),  # Simple scoring based on position
                    metadata={
                        "price": product.get('price'),
                        "currency": product.get('currency', 'USD'),
                        "image_url": product.get('image_url', ''),
                        "url": product.get('url', ''),
                        "sku": product.get('sku', ''),
                        "categories": product.get('categories', []),
                        "fallback_search": True
                    }
                ))
            
            took = time.time() - start_time
            
            logger.info("Fallback search completed", query=search_request.query, results=len(results), took=took)
            
            response = SearchResponse(
                results=results,
                total=len(results),
                query=search_request.query,
                took=took
            )
            
            # Add fallback metadata in Magento-compatible format
            response_dict = response.dict()
            response_dict['search_metadata'] = {
                'nlp_enabled': False,
                'semantic_search': False,
                'typo_corrected': False,
                'ai_enhanced': False,
                'intent_type': 'fallback',
                'processing_time': took,
                'corrections': [],
                'fallback_used': True
            }
            
            return response_dict
            
        except Exception as fallback_error:
            logger.error("Both semantic and fallback search failed", 
                        error=str(fallback_error), query=search_request.query)
            
            response = SearchResponse(
                results=[],
                total=0,
                query=search_request.query,
                took=time.time() - start_time
            )
            
            # Add error metadata
            response_dict = response.dict()
            response_dict['search_metadata'] = {
                'nlp_enabled': False,
                'semantic_search': False,
                'typo_corrected': False,
                'ai_enhanced': False,
                'intent_type': 'error',
                'processing_time': time.time() - start_time,
                'corrections': [],
                'error': str(fallback_error)
            }
            
            return response_dict


@router.get("/")
async def search_products_get(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    request: Request = None
):
    """Search for products via GET request"""
    search_request = SearchRequest(query=q, limit=limit, offset=offset)
    return await search_products(search_request, request)