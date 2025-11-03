"""
Verify that products were correctly indexed to Elasticsearch and Qdrant

This script:
1. Checks Elasticsearch index document count
2. Lists sample products from Elasticsearch
3. Checks Qdrant collection count
4. Validates product data structure
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add backend directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'search-service'))

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Try to import required modules
try:
    from elasticsearch import AsyncElasticsearch
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False
    print("Warning: elasticsearch module not available. Install with: pip install elasticsearch")

try:
    from qdrant_client import AsyncQdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("Warning: qdrant_client module not available. Install with: pip install qdrant-client")

import json

# Configuration
MERCHANT_ID = int(os.getenv('MERCHANT_ID', '1'))
ES_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')

INDEX_NAME = f"discovery_products_m{MERCHANT_ID}"
COLLECTION_NAME = f"products_merchant_{MERCHANT_ID}"


async def check_elasticsearch():
    """Check Elasticsearch index status and sample products"""
    if not ES_AVAILABLE:
        print("❌ Cannot check Elasticsearch - module not installed")
        return
    print("=" * 60)
    print("ELASTICSEARCH VERIFICATION")
    print("=" * 60)
    
    es = AsyncElasticsearch([ES_URL], request_timeout=30)
    
    try:
        # Check if index exists
        exists = await es.indices.exists(index=INDEX_NAME)
        print(f"\nIndex Name: {INDEX_NAME}")
        print(f"Index Exists: {exists}")
        
        if not exists:
            print("❌ Index does not exist! Products may not have been indexed.")
            await es.close()
            return
        
        # Get document count
        count_result = await es.count(index=INDEX_NAME)
        doc_count = count_result['count']
        print(f"Document Count: {doc_count}")
        
        if doc_count == 0:
            print("⚠️  Warning: Index exists but has 0 documents!")
        else:
            print(f"✅ Index has {doc_count} documents")
        
        # Get index stats
        stats = await es.indices.stats(index=INDEX_NAME)
        print(f"\nIndex Statistics:")
        print(f"  Total Documents: {stats['indices'][INDEX_NAME]['total']['docs']['count']}")
        print(f"  Index Size: {stats['indices'][INDEX_NAME]['total']['store']['size_in_bytes'] / 1024 / 1024:.2f} MB")
        
        # Get field mappings to verify structure
        print(f"\n🔍 Field Mappings Verification:")
        try:
            mappings = await es.indices.get_mapping(index=INDEX_NAME)
            index_mappings = mappings[INDEX_NAME]['mappings']['properties']
            required_fields = ['merchant_id', 'product_id', 'sku', 'name', 'price']
            missing_fields = []
            for field in required_fields:
                if field not in index_mappings:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"  ⚠️  Missing required fields in mapping: {missing_fields}")
            else:
                print(f"  ✅ All required fields mapped correctly")
                field_types = {f: index_mappings[f].get('type', 'unknown') for f in required_fields}
                print(f"  Field Types:")
                for field, ftype in field_types.items():
                    print(f"    - {field}: {ftype}")
                
                total_fields = len(index_mappings)
                print(f"  Total mapped fields: {total_fields}")
                if total_fields > 10:
                    other_fields = [f for f in sorted(index_mappings.keys()) if f not in required_fields][:5]
                    print(f"  Other fields: {', '.join(other_fields)}...")
        except Exception as e:
            print(f"  ⚠️  Could not verify mappings: {e}")
        
        # Get sample products
        print(f"\n📦 Sample Products (first 5):")
        search_result = await es.search(
            index=INDEX_NAME,
            body={
                "query": {"match_all": {}},
                "size": 5
            }
        )
        
        hits = search_result.get('hits', {}).get('hits', [])
        if hits:
            for i, hit in enumerate(hits, 1):
                source = hit.get('_source', {})
                print(f"\n  Product {i}:")
                print(f"    ID: {hit.get('_id')}")
                print(f"    Product ID: {source.get('product_id')}")
                print(f"    SKU: {source.get('sku')}")
                print(f"    Name: {source.get('name', 'N/A')[:50]}...")
                print(f"    Price: ${source.get('price', 0)}")
                print(f"    In Stock: {source.get('in_stock')}")
        else:
            print("  ⚠️  No products found in index!")
        
        # Check for common field issues
        print(f"\n🔍 Field Validation (Sample Documents):")
        if hits:
            for i, hit in enumerate(hits, 1):
                sample = hit.get('_source', {})
                print(f"\n  Document {i}:")
                required_fields = ['merchant_id', 'product_id', 'sku', 'name', 'price']
                missing_fields = [f for f in required_fields if f not in sample]
                if missing_fields:
                    print(f"    ❌ Missing required fields: {missing_fields}")
                else:
                    print(f"    ✅ All required fields present")
                
                # Check merchant_id matches
                if sample.get('merchant_id') != MERCHANT_ID:
                    print(f"    ⚠️  Warning: merchant_id ({sample.get('merchant_id')}) != expected ({MERCHANT_ID})")
                else:
                    print(f"    ✅ Merchant ID: {sample.get('merchant_id')}")
                
                # Check data types
                price = sample.get('price')
                if price is not None and not isinstance(price, (int, float)):
                    print(f"    ⚠️  Warning: price is {type(price).__name__}, expected number")
                else:
                    print(f"    ✅ Price: ${price}")
                
                print(f"    ✅ Product ID: {sample.get('product_id')}")
                print(f"    ✅ SKU: {sample.get('sku')}")
                print(f"    ✅ Name: {sample.get('name', 'N/A')[:50]}")
        else:
            print("  ⚠️  No documents to validate")
        
        await es.close()
        
    except Exception as e:
        print(f"❌ Error checking Elasticsearch: {e}")
        import traceback
        traceback.print_exc()
        await es.close()


async def check_qdrant():
    """Check Qdrant collection status"""
    if not QDRANT_AVAILABLE:
        print("❌ Cannot check Qdrant - module not installed")
        return
    print("\n" + "=" * 60)
    print("QDRANT VERIFICATION")
    print("=" * 60)
    
    try:
        client = AsyncQdrantClient(url=QDRANT_URL, timeout=30)
        
        # Get collections
        collections = await client.get_collections()
        collection_exists = any(c.name == COLLECTION_NAME for c in collections.collections)
        
        print(f"\nCollection Name: {COLLECTION_NAME}")
        print(f"Collection Exists: {collection_exists}")
        
        if not collection_exists:
            print("❌ Collection does not exist! Embeddings may not have been indexed.")
            return
        
        # Try to get collection info - handle version compatibility issues
        try:
            collection_info = await client.get_collection(COLLECTION_NAME)
            points_count = collection_info.points_count
            print(f"Points Count: {points_count}")
            
            if points_count == 0:
                print("⚠️  Warning: Collection exists but has 0 vectors!")
            else:
                print(f"✅ Collection has {points_count} vectors")
            
            try:
                print(f"\nCollection Configuration:")
                print(f"  Vector Size: {collection_info.config.params.vectors.size}")
                print(f"  Distance: {collection_info.config.params.vectors.distance}")
            except AttributeError:
                print(f"\nCollection Configuration: (unable to parse - version mismatch)")
        except Exception as e:
            # Fallback: try to get count via API directly
            print(f"⚠️  Could not get full collection info (version mismatch), trying alternative method...")
            try:
                # Use scroll to count points
                scroll_result = await client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=1,
                    with_payload=False,
                    with_vectors=False
                )
                # Get total count by scrolling through
                points_count = 0
                offset = None
                while True:
                    scroll_result = await client.scroll(
                        collection_name=COLLECTION_NAME,
                        limit=100,
                        offset=offset,
                        with_payload=False,
                        with_vectors=False
                    )
                    points = scroll_result[0]
                    if not points:
                        break
                    points_count += len(points)
                    offset = scroll_result[1]  # Next offset
                    if not offset:
                        break
                print(f"Points Count (calculated): {points_count}")
                if points_count == 0:
                    print("⚠️  Warning: Collection exists but has 0 vectors!")
                else:
                    print(f"✅ Collection has {points_count} vectors")
            except Exception as e2:
                print(f"❌ Could not determine vector count: {e2}")
                points_count = None
        
        # Get sample points
        print(f"\n📊 Sample Vectors (first 3):")
        try:
            scroll_result = await client.scroll(
                collection_name=COLLECTION_NAME,
                limit=3,
                with_payload=True,
                with_vectors=False
            )
            
            points = scroll_result[0]
            if points:
                for i, point in enumerate(points, 1):
                    print(f"\n  Vector {i}:")
                    print(f"    ID: {point.id}")
                    print(f"    Payload: {point.payload}")
            else:
                print("  ⚠️  No vectors found in collection!")
        except Exception as e:
            print(f"  ⚠️  Could not retrieve sample vectors: {e}")
        
    except Exception as e:
        print(f"❌ Error checking Qdrant: {e}")
        import traceback
        traceback.print_exc()


async def compare_counts():
    """Compare Elasticsearch and Qdrant document counts"""
    print("\n" + "=" * 60)
    print("COUNT COMPARISON")
    print("=" * 60)
    
    es = AsyncElasticsearch([ES_URL], request_timeout=30)
    
    try:
        # Elasticsearch count
        exists = await es.indices.exists(index=INDEX_NAME)
        if exists:
            count_result = await es.count(index=INDEX_NAME)
            es_count = count_result['count']
        else:
            es_count = 0
        
        # Qdrant count
        try:
            client = AsyncQdrantClient(url=QDRANT_URL, timeout=30)
            collections = await client.get_collections()
            collection_exists = any(c.name == COLLECTION_NAME for c in collections.collections)
            
            if collection_exists:
                try:
                    collection_info = await client.get_collection(COLLECTION_NAME)
                    qdrant_count = collection_info.points_count
                except Exception:
                    # Fallback: count by scrolling
                    qdrant_count = 0
                    offset = None
                    while True:
                        scroll_result = await client.scroll(
                            collection_name=COLLECTION_NAME,
                            limit=100,
                            offset=offset,
                            with_payload=False,
                            with_vectors=False
                        )
                        points = scroll_result[0]
                        if not points:
                            break
                        qdrant_count += len(points)
                        offset = scroll_result[1]
                        if not offset:
                            break
            else:
                qdrant_count = 0
        except Exception as e:
            print(f"⚠️  Could not get Qdrant count: {e}")
            qdrant_count = -1
        
        print(f"\nElasticsearch Documents: {es_count}")
        print(f"Qdrant Vectors: {qdrant_count if qdrant_count >= 0 else 'N/A'}")
        
        if qdrant_count >= 0:
            if es_count == qdrant_count:
                print(f"✅ Counts match! ({es_count} products indexed in both)")
            elif es_count > qdrant_count:
                print(f"⚠️  Warning: More documents in Elasticsearch than vectors in Qdrant")
                print(f"   This may indicate some products failed embedding generation")
            else:
                print(f"⚠️  Warning: More vectors in Qdrant than documents in Elasticsearch")
                print(f"   This should not happen - possible data inconsistency")
        
        await es.close()
        
    except Exception as e:
        print(f"❌ Error comparing counts: {e}")
        import traceback
        traceback.print_exc()
        await es.close()


async def check_index_health():
    """Check overall index health"""
    print("\n" + "=" * 60)
    print("OVERALL HEALTH CHECK")
    print("=" * 60)
    
    es = AsyncElasticsearch([ES_URL], request_timeout=30)
    
    try:
        exists = await es.indices.exists(index=INDEX_NAME)
        
        if not exists:
            print("❌ Index does not exist")
            print("\nRecommendation: Run POST /api/v1/index/ensure or index products")
            await es.close()
            return
        
        # Try a simple search
        search_result = await es.search(
            index=INDEX_NAME,
            body={"query": {"match_all": {}}, "size": 1}
        )
        
        hits = search_result.get('hits', {}).get('hits', [])
        total = search_result.get('hits', {}).get('total', {})
        total_value = total.get('value', 0) if isinstance(total, dict) else total
        
        if total_value > 0:
            print(f"✅ Index is healthy and searchable")
            print(f"   Total searchable products: {total_value}")
            
            # Test actual search functionality
            print(f"\n🔍 Testing Search Functionality:")
            
            # Test 1: Search by name field (match_all should work)
            try:
                # Use match_all with exists filter for name field
                name_search = await es.search(
                    index=INDEX_NAME,
                    body={
                        "query": {
                            "exists": {
                                "field": "name"
                            }
                        },
                        "size": 1
                    }
                )
                name_hits = name_search.get('hits', {}).get('total', {})
                name_count = name_hits.get('value', 0) if isinstance(name_hits, dict) else name_hits
                if name_count > 0:
                    print(f"  ✅ Name field searchable: {name_count} documents match")
                else:
                    print(f"  ⚠️  Name search returned 0 results")
            except Exception as e:
                print(f"  ⚠️  Name search failed: {e}")
            
            # Test 2: Filter by merchant_id
            try:
                merchant_filter = await es.search(
                    index=INDEX_NAME,
                    body={
                        "query": {
                            "term": {
                                "merchant_id": MERCHANT_ID
                            }
                        },
                        "size": 1
                    }
                )
                merchant_hits = merchant_filter.get('hits', {}).get('total', {})
                merchant_count = merchant_hits.get('value', 0) if isinstance(merchant_hits, dict) else merchant_hits
                if merchant_count == total_value:
                    print(f"  ✅ Merchant ID filter works: {merchant_count} documents")
                else:
                    print(f"  ⚠️  Merchant filter mismatch: {merchant_count} vs {total_value}")
            except Exception as e:
                print(f"  ⚠️  Merchant filter failed: {e}")
            
            # Test 3: Autocomplete field search
            try:
                # Use exists filter for autocomplete field
                autocomplete_search = await es.search(
                    index=INDEX_NAME,
                    body={
                        "query": {
                            "exists": {
                                "field": "name.autocomplete"
                            }
                        },
                        "size": 1
                    }
                )
                auto_hits = autocomplete_search.get('hits', {}).get('total', {})
                auto_count = auto_hits.get('value', 0) if isinstance(auto_hits, dict) else auto_hits
                if auto_count > 0:
                    print(f"  ✅ Autocomplete field searchable: {auto_count} documents match")
                else:
                    print(f"  ⚠️  Autocomplete search returned 0 results")
            except Exception as e:
                print(f"  ⚠️  Autocomplete search failed: {e}")
            
            # Test 4: Price range filter
            try:
                price_filter = await es.search(
                    index=INDEX_NAME,
                    body={
                        "query": {
                            "range": {
                                "price": {
                                    "gte": 0
                                }
                            }
                        },
                        "size": 1
                    }
                )
                price_hits = price_filter.get('hits', {}).get('total', {})
                price_count = price_hits.get('value', 0) if isinstance(price_hits, dict) else price_hits
                if price_count > 0:
                    print(f"  ✅ Price range filter works: {price_count} documents")
                else:
                    print(f"  ⚠️  Price filter returned 0 results")
            except Exception as e:
                print(f"  ⚠️  Price filter failed: {e}")
                
        else:
            print(f"⚠️  Index exists but no searchable products")
        
        await es.close()
        
    except Exception as e:
        print(f"❌ Error checking index health: {e}")
        await es.close()


async def main():
    """Main verification function"""
    print("\n" + "=" * 60)
    print("PRODUCT INDEXING VERIFICATION")
    print(f"Merchant ID: {MERCHANT_ID}")
    print("=" * 60)
    
    await check_elasticsearch()
    await check_qdrant()
    await compare_counts()
    await check_index_health()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print("\nIf you see issues:")
    print("1. Check that index_magento_products.py completed without errors")
    print("2. Check Elasticsearch logs for indexing errors")
    print("3. Verify product data format matches schema")
    print("4. Try re-indexing with: python scripts/index_magento_products.py")


if __name__ == '__main__':
    asyncio.run(main())

