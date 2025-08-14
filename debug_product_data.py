#!/usr/bin/env python3
"""
Debug script to check product data structure in the search index
"""

import json
import requests

def debug_product_data():
    """Debug the product data to understand why prices and images are not showing"""
    
    # Check what's in the products index file on the server
    try:
        # Try to get sample product data from the server
        response = requests.get("http://ai-product-discovery.softdemonew.info:7001/api/v1/index/status")
        if response.status_code == 200:
            print("✅ Index Status:")
            print(json.dumps(response.json(), indent=2))
        
        # Test autocomplete to see current response
        response = requests.get("http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=Hero&limit=1")
        if response.status_code == 200:
            data = response.json()
            print("\n📋 Current Autocomplete Response:")
            print(json.dumps(data, indent=2))
            
            if data.get('suggestions'):
                suggestion = data['suggestions'][0]
                print(f"\n🔍 Analysis of first suggestion:")
                print(f"  Title: {suggestion.get('title')}")
                print(f"  Price: {suggestion.get('price')}")
                print(f"  Image: {suggestion.get('image')}")
                print(f"  Category: {suggestion.get('category')}")
                print(f"  SKU: {suggestion.get('sku')}")
                print(f"  ID: {suggestion.get('id')}")
                print(f"  NLP Enhanced: {suggestion.get('nlp_enhanced')}")
                print(f"  Is Corrected: {suggestion.get('is_corrected')}")
        
        # Test search to see if that works better
        search_data = {
            "query": "Hero Hoodie",
            "limit": 1,
            "filters": {}
        }
        response = requests.post("http://ai-product-discovery.softdemonew.info:7001/api/v1/search/", 
                               json=search_data)
        if response.status_code == 200:
            data = response.json()
            print(f"\n🔍 Search API Response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"\n❌ Search API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_product_data()
