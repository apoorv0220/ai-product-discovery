"""
Diagnostic script to check data flow from Elasticsearch to search results

This script:
1. Queries Elasticsearch directly to see what's stored
2. Makes a search API call to see what's returned
3. Compares the two to identify where data is lost

Usage:
    python scripts/diagnose_data_flow.py --merchant-id 1
"""

import asyncio
import sys
import os
from pathlib import Path
import json

# Add backend directories to path
script_dir = Path(__file__).parent
backend_dir = script_dir.parent / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "search-service"))

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = script_dir.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from elasticsearch import AsyncElasticsearch
import argparse

# Configuration
ES_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')

async def query_elasticsearch_direct(merchant_id: int):
    """Query Elasticsearch directly to see what's stored"""
    es = AsyncElasticsearch([ES_URL])
    
    index_name = f"discovery_products_m{merchant_id}"
    
    print("="*80)
    print("DIAGNOSTIC: Querying Elasticsearch Directly")
    print("="*80)
    
    try:
        # Check if index exists
        exists = await es.indices.exists(index=index_name)
        if not exists:
            print(f"[ERROR] Index {index_name} does not exist!")
            await es.close()
            return
        
        print(f"[OK] Index {index_name} exists")
        
        # Get index stats
        stats = await es.indices.stats(index=index_name)
        doc_count = stats['indices'][index_name]['total']['docs']['count']
        print(f"[INFO] Total documents: {doc_count}")
        
        # Get a sample document
        response = await es.search(
            index=index_name,
            body={
                "query": {"match_all": {}},
                "size": 1,
                "_source": True
            }
        )
        
        if response['hits']['total']['value'] > 0:
            sample_doc = response['hits']['hits'][0]['_source']
            
            print("\n[SAMPLE] Product Document:")
            print("-"*80)
            print(f"Product ID: {sample_doc.get('product_id')}")
            print(f"SKU: {sample_doc.get('sku')}")
            print(f"Name: {sample_doc.get('name')}")
            print(f"Description: {sample_doc.get('description', 'N/A')[:100]}...")
            print(f"Price: {sample_doc.get('price')}")
            print(f"Special Price: {sample_doc.get('special_price')}")
            print(f"Currency: {sample_doc.get('currency')}")
            print(f"Image URL: {sample_doc.get('image_url')}")
            print(f"URL: {sample_doc.get('url')}")
            print(f"Categories: {sample_doc.get('categories')}")
            print(f"Brand: {sample_doc.get('brand')}")
            print(f"In Stock: {sample_doc.get('in_stock')}")
            print(f"Stock Quantity: {sample_doc.get('stock_quantity')}")
            print(f"Attributes: {sample_doc.get('attributes')}")
            print(f"Status: {sample_doc.get('status')}")
            print(f"Visibility: {sample_doc.get('visibility')}")
            
            print("\n[FIELDS] All fields in document:")
            print(json.dumps(list(sample_doc.keys()), indent=2))
            
            # Analyze data completeness
            print("\n[ANALYSIS] Data Completeness:")
            print("-"*80)
            
            # Query all documents to check completeness
            all_response = await es.search(
                index=index_name,
                body={
                    "query": {"match_all": {}},
                    "size": 100,  # Check first 100 products
                    "_source": ["price", "image_url", "categories", "description"]
                }
            )
            
            total = len(all_response['hits']['hits'])
            with_price = sum(1 for doc in all_response['hits']['hits'] if doc['_source'].get('price', 0) > 0)
            with_image = sum(1 for doc in all_response['hits']['hits'] if doc['_source'].get('image_url'))
            with_categories = sum(1 for doc in all_response['hits']['hits'] if doc['_source'].get('categories'))
            with_description = sum(1 for doc in all_response['hits']['hits'] if doc['_source'].get('description'))
            
            print(f"Products with price > 0: {with_price}/{total} ({with_price/total*100:.1f}%)")
            print(f"Products with image URL: {with_image}/{total} ({with_image/total*100:.1f}%)")
            print(f"Products with categories: {with_categories}/{total} ({with_categories/total*100:.1f}%)")
            print(f"Products with description: {with_description}/{total} ({with_description/total*100:.1f}%)")
            
            # Determine if data is complete or incomplete in ES
            if with_price/total < 0.5 or with_image/total < 0.5 or with_categories/total < 0.5:
                print("\n[FINDING] Data in Elasticsearch is INCOMPLETE")
                print("   Problem is BEFORE Elasticsearch (API reception or indexer transformation)")
            else:
                print("\n[FINDING] Data in Elasticsearch appears COMPLETE")
                print("   If search results are incomplete, problem is in search query/response")
            
        else:
            print("[ERROR] No documents found in index")
        
    except Exception as e:
        print(f"[ERROR] Error querying Elasticsearch: {e}")
    finally:
        await es.close()


async def test_search_api(merchant_id: int, api_key: str = None):
    """Test the search API to see what's returned"""
    import aiohttp
    
    print("\n" + "="*80)
    print("DIAGNOSTIC: Testing Search API")
    print("="*80)
    
    # Use a simple search query
    search_url = f"http://localhost:7099/api/v1/search/"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "query": "shoulder",  # Simple query from your example
        "limit": 5,
        "search_mode": "keyword"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(search_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"\n[SEARCH] Returned {len(data.get('results', []))} results")
                    
                    if data.get('results'):
                        result = data['results'][0]
                        print("\n[RESULT] First Search Result:")
                        print("-"*80)
                        print(f"Product ID: {result.get('product_id')}")
                        print(f"Title: {result.get('title')}")
                        print(f"Score: {result.get('score')}")
                        print(f"Metadata: {json.dumps(result.get('metadata', {}), indent=2)}")
                        
                        # Check what's missing
                        metadata = result.get('metadata', {})
                        print("\n[COMPLETENESS] Data in Search Results:")
                        print("-"*80)
                        print(f"Price: {metadata.get('price')} {'[OK]' if metadata.get('price', 0) > 0 else '[MISSING]'}")
                        print(f"Image URL: {metadata.get('image_url') or 'N/A'} {'[OK]' if metadata.get('image_url') else '[MISSING]'}")
                        print(f"Categories: {metadata.get('categories', [])} {'[OK]' if metadata.get('categories') else '[MISSING]'}")
                        print(f"URL: {metadata.get('url')} {'[OK]' if metadata.get('url') else '[MISSING]'}")
                        
                    else:
                        print("[ERROR] No search results returned")
                else:
                    print(f"[ERROR] Search API returned status {response.status}")
                    text = await response.text()
                    print(f"Response: {text[:500]}")
                    
    except Exception as e:
        print(f"[ERROR] Error calling search API: {e}")


async def main():
    """Main diagnostic function"""
    parser = argparse.ArgumentParser(description="Diagnose data flow from ES to search results")
    parser.add_argument("--merchant-id", type=int, default=1, help="Merchant ID")
    parser.add_argument("--api-key", type=str, help="API key for search API (optional)")
    
    args = parser.parse_args()
    
    print("Starting Data Flow Diagnostic")
    print(f"Merchant ID: {args.merchant_id}")
    print()
    
    # Step 1: Check what's in Elasticsearch
    await query_elasticsearch_direct(args.merchant_id)
    
    # Step 2: Check what search API returns
    if args.api_key:
        await test_search_api(args.merchant_id, args.api_key)
    else:
        print("\n[WARNING] Skipping search API test (no API key provided)")
        print("   Run with --api-key to test search API")
    
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

