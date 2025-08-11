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
from typing import List, Optional, Dict, Any
import structlog

logger = structlog.get_logger()

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request model"""
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20
    offset: int = 0


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


@router.post("/", response_model=SearchResponse)
async def search_products(search_request: SearchRequest, request: Request):
    """Advanced semantic search with NLP processing"""
    import time
    start_time = time.time()
    
    logger.info("Processing semantic search request", query=search_request.query)
    
    try:
        # Try semantic search first
        from ..core.nlp_processor import semantic_search_engine
        
        # Perform semantic search with NLP
        search_results = await semantic_search_engine.search(
            query=search_request.query,
            limit=search_request.limit,
            offset=search_request.offset
        )
        
        # Convert to SearchResult objects
        results = []
        for result in search_results['results']:
            results.append(SearchResult(
                product_id=result['product_id'],
                title=result['title'],
                score=result['score'],
                metadata=result['metadata']
            ))
        
        took = time.time() - start_time
        
        logger.info("Semantic search completed", 
                   query=search_request.query,
                   intent=search_results.get('intent', {}).get('type'),
                   results=len(results),
                   corrections=len(search_results.get('corrections', [])),
                   took=took)
        
        # Enhanced response with NLP insights
        response = SearchResponse(
            results=results,
            total=search_results['total'],
            query=search_request.query,
            took=took
        )
        
        # Add NLP metadata to response
        response.__dict__['nlp_insights'] = {
            'processed_query': search_results.get('processed_query'),
            'intent': search_results.get('intent'),
            'corrections': search_results.get('corrections'),
            'semantic_search': True
        }
        
        return response
        
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
            
            # Add fallback metadata
            response.__dict__['nlp_insights'] = {
                'processed_query': search_request.query,
                'semantic_search': False,
                'fallback_used': True
            }
            
            return response
            
        except Exception as fallback_error:
            logger.error("Both semantic and fallback search failed", 
                        error=str(fallback_error), query=search_request.query)
            return SearchResponse(
                results=[],
                total=0,
                query=search_request.query,
                took=time.time() - start_time
            )


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