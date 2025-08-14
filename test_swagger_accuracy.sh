#!/bin/bash

echo "🔍 Testing Swagger Documentation Accuracy"
echo "========================================"

# Configuration
BACKEND_URL="http://ai-product-discovery.softdemonew.info:7001"

echo "Testing that actual API responses match documented schemas..."
echo ""

# Test 1: Autocomplete Response Structure
echo "1. 📝 Testing Autocomplete Response Structure"
echo "============================================="

AUTOCOMPLETE_RESPONSE=$(curl -s "$BACKEND_URL/api/v1/autocomplete/?q=hero&limit=3")

echo "Checking if autocomplete response matches documented format:"
echo "$AUTOCOMPLETE_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    
    # Check top-level structure
    required_top = ['suggestions', 'query', 'autocomplete_metadata']
    missing_top = [f for f in required_top if f not in data]
    if missing_top:
        print(f'❌ Missing top-level fields: {missing_top}')
    else:
        print('✅ Top-level structure matches schema')
    
    # Check suggestion structure
    if 'suggestions' in data and data['suggestions']:
        suggestion = data['suggestions'][0]
        required_suggestion = [
            'suggestion', 'title', 'type', 'count', 'image', 'price', 
            'url', 'category', 'sku', 'id', 'nlp_enhanced', 'is_corrected',
            'correction_confidence', 'intent_type'
        ]
        missing_suggestion = [f for f in required_suggestion if f not in suggestion]
        if missing_suggestion:
            print(f'❌ Missing suggestion fields: {missing_suggestion}')
        else:
            print('✅ Suggestion structure matches schema')
            
        # Check types
        type_checks = [
            ('suggestion', str), ('title', str), ('type', str), ('count', int),
            ('image', str), ('price', str), ('url', str), ('category', str),
            ('sku', str), ('id', int), ('nlp_enhanced', bool), ('is_corrected', bool),
            ('correction_confidence', (int, float)), ('intent_type', str)
        ]
        
        type_errors = []
        for field, expected_type in type_checks:
            if field in suggestion and not isinstance(suggestion[field], expected_type):
                type_errors.append(f'{field}: expected {expected_type}, got {type(suggestion[field])}')
        
        if type_errors:
            print(f'❌ Type mismatches: {type_errors}')
        else:
            print('✅ All field types match schema')
    
    # Check metadata structure
    if 'autocomplete_metadata' in data:
        metadata = data['autocomplete_metadata']
        required_metadata = ['nlp_processing', 'typo_corrections', 'intent_detection', 
                            'semantic_search', 'total_suggestions']
        missing_metadata = [f for f in required_metadata if f not in metadata]
        if missing_metadata:
            print(f'❌ Missing metadata fields: {missing_metadata}')
        else:
            print('✅ Metadata structure matches schema')
            
except Exception as e:
    print(f'❌ Error parsing response: {e}')
"

echo ""

# Test 2: Search Response Structure  
echo "2. 🔍 Testing Search Response Structure"
echo "======================================="

SEARCH_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/v1/search/" \
    -H "Content-Type: application/json" \
    -d '{"query": "hero hoodie", "limit": 3}')

echo "Checking if search response matches documented format:"
echo "$SEARCH_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    
    # Check top-level structure
    required_top = ['results', 'total', 'query', 'took', 'search_metadata']
    missing_top = [f for f in required_top if f not in data]
    if missing_top:
        print(f'❌ Missing top-level fields: {missing_top}')
    else:
        print('✅ Top-level structure matches schema')
    
    # Check result structure
    if 'results' in data and data['results']:
        result = data['results'][0]
        required_result = ['product_id', 'title', 'score', 'metadata']
        missing_result = [f for f in required_result if f not in result]
        if missing_result:
            print(f'❌ Missing result fields: {missing_result}')
        else:
            print('✅ Result structure matches schema')
    
    # Check search_metadata structure
    if 'search_metadata' in data:
        metadata = data['search_metadata']
        required_metadata = ['nlp_enabled', 'semantic_search', 'typo_corrected', 
                            'ai_enhanced', 'intent_type', 'processing_time', 'corrections']
        missing_metadata = [f for f in required_metadata if f not in metadata]
        if missing_metadata:
            print(f'❌ Missing metadata fields: {missing_metadata}')
        else:
            print('✅ Search metadata matches schema')
            
except Exception as e:
    print(f'❌ Error parsing search response: {e}')
"

echo ""

# Test 3: Error Response Structure
echo "3. 🚨 Testing Error Response Structure"
echo "====================================="

ERROR_RESPONSE=$(curl -s "$BACKEND_URL/api/v1/autocomplete/?q=&limit=3")

echo "Checking if error response matches documented format:"
echo "$ERROR_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    
    # Error responses should still have the same structure
    if 'error' in data:
        print('✅ Error field present in response')
    
    if 'suggestions' in data and isinstance(data['suggestions'], list):
        print('✅ Error response maintains suggestions array structure')
    
    if 'autocomplete_metadata' in data:
        print('✅ Error response includes metadata')
        
except Exception as e:
    print(f'❌ Error parsing error response: {e}')
"

echo ""

# Test 4: OpenAPI Schema Validation
echo "4. 📊 Testing OpenAPI Schema Accessibility"
echo "=========================================="

echo "Checking if OpenAPI/Swagger docs are accessible:"
OPENAPI_RESPONSE=$(curl -s "$BACKEND_URL/openapi.json")

if echo "$OPENAPI_RESPONSE" | grep -q '"openapi"'; then
    echo "✅ OpenAPI schema is accessible"
    
    # Check if our endpoints are documented
    if echo "$OPENAPI_RESPONSE" | grep -q '"/api/v1/autocomplete/"'; then
        echo "✅ Autocomplete endpoint documented"
    else
        echo "❌ Autocomplete endpoint not found in schema"
    fi
    
    if echo "$OPENAPI_RESPONSE" | grep -q '"/api/v1/search/"'; then
        echo "✅ Search endpoint documented"
    else
        echo "❌ Search endpoint not found in schema"
    fi
else
    echo "❌ OpenAPI schema not accessible"
fi

echo ""

# Summary
echo "🎯 Documentation Accuracy Summary"
echo "================================="
echo ""
echo "✅ Tests completed!"
echo ""
echo "📋 What was verified:"
echo "1. Autocomplete response structure matches documented schema"
echo "2. Search response structure matches documented schema"  
echo "3. Error responses maintain consistent format"
echo "4. OpenAPI/Swagger documentation is accessible"
echo ""
echo "🔧 If any tests failed:"
echo "1. Check if the search service is running with updated code"
echo "2. Verify OpenAI API key is set correctly"
echo "3. Ensure all schema files are deployed"
echo "4. Restart the service to load new schemas"
echo ""
echo "📖 Access documentation at:"
echo "• Swagger UI: $BACKEND_URL/docs"
echo "• ReDoc: $BACKEND_URL/redoc"
echo "• OpenAPI JSON: $BACKEND_URL/openapi.json"
