"""
Data exploration script to understand ingested product data.

This script provides insights into the product catalog to help create
meaningful semantic search tests and verify data completeness.

Usage:
    python scripts/explore_product_data.py --merchant-id 1 [--sample-size 10]
"""

import asyncio
import sys
import os
from pathlib import Path
import json
from collections import Counter, defaultdict
from typing import Dict, Any, List

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


def prepare_embedding_text(product: Dict[str, Any]) -> str:
    """
    Prepare product text for embedding generation (same logic as EmbeddingGenerator)
    
    Args:
        product: Product dictionary
        
    Returns:
        Combined text for embedding
    """
    parts = []
    
    # Product name (most important)
    if product.get("name"):
        parts.append(product["name"])
    
    # Description
    if product.get("description"):
        desc = product["description"]
        # Limit description length
        if len(desc) > 500:
            desc = desc[:500] + "..."
        parts.append(desc)
    elif product.get("short_description"):
        parts.append(product["short_description"])
    
    # Categories
    categories = product.get("categories", [])
    if categories:
        # Extract category names if they're objects
        if isinstance(categories[0], dict):
            category_names = [cat.get("name", cat.get("title", "")) for cat in categories if cat.get("name") or cat.get("title")]
        else:
            category_names = [str(cat) for cat in categories]
        if category_names:
            parts.append(f"Category: {', '.join(category_names)}")
    
    # Brand
    if product.get("brand"):
        parts.append(f"Brand: {product['brand']}")
    
    # Key attributes (color, size, material, etc.)
    attributes = product.get("attributes", {})
    if isinstance(attributes, dict):
        key_attrs = []
        for key in ["color", "size", "material", "style", "type"]:
            if key in attributes and attributes[key]:
                key_attrs.append(f"{key}: {attributes[key]}")
        if key_attrs:
            parts.append("Attributes: " + ", ".join(key_attrs))
    
    return " | ".join(parts)


