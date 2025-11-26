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
from core.facets import FacetGenerator

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

# Initialize facet generator
facet_generator = FacetGenerator()


class SearchRequest(BaseModel):
    """Search request model"""
    query: str
    filters: Optional[Union[Dict[str, Any], List]] = None
    limit: int = 20
    offset: int = 0
    search_mode: str = "keyword"  # "keyword", "semantic", "hybrid"
    hybrid_weights: Optional[Dict[str, float]] = None  # Custom weights for hybrid search
    
    @validator('filters', pre=True)
    def normalize_filters(cls, v):
        """Convert filters array to dict if needed"""
        if isinstance(v, list):
            return {}
        return v or {}
    
    @validator('search_mode')
    def validate_search_mode(cls, v):
        """Validate search mode"""
        valid_modes = ["keyword", "semantic", "hybrid"]
        if v not in valid_modes:
            return "keyword"
        return v


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
    facets: Optional[Dict[str, Any]] = None  # Facets for filtering


async def _perform_keyword_search(
    query: str,
    merchant_id: int,
    limit: int,
    offset: int,
    filters: Optional[Dict],
    es_client,
    search_cache,
    include_facets: bool = True
) -> Dict[str, Any]:
    """Perform keyword search using Elasticsearch"""
    from core.query_builder import SearchQueryBuilder
    
    # Build aggregations for facets if requested
    aggregations = None
    if include_facets:
        facet_types = facet_generator.get_facets_for_context(query)
        aggregations = facet_generator.build_aggregations(facet_types)
    
    qb = SearchQueryBuilder()
    es_query = qb.build_product_search_query(
        merchant_id=merchant_id,
        query=query,
        filters=filters,
        sort=None,
        size=limit,
        from_=offset,
        aggregations=aggregations,
    )
    
    # Check cache
    cache_key = None
    cached = None
    if search_cache:
        cache_key = search_cache.generate_cache_key(
            "search",
            merchant_id,
            query,
            filters,
            limit=limit,
            offset=offset
        )
        cached = await search_cache.get_cached(cache_key)
    
    if cached is None:
        results = await es_client.search(
            merchant_id=merchant_id,
            query=es_query,
            from_=offset,
            size=limit,
        )
    else:
        results = cached
        hits = results.get("hits", {}).get("hits", [])
        if len(hits) > limit:
            results["hits"]["hits"] = hits[:limit]
    
    hits = results.get("hits", {}).get("hits", [])
    total = results.get("hits", {}).get("total", {}).get("value", 0)
    aggregations = results.get("aggregations", {})
    
    formatted = []
    for h in hits:
        src = h.get("_source", {})
        category_names = src.get("categories") or []
        category_ids = src.get("category_ids") or []

        # Ensure lists
        if not isinstance(category_names, list):
            category_names = [category_names]
        if not isinstance(category_ids, list):
            category_ids = [category_ids]

        categories_structured = []
        max_len = max(len(category_names), len(category_ids))
        for idx in range(max_len):
            cat_obj = {}
            if idx < len(category_ids) and category_ids[idx] not in (None, ""):
                cat_obj["id"] = str(category_ids[idx])
            if idx < len(category_names) and category_names[idx]:
                cat_obj["name"] = category_names[idx]
            if cat_obj:
                categories_structured.append(cat_obj)

        # If we only have names and no IDs, present names to maintain backwards compatibility
        categories_response = categories_structured if categories_structured else category_names

        formatted.append({
            "product_id": str(src.get("product_id", "")),
            "name": src.get("name", ""),
            "title": src.get("name", ""),
            "score": float(h.get("_score", 0.0)),
            "metadata": {
                "price": src.get("price"),
                "currency": src.get("currency"),
                "image_url": src.get("image_url"),
                "url": src.get("url"),
                "categories": categories_response,
                "category_names": category_names,
                "category_ids": category_ids,
                "sku": src.get("sku", ""),
                "description": src.get("description"),
                "short_description": src.get("short_description"),
                "attributes": src.get("attributes", {}),
            },
        })
    
    # Parse facets from aggregations
    facets_dict = None
    if aggregations:
        facets = facet_generator.parse_aggregations(aggregations, filters)
        facets_dict = {name: facet.to_dict() for name, facet in facets.items()}
    
    # Cache if not cached
    if cached is None and search_cache and cache_key:
        await search_cache.cache_result(cache_key, results, search_cache.SEARCH_TTL)
    
    return {
        "results": formatted,
        "total": total,
        "cache_status": "hit" if cached is not None else "miss",
        "facets": facets_dict
    }


