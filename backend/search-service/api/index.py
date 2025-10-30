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

from core.elasticsearch_client import ElasticsearchManager
from core.elasticsearch_mappings import get_product_index_settings, PRODUCT_INDEX_MAPPING
from core.synonym_loader import FileSynonymLoader
from core.indexer import ProductIndexer

logger = structlog.get_logger()
router = APIRouter()

SYNONYMS_PATH = Path(os.path.dirname(os.path.dirname(__file__))) / "config" / "synonyms.txt"

@router.get("/status")
async def get_index_status(request: Request):
    """Get status of the search index for current merchant."""
    try:
        es: ElasticsearchManager = request.app.state.elasticsearch
        merchant_id = getattr(request.state, "merchant_id", None)
        index_name = es.get_index_name(merchant_id)
        exists = await es._execute_with_retry(es.client.indices.exists, index=index_name) if es.client else False
        stats = await es.get_index_stats(merchant_id) if exists else {}
        return {"index": index_name, "exists": bool(exists), "stats": stats}
    except Exception as e:
        logger.error("Failed to get index status", error=str(e))
        return {"error": str(e)}

def _get_synonyms() -> List[str]:
    loader = FileSynonymLoader(SYNONYMS_PATH)
    return loader.load_synonyms()

async def _ensure_index(request: Request, merchant_id: int) -> None:
    es: ElasticsearchManager = request.app.state.elasticsearch
    synonyms = _get_synonyms()
    settings = get_product_index_settings(synonyms)
    await es.ensure_index(merchant_id, settings, PRODUCT_INDEX_MAPPING)


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
        merchant_id = getattr(request.state, "merchant_id", None)
        await _ensure_index(request, merchant_id)
        es: ElasticsearchManager = request.app.state.elasticsearch
        indexer = ProductIndexer(es)
        result = await indexer.index_products_bulk(merchant_id, index_request.products)

        # Invalidate cache for this merchant
        cache = getattr(request.app.state, "search_cache", None)
        if cache:
            await cache.invalidate_merchant_cache(merchant_id)

        logger.info("Indexed products to Elasticsearch", merchant_id=merchant_id, success=result.success_count, failed=result.failure_count)

        return IndexResponse(
            success=result.failure_count == 0,
            indexed_count=result.success_count,
            message=("Indexed successfully" if result.failure_count == 0 else f"Indexed with {result.failure_count} errors"),
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
        merchant_id = getattr(request.state, "merchant_id", None)
        es: ElasticsearchManager = request.app.state.elasticsearch
        indexer = ProductIndexer(es)
        ok = await indexer.delete_product(merchant_id, product_id)
        cache = getattr(request.app.state, "search_cache", None)
        if cache:
            await cache.invalidate_merchant_cache(merchant_id)
        return {"success": ok, "message": ("Deleted" if ok else "Not found or failed")}
    except Exception as e:
        logger.error("Error deleting product from index", error=str(e))
        return {"success": False, "message": str(e)}


@router.post("/ensure")
async def ensure_index(request: Request):
    """Ensure the ES index exists for current merchant (creates if missing) with synonyms loaded."""
    try:
        merchant_id = getattr(request.state, "merchant_id", None)
        await _ensure_index(request, merchant_id)
        return {"success": True}
    except Exception as e:
        logger.error("Failed to ensure index", error=str(e))
        return {"success": False, "error": str(e)}