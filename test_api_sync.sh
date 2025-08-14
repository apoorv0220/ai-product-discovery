#!/bin/bash

echo "🔄 Testing API Synchronization Between Backend and Magento"
echo "========================================================"

# Configuration
BACKEND_URL="http://ai-product-discovery.softdemonew.info:7001"
MAGENTO_URL="https://magento-test.softdemonew.info"

echo "Backend API URL: $BACKEND_URL"
echo "Magento URL: $MAGENTO_URL"
echo ""

# Test 1: Backend Autocomplete API Format
echo "1. 🔍 Testing Backend Autocomplete API Response Format"
echo "====================================================="
echo "Testing: $BACKEND_URL/api/v1/autocomplete/?q=hero&limit=3"
echo ""

BACKEND_RESPONSE=$(curl -s "$BACKEND_URL/api/v1/autocomplete/?q=hero&limit=3")
echo "Backend Response:"
echo "$BACKEND_RESPONSE" | python3 -m json.tool
echo ""

# Check if response has required fields for Magento
echo "Checking required fields for Magento compatibility:"
echo "$BACKEND_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    required_fields = ['suggestions', 'query', 'autocomplete_metadata']
    missing = [f for f in required_fields if f not in data]
    if missing:
        print(f'❌ Missing top-level fields: {missing}')
    else:
        print('✅ Top-level fields present')
    
    if 'suggestions' in data and data['suggestions']:
        suggestion = data['suggestions'][0]
        required_suggestion_fields = ['title', 'image', 'price', 'url', 'category', 'sku', 'id']
        missing_suggestion = [f for f in required_suggestion_fields if f not in suggestion]
        if missing_suggestion:
            print(f'❌ Missing suggestion fields: {missing_suggestion}')
        else:
            print('✅ All suggestion fields present')
            print(f'   title: {suggestion.get(\"title\", \"N/A\")}')
            print(f'   price: {suggestion.get(\"price\", \"N/A\")}')
            print(f'   category: {suggestion.get(\"category\", \"N/A\")}')
    else:
        print('⚠️  No suggestions to check')
except Exception as e:
    print(f'❌ Error parsing JSON: {e}')
"
echo ""

# Test 2: Magento Autocomplete API
echo "2. 🔗 Testing Magento Autocomplete API"
echo "====================================="
echo "Testing: $MAGENTO_URL/discovery/search/autocomplete/?q=hero&limit=3"
echo ""

MAGENTO_RESPONSE=$(curl -s "$MAGENTO_URL/discovery/search/autocomplete/?q=hero&limit=3")
echo "Magento Response:"
echo "$MAGENTO_RESPONSE" | python3 -m json.tool
echo ""

# Test 3: Backend Search API Format
echo "3. 🔍 Testing Backend Search API Response Format"
echo "=============================================="
echo "Testing: $BACKEND_URL/api/v1/search/ (POST)"
echo ""

SEARCH_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/v1/search/" \
    -H "Content-Type: application/json" \
    -d '{"query": "hero hoodie", "limit": 3, "offset": 0}')

echo "Search Response:"
echo "$SEARCH_RESPONSE" | python3 -m json.tool
echo ""

# Check search response format
echo "Checking search response format for Magento compatibility:"
echo "$SEARCH_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    required_fields = ['results', 'total', 'query', 'took', 'search_metadata']
    missing = [f for f in required_fields if f not in data]
    if missing:
        print(f'❌ Missing search fields: {missing}')
    else:
        print('✅ Search response format compatible')
        
    if 'search_metadata' in data:
        metadata = data['search_metadata']
        required_metadata = ['nlp_enabled', 'semantic_search', 'typo_corrected', 'ai_enhanced']
        missing_meta = [f for f in required_metadata if f not in metadata]
        if missing_meta:
            print(f'❌ Missing metadata fields: {missing_meta}')
        else:
            print('✅ Search metadata complete')
            
except Exception as e:
    print(f'❌ Error parsing search JSON: {e}')
"
echo ""

# Test 4: Index API Status
echo "4. 📊 Testing Index API Status"
echo "============================="
echo "Testing: $BACKEND_URL/api/v1/index/status"
echo ""

INDEX_STATUS=$(curl -s "$BACKEND_URL/api/v1/index/status")
echo "Index Status:"
echo "$INDEX_STATUS" | python3 -m json.tool
echo ""

# Test 5: Typo Correction
echo "5. 🔧 Testing Typo Correction Feature"
echo "====================================="
echo "Testing 'Hro Hoodie' typo correction..."
echo ""

TYPO_BACKEND=$(curl -s "$BACKEND_URL/api/v1/autocomplete/?q=Hro%20Hoodie&limit=3")
TYPO_MAGENTO=$(curl -s "$MAGENTO_URL/discovery/search/autocomplete/?q=Hro%20Hoodie&limit=3")

echo "Backend typo response:"
echo "$TYPO_BACKEND" | python3 -m json.tool
echo ""

echo "Magento typo response:"
echo "$TYPO_MAGENTO" | python3 -m json.tool
echo ""

# Test 6: Semantic Search
echo "6. 🧠 Testing Semantic Search Feature"
echo "====================================="
echo "Testing 'I want to buy a comfortable hoodie' semantic search..."
echo ""

SEMANTIC_BACKEND=$(curl -s "$BACKEND_URL/api/v1/autocomplete/?q=I%20want%20to%20buy%20a%20comfortable%20hoodie&limit=3")
SEMANTIC_MAGENTO=$(curl -s "$MAGENTO_URL/discovery/search/autocomplete/?q=I%20want%20to%20buy%20a%20comfortable%20hoodie&limit=3")

echo "Backend semantic response:"
echo "$SEMANTIC_BACKEND" | python3 -m json.tool
echo ""

echo "Magento semantic response:"
echo "$SEMANTIC_MAGENTO" | python3 -m json.tool
echo ""

# Summary
echo "🎯 API Synchronization Test Summary"
echo "===================================="
echo ""
echo "✅ Tests completed!"
echo ""
echo "📋 What to check:"
echo "1. Backend autocomplete returns 'suggestions', 'query', 'autocomplete_metadata'"
echo "2. Each suggestion has: title, image, price, url, category, sku, id"
echo "3. Magento autocomplete works and formats data correctly"
echo "4. Search API returns proper search_metadata"
echo "5. Typo correction works on both backend and frontend"
echo "6. Semantic search extracts meaningful terms"
echo ""
echo "🔧 If any tests fail:"
echo "1. Check if AI services are running"
echo "2. Verify OpenAI API key is set"
echo "3. Ensure all code changes are deployed"
echo "4. Check service logs for errors"
