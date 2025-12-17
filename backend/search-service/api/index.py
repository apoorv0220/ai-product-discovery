"""
AI Product Discovery Suite - Search Service Indexing API

@category    Backend
@package     SearchService
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from fastapi import APIRouter, Request, HTTPException, status
from typing import Dict, Any, List, Optional
import structlog
import json
import os
from pathlib import Path

from shared.middleware.auth import get_merchant_id
from core.elasticsearch_client import ElasticsearchManager
from core.elasticsearch_mappings import get_product_index_settings, PRODUCT_INDEX_MAPPING
from core.synonym_loader import FileSynonymLoader
from core.indexer import ProductIndexer
from core.embedding_generator import EmbeddingGenerator
from schemas.product import calculate_data_quality, DataQualityMetrics
from schemas.index import IndexRequest, IndexResponse, IndexStatusResponse, EnsureIndexResponse, DeleteProductResponse

logger = structlog.get_logger()
router = APIRouter()

SYNONYMS_PATH = Path(os.path.dirname(os.path.dirname(__file__))) / "config" / "synonyms.txt"

@router.get("/status")
async def get_index_status(request: Request):
    """Get status of the search index for current merchant."""
    try:
        merchant_id = get_merchant_id(request)
        es: ElasticsearchManager = request.app.state.elasticsearch
        index_name = es.get_index_name(merchant_id)
        exists = await es._execute_with_retry(es.client.indices.exists, index=index_name) if es.client else False
        stats = await es.get_index_stats(merchant_id) if exists else {}
        return {"index": index_name, "exists": bool(exists), "stats": stats}
    except HTTPException:
        raise
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




@router.post("/products", response_model=IndexResponse)
async def index_products(index_request: IndexRequest, request: Request):
    """Index products for search (Elasticsearch + Qdrant embeddings)"""
    try:
        merchant_id = get_merchant_id(request)
        
        # DIAGNOSTIC: Log received product data
        logger.info("="*60)
        logger.info("DIAGNOSTIC: Index products endpoint called",
                   merchant_id=merchant_id,
                   product_count=len(index_request.products))
        
        if index_request.products:
            # Log first product's fields for inspection
            first_product = index_request.products[0]
            logger.info("DIAGNOSTIC: First product fields",
                       product_id=first_product.get('id'),
                       sku=first_product.get('sku'),
                       has_name=bool(first_product.get('name')),
                       has_description=bool(first_product.get('description')),
                       has_price='price' in first_product,
                       price_value=first_product.get('price'),
                       has_image='image_url' in first_product,
                       image_url=first_product.get('image_url', '')[:100] if first_product.get('image_url') else None,
                       has_categories='categories' in first_product,
                       categories=first_product.get('categories'),
                       has_stock='stock' in first_product,
                       stock_data=first_product.get('stock'),
                       all_fields=list(first_product.keys()))
            
            # Log data completeness statistics
            products_with_price = sum(1 for p in index_request.products if p.get('price', 0) > 0)
            products_with_image = sum(1 for p in index_request.products if p.get('image_url'))
            products_with_categories = sum(1 for p in index_request.products if p.get('categories'))
            
            logger.info("DIAGNOSTIC: Data completeness",
                       total_products=len(index_request.products),
                       with_price=products_with_price,
                       with_image=products_with_image,
                       with_categories=products_with_categories,
                       completeness_price=f"{products_with_price/len(index_request.products)*100:.1f}%",
                       completeness_image=f"{products_with_image/len(index_request.products)*100:.1f}%",
                       completeness_categories=f"{products_with_categories/len(index_request.products)*100:.1f}%")
        logger.info("="*60)
        
        await _ensure_index(request, merchant_id)
        es: ElasticsearchManager = request.app.state.elasticsearch
        indexer = ProductIndexer(es)
        
        # Index to Elasticsearch
        result = await indexer.index_products_bulk(merchant_id, index_request.products)

        # Generate and store embeddings in Qdrant (if services are available)
        embedding_result = None
        embedding_service = getattr(request.app.state, "embedding_service", None)
        qdrant_manager = getattr(request.app.state, "qdrant_manager", None)
        
        if embedding_service and qdrant_manager:
            try:
                embedding_generator = EmbeddingGenerator(embedding_service, qdrant_manager)
                embedding_result = await embedding_generator.generate_and_store_embeddings(
                    merchant_id,
                    index_request.products
                )
                logger.info("Generated embeddings for products",
                           merchant_id=merchant_id,
                           success=embedding_result["success_count"],
                           failed=embedding_result["failure_count"])
            except Exception as e:
                logger.warning("Failed to generate embeddings",
                             merchant_id=merchant_id,
                             error=str(e))
                # Don't fail the entire indexing if embeddings fail

        # Invalidate cache for this merchant
        cache = getattr(request.app.state, "search_cache", None)
        if cache:
            await cache.invalidate_merchant_cache(merchant_id)

        # Calculate data quality metrics
        data_quality = calculate_data_quality(index_request.products)
        
        logger.info("Indexed products to Elasticsearch",
                   merchant_id=merchant_id,
                   success=result.success_count,
                   failed=result.failure_count,
                   data_quality_score=data_quality.completeness_score)

        message = "Indexed successfully"
        if result.failure_count > 0:
            error_details = []
            if result.errors:
                # Extract error reasons from Elasticsearch errors
                for err in result.errors[:3]:  # Get first 3 errors
                    if isinstance(err, dict):
                        error_reason = None
                        # Try to extract Elasticsearch error reason
                        if 'index' in err and 'error' in err['index']:
                            es_error = err['index']['error']
                            if isinstance(es_error, dict):
                                error_reason = es_error.get('reason', str(es_error))
                            else:
                                error_reason = str(es_error)
                        elif 'error' in err:
                            error_reason = str(err['error'])
                        elif 'exception' in err:
                            error_reason = err['exception']
                        
                        if error_reason:
                            error_details.append(error_reason[:200])  # Truncate long errors
            if error_details:
                message = f"Indexed with {result.failure_count} errors: {', '.join(error_details)}"
            else:
                message = f"Indexed with {result.failure_count} errors"
        if embedding_result and embedding_result["failure_count"] > 0:
            message += f" (embeddings: {embedding_result['failure_count']} errors)"
        
        # Add data quality warning if completeness is low
        if data_quality.completeness_score < 80:
            message += f" - WARNING: Data quality is {data_quality.completeness_score:.1f}%"

        return IndexResponse(
            success=result.failure_count == 0,
            indexed_count=result.success_count,
            message=message,
            data_quality=data_quality
        )
    except HTTPException:
        raise
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
        merchant_id = get_merchant_id(request)
        es: ElasticsearchManager = request.app.state.elasticsearch
        indexer = ProductIndexer(es)
        ok = await indexer.delete_product(merchant_id, product_id)
        cache = getattr(request.app.state, "search_cache", None)
        if cache:
            await cache.invalidate_merchant_cache(merchant_id)
        return {"success": ok, "message": ("Deleted" if ok else "Not found or failed")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting product from index", error=str(e))
        return {"success": False, "message": str(e)}


@router.post("/ensure")
async def ensure_index(request: Request):
    """Ensure the ES index exists for current merchant (creates if missing) with synonyms loaded."""
    try:
        merchant_id = get_merchant_id(request)
        await _ensure_index(request, merchant_id)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to ensure index", error=str(e))
        return {"success": False, "error": str(e)}