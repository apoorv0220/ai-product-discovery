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

# Import schemas with personalization support
from schemas.search import (
    SearchResultItem,
    SearchMetadata,
    SearchResponse,
    SearchRequest,
    SearchCorrection,
    SearchErrorResponse
)
from core.personalized_search import personalized_search_engine

logger = structlog.get_logger()

router = APIRouter()

# Initialize facet generator
facet_generator = FacetGenerator()


# Use SearchRequest from schemas (API-first approach)


# Use SearchResultItem and SearchResponse from schemas (API-first approach)


def _calibrate_semantic_scores_by_attributes(
    results: List[Dict[str, Any]],
    query_attributes: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Calibrate semantic search scores based on attribute coverage (Hybrid+ Scoring Tweaks).

    For semantic search, we boost products that have attributes mentioned in the query.
    This provides category-based intelligence even when relying on vector similarity.
    """
    attributes_list = query_attributes.get("attributes", [])
    query = query_attributes.get("query", "").lower()

    if not attributes_list and not query:
        return results

    calibrated_results = []

    for result in results:
        score_multiplier = 1.0
        attribute_coverage = 0

        # Get product attributes
        attributes = result.get("metadata", {}).get("attributes", {})

        # Check coverage for each query attribute
        for attr in attributes_list:
            if attr.lower() in ["color", "colour"]:
                if attributes.get("color"):
                    attribute_coverage += 1
                    score_multiplier *= 1.3  # Stronger boost for semantic search
            elif attr.lower() in ["size", "sizing"]:
                if attributes.get("size"):
                    attribute_coverage += 1
                    score_multiplier *= 1.2
            elif attr.lower() in ["material", "fabric"]:
                if attributes.get("material"):
                    attribute_coverage += 1
                    score_multiplier *= 1.2
            elif attr.lower() in ["brand", "manufacturer"]:
                if result.get("metadata", {}).get("brand") or attributes.get("manufacturer"):
                    attribute_coverage += 1
                    score_multiplier *= 1.4  # Brand is very important for semantic search

        # Category-based boosting for semantic search
        category_names_list = result.get("metadata", {}).get("category_names", [])
        if isinstance(category_names_list, str):
            category_names_list = [category_names_list]
        category_names_str = " ".join(str(cat).lower() for cat in category_names_list)
        product_name = str(result.get("name", "")).lower()

        # Boost based on product type matching query intent
        if "top" in query or "shirt" in query or "tee" in query:
            if "tee" in category_names_str or "top" in product_name or "shirt" in product_name:
                score_multiplier *= 2.0  # Strong boost for tops when looking for tops
            elif "pant" in category_names_str or "pant" in product_name:
                score_multiplier *= 0.5  # Reduce pants when looking for tops

        if "pant" in query or "trouser" in query:
            if "pant" in category_names_str or "pant" in product_name:
                score_multiplier *= 2.0  # Strong boost for pants when looking for pants
            elif "tee" in category_names_str or "top" in product_name or "shirt" in product_name:
                score_multiplier *= 0.5  # Reduce tops when looking for pants

        # Apply score calibration
        if score_multiplier > 1.0:
            result["score"] *= score_multiplier
            result["attribute_coverage"] = attribute_coverage
            result["semantic_boost"] = score_multiplier

        calibrated_results.append(result)

    # Re-sort by calibrated scores
    calibrated_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    return calibrated_results


def _extract_query_attributes(query: str) -> Dict[str, Any]:
    """
    Extract attributes mentioned in query for score calibration (Hybrid+ Scoring Tweaks).

    This enables boosting products that have the attributes mentioned in the query.
    Domain-agnostic - works for any product type.

    Args:
        query: Search query string

    Returns:
        Dict with 'attributes' list and 'query' string for category matching
    """
    if not query:
        return {"attributes": [], "query": ""}

    query_lower = query.lower()
    attributes = []

    # Generic attribute keywords that work across all domains
    attribute_keywords = {
        "color": ["color", "colour", "colored", "coloured"],
        "size": ["size", "sized", "sizing"],
        "material": ["material", "fabric", "made of", "cotton", "polyester", "wool", "nylon"],
        "brand": ["brand", "branded", "manufacturer"]
    }

    for attr, keywords in attribute_keywords.items():
        for keyword in keywords:
            if keyword in query_lower:
                attributes.append(attr)
                break  # Only add each attribute once

    return {"attributes": attributes, "query": query}


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
    include_facets: bool = True,
    query_attributes: Optional[Dict[str, Any]] = None
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
        score_threshold=0.35,
        filter_conditions=filter_conditions if len(filter_conditions) > 1 else None
    )
    
    # Apply offset
    if offset > 0:
        search_results = search_results[offset:]
    
    search_results = search_results[:limit]

    # Fetch full metadata for semantic results from Elasticsearch
    if es_client and search_results:
        product_ids = [str(r.get("product_id")) for r in search_results if r.get("product_id")]
        if product_ids:
            es_metadata_query = {
                "query": {"terms": {"product_id": product_ids}},
                "_source": ["categories", "category_ids", "attributes", "brand", "name", "description", "short_description", "price", "special_price", "image_url", "url"]
            }
            try:
                es_metadata_response = await es_client.search(
                    index=f"discovery_products_m{merchant_id}",
                    body=es_metadata_query,
                    size=len(product_ids)
                )
                es_metadata_map = {str(h["_source"]["product_id"]): h["_source"] for h in es_metadata_response["hits"]["hits"]}

                # Merge full metadata into semantic results
                for i, result in enumerate(search_results):
                    full_metadata = es_metadata_map.get(str(result.get("product_id")))
                    if full_metadata:
                        # Update existing metadata with more comprehensive data from ES
                        # Note: ES stores categories as "categories" field (which contains category names)
                        result["metadata"].update({
                            "categories": full_metadata.get("categories", []),  # This contains category names
                            "category_names": full_metadata.get("categories", []),  # Duplicate for compatibility
                            "category_ids": full_metadata.get("category_ids", []),
                            "attributes": full_metadata.get("attributes", {}),
                            "brand": full_metadata.get("brand"),
                            "description": full_metadata.get("description"),
                            "short_description": full_metadata.get("short_description"),
                            "price": full_metadata.get("price"),
                            "special_price": full_metadata.get("special_price"),
                            "image_url": full_metadata.get("image_url"),
                            "url": full_metadata.get("url"),
                        })
            except Exception as e:
                logger.warning("Failed to fetch full metadata for semantic results from ES", error=str(e))

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
                merchant_id=merchant_id,
                query=es_query,
                from_=0,
                size=0
            )

            facets_dict = facet_generator.parse_aggregations(
                es_response.get("aggregations", {}),
                filters
            )
        except Exception as e:
            logger.warning("Failed to generate facets for semantic search", error=str(e))

    # Get full product data from Elasticsearch for metadata enrichment
    product_ids = [str(result.get("product_id", "")) for result in search_results]
    enriched_metadata = {}

    if es_client and product_ids:
        try:
            # Query Elasticsearch to get full metadata for these products
            es_query = {
                "query": {
                    "terms": {
                        "product_id": product_ids
                    }
                },
                "size": len(product_ids),
                "_source": ["product_id", "categories", "category_ids", "attributes", "brand"]
            }

            es_response = await es_client.search(
                merchant_id=merchant_id,
                query=es_query,
                from_=0,
                size=len(product_ids)
            )

            # Build lookup table
            for hit in es_response.get("hits", {}).get("hits", []):
                src = hit.get("_source", {})
                pid = str(src.get("product_id", ""))
                enriched_metadata[pid] = {
                    "categories": src.get("categories", []),
                    "category_names": src.get("categories", []),  # categories field contains the names
                    "category_ids": src.get("category_ids", []),
                    "attributes": src.get("attributes", {}),
                    "brand": src.get("brand")
                }

        except Exception as e:
            logger.warning("Failed to enrich semantic search results with metadata", error=str(e))

    # Format results with enriched metadata
    formatted = []
    for result in search_results:
        pid = str(result.get("product_id", ""))
        enriched = enriched_metadata.get(pid, {})

        formatted.append({
            "product_id": pid,
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
                "categories": enriched.get("categories", []),
                "category_names": enriched.get("category_names", []),
                "category_ids": enriched.get("category_ids", []),
                "is_in_stock": result.get("is_in_stock"),
                "description": result.get("description"),
                "short_description": result.get("short_description"),
                "attributes": enriched.get("attributes", result.get("attributes", {})),
                "brand": enriched.get("brand")
            }
        })
    
    # Apply attribute-based score calibration (Hybrid+ Scoring Tweaks)
    if query_attributes:
        formatted = _calibrate_semantic_scores_by_attributes(formatted, query_attributes)

    return {
        "results": formatted,
        "total": len(formatted),
        "facets": facets_dict
    }


@router.post("/")
async def search_products(search_request: SearchRequest, request: Request):
    """Product search with personalization support using API-first architecture."""
    start_time = time.time()
    personalization_start_time = None
    merchant_id = get_merchant_id(request)
    correlation_id = getattr(request.state, "correlation_id", "")

    if not search_request.query or len(search_request.query) > 500:
        raise HTTPException(status_code=400, detail={"error": "Invalid query"})

    try:
        es_client = request.app.state.elasticsearch
        search_cache = getattr(request.app.state, "search_cache", None)
        embedding_service = getattr(request.app.state, "embedding_service", None)
        qdrant_manager = getattr(request.app.state, "qdrant_manager", None)

        # Initialize personalization metadata
        personalization_applied = False
        personalization_profile_used = False
        personalization_processing_time = 0.0  # Initialize to avoid NameError
        user_id_used = search_request.user_id
        session_id_used = search_request.session_id

        # Use hybrid search by default (best results)
        # If semantic services not available, fallback to keyword
        search_mode = "hybrid"
        if not embedding_service or not qdrant_manager:
            logger.warning("Semantic search services not available, falling back to keyword search")
            search_mode = "keyword"

        # Default hybrid weights
        keyword_weight = 0.7
        semantic_weight = 0.3

        # Extract query attributes for score calibration (Hybrid+ Scoring Tweaks)
        query_attributes = _extract_query_attributes(search_request.query)

        # Perform search based on available services
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
                include_facets=True,
                query_attributes=query_attributes
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
                return await _perform_semantic_search(q, m_id, l, o, f, embedding_service, qdrant_manager, es_client, search_cache, include_facets=False, query_attributes=query_attributes)
            
            hybrid_result = await hybrid_search(
                keyword_search_func,
                semantic_search_func,
                search_request.query,
                merchant_id,
                search_request.limit,
                search_request.offset,
                search_request.filters,
                keyword_weight,
                semantic_weight,
                query_attributes
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

        # Format results to SearchResultItem model
        formatted = []
        for r in results:
            formatted.append(
                SearchResultItem(
                    product_id=str(r["product_id"]),
                    title=r.get("name", r.get("title", "")),
                    score=r.get("hybrid_score", r.get("score", 0.0)),
                    metadata=r.get("metadata", {})
                )
            )

        # Apply personalization if enabled and user context provided
        if (search_request.personalize and
            (search_request.user_id or search_request.session_id)):
            personalization_start_time = time.time()
            try:
                logger.info("Applying personalization",
                          user_id=search_request.user_id,
                          session_id=search_request.session_id,
                          result_count=len(formatted))

                # Apply personalized ranking
                formatted = await personalized_search_engine.apply_personalized_ranking(
                    formatted,
                    user_id=search_request.user_id,
                    session_id=search_request.session_id,
                    user_context=search_request.user_context
                )

                personalization_applied = True
                personalization_profile_used = len(formatted) > 0

                personalization_processing_time = time.time() - personalization_start_time
                logger.info("Personalization applied successfully",
                          processing_time=personalization_processing_time,
                          profile_used=personalization_profile_used)

            except Exception as e:
                logger.warning("Personalization failed, continuing with original results",
                            error=str(e))
                personalization_processing_time = time.time() - (personalization_start_time or time.time())
        
        took = time.time() - start_time

        # Create search metadata with personalization info
        search_metadata = SearchMetadata(
            nlp_enabled=True,  # Assuming NLP is enabled
            semantic_search=(search_mode in ["semantic", "hybrid"]),
            personalization_applied=personalization_applied,
            user_id=user_id_used,
            session_id=session_id_used,
            personalization_profile_used=personalization_profile_used,
            personalization_processing_time=personalization_processing_time or 0.0,
            processing_time=took
        )

        # Create response using updated schema
        response = SearchResponse(
            results=formatted,
            total=total,
            query=search_request.query,
            took=took,
            facets=facets_dict,
            search_metadata=search_metadata
        )

        response_dict = response.dict()

        # Add additional metadata for backward compatibility
        response_dict["search_metadata"].update({
            "correlation_id": correlation_id,
            "cache_status": cache_status,
            "zero_results": total == 0,
            "merchant_id": merchant_id,
        })

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