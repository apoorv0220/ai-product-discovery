"""
Quick verification script for Phase 2 implementation.

Checks:
- Service health
- Qdrant connection and embeddings
- Elasticsearch connection
- Basic search functionality

Usage:
    python scripts/verify_phase2.py [--merchant-id MERCHANT_ID]

@category    Scripts
@package     SearchService
@license     MIT License
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
import httpx

# Add backend directories to path (same pattern as verify_indexed_products.py)
script_dir = Path(__file__).parent
backend_dir = script_dir.parent / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "search-service"))

# Load .env file if exists
try:
    from dotenv import load_dotenv
    env_path = script_dir.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from shared.config.settings import SearchServiceSettings
from core.elasticsearch_client import ElasticsearchManager
from core.qdrant_client import QdrantManager
from shared.config.qdrant import QDRANT_CONFIG
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(colors=False)
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_check(name: str, passed: bool, details: str = ""):
    """Print check result"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status}: {name}")
    if details:
        print(f"   {details}")


async def check_service_health(port: int = 7099) -> bool:
    """Check if search service is healthy"""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Try with trailing slash first (FastAPI redirects /health to /health/)
            response = await client.get(f"http://localhost:{port}/health/", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
    except Exception as e:
        logger.error("Service health check failed", error=str(e))
    return False


async def check_qdrant(merchant_id: int) -> dict:
    """Check Qdrant connection and collection"""
    result = {
        "connected": False,
        "collection_exists": False,
        "vectors_count": 0,
        "points_count": 0
    }
    
    try:
        qm = QdrantManager(url=QDRANT_CONFIG["url"], api_key=QDRANT_CONFIG["api_key"])
        await qm.initialize()
        result["connected"] = True
        
        # Try to get collection info via client (may fail due to version mismatch)
        info = await qm.get_collection_info(merchant_id)
        if info:
            result["collection_exists"] = True
            result["vectors_count"] = info.get("vectors_count", 0)
            result["points_count"] = info.get("points_count", 0)
        else:
            # Client method returned None (likely due to version mismatch), use direct API call
            logger.debug("Client method returned None, trying direct API call")
            try:
                import httpx
                collection_name = f"products_merchant_{merchant_id}"
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{QDRANT_CONFIG['url']}/collections/{collection_name}",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        result_data = data.get("result", {})
                        if result_data:
                            result["collection_exists"] = True
                            # Qdrant API returns points_count, vectors are stored but may not be indexed yet
                            points = result_data.get("points_count", 0)
                            indexed = result_data.get("indexed_vectors_count", 0)
                            result["points_count"] = points
                            # If we have points, we have vectors (they may just not be indexed yet)
                            # Each point in Qdrant contains a vector, so points_count = vectors_count
                            result["vectors_count"] = points if points > 0 else indexed
                            logger.info("Collection info retrieved via API fallback",
                                      collection=collection_name,
                                      points=points,
                                      indexed=indexed)
                    elif response.status_code == 404:
                        # Collection doesn't exist
                        result["collection_exists"] = False
                        logger.debug("Collection not found", collection=collection_name)
                    else:
                        logger.warning("Unexpected status code from Qdrant API", 
                                     status_code=response.status_code)
            except Exception as api_error:
                logger.warning("Could not get collection info via API", 
                             api_error=str(api_error)[:100])
        
        await qm.close()
    except Exception as e:
        logger.error("Qdrant check failed", error=str(e))
    
    return result


async def check_elasticsearch(merchant_id: int) -> dict:
    """Check Elasticsearch connection and index"""
    result = {
        "connected": False,
        "index_exists": False,
        "doc_count": 0
    }
    
    try:
        es = ElasticsearchManager()
        await es.initialize()
        result["connected"] = True
        
        index_name = es.get_index_name(merchant_id)
        exists = await es._execute_with_retry(es.client.indices.exists, index=index_name)
        result["index_exists"] = bool(exists)
        
        if exists:
            # Get document count
            count_result = await es._execute_with_retry(
                es.client.count, 
                index=index_name
            )
            # Handle different response formats
            if hasattr(count_result, 'body'):
                result["doc_count"] = count_result.body.get("count", 0)
            elif isinstance(count_result, dict):
                result["doc_count"] = count_result.get("count", 0)
            else:
                result["doc_count"] = getattr(count_result, "count", 0)
        
        await es.close()
    except Exception as e:
        logger.error("Elasticsearch check failed", error=str(e))
    
    return result


async def check_search_api(api_key: str, port: int = 7099) -> dict:
    """Check if search API works"""
    result = {
        "keyword_search": False,
        "semantic_search": False,
        "hybrid_search": False,
        "facets": False
    }
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    try:
        async with httpx.AsyncClient() as client:
            # Test keyword search
            try:
                response = await client.post(
                    f"http://localhost:{port}/api/v1/search/",
                    headers=headers,
                    json={"query": "test", "limit": 5},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    result["keyword_search"] = True
                    result["facets"] = "facets" in data
            except Exception:
                pass
            
            # Test semantic search
            try:
                response = await client.post(
                    f"http://localhost:{port}/api/v1/search/semantic",
                    headers=headers,
                    json={"query": "test", "limit": 5},
                    timeout=10.0
                )
                if response.status_code == 200:
                    result["semantic_search"] = True
            except Exception:
                pass
            
            # Test hybrid search
            try:
                response = await client.post(
                    f"http://localhost:{port}/api/v1/search/",
                    headers=headers,
                    json={"query": "test", "search_mode": "hybrid", "limit": 5},
                    timeout=10.0
                )
                if response.status_code == 200:
                    result["hybrid_search"] = True
            except Exception:
                pass
    except Exception as e:
        logger.error("Search API check failed", error=str(e))
    
    return result


async def main():
    """Main verification function"""
    parser = argparse.ArgumentParser(description="Verify Phase 2 implementation")
    parser.add_argument("--merchant-id", type=int, default=1, help="Merchant ID")
    parser.add_argument("--api-key", type=str, help="API key for testing search endpoints")
    parser.add_argument("--port", type=int, default=7099, help="Search service port")
    
    args = parser.parse_args()
    
    print_section("Phase 2 Verification")
    print(f"Merchant ID: {args.merchant_id}")
    print(f"Service Port: {args.port}")
    
    # Check service health
    print_section("1. Service Health")
    health_ok = await check_service_health(args.port)
    print_check("Search Service Health", health_ok, 
                f"http://localhost:{args.port}/health" if health_ok else "Service not responding")
    
    # Check Elasticsearch
    print_section("2. Elasticsearch")
    es_result = await check_elasticsearch(args.merchant_id)
    print_check("Elasticsearch Connection", es_result["connected"])
    print_check("Index Exists", es_result["index_exists"])
    print_check("Products Indexed", es_result["doc_count"] > 0, 
                f"Found {es_result['doc_count']} products")
    
    # Check Qdrant
    print_section("3. Qdrant")
    qdrant_result = await check_qdrant(args.merchant_id)
    print_check("Qdrant Connection", qdrant_result["connected"])
    print_check("Collection Exists", qdrant_result["collection_exists"])
    print_check("Embeddings Generated", qdrant_result["vectors_count"] > 0,
                f"Found {qdrant_result['vectors_count']} vectors")
    print_check("Product Points", qdrant_result["points_count"] > 0,
                f"Found {qdrant_result['points_count']} points")
    
    if qdrant_result["vectors_count"] == 0:
        print("\n[WARNING] No embeddings found!")
        print(f"   Run: python scripts/generate_product_embeddings.py --merchant-id {args.merchant_id}")
    
    # Check search APIs
    if args.api_key:
        print_section("4. Search API Endpoints")
        api_result = await check_search_api(args.api_key, args.port)
        print_check("Keyword Search", api_result["keyword_search"])
        print_check("Semantic Search", api_result["semantic_search"],
                    "Requires embeddings" if not api_result["semantic_search"] else "")
        print_check("Hybrid Search", api_result["hybrid_search"],
                    "Requires embeddings" if not api_result["hybrid_search"] else "")
        print_check("Facets in Response", api_result["facets"])
    else:
        print_section("4. Search API Endpoints")
        print("[SKIP] Skipped (provide --api-key to test)")
    
    # Summary
    print_section("Verification Summary")
    
    all_checks = [
        ("Service Health", health_ok),
        ("Elasticsearch", es_result["connected"] and es_result["index_exists"]),
        ("Qdrant", qdrant_result["connected"] and qdrant_result["collection_exists"]),
        ("Embeddings", qdrant_result["vectors_count"] > 0),
    ]
    
    if args.api_key:
        api_result = await check_search_api(args.api_key, args.port)
        all_checks.extend([
            ("Keyword Search", api_result["keyword_search"]),
            ("Semantic Search", api_result["semantic_search"]),
            ("Hybrid Search", api_result["hybrid_search"]),
        ])
    
    passed = sum(1 for _, ok in all_checks if ok)
    total = len(all_checks)
    
    print(f"Passed: {passed}/{total} checks")
    
    if passed == total:
        print("\n[SUCCESS] All checks passed! Phase 2 verification complete.")
    else:
        print("\n[WARNING] Some checks failed. Review output above.")
        print("\nNext steps:")
        if not qdrant_result["vectors_count"] > 0:
            print(f"  - Generate embeddings: python scripts/generate_product_embeddings.py --merchant-id {args.merchant_id}")
        if not health_ok:
            print("  - Start search service: python backend/search-service/main.py")
        if args.api_key and not api_result.get("semantic_search"):
            print("  - Ensure embeddings are generated for semantic search to work")


if __name__ == "__main__":
    asyncio.run(main())

