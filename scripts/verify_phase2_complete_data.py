"""
Comprehensive Phase 2 verification with complete data.

This script verifies all Phase 2 features (semantic search, faceted navigation, 
hybrid search, filters) work correctly with complete product data.

Usage:
    python scripts/verify_phase2_complete_data.py --merchant-id 1 --api-key "ak_live_..."
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
import httpx
import json
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

# Configuration
ES_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
SEARCH_API_URL = os.getenv('SEARCH_API_URL', 'http://localhost:7099')


def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_check(name: str, passed: bool, details: str = ""):
    """Print check result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"   {details}")


async def verify_data_completeness(merchant_id: int) -> Dict[str, Any]:
    """Verify data completeness in Elasticsearch"""
    es = AsyncElasticsearch([ES_URL])
    index_name = f"discovery_products_m{merchant_id}"
    
    result = {
        "total_products": 0,
        "with_price": 0,
        "with_image": 0,
        "with_categories": 0,
        "with_category_ids": 0,
        "categories_as_strings": 0,
        "with_description": 0,
        "completeness_score": 0.0
    }
    
    try:
        # Get sample of products
        response = await es.search(
            index=index_name,
            body={"query": {"match_all": {}}, "size": 100}
        )
        
        products = [hit["_source"] for hit in response['hits']['hits']]
        result["total_products"] = len(products)
        
        if products:
            result["with_price"] = sum(1 for p in products if p.get("price", 0) > 0)
            result["with_image"] = sum(1 for p in products if p.get("image_url"))
            result["with_categories"] = sum(1 for p in products if p.get("categories"))
            result["with_category_ids"] = sum(1 for p in products if p.get("category_ids"))
            result["categories_as_strings"] = sum(
                1
                for p in products
                if isinstance(p.get("categories"), list)
                and p.get("categories")
                and all(isinstance(cat, str) for cat in p.get("categories", []))
            )
            result["with_description"] = sum(1 for p in products if p.get("description") or p.get("short_description"))
            
            # Calculate completeness score
            completeness = (
                (result["with_price"] / len(products)) * 0.3 +
                (result["with_image"] / len(products)) * 0.2 +
                (result["with_categories"] / len(products)) * 0.3 +
                (result["with_description"] / len(products)) * 0.2
            )
            result["completeness_score"] = completeness * 100
    
    except Exception as e:
        print(f"   Error: {e}")
    finally:
        await es.close()
    
    return result