async def _perform_semantic_search(
    query: str,
    merchant_id: int,
    limit: int,
    offset: int,
    filters: Optional[Dict],
    embedding_service,
    qdrant_manager,
    es_client=None,
    search_cache=None,
    include_facets: bool = True
) -> Dict[str, Any]:
    """Perform semantic search using Qdrant"""
    # Generate query embedding
    query_embedding = await embedding_service.generate_embedding(query)

    # Build filter conditions
    filter_conditions = {"merchant_id": merchant_id}
    if filters:
        if "category" in filters:
            filter_conditions["category_id"] = filters["category"]
        if "status" in filters:
            filter_conditions["status"] = filters["status"]
        if "in_stock" in filters:
            filter_conditions["is_in_stock"] = bool(filters["in_stock"])

    # Search in Qdrant
    search_results = await qdrant_manager.search(
        merchant_id=merchant_id,
        query_vector=query_embedding,
        limit=limit + offset,
        score_threshold=0.5,
        filter_conditions=filter_conditions if len(filter_conditions) > 1 else None
    )

    # Apply offset
    if offset > 0:
        search_results = search_results[offset:]

    search_results = search_results[:limit]

    # Generate facets by querying Elasticsearch (since Qdrant doesn't support aggregations)
    facets_dict = None
    if include_facets and es_client:
        try:
            facet_types = facet_generator.get_facets_for_context(query)
            aggregations = facet_generator.build_aggregations(facet_types)

            from core.query_builder import SearchQueryBuilder
            qb = SearchQueryBuilder()
            es_query = qb.build_product_search_query(
                merchant_id=merchant_id,
                query=query,  # Use semantic query for facet context
                filters=filters,
                sort=None,
                size=0,  # We only need aggregations, not results
                from_=0,
                aggregations=aggregations,
            )

            es_response = await es_client.search(
                index=f"products_{merchant_id}",
                body=es_query
            )

            facets_dict = facet_generator.parse_aggregations(
                es_response.get("aggregations", {}),
                filters
            )
        except Exception as e:
            logger.warning("Failed to generate facets for semantic search", error=str(e))

    # Format results
    formatted = []
    for result in search_results:
        formatted.append({
            "product_id": str(result.get("product_id", "")),
            "name": result.get("name", ""),
            "title": result.get("name", ""),
            "score": float(result.get("score", 0.0)),
            "metadata": {
                "sku": result.get("sku", ""),
                "price": result.get("price"),
                "special_price": result.get("special_price"),
                "image_url": result.get("image_url"),
                "url_key": result.get("url_key"),
                "category_name": result.get("category_name"),
                "is_in_stock": result.get("is_in_stock"),
                "description": result.get("description"),
                "short_description": result.get("short_description"),
                "attributes": result.get("attributes", {}),
            }
        })

    return {
        "results": formatted,
        "total": len(formatted),
        "facets": facets_dict
    }


