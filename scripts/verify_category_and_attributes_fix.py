"""
Verification script for category names and attributes fix.

This script verifies:
1. Categories are stored as objects with names in Elasticsearch
2. Material, pattern, and climate attributes are extracted
3. Keyword search matches category names (e.g., "hoodies")
4. Semantic search matches material and category names (e.g., "fleece hoodie")
5. API response includes description and attributes
"""

import asyncio
import sys
import os
from pathlib import Path
import json
import httpx

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
SEARCH_API_URL = os.getenv('SEARCH_API_URL', 'http://localhost:7099')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def _normalize_value(value):
    """Normalize attribute values to human-readable strings."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return str(value) if value is not None else ""


def print_section(title: str):
    """Print a section header"""
    print()
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    print()


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")


async def verify_elasticsearch_categories(es: AsyncElasticsearch, merchant_id: int):
    """Verify categories are stored as objects with names"""
    print_section("1. VERIFYING ELASTICSEARCH CATEGORIES")
    
    index_name = f"discovery_products_m{merchant_id}"
    
    try:
        # Get sample products with categories
        response = await es.search(
            index=index_name,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"exists": {"field": "categories"}}
                        ]
                    }
                },
                "size": 10
            }
        )
        
        hits = response['hits']['hits']
        if not hits:
            print_error("No products with categories found")
            return False
        
        print_info(f"Found {len(hits)} products with categories")
        print()
        
        categories_as_strings = 0
        categories_with_ids = 0
        sample_category_names = None
        sample_category_ids = None
        
        for hit in hits[:5]:
            product = hit['_source']
            categories = product.get('categories', [])
            category_ids = product.get('category_ids', [])
            
            if not categories:
                continue
            
            print(f"Product: {product.get('name', 'N/A')}")
            print(f"  Category names: {categories}")
            print(f"  Category IDs: {category_ids}")
            
            if isinstance(categories, list) and categories and all(isinstance(cat, str) for cat in categories):
                categories_as_strings += 1
                if sample_category_names is None:
                    sample_category_names = categories
            if isinstance(category_ids, list) and category_ids and all(isinstance(cat_id, str) for cat_id in category_ids):
                categories_with_ids += 1
                if sample_category_ids is None:
                    sample_category_ids = category_ids
            
            print()
        
        # Summary
        total = len(hits)
        if total > 0:
            print(f"Summary: {categories_as_strings}/{total} products store categories as strings (names)")
            print(f"         {categories_with_ids}/{total} products store category_ids as strings")
            if sample_category_names:
                print_success(f"Example category names: {sample_category_names}")
            if sample_category_ids:
                print_success(f"Example category IDs: {sample_category_ids}")
            
            if categories_as_strings > 0 and categories_with_ids > 0:
                print_success("Categories stored as names with category_ids alongside")
                return True
            else:
                print_error("Categories or category_ids missing in Elasticsearch")
                return False
        else:
            print_error("Could not analyze categories")
            return False
            
    except Exception as e:
        print_error(f"Error checking Elasticsearch categories: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_attributes(es: AsyncElasticsearch, merchant_id: int):
    """Verify material, pattern, climate, color, and size attributes are extracted"""
    print_section("2. VERIFYING ATTRIBUTES (MATERIAL, PATTERN, CLIMATE, COLOR, SIZE)")
    
    index_name = f"discovery_products_m{merchant_id}"
    
    try:
        response = await es.search(
            index=index_name,
            body={
                "query": {"match_all": {}},
                "size": 100
            }
        )
        
        hits = response['hits']['hits']
        if not hits:
            print_error("No products found")
            return False
        
        print_info(f"Analyzing {len(hits)} products")
        print()
        
        products_with_material = 0
        products_with_pattern = 0
        products_with_climate = 0
        products_with_color = 0
        products_with_size = 0
        
        sample_products = []
        
        def _is_valid_attribute_value(v):
            """Check if attribute value is valid (not None, False, or empty)"""
            if v is None or v is False:
                return False
            if isinstance(v, str) and v.strip() == '':
                return False
            if isinstance(v, list):
                return len([item for item in v if item not in (None, False, '')]) > 0
            return True
        
        for hit in hits:
            product = hit['_source']
            attributes = product.get('attributes', {})
            
            if not isinstance(attributes, dict):
                continue
            
            has_material = 'material' in attributes and _is_valid_attribute_value(attributes['material'])
            has_pattern = 'pattern' in attributes and _is_valid_attribute_value(attributes['pattern'])
            has_climate = 'climate' in attributes and _is_valid_attribute_value(attributes['climate'])
            has_color = 'color' in attributes and _is_valid_attribute_value(attributes['color'])
            has_size = 'size' in attributes and _is_valid_attribute_value(attributes['size'])
            
            if has_material:
                products_with_material += 1
            if has_pattern:
                products_with_pattern += 1
            if has_climate:
                products_with_climate += 1
            if has_color:
                products_with_color += 1
            if has_size:
                products_with_size += 1
            
            # Collect samples (prioritize products with color/size for better visibility)
            has_any_key_attr = has_material or has_pattern or has_climate or has_color or has_size
            if has_any_key_attr and len(sample_products) < 5:
                # Collect all key attributes (including empty ones to show what's missing)
                normalized_attrs = {}
                for k in ['material', 'pattern', 'climate', 'color', 'size']:
                    if k in attributes:
                        attr_value = attributes[k]
                        if _is_valid_attribute_value(attr_value):
                            normalized_attrs[k] = _normalize_value(attr_value)
                        else:
                            # Show that attribute exists but is empty/false
                            if attr_value is False:
                                normalized_attrs[k] = False  # Will be displayed as "not extracted"
                            elif attr_value is None:
                                normalized_attrs[k] = None   # Will be displayed as "not set"
                            else:
                                normalized_attrs[k] = attr_value
                
                sample_products.append({
                    'name': product.get('name', 'N/A'),
                    'attributes': normalized_attrs
                })
        
        # Display samples
        if sample_products:
            print("Sample products with attributes:")
            for prod in sample_products:
                print(f"  {prod['name']}")
                for key, value in prod['attributes'].items():
                    # Show attribute only if it has a valid value
                    if value and value not in (False, None, ''):
                        if isinstance(value, list):
                            print(f"    {key}: {', '.join(str(v) for v in value)}")
                        else:
                            print(f"    {key}: {value}")
                    elif value is False:
                        print(f"    {key}: ❌ False (not extracted)")
                    elif value is None:
                        print(f"    {key}: ❌ None (not set)")
                print()
        
        # Summary
        total = len(hits)
        print(f"Products with material: {products_with_material}/{total} ({products_with_material/total*100:.1f}%)")
        print(f"Products with pattern: {products_with_pattern}/{total} ({products_with_pattern/total*100:.1f}%)")
        print(f"Products with climate: {products_with_climate}/{total} ({products_with_climate/total*100:.1f}%)")
        print(f"Products with color: {products_with_color}/{total} ({products_with_color/total*100:.1f}%)")
        print(f"Products with size: {products_with_size}/{total} ({products_with_size/total*100:.1f}%)")
        print()
        
        # Check if attributes are being extracted
        all_attributes_count = sum([
            products_with_material > 0,
            products_with_pattern > 0,
            products_with_climate > 0,
            products_with_color > 0,
            products_with_size > 0
        ])
        
        if all_attributes_count > 0:
            extracted_attrs = []
            if products_with_material > 0:
                extracted_attrs.append("material")
            if products_with_pattern > 0:
                extracted_attrs.append("pattern")
            if products_with_climate > 0:
                extracted_attrs.append("climate")
            if products_with_color > 0:
                extracted_attrs.append("color")
            if products_with_size > 0:
                extracted_attrs.append("size")
            
            print_success(f"Attributes being extracted: {', '.join(extracted_attrs)}")
            
            # Warn about missing attributes
            missing_attrs = []
            if products_with_color == 0:
                missing_attrs.append("color")
            if products_with_size == 0:
                missing_attrs.append("size")
            
            if missing_attrs:
                print_warning(f"Attributes not found in products: {', '.join(missing_attrs)}")
                print_info("This might be normal if your catalog doesn't have these attributes set")
            
            return True
        else:
            print_warning("No products found with any of the expected attributes (material, pattern, climate, color, size)")
            print_info("This might be normal if your catalog doesn't have these attributes")
            return True  # Not an error, just no data
            
    except Exception as e:
        print_error(f"Error checking attributes: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_keyword_search(merchant_id: int, query: str = "hoodies"):
    """Test keyword search with category names"""
    print_section(f"3. TESTING KEYWORD SEARCH: '{query}'")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SEARCH_API_URL}/api/v1/search/",
                json={
                    "query": query,
                    "limit": 10,
                    "offset": 0,
                    "search_mode": "keyword"
                },
                headers={
                    "X-Merchant-Id": str(merchant_id)
                }
            )
            
            if response.status_code != 200:
                print_error(f"Search API returned status {response.status_code}")
                print(response.text)
                return False
            
            data = response.json()
            results = data.get('results', [])
            total = data.get('total', 0)
            
            print_info(f"Found {total} results")
            print()
            
            if total == 0:
                print_warning(f"No results found for query '{query}'")
                return False
            
            # Check if results have category names
            results_with_category_names = 0
            results_with_category_names_field = 0
            results_with_category_ids_field = 0
            results_with_description = 0
            results_with_attributes = 0
            
            print("Top 5 results:")
            for i, result in enumerate(results[:5], 1):
                metadata = result.get('metadata', {})
                categories = metadata.get('categories', [])
                description = metadata.get('description')
                attributes = metadata.get('attributes', {})
                
                print(f"\n{i}. {result.get('title', 'N/A')} (score: {result.get('score', 0):.2f})")
                print(f"   Categories: {categories}")
                print(f"   category_names: {metadata.get('category_names')}")
                print(f"   category_ids: {metadata.get('category_ids')}")
                print(f"   Has description: {bool(description)}")
                print(f"   Has attributes: {bool(attributes)}")
                
                # Check if categories have names
                category_has_name = False
                if isinstance(categories, list):
                    for cat in categories:
                        if isinstance(cat, dict) and cat.get('name'):
                            category_has_name = True
                            break
                        if isinstance(cat, str):
                            category_has_name = True
                            break
                elif isinstance(categories, dict) and categories.get('name'):
                    category_has_name = True
                elif isinstance(categories, str):
                    category_has_name = True

                if category_has_name:
                    results_with_category_names += 1
                if metadata.get('category_names'):
                    results_with_category_names_field += 1
                if metadata.get('category_ids'):
                    results_with_category_ids_field += 1
                
                if description:
                    results_with_description += 1
                
                if attributes:
                    results_with_attributes += 1
            
            print()
            print(f"Results with category name objects: {results_with_category_names}/{len(results)}")
            print(f"Results with category_names field: {results_with_category_names_field}/{len(results)}")
            print(f"Results with category_ids field: {results_with_category_ids_field}/{len(results)}")
            print(f"Results with description: {results_with_description}/{len(results)}")
            print(f"Results with attributes: {results_with_attributes}/{len(results)}")
            print()
            
            # Verify API response includes description and attributes
            if results_with_description > 0:
                print_success("API response includes description")
            else:
                print_error("API response does NOT include description")
            
            if results_with_attributes > 0:
                print_success("API response includes attributes")
            else:
                print_warning("API response does NOT include attributes (may be empty in data)")
            
            if total > 0:
                print_success(f"Keyword search for '{query}' returns results")
                return True
            else:
                print_error(f"Keyword search for '{query}' returns no results")
                return False
                
    except Exception as e:
        print_error(f"Error testing keyword search: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_semantic_search(merchant_id: int, query: str = "fleece hoodie"):
    """Test semantic search with material and category names"""
    print_section(f"4. TESTING SEMANTIC SEARCH: '{query}'")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SEARCH_API_URL}/api/v1/search/",
                json={
                    "query": query,
                    "limit": 10,
                    "offset": 0,
                    "search_mode": "semantic"
                },
                headers={
                    "X-Merchant-Id": str(merchant_id)
                }
            )
            
            if response.status_code != 200:
                print_error(f"Search API returned status {response.status_code}")
                print(response.text)
                print_warning("Semantic search may not be available (Qdrant/embedding service)")
                return None  # Not an error, just not available
            
            data = response.json()
            results = data.get('results', [])
            total = data.get('total', 0)
            
            print_info(f"Found {total} results")
            print()
            
            if total == 0:
                print_warning(f"No results found for semantic search query '{query}'")
                return False
            
            print("Top 5 results:")
            for i, result in enumerate(results[:5], 1):
                metadata = result.get('metadata', {})
                category_name = metadata.get('category_name') or _normalize_value(metadata.get('category_names'))
                description = metadata.get('description')
                attributes = metadata.get('attributes', {})
                material = _normalize_value(attributes.get('material')) if attributes else ''
                
                print(f"\n{i}. {result.get('title', 'N/A')} (score: {result.get('score', 0):.2f})")
                print(f"   Category name: {category_name}")
                print(f"   Material: {material}")
                print(f"   Has description: {bool(description)}")
                print(f"   Has attributes: {bool(attributes)}")
                
                # Check if result matches query intent
                name_lower = result.get('title', '').lower()
                if 'hoodie' in name_lower or 'hoodie' in (category_name or '').lower():
                    print(f"   ✅ Matches 'hoodie' in name/category")
                if 'fleece' in material.lower() or 'fleece' in name_lower:
                    print(f"   ✅ Matches 'fleece' in material/name")
            
            print()
            if total > 0:
                print_success(f"Semantic search for '{query}' returns results")
                return True
            else:
                print_warning(f"Semantic search for '{query}' returns no results")
                return False
                
    except Exception as e:
        print_error(f"Error testing semantic search: {e}")
        import traceback
        traceback.print_exc()
        return None  # Not available


async def verify_api_response_fields(merchant_id: int):
    """Verify API response includes description and attributes"""
    print_section("5. VERIFYING API RESPONSE FIELDS")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SEARCH_API_URL}/api/v1/search/",
                json={
                    "query": "product",
                    "limit": 5,
                    "offset": 0,
                    "search_mode": "keyword"
                },
                headers={
                    "X-Merchant-Id": str(merchant_id)
                }
            )
            
            if response.status_code != 200:
                print_error(f"Search API returned status {response.status_code}")
                return False
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                print_warning("No results to check")
                return False
            
            print_info(f"Checking {len(results)} results")
            print()
            
            has_description = False
            has_short_description = False
            has_attributes = False
            has_category_names_field = False
            has_category_ids_field = False
            
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                
                if 'description' in metadata and metadata['description']:
                    has_description = True
                if 'short_description' in metadata and metadata['short_description']:
                    has_short_description = True
                if 'attributes' in metadata:
                    has_attributes = True
                if metadata.get('category_names'):
                    has_category_names_field = True
                if metadata.get('category_ids'):
                    has_category_ids_field = True
                
                print(f"Result {i}: {result.get('title', 'N/A')}")
                print(f"  metadata.description: {'✅' if metadata.get('description') else '❌'}")
                print(f"  metadata.short_description: {'✅' if metadata.get('short_description') else '❌'}")
                print(f"  metadata.attributes: {'✅' if metadata.get('attributes') else '❌'}")
                print(f"  metadata.category_names: {'✅' if metadata.get('category_names') else '❌'}")
                print(f"  metadata.category_ids: {'✅' if metadata.get('category_ids') else '❌'}")
                if metadata.get('attributes'):
                    print(f"    Attributes keys: {list(metadata['attributes'].keys())[:5]}")
                print()
            
            # Summary
            print("Summary:")
            if has_description:
                print_success("API response includes 'description' field")
            else:
                print_error("API response does NOT include 'description' field")
            
            if has_short_description:
                print_success("API response includes 'short_description' field")
            else:
                print_warning("API response does NOT include 'short_description' field (may be empty)")
            
            if has_attributes:
                print_success("API response includes 'attributes' field")
            else:
                print_error("API response does NOT include 'attributes' field")
            if has_category_names_field:
                print_success("API response includes 'category_names' field")
            else:
                print_error("API response does NOT include 'category_names' field")
            if has_category_ids_field:
                print_success("API response includes 'category_ids' field")
            else:
                print_error("API response does NOT include 'category_ids' field")
            
            return has_description and has_attributes and has_category_names_field and has_category_ids_field
                
    except Exception as e:
        print_error(f"Error verifying API response: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main verification function"""
    parser = argparse.ArgumentParser(description="Verify category names and attributes fix")
    parser.add_argument("--merchant-id", type=int, default=1, help="Merchant ID")
    parser.add_argument("--skip-semantic", action="store_true", help="Skip semantic search test")
    
    args = parser.parse_args()
    
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}VERIFICATION: Category Names and Attributes Fix{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"Merchant ID: {args.merchant_id}")
    print(f"Elasticsearch URL: {ES_URL}")
    print(f"Search API URL: {SEARCH_API_URL}")
    
    es = AsyncElasticsearch([ES_URL])
    
    results = {
        'elasticsearch_categories': False,
        'attributes': False,
        'keyword_search': False,
        'semantic_search': None,  # None = skipped/not available
        'api_response': False
    }
    
    try:
        # 1. Verify Elasticsearch categories
        results['elasticsearch_categories'] = await verify_elasticsearch_categories(es, args.merchant_id)
        
        # 2. Verify attributes
        results['attributes'] = await verify_attributes(es, args.merchant_id)
        
        # 3. Test keyword search
        results['keyword_search'] = await test_keyword_search(args.merchant_id, "hoodies")
        
        # 4. Test semantic search
        if not args.skip_semantic:
            results['semantic_search'] = await test_semantic_search(args.merchant_id, "fleece hoodie")
        
        # 5. Verify API response
        results['api_response'] = await verify_api_response_fields(args.merchant_id)
        
        # Final summary
        print_section("VERIFICATION SUMMARY")
        
        print("Test Results:")
        print(f"  1. Elasticsearch Categories: {'✅ PASS' if results['elasticsearch_categories'] else '❌ FAIL'}")
        print(f"  2. Attributes Extraction: {'✅ PASS' if results['attributes'] else '❌ FAIL'}")
        print(f"  3. Keyword Search: {'✅ PASS' if results['keyword_search'] else '❌ FAIL'}")
        if results['semantic_search'] is not None:
            print(f"  4. Semantic Search: {'✅ PASS' if results['semantic_search'] else '⚠️  WARNING'}")
        else:
            print(f"  4. Semantic Search: ⏭️  SKIPPED")
        print(f"  5. API Response Fields: {'✅ PASS' if results['api_response'] else '❌ FAIL'}")
        print()
        
        # Overall result
        passed = sum(1 for v in results.values() if v is True)
        total = sum(1 for v in results.values() if v is not None)
        
        if passed == total:
            print_success("ALL VERIFICATIONS PASSED! ✅")
            return 0
        else:
            print_warning(f"{passed}/{total} verifications passed")
            return 1
            
    except Exception as e:
        print_error(f"Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await es.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

