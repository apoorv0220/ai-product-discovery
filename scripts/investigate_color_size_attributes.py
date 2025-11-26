"""
Investigate why color and size attributes are not being extracted.

This script checks:
1. Product types in the collection
2. Whether color/size attributes exist in Magento
3. How to extract color/size from configurable products and their variants
"""

import asyncio
import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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

ES_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')


async def investigate_attributes(merchant_id: int):
    """Investigate color and size attribute extraction"""
    es = AsyncElasticsearch([ES_URL])
    index_name = f"discovery_products_m{merchant_id}"
    
    print("="*80)
    print("INVESTIGATING COLOR AND SIZE ATTRIBUTES")
    print("="*80)
    print(f"Merchant ID: {merchant_id}")
    print(f"Index: {index_name}")
    print()
    
    try:
        # Get sample products
        response = await es.search(
            index=index_name,
            body={
                "query": {"match_all": {}},
                "size": 20
            }
        )
        
        hits = response['hits']['hits']
        if not hits:
            print("❌ No products found")
            return
        
        print(f"Analyzing {len(hits)} products\n")
        print("="*80)
        print("1. PRODUCT TYPES AND ATTRIBUTES")
        print("="*80)
        print()
        
        # Check product types
        product_types = {}
        products_with_attributes_structure = []
        
        for hit in hits:
            product = hit['_source']
            product_type = product.get('attributes', {}).get('type', 'unknown')
            
            if product_type not in product_types:
                product_types[product_type] = 0
            product_types[product_type] += 1
            
            # Collect detailed attribute info for first 5 products
            if len(products_with_attributes_structure) < 5:
                attrs = product.get('attributes', {})
                products_with_attributes_structure.append({
                    'name': product.get('name', 'N/A'),
                    'sku': product.get('sku', 'N/A'),
                    'type': attrs.get('type', 'N/A'),
                    'attributes': attrs,
                    'has_color_key': 'color' in attrs,
                    'has_size_key': 'size' in attrs,
                    'color_value': attrs.get('color'),
                    'size_value': attrs.get('size'),
                    'color_type': type(attrs.get('color')).__name__ if 'color' in attrs else None,
                    'size_type': type(attrs.get('size')).__name__ if 'size' in attrs else None,
                })
        
        print("Product Types Distribution:")
        for ptype, count in sorted(product_types.items()):
            print(f"  {ptype}: {count} products")
        print()
        
        print("="*80)
        print("2. DETAILED ATTRIBUTE ANALYSIS (Sample Products)")
        print("="*80)
        print()
        
        for i, prod_info in enumerate(products_with_attributes_structure, 1):
            print(f"Product {i}: {prod_info['name']}")
            print(f"  SKU: {prod_info['sku']}")
            print(f"  Type: {prod_info['type']}")
            print(f"  Has 'color' key: {prod_info['has_color_key']}")
            print(f"  Has 'size' key: {prod_info['has_size_key']}")
            
            if prod_info['has_color_key']:
                print(f"  Color value: {prod_info['color_value']} (type: {prod_info['color_type']})")
            else:
                print(f"  Color: ❌ Key not present in attributes")
            
            if prod_info['has_size_key']:
                print(f"  Size value: {prod_info['size_value']} (type: {prod_info['size_type']})")
            else:
                print(f"  Size: ❌ Key not present in attributes")
            
            print(f"  All attribute keys: {list(prod_info['attributes'].keys())}")
            print()
        
        print("="*80)
        print("3. COLOR/SIZE EXTRACTION STATISTICS")
        print("="*80)
        print()
        
        products_with_color_key = 0
        products_with_size_key = 0
        products_with_color_value = 0
        products_with_size_value = 0
        color_false_count = 0
        size_false_count = 0
        color_none_count = 0
        size_none_count = 0
        
        for hit in hits:
            attrs = hit['_source'].get('attributes', {})
            
            if 'color' in attrs:
                products_with_color_key += 1
                color_val = attrs['color']
                if color_val is False:
                    color_false_count += 1
                elif color_val is None:
                    color_none_count += 1
                elif color_val not in (None, False, ''):
                    products_with_color_value += 1
            
            if 'size' in attrs:
                products_with_size_key += 1
                size_val = attrs['size']
                if size_val is False:
                    size_false_count += 1
                elif size_val is None:
                    size_none_count += 1
                elif size_val not in (None, False, ''):
                    products_with_size_value += 1
        
        print(f"Products with 'color' key: {products_with_color_key}/{len(hits)} ({products_with_color_key/len(hits)*100:.1f}%)")
        if products_with_color_key > 0:
            print(f"  - With valid value: {products_with_color_value}")
            print(f"  - With False: {color_false_count}")
            print(f"  - With None: {color_none_count}")
        
        print(f"Products with 'size' key: {products_with_size_key}/{len(hits)} ({products_with_size_key/len(hits)*100:.1f}%)")
        if products_with_size_key > 0:
            print(f"  - With valid value: {products_with_size_value}")
            print(f"  - With False: {size_false_count}")
            print(f"  - With None: {size_none_count}")
        print()
        
        print("="*80)
        print("4. RECOMMENDATIONS")
        print("="*80)
        print()
        
        if products_with_color_key == 0 and products_with_size_key == 0:
            print("❌ Color and size keys are NOT being added to attributes at all.")
            print("   This suggests the extraction code is filtering them out completely.")
            print("   Possible causes:")
            print("   1. getAttributeText() returns false and it's being filtered")
            print("   2. Attributes don't exist on the products being synced")
            print("   3. Products are configurable and attributes are on variants")
        elif products_with_color_key > 0 and products_with_color_value == 0:
            print("⚠️  Color key exists but all values are False/None/empty")
            print("   This suggests:")
            print("   1. Products don't have color values set in Magento")
            print("   2. Color is a variant attribute (configurable products)")
            print("   3. Attribute code might be wrong (e.g., 'colour' vs 'color')")
        elif products_with_color_value > 0:
            print("✅ Some products DO have color values - extraction is working!")
            print("   Check if all products should have color or only specific types.")
        
        if 'configurable' in product_types:
            print()
            print("📋 CONFIGURABLE PRODUCTS DETECTED")
            print("   Configurable products typically have color/size on variants (simple products)")
            print("   Consider:")
            print("   1. Syncing simple products (variants) instead of/configurable products")
            print("   2. Aggregating all color/size values from variants")
            print("   3. Extracting from configurable product's available options")
        
        print()
        print("="*80)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await es.close()


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Investigate color and size attribute extraction")
    parser.add_argument("--merchant-id", type=int, default=1, help="Merchant ID")
    
    args = parser.parse_args()
    await investigate_attributes(args.merchant_id)


if __name__ == "__main__":
    asyncio.run(main())