@router.post("/")
async def search_products(search_request: SearchRequest, request: Request):
    """Product search with support for keyword, semantic, and hybrid modes."""
    start_time = time.time()
    merchant_id = get_merchant_id(request)
    correlation_id = getattr(request.state, "correlation_id", "")

    if not search_request.query or len(search_request.query) > 500:
        raise HTTPException(status_code=400, detail={"error": "Invalid query"})

    try:
        es_client = request.app.state.elasticsearch
        search_cache = getattr(request.app.state, "search_cache", None)
        embedding_service = getattr(request.app.state, "embedding_service", None)
        qdrant_manager = getattr(request.app.state, "qdrant_manager", None)
        
        # Determine search mode
        search_mode = search_request.search_mode
        
        # If hybrid/semantic requested but services not available, fallback to keyword
        if search_mode in ["semantic", "hybrid"] and (not embedding_service or not qdrant_manager):
            logger.warning("Semantic search requested but services not available, falling back to keyword")
            search_mode = "keyword"
        
        # Get hybrid weights
        keyword_weight = 0.7
        semantic_weight = 0.3
        if search_request.hybrid_weights:
            keyword_weight = search_request.hybrid_weights.get("keyword", 0.7)
            semantic_weight = search_request.hybrid_weights.get("semantic", 0.3)
        
        # Perform search based on mode
        facets_dict = None
        if search_mode == "keyword":
            result_data = await _perform_keyword_search(
                search_request.query,
                merchant_id,
                search_request.limit,
                search_request.offset,
                search_request.filters,
                es_client,
                search_cache,
                include_facets=True
            )
            results = result_data["results"]
            total = result_data["total"]
            cache_status = result_data.get("cache_status", "miss")
            facets_dict = result_data.get("facets")
            
        elif search_mode == "semantic":
            result_data = await _perform_semantic_search(
                search_request.query,
                merchant_id,
                search_request.limit,
                search_request.offset,
                search_request.filters,
                embedding_service,
                qdrant_manager,
                es_client,
                search_cache,
                include_facets=True
            )
            results = result_data["results"]
            total = result_data["total"]
            cache_status = "miss"  # Semantic search not cached yet
            facets_dict = result_data.get("facets")
            
        else:  # hybrid
            from core.hybrid_search import hybrid_search
            
            # Define search functions
            async def keyword_search_func(q, m_id, l, o, f):
                return await _perform_keyword_search(q, m_id, l, o, f, es_client, search_cache, include_facets=True)
            
            async def semantic_search_func(q, m_id, l, o, f):
                return await _perform_semantic_search(q, m_id, l, o, f, embedding_service, qdrant_manager, es_client, search_cache, include_facets=False)
            
            hybrid_result = await hybrid_search(
                keyword_search_func,
                semantic_search_func,
                search_request.query,
                merchant_id,
                search_request.limit,
                search_request.offset,
                search_request.filters,
                keyword_weight,
                semantic_weight
            )
            results = hybrid_result["results"]
            total = hybrid_result["merged_count"]
            cache_status = "miss"  # Hybrid search not cached yet
            # Get facets from keyword search (which includes aggregations)
            keyword_result = await _perform_keyword_search(
                search_request.query,
                merchant_id,
                1,  # Just need aggregations
                0,
                search_request.filters,
                es_client,
                search_cache,
                include_facets=True
            )
            facets_dict = keyword_result.get("facets")
        
        # Format results to SearchResult model
        formatted = []
        for r in results:
            formatted.append(
                SearchResult(
                    product_id=r["product_id"],
                    title=r.get("name", r.get("title", "")),
                    score=r.get("score", r.get("hybrid_score", 0.0)),
                    metadata=r.get("metadata", {})
                )
            )
        
        took = time.time() - start_time
        
        response = SearchResponse(
            results=formatted,
            total=total,
            query=search_request.query,
            took=took,
            facets=facets_dict,
        )
        response_dict = response.dict()
        response_dict["search_metadata"] = {
            "correlation_id": correlation_id,
            "cache_status": cache_status,
            "zero_results": total == 0,
            "merchant_id": merchant_id,
            "search_mode": search_mode,
        }
        
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