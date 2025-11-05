"""
AI Product Discovery Suite - Search Service API

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from pydantic import validator
import structlog
import time

from shared.middleware.auth import get_merchant_id

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
    """Elasticsearch-powered product search with observability."""
    start_time = time.time()
    merchant_id = get_merchant_id(request)
    correlation_id = getattr(request.state, "correlation_id", "")

    if not search_request.query or len(search_request.query) > 500:
        raise HTTPException(status_code=400, detail={"error": "Invalid query"})

    try:
        from core.query_builder import SearchQueryBuilder
        es_client = request.app.state.elasticsearch
        search_cache = getattr(request.app.state, "search_cache", None)

        qb = SearchQueryBuilder()
        es_query = qb.build_product_search_query(
            merchant_id=merchant_id,
            query=search_request.query,
            filters=search_request.filters,
            sort=None,
            size=search_request.limit,
            from_=search_request.offset,
        )

        # Cache key (include pagination parameters)
        cache_key = None
        cached = None
        if search_cache:
            cache_key = search_cache.generate_cache_key(
                "search", 
                merchant_id, 
                search_request.query, 
                search_request.filters,
                limit=search_request.limit,
                offset=search_request.offset
            )
            cached = await search_cache.get_cached(cache_key)

        if cached is None:
            results = await es_client.search(
            merchant_id=merchant_id,
            query=es_query,
            from_=search_request.offset,
            size=search_request.limit,
        )
        else:
            # Use cached results, but ensure we slice to requested limit if needed
            results = cached
            # Ensure cached results match requested pagination (safety check)
            hits = results.get("hits", {}).get("hits", [])
            if len(hits) > search_request.limit:
                results["hits"]["hits"] = hits[:search_request.limit]

        hits = results.get("hits", {}).get("hits", [])
        total = results.get("hits", {}).get("total", {}).get("value", 0)
        took = time.time() - start_time

        formatted = []
        for h in hits:
            src = h.get("_source", {})
            formatted.append(
                SearchResult(
                    product_id=str(src.get("product_id", "")),
                    title=src.get("name", ""),
                    score=float(h.get("_score", 0.0)),
                    metadata={
                        "price": src.get("price"),
                        "currency": src.get("currency"),
                        "image_url": src.get("image_url"),
                        "url": src.get("url"),
                        "categories": src.get("categories", []),
                        "sku": src.get("sku", ""),
                    },
                )
            )

        response = SearchResponse(
            results=formatted,
            total=total,
            query=search_request.query,
            took=took,
        )
        response_dict = response.dict()
        response_dict["search_metadata"] = {
            "correlation_id": correlation_id,
            "cache_status": "hit" if cached is not None else "miss",
            "zero_results": total == 0,
            "merchant_id": merchant_id,
        }
        if cached is None and search_cache and cache_key:
            await search_cache.cache_result(cache_key, results, search_cache.SEARCH_TTL)
        return response_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Search failed"})


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