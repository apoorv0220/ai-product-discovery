"""
AI Product Discovery Suite - Semantic Search API

Semantic search endpoint using Qdrant vector similarity search.

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import structlog
import time

from shared.middleware.auth import get_merchant_id

logger = structlog.get_logger()
router = APIRouter()


class SemanticSearchRequest(BaseModel):
    """Semantic search request model"""
    query: str = Field(..., description="Search query")
    limit: int = Field(20, ge=1, le=100, description="Number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")


class SemanticSearchResult(BaseModel):
    """Semantic search result item"""
    product_id: str
    name: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class SemanticSearchResponse(BaseModel):
    """Semantic search response model"""
    results: List[SemanticSearchResult]
    total: int
    query: str
    took: float
    search_mode: str = "semantic"


@router.post("/")
async def semantic_search(semantic_request: SemanticSearchRequest, request: Request):
    """Semantic search using vector similarity in Qdrant"""
    start_time = time.time()
    merchant_id = get_merchant_id(request)
    correlation_id = getattr(request.state, "correlation_id", "")
    
    if not semantic_request.query or len(semantic_request.query) > 500:
        raise HTTPException(status_code=400, detail={"error": "Invalid query"})
    
    # Check if services are available
    embedding_service = getattr(request.app.state, "embedding_service", None)
    qdrant_manager = getattr(request.app.state, "qdrant_manager", None)
    
    if not embedding_service or not qdrant_manager:
        raise HTTPException(
            status_code=503,
            detail={"error": "Semantic search unavailable - embedding service or Qdrant not initialized"}
        )
    
    try:
        # Generate query embedding
        query_embedding = await embedding_service.generate_embedding(semantic_request.query)
        
        # Build filter conditions
        filter_conditions = {"merchant_id": merchant_id}
        
        if semantic_request.filters:
            # Add optional filters
            if "category" in semantic_request.filters:
                filter_conditions["category_id"] = semantic_request.filters["category"]
            if "status" in semantic_request.filters:
                filter_conditions["status"] = semantic_request.filters["status"]
            if "in_stock" in semantic_request.filters:
                filter_conditions["is_in_stock"] = bool(semantic_request.filters["in_stock"])
        
        # Search in Qdrant
        search_results = await qdrant_manager.search(
            merchant_id=merchant_id,
            query_vector=query_embedding,
            limit=semantic_request.limit + semantic_request.offset,  # Get more to account for offset
            score_threshold=semantic_request.min_score,
            filter_conditions=filter_conditions if len(filter_conditions) > 1 else None
        )
        
        # Apply offset
        if semantic_request.offset > 0:
            search_results = search_results[semantic_request.offset:]
        
        # Limit results
        search_results = search_results[:semantic_request.limit]
        
        # Format results
        formatted_results = []
        for result in search_results:
            formatted_results.append(
                SemanticSearchResult(
                    product_id=str(result.get("product_id", "")),
                    name=result.get("name", ""),
                    score=float(result.get("score", 0.0)),
                    metadata={
                        "sku": result.get("sku", ""),
                        "price": result.get("price"),
                        "special_price": result.get("special_price"),
                        "image_url": result.get("image_url"),
                        "url_key": result.get("url_key"),
                        "category_name": result.get("category_name"),
                        "is_in_stock": result.get("is_in_stock"),
                    }
                )
            )
        
        took = time.time() - start_time
        
        response = SemanticSearchResponse(
            results=formatted_results,
            total=len(formatted_results),  # Note: Qdrant doesn't return total count efficiently
            query=semantic_request.query,
            took=took,
            search_mode="semantic"
        )
        
        response_dict = response.dict()
        response_dict["search_metadata"] = {
            "correlation_id": correlation_id,
            "merchant_id": merchant_id,
            "min_score": semantic_request.min_score,
            "search_mode": "semantic"
        }
        
        logger.info("Semantic search completed",
                   merchant_id=merchant_id,
                   query=semantic_request.query,
                   results_count=len(formatted_results),
                   took_ms=took * 1000)
        
        return response_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Semantic search failed",
                    merchant_id=merchant_id,
                    query=semantic_request.query,
                    error=str(e))
        raise HTTPException(status_code=500, detail={"error": "Semantic search failed"})

