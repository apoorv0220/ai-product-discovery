"""
Index products from Magento database to Elasticsearch and Qdrant

This script:
1. Connects to Magento MySQL database
2. Fetches products with attributes
3. Transforms to our schema
4. Indexes to Elasticsearch
5. Generates embeddings and indexes to Qdrant
"""

import asyncio
import os
import sys
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

# Add backend directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'search-service'))

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from elasticsearch import AsyncElasticsearch
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Magento database configuration
MAGENTO_DB_CONFIG = {
    'host': os.getenv('MAGENTO_DB_HOST', 'localhost'),
    'port': int(os.getenv('MAGENTO_DB_PORT', '3306')),
    'db': os.getenv('MAGENTO_DB_NAME', 'magento'),
    'user': os.getenv('MAGENTO_DB_USER', 'root'),
    'password': os.getenv('MAGENTO_DB_PASSWORD', ''),
}

# Elasticsearch and Qdrant URLs
ES_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')

# Configuration
MERCHANT_ID = int(os.getenv('MERCHANT_ID', '1'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def fetch_magento_products(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch products from Magento database
    
    Args:
        limit: Optional limit on number of products
        
    Returns:
        List of product dictionaries
    """
    try:
        import aiomysql
        
        # Connect to Magento MySQL database
        logger.info(f"Connecting to Magento database at {MAGENTO_DB_CONFIG['host']}:{MAGENTO_DB_CONFIG['port']}")
        conn = await aiomysql.connect(**MAGENTO_DB_CONFIG)
        cursor = await conn.cursor(aiomysql.DictCursor)
        
        # Query to fetch products from Magento
        # Simplified query - will need adjustments based on actual Magento schema
        query = """
        SELECT 
            cpe.entity_id as id,
            cpe.sku,
            cpev.value as name,
            cped.value as description,
            cpev_short.value as short_description,
            cps.qty as stock_qty
        FROM catalog_product_entity cpe
        LEFT JOIN catalog_product_entity_varchar cpev 
            ON cpev.entity_id = cpe.entity_id 
            AND cpev.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 4)
        LEFT JOIN catalog_product_entity_text cped 
            ON cped.entity_id = cpe.entity_id 
            AND cped.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'description' AND entity_type_id = 4)
        LEFT JOIN catalog_product_entity_varchar cpev_short 
            ON cpev_short.entity_id = cpe.entity_id 
            AND cpev_short.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'short_description' AND entity_type_id = 4)
        LEFT JOIN cataloginventory_stock_item cps ON cps.product_id = cpe.entity_id
        WHERE cpe.sku IS NOT NULL
        """
        
        if limit:
            query += f" LIMIT {limit}"
        else:
            query += " LIMIT 100"
        
        await cursor.execute(query)
        products = await cursor.fetchall()
        
        await cursor.close()
        conn.close()
        
        logger.info(f"Fetched {len(products)} products from Magento")
        return products
        
    except ImportError:
        logger.error("aiomysql not installed. Install with: pip install aiomysql pymysql")
        raise
    except Exception as e:
        logger.error(f"Error fetching products from Magento: {e}")
        raise


def transform_product(magento_product: Dict[str, Any], merchant_id: int) -> Dict[str, Any]:
    """
    Transform Magento product to our schema
    
    Args:
        magento_product: Product data from Magento
        merchant_id: Merchant ID
        
    Returns:
        Transformed product dictionary
    """
    from datetime import datetime, timezone
    
    return {
        'merchant_id': merchant_id,
        'product_id': str(magento_product.get('id', '')),
        'sku': magento_product.get('sku', ''),
        'name': magento_product.get('name', ''),
        'description': magento_product.get('description', ''),
        'short_description': magento_product.get('short_description', ''),
        'price': float(magento_product.get('price', 0)),
        'special_price': None,
        'currency': 'USD',
        'categories': [magento_product.get('category_key', '')] if magento_product.get('category_key') else [],
        'brand': None,
        'status': 1,
        'visibility': 4,
        'in_stock': True if magento_product.get('stock_qty', 0) > 0 else False,
        'stock_quantity': int(magento_product.get('stock_qty', 0)),
        'attributes': {},
        'url': f"/products/{magento_product.get('sku', '')}",
        'image_url': '',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }


async def index_to_elasticsearch(products: List[Dict[str, Any]], merchant_id: int):
    """
    Index products to Elasticsearch
    
    Args:
        products: List of products to index
        merchant_id: Merchant ID
    """
    es = AsyncElasticsearch([ES_URL], request_timeout=120)
    
    index_name = f"discovery_products_m{merchant_id}"
    
    # Check if index exists, create if not
    from core import elasticsearch_mappings
    get_product_index_settings = elasticsearch_mappings.get_product_index_settings
    PRODUCT_INDEX_MAPPING = elasticsearch_mappings.PRODUCT_INDEX_MAPPING
    
    # Try to check if index exists, but don't block if it times out
    try:
        exists = await asyncio.wait_for(es.indices.exists(index=index_name), timeout=5)
        if not exists:
            logger.info("Creating Elasticsearch index with mappings...")
            settings = get_product_index_settings(synonyms=[])
            await asyncio.wait_for(
                es.indices.create(
                    index=index_name,
                    settings=settings,
                    mappings=PRODUCT_INDEX_MAPPING
                ),
                timeout=30
            )
            logger.info(f"Created Elasticsearch index: {index_name}")
    except asyncio.TimeoutError:
        logger.warning("Index creation timed out, continuing anyway...")
    except Exception as e:
        logger.warning(f"Could not check/create index: {e}, continuing anyway...")
    
    # Prepare bulk actions
    from elasticsearch.helpers import async_bulk
    
    actions = []
    for product in products:
        actions.append({
            '_op_type': 'index',
            '_index': index_name,
            '_id': f"{merchant_id}_{product['product_id']}",
            '_source': product
        })
    
    # Bulk index
    logger.info(f"Indexing {len(actions)} products to Elasticsearch...")
    success, failed = await async_bulk(es, actions)
    logger.info(f"Indexed {success} products successfully, {len(failed)} failed")
    
    if failed:
        logger.error(f"Failed products: {failed[:5]}")  # Show first 5 failures
    
    # Refresh index
    await es.indices.refresh(index=index_name)
    await es.close()


async def index_to_qdrant(products: List[Dict[str, Any]], merchant_id: int):
    """
    Generate embeddings and index to Qdrant
    
    Args:
        products: List of products to index
        merchant_id: Merchant ID
    """
    try:
        from core import embedding_service as embedding_module
        EmbeddingService = embedding_module.EmbeddingService
        
        # Initialize embedding service
        emb_service = EmbeddingService()
        await emb_service.initialize()
        
        client = AsyncQdrantClient(url=QDRANT_URL, timeout=30)
        # Use the same naming convention as the config
        collection_name = f"products_merchant_{merchant_id}"
        
        # Try to check if collection exists with timeout
        try:
            collections = await asyncio.wait_for(client.get_collections(), timeout=10)
            collection_exists = any(c.name == collection_name for c in collections.collections)
        except asyncio.TimeoutError:
            logger.warning("Timeout checking collections, attempting to create anyway...")
            collection_exists = False
        
        if not collection_exists:
            # Create collection with timeout
            try:
                await asyncio.wait_for(
                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                    ),
                    timeout=30
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
            except asyncio.TimeoutError:
                logger.error("Timeout creating Qdrant collection")
                raise
        
        # Process in batches - use product_id hash as unique ID
        logger.info(f"Generating embeddings for {len(products)} products...")
        
        points = []
        for product in products:
            # Create searchable text
            searchable_text = f"{product['name']} {product['description']} {product.get('short_description', '')}"
            
            # Generate embedding
            try:
                embedding = await asyncio.wait_for(
                    emb_service.generate_embedding(searchable_text),
                    timeout=5
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout generating embedding for {product['product_id']}, skipping...")
                continue
            
            # Use hash of merchant_id and product_id as unique point ID
            import hashlib
            unique_id = int(hashlib.md5(f"{merchant_id}_{product['product_id']}".encode()).hexdigest()[:8], 16)
            
            # Create point
            points.append(
                PointStruct(
                    id=unique_id,
                    vector=embedding,
                    payload={
                        'product_id': product['product_id'],
                        'sku': product['sku'],
                        'name': product['name'],
                        'merchant_id': merchant_id,
                    }
                )
            )
            
            if len(points) >= BATCH_SIZE:
                try:
                    await asyncio.wait_for(
                        client.upsert(collection_name=collection_name, points=points),
                        timeout=30
                    )
                    logger.info(f"Indexed {len(points)} products to Qdrant")
                    points = []
                except asyncio.TimeoutError:
                    logger.error(f"Timeout upserting batch to Qdrant")
                    points = []
        
        # Upsert remaining points
        if points:
            try:
                await asyncio.wait_for(
                    client.upsert(collection_name=collection_name, points=points),
                    timeout=30
                )
                logger.info(f"Indexed remaining {len(points)} products to Qdrant")
            except asyncio.TimeoutError:
                logger.error("Timeout upserting final batch to Qdrant")
        
        logger.info(f"Successfully indexed all products to Qdrant")
        
    except Exception as e:
        logger.error(f"Error indexing to Qdrant: {e}")
        raise


async def main():
    """Main execution function with chunked processing"""
    logger.info("Starting Magento product indexing...")
    
    try:
        # Check if we have Magento DB credentials
        if not MAGENTO_DB_CONFIG.get('password'):
            logger.warning("MAGENTO_DB_PASSWORD not set. Please set environment variables:")
            logger.warning("  MAGENTO_DB_HOST=hostname")
            logger.warning("  MAGENTO_DB_PORT=3306")
            logger.warning("  MAGENTO_DB_NAME=database_name")
            logger.warning("  MAGENTO_DB_USER=username")
            logger.warning("  MAGENTO_DB_PASSWORD=password")
            return
        
        # Fetch products
        products = await fetch_magento_products(limit=None)
        
        if not products:
            logger.error("No products found in Magento database")
            return
        
        logger.info(f"Found {len(products)} products total")
        
        # Process in chunks to avoid timeouts
        CHUNK_SIZE = BATCH_SIZE  # Use BATCH_SIZE from config
        total_products = len(products)
        es_success = 0
        es_failed = 0
        qdrant_success = 0
        qdrant_failed = 0
        
        for chunk_start in range(0, total_products, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, total_products)
            chunk = products[chunk_start:chunk_end]
            
            logger.info(f"Processing chunk {chunk_start//CHUNK_SIZE + 1}/{(total_products + CHUNK_SIZE - 1)//CHUNK_SIZE}: products {chunk_start}-{chunk_end-1}")
            
            # Transform products
            transformed = [transform_product(p, MERCHANT_ID) for p in chunk]
            
            # Index to Elasticsearch
            try:
                logger.info(f"Indexing {len(transformed)} products to Elasticsearch...")
                await index_to_elasticsearch(transformed, MERCHANT_ID)
                es_success += len(transformed)
            except Exception as e:
                logger.error(f"Elasticsearch indexing failed for chunk: {e}")
                es_failed += len(transformed)
            
            # Index to Qdrant
            try:
                logger.info(f"Indexing {len(transformed)} products to Qdrant...")
                await index_to_qdrant(transformed, MERCHANT_ID)
                qdrant_success += len(transformed)
            except Exception as e:
                logger.error(f"Qdrant indexing failed for chunk: {e}")
                qdrant_failed += len(transformed)
        
        # Summary
        logger.info("=" * 60)
        logger.info("Indexing complete!")
        logger.info(f"Elasticsearch: {es_success} succeeded, {es_failed} failed")
        logger.info(f"Qdrant: {qdrant_success} succeeded, {qdrant_failed} failed")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