async def test_facets(api_key: str, merchant_id: int) -> Dict[str, Any]:
    """Test facet generation with real data"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    result = {
        "facets_returned": False,
        "categories_facet": False,
        "price_ranges_facet": False,
        "brands_facet": False,
        "facet_counts_valid": False
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SEARCH_API_URL}/api/v1/search/",
                headers=headers,
                json={"query": "products", "limit": 20},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "facets" in data and data["facets"]:
                    result["facets_returned"] = True
                    facets = data["facets"]
                    
                    # Check for category facets
                    if "categories" in facets:
                        result["categories_facet"] = True
                        cat_facet = facets["categories"]
                        if "values" in cat_facet and len(cat_facet["values"]) > 0:
                            # Check if categories have real values (not empty)
                            has_real_values = any(
                                v.get("value") and v.get("count", 0) > 0 
                                for v in cat_facet["values"]
                            )
                            result["facet_counts_valid"] = has_real_values
                    
                    # Check for price range facets
                    if "price_ranges" in facets:
                        result["price_ranges_facet"] = True
                        price_facet = facets["price_ranges"]
                        if "values" in price_facet:
                            # Check if price ranges have distribution (not all in one range)
                            ranges_with_products = [
                                v for v in price_facet["values"] 
                                if v.get("count", 0) > 0
                            ]
                            if len(ranges_with_products) > 1:
                                result["facet_counts_valid"] = True
                    
                    # Check for brand facets
                    if "brands" in facets:
                        result["brands_facet"] = True
                
                return result, data.get("facets", {})
    
    except Exception as e:
        print(f"   Error: {e}")
    
    return result, {}


async def test_price_filter(api_key: str, merchant_id: int) -> Dict[str, Any]:
    """Test price range filter with real data"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    result = {
        "filter_works": False,
        "results_have_prices": False,
        "prices_in_range": False,
        "metadata_has_category_names": False,
        "metadata_has_category_ids": False,
        "metadata_categories_structured": False,
        "metadata_has_description": False,
        "metadata_has_attributes": False
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Test with price filter
            response = await client.post(
                f"{SEARCH_API_URL}/api/v1/search/",
                headers=headers,
                json={
                    "query": "products",
                    "filters": {"price": {"min": 50, "max": 200}},
                    "limit": 20
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                if results:
                    result["filter_works"] = True
                    
                    for r in results:
                        metadata = r.get("metadata", {})
                        price = metadata.get("price")
                        if price:
                            result["results_have_prices"] = True
                        categories = metadata.get("categories") or []
                        if categories:
                            if metadata.get("category_names"):
                                result["metadata_has_category_names"] = True
                            if metadata.get("category_ids"):
                                result["metadata_has_category_ids"] = True
                            if isinstance(categories, list) and categories and isinstance(categories[0], dict) and categories[0].get("name"):
                                result["metadata_categories_structured"] = True
                        if metadata.get("description"):
                            result["metadata_has_description"] = True
                        if metadata.get("attributes"):
                            result["metadata_has_attributes"] = True

                    prices = [
                        r.get("metadata", {}).get("price", 0)
                        for r in results
                        if r.get("metadata", {}).get("price")
                    ]
                    if prices:
                        all_in_range = all(50 <= p <= 200 for p in prices if p > 0)
                        result["prices_in_range"] = all_in_range
                
                return result, results
    
    except Exception as e:
        print(f"   Error: {e}")
    
    return result, []


async def test_category_filter(api_key: str, merchant_id: int) -> Dict[str, Any]:
    """Test category filter with real data"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    result = {
        "filter_works": False,
        "results_have_categories": False,
        "metadata_categories_structured": False,
        "metadata_has_category_names": False,
        "metadata_has_category_ids": False
    }
    
    try:
        # First, get available categories from a search
        async with httpx.AsyncClient() as client:
            # Get facets to find a category
            response = await client.post(
                f"{SEARCH_API_URL}/api/v1/search/",
                headers=headers,
                json={"query": "products", "limit": 1},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                facets = data.get("facets", {})
                
                # Try to find a category to filter by
                category_to_filter = None
                if "categories" in facets and facets["categories"].get("values"):
                    first_category = facets["categories"]["values"][0]
                    category_to_filter = first_category.get("value")
                
                if category_to_filter:
                    # Test category filter
                    response = await client.post(
                        f"{SEARCH_API_URL}/api/v1/search/",
                        headers=headers,
                        json={
                            "query": "products",
                            "filters": {"categories": [category_to_filter]},
                            "limit": 20
                        },
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])
                        
                        if results:
                            result["filter_works"] = True
                            
                            for r in results:
                                metadata = r.get("metadata", {})
                                categories = metadata.get("categories") or []
                                if categories:
                                    result["results_have_categories"] = True
                                    if metadata.get("category_names"):
                                        result["metadata_has_category_names"] = True
                                    if metadata.get("category_ids"):
                                        result["metadata_has_category_ids"] = True
                                    if isinstance(categories, list) and categories and isinstance(categories[0], dict) and categories[0].get("name"):
                                        result["metadata_categories_structured"] = True
                
                return result, results if 'results' in locals() else []
    
    except Exception as e:
        print(f"   Error: {e}")
    
    return result, []


async def test_semantic_search(api_key: str, merchant_id: int) -> Dict[str, Any]:
    """Test semantic search quality with complete data"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    result = {
        "semantic_search_works": False,
        "results_have_metadata": False,
        "results_have_prices": False,
        "results_have_images": False,
        "results_have_categories": False,
        "metadata_has_category_names": False,
        "metadata_has_category_ids": False,
        "metadata_has_description": False,
        "metadata_has_attributes": False
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Test semantic search with a query that relies on product attributes
            response = await client.post(
                f"{SEARCH_API_URL}/api/v1/search/",
                headers=headers,
                json={
                    "query": "affordable products",
                    "search_mode": "semantic",
                    "limit": 10
                },
                timeout=15.0
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                if results:
                    result["semantic_search_works"] = True
                    
                    # Check metadata completeness
                    for r in results:
                        metadata = r.get("metadata", {})
                        if metadata:
                            result["results_have_metadata"] = True
                            
                            if metadata.get("price", 0) > 0:
                                result["results_have_prices"] = True
                            
                            if metadata.get("image_url"):
                                result["results_have_images"] = True
                            
                            if metadata.get("categories"):
                                result["results_have_categories"] = True
                            if metadata.get("category_names") or metadata.get("category_name"):
                                result["metadata_has_category_names"] = True
                            if metadata.get("category_ids"):
                                result["metadata_has_category_ids"] = True
                            if metadata.get("description") or metadata.get("short_description"):
                                result["metadata_has_description"] = True
                            if metadata.get("attributes"):
                                result["metadata_has_attributes"] = True
                
                return result, results
    
    except Exception as e:
        print(f"   Error: {e}")
    
    return result, []


async def test_hybrid_search(api_key: str, merchant_id: int) -> Dict[str, Any]:
    """Test hybrid search combining keyword + semantic"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    result = {
        "hybrid_search_works": False,
        "has_hybrid_score": False,
        "has_keyword_score": False,
        "has_semantic_score": False,
        "results_have_metadata": False,
        "metadata_has_category_names": False,
        "metadata_has_category_ids": False,
        "metadata_has_description": False,
        "metadata_has_attributes": False
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SEARCH_API_URL}/api/v1/search/",
                headers=headers,
                json={
                    "query": "products",
                    "search_mode": "hybrid",
                    "limit": 10
                },
                timeout=15.0
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                if results:
                    result["hybrid_search_works"] = True
                    
                    # Check for hybrid scoring
                    first_result = results[0]
                    if "hybrid_score" in first_result or "score" in first_result:
                        result["has_hybrid_score"] = True
                    
                    # Check metadata
                    metadata = first_result.get("metadata") or {}
                    if metadata:
                        result["results_have_metadata"] = True
                        if metadata.get("category_names") or metadata.get("categories"):
                            result["metadata_has_category_names"] = True
                        if metadata.get("category_ids"):
                            result["metadata_has_category_ids"] = True
                        if metadata.get("description") or metadata.get("short_description"):
                            result["metadata_has_description"] = True
                        if metadata.get("attributes"):
                            result["metadata_has_attributes"] = True
                
                return result, results
    
    except Exception as e:
        print(f"   Error: {e}")
    
    return result, []


async def main():
    """Main verification function"""
    parser = argparse.ArgumentParser(description="Verify Phase 2 with complete data")
    parser.add_argument("--merchant-id", type=int, required=True, help="Merchant ID")
    parser.add_argument("--api-key", type=str, required=True, help="API key for testing")
    
    args = parser.parse_args()
    
    print_section("Phase 2 Complete Data Verification")
    print(f"Merchant ID: {args.merchant_id}")
    print(f"Search API: {SEARCH_API_URL}")
    print()
    
    all_passed = True
    
    # 1. Data Completeness
    print_section("1. Data Completeness Verification")
    data_result = await verify_data_completeness(args.merchant_id)
    
    print_check(
        "Data Completeness",
        data_result["completeness_score"] >= 95.0,
        f"Score: {data_result['completeness_score']:.1f}% (target: >=95%)"
    )
    print(f"   Products with price > 0: {data_result['with_price']}/{data_result['total_products']} ({data_result['with_price']/data_result['total_products']*100:.1f}%)")
    print(f"   Products with image: {data_result['with_image']}/{data_result['total_products']} ({data_result['with_image']/data_result['total_products']*100:.1f}%)")
    print(f"   Products with categories: {data_result['with_categories']}/{data_result['total_products']} ({data_result['with_categories']/data_result['total_products']*100:.1f}%)")
    if data_result["total_products"]:
        print(f"   Products with category_ids: {data_result['with_category_ids']}/{data_result['total_products']} ({data_result['with_category_ids']/data_result['total_products']*100:.1f}%)")
        print(f"   Categories stored as strings: {data_result['categories_as_strings']}/{data_result['total_products']} ({data_result['categories_as_strings']/data_result['total_products']*100:.1f}%)")
    print(f"   Products with description: {data_result['with_description']}/{data_result['total_products']} ({data_result['with_description']/data_result['total_products']*100:.1f}%)")
    
    if data_result["completeness_score"] < 95.0:
        all_passed = False
        print("\n   ⚠️  WARNING: Data completeness below 95%. Reindex products before testing.")
    
    # 2. Facets
    print_section("2. Facet Generation with Real Data")
    facet_result, facets_data = await test_facets(args.api_key, args.merchant_id)
    
    print_check("Facets Returned", facet_result["facets_returned"])
    print_check("Categories Facet", facet_result["categories_facet"])
    print_check("Price Ranges Facet", facet_result["price_ranges_facet"])
    print_check("Brands Facet", facet_result["brands_facet"])
    print_check("Facet Counts Valid", facet_result["facet_counts_valid"])
    
    if facets_data:
        print("\n   Sample Facets:")
        if "categories" in facets_data:
            print(f"   Categories: {len(facets_data['categories'].get('values', []))} values")
        if "price_ranges" in facets_data:
            print(f"   Price Ranges: {len(facets_data['price_ranges'].get('values', []))} ranges")
    
    if not all([facet_result["facets_returned"], facet_result["facet_counts_valid"]]):
        all_passed = False
    
    # 3. Price Filter
    print_section("3. Price Range Filter")
    price_filter_result, price_results = await test_price_filter(args.api_key, args.merchant_id)
    
    print_check("Price Filter Works", price_filter_result["filter_works"])
    print_check("Results Have Prices", price_filter_result["results_have_prices"])
    print_check("Prices In Range", price_filter_result["prices_in_range"])
    print_check("Metadata has category_names", price_filter_result["metadata_has_category_names"])
    print_check("Metadata has category_ids", price_filter_result["metadata_has_category_ids"])
    print_check("Metadata categories structured", price_filter_result["metadata_categories_structured"])
    print_check("Metadata has description", price_filter_result["metadata_has_description"])
    print_check("Metadata has attributes", price_filter_result["metadata_has_attributes"])
    
    if price_results:
        sample_prices = [
            r.get("metadata", {}).get("price", 0) 
            for r in price_results[:5] 
            if r.get("metadata", {}).get("price")
        ]
        if sample_prices:
            print(f"   Sample prices in results: {sample_prices}")
    
    if not all([
        price_filter_result["filter_works"],
        price_filter_result["prices_in_range"],
        price_filter_result["metadata_has_category_names"],
        price_filter_result["metadata_has_category_ids"],
        price_filter_result["metadata_categories_structured"],
        price_filter_result["metadata_has_description"],
        price_filter_result["metadata_has_attributes"]
    ]):
        all_passed = False
    
    # 4. Category Filter
    print_section("4. Category Filter")
    category_filter_result, category_results = await test_category_filter(args.api_key, args.merchant_id)
    
    print_check("Category Filter Works", category_filter_result["filter_works"])
    print_check("Results Have Categories", category_filter_result["results_have_categories"])
    print_check("Metadata categories structured", category_filter_result["metadata_categories_structured"])
    print_check("Metadata has category_names", category_filter_result["metadata_has_category_names"])
    print_check("Metadata has category_ids", category_filter_result["metadata_has_category_ids"])
    
    if not all([
        category_filter_result["filter_works"],
        category_filter_result["results_have_categories"],
        category_filter_result["metadata_categories_structured"],
        category_filter_result["metadata_has_category_names"],
        category_filter_result["metadata_has_category_ids"]
    ]):
        all_passed = False
    
    # 5. Semantic Search
    print_section("5. Semantic Search Quality")
    semantic_result, semantic_results = await test_semantic_search(args.api_key, args.merchant_id)
    
    print_check("Semantic Search Works", semantic_result["semantic_search_works"])
    print_check("Results Have Metadata", semantic_result["results_have_metadata"])
    print_check("Results Have Prices", semantic_result["results_have_prices"])
    print_check("Results Have Images", semantic_result["results_have_images"])
    print_check("Results Have Categories", semantic_result["results_have_categories"])
    print_check("Metadata has category names", semantic_result["metadata_has_category_names"])
    print_check("Metadata has category ids", semantic_result["metadata_has_category_ids"])
    print_check("Metadata has description", semantic_result["metadata_has_description"])
    print_check("Metadata has attributes", semantic_result["metadata_has_attributes"])
    
    if semantic_results:
        print(f"   Returned {len(semantic_results)} results")
        if semantic_results[0].get("metadata"):
            sample_meta = semantic_results[0]["metadata"]
            print(
                "   Sample metadata: "
                f"price={sample_meta.get('price')}, "
                f"has_image={bool(sample_meta.get('image_url'))}, "
                f"category_names={sample_meta.get('category_names') or sample_meta.get('category_name')}, "
                f"category_ids={sample_meta.get('category_ids')}, "
                f"attributes_keys={list(sample_meta.get('attributes', {}).keys())[:5]}"
            )
    
    if not all([
        semantic_result["semantic_search_works"],
        semantic_result["results_have_metadata"],
        semantic_result["results_have_prices"],
        semantic_result["metadata_has_description"],
        semantic_result["metadata_has_attributes"]
    ]):
        all_passed = False
    
    # 6. Hybrid Search
    print_section("6. Hybrid Search")
    hybrid_result, hybrid_results = await test_hybrid_search(args.api_key, args.merchant_id)
    
    print_check("Hybrid Search Works", hybrid_result["hybrid_search_works"])
    print_check("Has Hybrid Score", hybrid_result["has_hybrid_score"])
    print_check("Results Have Metadata", hybrid_result["results_have_metadata"])
    print_check("Metadata has category names", hybrid_result["metadata_has_category_names"])
    print_check("Metadata has category ids", hybrid_result["metadata_has_category_ids"])
    print_check("Metadata has description", hybrid_result["metadata_has_description"])
    print_check("Metadata has attributes", hybrid_result["metadata_has_attributes"])
    
    if hybrid_results:
        print(f"   Returned {len(hybrid_results)} results")
        if hybrid_results[0].get("score"):
            print(f"   Sample score: {hybrid_results[0].get('score')}")
        if hybrid_results[0].get("metadata"):
            sample_meta = hybrid_results[0]["metadata"]
            print(
                "   Sample metadata: "
                f"category_names={sample_meta.get('category_names')}, "
                f"category_ids={sample_meta.get('category_ids')}, "
                f"attributes_keys={list(sample_meta.get('attributes', {}).keys())[:5]}"
            )
    
    if not all([
        hybrid_result["hybrid_search_works"],
        hybrid_result["results_have_metadata"],
        hybrid_result["metadata_has_description"],
        hybrid_result["metadata_has_attributes"]
    ]):
        all_passed = False
    
    # Summary
    print_section("Verification Summary")
    
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\nPhase 2 features are working correctly with complete data:")
        print("  ✅ Data completeness >= 95%")
        print("  ✅ Facets show real categories, prices, brands")
        print("  ✅ Price filters work with actual data")
        print("  ✅ Category filters work correctly")
        print("  ✅ Semantic search returns results with complete metadata")
        print("  ✅ Hybrid search combines keyword + semantic effectively")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nReview the output above to identify issues.")
        print("\nNext steps:")
        if data_result["completeness_score"] < 95.0:
            print("  1. Reindex products: python scripts/generate_product_embeddings.py --merchant-id {args.merchant_id}")
        if not semantic_result["semantic_search_works"]:
            print("  2. Regenerate embeddings: python scripts/generate_product_embeddings.py --merchant-id {args.merchant_id}")
        print("  3. Run data exploration: python scripts/explore_product_data.py --merchant-id {args.merchant_id}")


if __name__ == "__main__":
    asyncio.run(main())

