"""
Bulk embedding generation script for existing products.

This script generates embeddings for all products in Elasticsearch and stores them in Qdrant.

Usage:
    python scripts/generate_product_embeddings.py [--merchant-id MERCHANT_ID] [--batch-size BATCH_SIZE]

@category    Scripts
@package     SearchService
@license     MIT License
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path

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
from core.embedding_service import EmbeddingService
from core.qdrant_client import QdrantManager
from core.embedding_generator import EmbeddingGenerator
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


async def fetch_all_products(es_manager: ElasticsearchManager, merchant_id: int) -> list:
    """
    Fetch all products from Elasticsearch index
    
    Args:
        es_manager: Elasticsearch manager instance
        merchant_id: Merchant ID
        
    Returns:
        List of product documents
    """
    index_name = es_manager.get_index_name(merchant_id)
    products = []
    
    # Scroll through all products
    query = {
        "query": {"match_all": {}},
        "size": 1000
    }
    
    try:
        # Initial search
        response = await es_manager._execute_with_retry(
            es_manager.client.search,
            index=index_name,
            body=query,
            scroll="5m"
        )
        
        scroll_id = response.get("_scroll_id")
        hits = response.get("hits", {}).get("hits", [])
        
        while hits:
            for hit in hits:
                products.append(hit["_source"])
            
            if not scroll_id:
                break
            
            # Continue scrolling
            response = await es_manager._execute_with_retry(
                es_manager.client.scroll,
                scroll_id=scroll_id,
                scroll="5m"
            )
            scroll_id = response.get("_scroll_id")
            hits = response.get("hits", {}).get("hits", [])
        
        # Clear scroll
        if scroll_id:
            try:
                await es_manager._execute_with_retry(
                    es_manager.client.clear_scroll,
                    scroll_id=scroll_id
                )
            except Exception:
                pass
        
        logger.info("Fetched products from Elasticsearch",
                   merchant_id=merchant_id,
                   count=len(products))
        
    except Exception as e:
        logger.error("Failed to fetch products from Elasticsearch",
                    merchant_id=merchant_id,
                    error=str(e))
        raise
    
    return products


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate embeddings for products")
    parser.add_argument("--merchant-id", type=int, required=True, help="Merchant ID")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of products (for testing)")
    
    args = parser.parse_args()
    
    settings = SearchServiceSettings()
    
    logger.info("Starting bulk embedding generation",
               merchant_id=args.merchant_id,
               batch_size=args.batch_size)
    
    # Initialize services
    es_manager = ElasticsearchManager()
    await es_manager.initialize()
    
    embedding_service = EmbeddingService()
    await embedding_service.initialize()
    
    qdrant_manager = QdrantManager(
        url=QDRANT_CONFIG["url"],
        api_key=QDRANT_CONFIG["api_key"]
    )
    await qdrant_manager.initialize()
    
    embedding_generator = EmbeddingGenerator(embedding_service, qdrant_manager)
    
    try:
        # Fetch all products
        print("Fetching products from Elasticsearch...")
        logger.info("Fetching products from Elasticsearch...")
        products = await fetch_all_products(es_manager, args.merchant_id)
        
        if args.limit:
            products = products[:args.limit]
            print(f"Limited to {args.limit} products for testing")
            logger.info(f"Limited to {args.limit} products for testing")
        
        if not products:
            print("[ERROR] No products found to process")
            logger.warning("No products found to process")
            return
        
        print(f"[OK] Found {len(products)} products")
        
        # Generate embeddings
        print(f"\nGenerating embeddings for {len(products)} products (batch size: {args.batch_size})...")
        logger.info("Generating embeddings...",
                   total_products=len(products),
                   batch_size=args.batch_size)
        
        result = await embedding_generator.generate_and_store_embeddings(
            args.merchant_id,
            products,
            batch_size=args.batch_size
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("EMBEDDING GENERATION SUMMARY")
        print("=" * 60)
        print(f"Merchant ID: {args.merchant_id}")
        print(f"Total Products: {len(products)}")
        print(f"Success: {result['success_count']}")
        print(f"Failed: {result['failure_count']}")
        print(f"Errors: {len(result['errors'])}")
        print("=" * 60)
        
        logger.info("Embedding generation complete",
                   merchant_id=args.merchant_id,
                   total_products=len(products),
                   success=result["success_count"],
                   failed=result["failure_count"],
                   errors=len(result["errors"]))
        
        if result["errors"]:
            print(f"\n[WARNING] {len(result['errors'])} errors occurred")
            logger.warning("Some errors occurred during embedding generation",
                          error_count=len(result["errors"]))
            for error in result["errors"][:5]:  # Show first 5 errors
                logger.error("Embedding error", **error)
        else:
            print("\n[SUCCESS] All embeddings generated successfully!")
        
    except Exception as e:
        logger.error("Failed to generate embeddings", error=str(e))
        raise
    finally:
        # Cleanup
        await embedding_service.cleanup()
        await qdrant_manager.close()
        await es_manager.close()
        
        logger.info("Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())

