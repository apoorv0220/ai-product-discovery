#!/usr/bin/env python3
"""
Debug script to check what metadata exists in Elasticsearch for specific products.
"""

import requests
import json
import sys

def debug_elasticsearch_metadata():
    """Query Elasticsearch directly to see what metadata exists for products."""

    # Elasticsearch URL (assuming it's running on localhost:9200)
    es_url = "http://localhost:9200"
    index_name = "discovery_products_m1"

    # Product IDs from the search results
    product_ids = ["670", "700", "462"]  # Primo Endurance Tank, Sparta Gym Tank, Helios EverCool Tee

    print("Debugging Elasticsearch metadata...")
    print(f"Elasticsearch URL: {es_url}")
    print(f"Index: {index_name}")
    print("-" * 50)

    for product_id in product_ids:
        print(f"\nChecking product ID: {product_id}")

        # Query to get the full document
        query = {
            "query": {
                "term": {
                    "product_id": product_id
                }
            },
            "_source": ["product_id", "categories", "category_ids", "brand", "attributes", "name"]
        }

        try:
            response = requests.post(
                f"{es_url}/{index_name}/_search",
                json=query,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", {}).get("hits", [])

                if hits:
                    source = hits[0]["_source"]
                    print(f"  Name: {source.get('name', 'N/A')}")
                    print(f"  Categories: {source.get('categories', [])}")
                    print(f"  Category IDs: {source.get('category_ids', [])}")
                    print(f"  Brand: {source.get('brand', 'N/A')}")
                    print(f"  Attributes: {source.get('attributes', {})}")

                    # Check if data exists
                    has_categories = len(source.get('categories', [])) > 0
                    has_brand = source.get('brand') is not None and source.get('brand') != ""

                    if has_categories or has_brand:
                        print("  [SUCCESS] Metadata exists in Elasticsearch!")
                    else:
                        print("  [WARNING] Metadata fields are empty in Elasticsearch!")
                else:
                    print("  [ERROR] Product not found in Elasticsearch!")
            else:
                print(f"  [ERROR] Elasticsearch query failed: {response.status_code}")
                print(f"  Response: {response.text}")

        except Exception as e:
            print(f"  [ERROR] Exception: {e}")

    print("\n" + "="*50)
    print("Summary:")
    print("If metadata exists in Elasticsearch but not in search results,")
    print("the issue is in the metadata enrichment code in search.py")
    print("If metadata is missing from Elasticsearch, the issue is in indexing.")

if __name__ == "__main__":
    debug_elasticsearch_metadata()
