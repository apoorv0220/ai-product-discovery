"""
Inspect what data is stored in Elasticsearch, Qdrant payload, and embeddings.

This script shows exactly what category information is stored in each location.
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
import httpx
import argparse

ES_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')


def prepare_embedding_text(product: dict) -> str:
    """Same logic as EmbeddingGenerator._prepare_embedding_text"""
    parts = []
    
    if product.get("name"):
        parts.append(product["name"])
    
    if product.get("description"):
        desc = product["description"]
        if len(desc) > 500:
            desc = desc[:500] + "..."
        parts.append(desc)
    elif product.get("short_description"):
        parts.append(product["short_description"])
    
    categories = product.get("categories", [])
    if categories:
        if isinstance(categories, list) and len(categories) > 0:
            if isinstance(categories[0], dict):
                category_names = [cat.get("name", cat.get("title", "")) for cat in categories if isinstance(cat, dict) and (cat.get("name") or cat.get("title"))]
            else:
                category_names = [str(cat) for cat in categories if cat]
        else:
            category_names = [str(categories)] if categories else []
        if category_names:
            parts.append(f"Category: {', '.join(category_names)}")
    
    if product.get("brand"):
        parts.append(f"Brand: {product['brand']}")
    
    attributes = product.get("attributes", {})
    if isinstance(attributes, dict):
        key_attrs = []
        for key in ["color", "size", "material", "pattern", "climate", "style", "type"]:
            if key in attributes and attributes[key]:
                key_attrs.append(f"{key}: {attributes[key]}")
        if key_attrs:
            parts.append("Attributes: " + ", ".join(key_attrs))
    
    return " | ".join(parts)


async def inspect_data(merchant_id: int):
    """Inspect data in all storage locations"""
    es = AsyncElasticsearch([ES_URL])
    
    index_name = f"discovery_products_m{merchant_id}"
    collection_name = f"products_merchant_{merchant_id}"
    
    print("="*80)
    print("DATA STORAGE INSPECTION")
    print("="*80)
    print(f"Merchant ID: {merchant_id}")
    print()
    
    try:
        # 1. Check Elasticsearch
        print("="*80)
        print("1. ELASTICSEARCH DATA")
        print("="*80)
        
        # Get a real product (not test product)
        response = await es.search(
            index=index_name,
            body={
                "query": {
                    "bool": {
                        "must_not": {
                            "term": {"product_id": "test-999"}
                        }
                    }
                },
                "size": 1
            }
        )
        
        if response['hits']['hits']:
            es_doc = response['hits']['hits'][0]['_source']
            print(f"Sample Product: {es_doc.get('name', 'N/A')}")
            print(f"Product ID: {es_doc.get('product_id', 'N/A')}")
            print()
            print("Categories field:")
            print(f"  Type: {type(es_doc.get('categories'))}")
            print(f"  Value: {es_doc.get('categories')}")
            if es_doc.get('categories'):
                if isinstance(es_doc['categories'], list) and len(es_doc['categories']) > 0:
                    print(f"  First category type: {type(es_doc['categories'][0])}")
                    print(f"  First category value: {es_doc['categories'][0]}")
            print()
            print("Other relevant fields:")
            print(f"  Name: {es_doc.get('name', 'N/A')}")
            print(f"  Description: {str(es_doc.get('description', 'N/A'))[:100]}...")
            print(f"  Attributes: {list(es_doc.get('attributes', {}).keys())[:5] if es_doc.get('attributes') else 'N/A'}")
        else:
            print("No products found in Elasticsearch")
        
        print()
        
        # 2. Check Qdrant Collection
        print("="*80)
        print("2. QDRANT COLLECTION")
        print("="*80)
        
        try:
            async with httpx.AsyncClient() as client:
                collection_response = await client.get(
                    f"{QDRANT_URL}/collections/{collection_name}",
                    timeout=5.0
                )
                if collection_response.status_code == 200:
                    collection_data = collection_response.json()
                    result = collection_data.get("result", {})
                    print(f"Collection exists: {collection_name}")
                    print(f"Vectors count: {result.get('vectors_count', 'N/A')}")
                    print(f"Points count: {result.get('points_count', 'N/A')}")
                elif collection_response.status_code == 404:
                    print(f"Collection not found: {collection_name}")
                    await es.close()
                    return
                else:
                    print(f"Error: {collection_response.status_code}")
        except Exception as e:
            print(f"Error accessing Qdrant: {e}")
            await es.close()
            return
        
        print()
        
        # 3. Check Qdrant Payload (metadata stored with vectors)
        print("="*80)
        print("3. QDRANT PAYLOAD (Metadata stored with vectors)")
        print("="*80)
        
        # Get a sample point using direct API call
        try:
            async with httpx.AsyncClient() as client:
                # Use scroll API directly
                scroll_response = await client.post(
                    f"{QDRANT_URL}/collections/{collection_name}/points/scroll",
                    json={
                        "limit": 1,
                        "with_payload": True,
                        "with_vectors": False
                    },
                    timeout=5.0
                )
                
                if scroll_response.status_code == 200:
                    scroll_data = scroll_response.json()
                    points = scroll_data.get("result", {}).get("points", [])
                    
                    if points:
                        point = points[0]
                        payload = point.get("payload", {})
                        print(f"Sample Product: {payload.get('name', 'N/A')}")
                        print(f"Product ID: {payload.get('product_id', 'N/A')}")
                        print()
                        print("Payload fields:")
                        for key, value in payload.items():
                            if key == 'category_id':
                                print(f"  {key}: {value} (type: {type(value).__name__})")
                            elif key == 'category_name':
                                print(f"  {key}: {value} (type: {type(value).__name__})")
                            else:
                                val_str = str(value)[:50] if value else "None"
                                print(f"  {key}: {val_str}... (type: {type(value).__name__})")
                    else:
                        print("No points found in Qdrant")
                else:
                    print(f"Error querying Qdrant: {scroll_response.status_code}")
        except Exception as e:
            print(f"Error accessing Qdrant payload: {e}")
        
        print()
        
        # 4. Check Embedding Text (what text was used to generate embeddings)
        print("="*80)
        print("4. EMBEDDING TEXT (What text was used for semantic search)")
        print("="*80)
        
        if response['hits']['hits']:
            es_doc = response['hits']['hits'][0]['_source']
            embedding_text = prepare_embedding_text(es_doc)
            print(f"Sample Product: {es_doc.get('name', 'N/A')}")
            print()
            print("Embedding Text:")
            print(f"  {embedding_text}")
            print()
            print("Analysis:")
            if "Category:" in embedding_text:
                # Extract category part
                category_part = embedding_text.split("Category:")[1].split("|")[0].strip()
                print(f"  [OK] Category information included: {category_part}")
                if category_part.replace(",", "").replace(" ", "").isdigit():
                    print(f"  [WARNING] Only category IDs in embedding text, not names!")
                else:
                    print(f"  [OK] Category names/values present in embedding text")
            else:
                print(f"  [ERROR] No category information in embedding text")
        
        print()
        
        # 5. Summary
        print("="*80)
        print("5. SUMMARY")
        print("="*80)
        
        print("\nCategory Information Storage:")
        print("  Elasticsearch:")
        if es_doc.get('categories'):
            cat_type = type(es_doc['categories'][0]).__name__ if isinstance(es_doc['categories'], list) and es_doc['categories'] else type(es_doc['categories']).__name__
            print(f"    - Categories stored as: {cat_type}")
            if isinstance(es_doc['categories'], list) and es_doc['categories']:
                if isinstance(es_doc['categories'][0], str) and es_doc['categories'][0].isdigit():
                    print(f"    - [WARNING] Only IDs, not names")
                elif isinstance(es_doc['categories'][0], dict):
                    print(f"    - [OK] Has category objects with names")
                else:
                    print(f"    - Value: {es_doc['categories'][0]}")
        
        # Check Qdrant payload from API call
        payload = None
        try:
            async with httpx.AsyncClient() as client:
                scroll_response = await client.post(
                    f"{QDRANT_URL}/collections/{collection_name}/points/scroll",
                    json={"limit": 1, "with_payload": True, "with_vectors": False},
                    timeout=5.0
                )
                if scroll_response.status_code == 200:
                    points = scroll_response.json().get("result", {}).get("points", [])
                    if points:
                        payload = points[0].get("payload", {})
                        print(f"  Qdrant Payload:")
                        print(f"    - category_id: {payload.get('category_id', 'N/A')}")
                        print(f"    - category_name: {payload.get('category_name', 'N/A')}")
                        if payload.get('category_name'):
                            print(f"    - [OK] Has category name in payload")
                        else:
                            print(f"    - [WARNING] No category name in payload")
        except Exception as e:
            print(f"  Qdrant Payload: Could not retrieve - {e}")
        
        print(f"  Embedding Text:")
        if "Category:" in embedding_text:
            category_part = embedding_text.split("Category:")[1].split("|")[0].strip()
            if category_part.replace(",", "").replace(" ", "").isdigit():
                print(f"    - [WARNING] Only category IDs in embedding text")
                print(f"    - [ERROR] PROBLEM: Semantic search won't understand category names!")
            else:
                print(f"    - [OK] Category names/values in embedding text")
        else:
            print(f"    - [ERROR] No category information in embedding text")
        
        print()
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await es.close()


async def main():
    parser = argparse.ArgumentParser(description="Inspect data storage")
    parser.add_argument("--merchant-id", type=int, default=1, help="Merchant ID")
    
    args = parser.parse_args()
    await inspect_data(args.merchant_id)


if __name__ == "__main__":
    asyncio.run(main())