async def explore_product_data(merchant_id: int, sample_size: int = 10):
    """Explore product data in Elasticsearch"""
    es = AsyncElasticsearch([ES_URL])
    
    index_name = f"discovery_products_m{merchant_id}"
    
    print("="*80)
    print("PRODUCT DATA EXPLORATION")
    print("="*80)
    print(f"Merchant ID: {merchant_id}")
    print(f"Index: {index_name}")
    print()
    
    try:
        # Check if index exists
        exists = await es.indices.exists(index=index_name)
        if not exists:
            print(f"❌ ERROR: Index {index_name} does not exist!")
            await es.close()
            return
        
        print(f"✅ Index {index_name} exists")
        print()
        
        # Get total document count
        stats = await es.indices.stats(index=index_name)
        total_docs = stats['indices'][index_name]['total']['docs']['count']
        print(f"📊 Total Products: {total_docs}")
        print()
        
        # Fetch all products for analysis (or sample if too many)
        max_fetch = min(1000, total_docs)  # Limit to 1000 for performance
        
        query = {
            "query": {"match_all": {}},
            "size": max_fetch,
            "_source": True
        }
        
        response = await es.search(index=index_name, body=query)
        products = [hit["_source"] for hit in response['hits']['hits']]
        
        if not products:
            print("❌ No products found in index")
            await es.close()
            return
        
        print(f"📦 Analyzing {len(products)} products")
        print()
        
        # ============================================================
        # 1. SUMMARY STATISTICS
        # ============================================================
        print("="*80)
        print("1. SUMMARY STATISTICS")
        print("="*80)
        
        # Data completeness
        with_price = sum(1 for p in products if p.get("price", 0) > 0)
        with_image = sum(1 for p in products if p.get("image_url"))
        with_categories = sum(1 for p in products if p.get("categories"))
        with_description = sum(1 for p in products if p.get("description") or p.get("short_description"))
        with_category_ids = sum(1 for p in products if p.get("category_ids"))
        with_brand = sum(1 for p in products if p.get("brand"))
        with_attributes = sum(1 for p in products if p.get("attributes") and isinstance(p.get("attributes"), dict) and len(p.get("attributes", {})) > 0)
        
        print(f"Products with price > 0: {with_price}/{len(products)} ({with_price/len(products)*100:.1f}%)")
        print(f"Products with image URL: {with_image}/{len(products)} ({with_image/len(products)*100:.1f}%)")
        print(f"Products with categories: {with_categories}/{len(products)} ({with_categories/len(products)*100:.1f}%)")
        print(f"Products with category_ids: {with_category_ids}/{len(products)} ({with_category_ids/len(products)*100:.1f}%)")
        print(f"Products with description: {with_description}/{len(products)} ({with_description/len(products)*100:.1f}%)")
        print(f"Products with brand: {with_brand}/{len(products)} ({with_brand/len(products)*100:.1f}%)")
        print(f"Products with attributes: {with_attributes}/{len(products)} ({with_attributes/len(products)*100:.1f}%)")
        print()
        
        # ============================================================
        # 2. PRICE DISTRIBUTION
        # ============================================================
        print("="*80)
        print("2. PRICE DISTRIBUTION")
        print("="*80)
        
        prices = [p.get("price", 0) for p in products if p.get("price", 0) > 0]
        
        if prices:
            print(f"Min Price: ${min(prices):.2f}")
            print(f"Max Price: ${max(prices):.2f}")
            print(f"Average Price: ${sum(prices)/len(prices):.2f}")
            print()
            
            # Price ranges
            ranges = {
                "$0-$50": sum(1 for p in prices if 0 < p <= 50),
                "$50-$100": sum(1 for p in prices if 50 < p <= 100),
                "$100-$200": sum(1 for p in prices if 100 < p <= 200),
                "$200-$500": sum(1 for p in prices if 200 < p <= 500),
                "$500+": sum(1 for p in prices if p > 500)
            }
            
            print("Price Range Distribution:")
            for range_name, count in ranges.items():
                if count > 0:
                    print(f"  {range_name}: {count} products ({count/len(prices)*100:.1f}%)")
        else:
            print("⚠️  No products with prices > 0")
        
        print()
        
        # ============================================================
        # 3. CATEGORY DISTRIBUTION
        # ============================================================
        print("="*80)
        print("3. CATEGORY DISTRIBUTION")
        print("="*80)
        
        category_counter = Counter()
        category_id_counter = Counter()
        for product in products:
            categories = product.get("categories", [])
            if categories:
                if isinstance(categories[0], dict):
                    # Extract category names
                    for cat in categories:
                        cat_name = cat.get("name") or cat.get("title") or str(cat.get("id", ""))
                        if cat_name:
                            category_counter[cat_name] += 1
                else:
                    # Categories are strings/IDs
                    for cat in categories:
                        category_counter[str(cat)] += 1
            category_ids = product.get("category_ids", [])
            if category_ids:
                for cat_id in category_ids:
                    category_id_counter[str(cat_id)] += 1
        
        if category_counter:
            print(f"Total Unique Categories: {len(category_counter)}")
            print()
            print("Top 20 Categories:")
            for cat_name, count in category_counter.most_common(20):
                print(f"  {cat_name}: {count} products ({count/len(products)*100:.1f}%)")
            if category_id_counter:
                print()
                print("Top 20 Category IDs:")
                for cat_id, count in category_id_counter.most_common(20):
                    print(f"  {cat_id}: {count} products ({count/len(products)*100:.1f}%)")
        else:
            print("⚠️  No categories found in products")
        
        print()
        
        # ============================================================
        # 4. BRAND DISTRIBUTION
        # ============================================================
        print("="*80)
        print("4. BRAND DISTRIBUTION")
        print("="*80)
        
        brand_counter = Counter()
        for product in products:
            brand = product.get("brand")
            if brand:
                brand_counter[str(brand)] += 1
        
        if brand_counter:
            print(f"Total Unique Brands: {len(brand_counter)}")
            print()
            print("Top 20 Brands:")
            for brand, count in brand_counter.most_common(20):
                print(f"  {brand}: {count} products ({count/len(products)*100:.1f}%)")
        else:
            print("⚠️  No brands found in products")
        
        print()
        
        # ============================================================
        # 5. ATTRIBUTE AVAILABILITY
        # ============================================================
        print("="*80)
        print("5. ATTRIBUTE AVAILABILITY")
        print("="*80)
        
        attribute_keys = defaultdict(int)
        key_attributes = ["color", "size", "material", "style", "type"]
        
        for product in products:
            attrs = product.get("attributes", {})
            if isinstance(attrs, dict):
                for key in attrs.keys():
                    attribute_keys[key] += 1
        
        if attribute_keys:
            print(f"Total Unique Attribute Keys: {len(attribute_keys)}")
            print()
            print("All Attribute Keys (sorted by frequency):")
            for key, count in sorted(attribute_keys.items(), key=lambda x: x[1], reverse=True):
                print(f"  {key}: {count} products ({count/len(products)*100:.1f}%)")
            
            print()
            print("Key Attributes for Embeddings (color, size, material, style, type):")
            for key in key_attributes:
                count = attribute_keys.get(key, 0)
                if count > 0:
                    print(f"  ✅ {key}: {count} products ({count/len(products)*100:.1f}%)")
                else:
                    print(f"  ❌ {key}: Not found")
        else:
            print("⚠️  No attributes found in products")
        
        print()
        
        # ============================================================
        # 6. SAMPLE PRODUCTS
        # ============================================================
        print("="*80)
        print("6. SAMPLE PRODUCTS")
        print("="*80)
        
        # Get products with complete data for samples
        complete_products = [
            p for p in products 
            if p.get("name") and p.get("price", 0) > 0 and p.get("categories") and (p.get("description") or p.get("short_description"))
        ]
        
        if not complete_products:
            complete_products = products[:sample_size]  # Fallback to first N
        
        sample_products = complete_products[:sample_size]
        
        print(f"Showing {len(sample_products)} sample products (with complete data):")
        print()
        
        for i, product in enumerate(sample_products, 1):
            print(f"--- Product {i} ---")
            print(f"ID: {product.get('product_id') or product.get('id', 'N/A')}")
            print(f"SKU: {product.get('sku', 'N/A')}")
            print(f"Name: {product.get('name', 'N/A')}")
            print(f"Price: ${product.get('price', 0):.2f}")
            if product.get('special_price'):
                print(f"Special Price: ${product.get('special_price'):.2f}")
            print(f"Brand: {product.get('brand', 'N/A')}")
            print(f"Categories: {product.get('categories', [])}")
            print(f"Image URL: {product.get('image_url', 'N/A')[:80]}..." if product.get('image_url') else "Image URL: N/A")
            print(f"Description: {str(product.get('description', product.get('short_description', 'N/A')))[:100]}...")
            print(f"Attributes: {list(product.get('attributes', {}).keys())[:5]}..." if product.get('attributes') else "Attributes: N/A")
            print()
        
        # ============================================================
        # 7. SAMPLE EMBEDDING TEXTS
        # ============================================================
        print("="*80)
        print("7. SAMPLE EMBEDDING TEXTS")
        print("="*80)
        
        print("Preview of embedding text that will be generated for semantic search:")
        print()
        
        for i, product in enumerate(sample_products[:5], 1):
            embedding_text = prepare_embedding_text(product)
            print(f"--- Product {i} Embedding Text ---")
            print(f"Product: {product.get('name', 'N/A')}")
            print(f"Embedding Text ({len(embedding_text)} chars):")
            print(f"  {embedding_text}")
            print()
        
        # ============================================================
        # 8. PRODUCTS SUITABLE FOR SEMANTIC SEARCH TESTING
        # ============================================================
        print("="*80)
        print("8. PRODUCTS SUITABLE FOR SEMANTIC SEARCH TESTING")
        print("="*80)
        
        # Products with good data for semantic search
        good_for_semantic = [
            p for p in products
            if p.get("name") and 
               (p.get("description") or p.get("short_description")) and
               p.get("categories") and
               p.get("price", 0) > 0
        ]
        
        print(f"Products suitable for semantic search testing: {len(good_for_semantic)}/{len(products)} ({len(good_for_semantic)/len(products)*100:.1f}%)")
        print()
        
        if good_for_semantic:
            print("Sample queries you can test:")
            print()
            
            # Suggest queries based on data
            if category_counter:
                top_category = category_counter.most_common(1)[0][0]
                print(f"  - Category search: '{top_category}'")
            
            if brand_counter:
                top_brand = brand_counter.most_common(1)[0][0]
                print(f"  - Brand search: '{top_brand}'")
            
            if prices:
                avg_price = sum(prices) / len(prices)
                print(f"  - Price-based: 'affordable products' (avg: ${avg_price:.2f})")
            
            if any("color" in str(p.get("attributes", {})).lower() for p in products):
                print(f"  - Attribute search: 'red products' or 'blue items'")
            
            print(f"  - General: 'products', 'items', 'goods'")
        
        print()
        
        # ============================================================
        # SUMMARY
        # ============================================================
        print("="*80)
        print("EXPLORATION SUMMARY")
        print("="*80)
        print(f"✅ Total Products: {total_docs}")
        print(f"✅ Data Completeness: {with_price/len(products)*100:.1f}% (price), {with_categories/len(products)*100:.1f}% (categories), {with_description/len(products)*100:.1f}% (description)")
        print(f"✅ Categories: {len(category_counter)} unique")
        print(f"✅ Brands: {len(brand_counter)} unique")
        print(f"✅ Attributes: {len(attribute_keys)} unique keys")
        print(f"✅ Ready for Semantic Search: {len(good_for_semantic)}/{len(products)} products")
        print("="*80)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await es.close()


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Explore product data in Elasticsearch")
    parser.add_argument("--merchant-id", type=int, required=True, help="Merchant ID")
    parser.add_argument("--sample-size", type=int, default=10, help="Number of sample products to show")
    
    args = parser.parse_args()
    
    await explore_product_data(args.merchant_id, args.sample_size)


if __name__ == "__main__":
    asyncio.run(main())

