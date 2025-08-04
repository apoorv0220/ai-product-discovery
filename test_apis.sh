#!/bin/bash

# Simple API testing script with example data
# Run this after starting the services to verify they work

echo "🧪 Testing AI Product Discovery Suite APIs"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

test_api() {
    local name="$1"
    local url="$2"
    local method="$3"
    local data="$4"
    
    echo -e "${BLUE}Testing $name...${NC}"
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null)
    else
        response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✅ $name: Success${NC}"
        echo "Response: $(echo "$body" | jq -r '. | tostring' 2>/dev/null || echo "$body" | head -c 100)..."
    else
        echo -e "${RED}❌ $name: Failed (HTTP $http_code)${NC}"
        echo "Error: $(echo "$body" | head -c 200)"
    fi
    echo ""
}

# Test Health Endpoints
echo "🏥 Health Check Tests"
echo "-------------------"
test_api "Search Service Health" "http://localhost:8001/health/" "GET"
test_api "Recommendation Service Health" "http://localhost:8002/health/" "GET"
test_api "Analytics Service Health" "http://localhost:8004/health/" "GET"
test_api "Shopping Assistant Health" "http://localhost:8005/health/" "GET"

# Test Search API
echo "🔍 Search API Tests"
echo "------------------"
test_api "Basic Search" "http://localhost:8001/api/v1/search/" "POST" \
    '{"query": "MacBook", "limit": 5}'

test_api "Search with Filters" "http://localhost:8001/api/v1/search/" "POST" \
    '{"query": "laptop", "limit": 3, "filters": {"category": "Laptops"}}'

test_api "Autocomplete" "http://localhost:8001/api/v1/autocomplete/?q=iPhone&limit=5" "GET"

# Test Recommendations API
echo "🤖 Recommendations API Tests"
echo "----------------------------"
test_api "Homepage Recommendations" "http://localhost:8002/api/v1/recommendations/" "POST" \
    '{"user_id": "1", "context": "home", "limit": 8}'

test_api "Product Page Recommendations" "http://localhost:8002/api/v1/recommendations/" "POST" \
    '{"user_id": "1", "context": "product_detail", "product_ids": ["1"], "limit": 6}'

# Test Analytics API
echo "📊 Analytics API Tests"
echo "---------------------"
test_api "Track Product View" "http://localhost:8004/api/v1/events/track" "POST" \
    '{"event_type": "product_view", "user_id": "1", "properties": {"product_id": "1", "page": "product_detail"}}'

test_api "Track Add to Cart" "http://localhost:8004/api/v1/events/track" "POST" \
    '{"event_type": "add_to_cart", "user_id": "1", "properties": {"product_id": "1", "quantity": 1}}'

# Test Shopping Assistant API
echo "🛍️ Shopping Assistant API Tests"
echo "--------------------------------"
test_api "Create Session" "http://localhost:8005/api/v1/sessions/create" "POST" \
    '{"user_id": "1"}'

test_api "Chat Message" "http://localhost:8005/api/v1/chat/message" "POST" \
    '{"session_id": "test_session", "message": "I need a laptop for programming under $2000"}'

test_api "Product Question" "http://localhost:8005/api/v1/chat/message" "POST" \
    '{"session_id": "test_session", "message": "What are the best gaming laptops you have?"}'

echo "🎯 Comprehensive API Tests"
echo "==========================="

# Complex search scenarios
echo "Testing complex search scenarios..."
test_api "Brand Search" "http://localhost:8001/api/v1/search/" "POST" \
    '{"query": "Apple", "limit": 10}'

test_api "Price Range Search" "http://localhost:8001/api/v1/search/" "POST" \
    '{"query": "smartphone", "filters": {"price_range": [500, 1500]}, "limit": 5}'

# Personalized recommendations
echo "Testing personalized recommendations..."
test_api "Gaming User Recommendations" "http://localhost:8002/api/v1/recommendations/" "POST" \
    '{"user_id": "3", "context": "home", "limit": 8}'

test_api "Photography User Recommendations" "http://localhost:8002/api/v1/recommendations/" "POST" \
    '{"user_id": "4", "context": "home", "limit": 8}'

# Analytics event sequence
echo "Testing analytics event sequence..."
test_api "Search Event" "http://localhost:8004/api/v1/events/track" "POST" \
    '{"event_type": "search", "user_id": "1", "properties": {"query": "MacBook Pro", "results_count": 5}}'

test_api "Click Event" "http://localhost:8004/api/v1/events/track" "POST" \
    '{"event_type": "click", "user_id": "1", "properties": {"product_id": "1", "position": 1}}'

test_api "Purchase Event" "http://localhost:8004/api/v1/events/track" "POST" \
    '{"event_type": "purchase", "user_id": "1", "properties": {"product_id": "1", "price": 2499.00, "order_id": "ORD123"}}'

# Shopping assistant conversation
echo "Testing shopping assistant conversation..."
test_api "Assistant Greeting" "http://localhost:8005/api/v1/chat/message" "POST" \
    '{"session_id": "conv_test", "message": "Hello, I am looking for a new laptop"}'

test_api "Assistant Specification" "http://localhost:8005/api/v1/chat/message" "POST" \
    '{"session_id": "conv_test", "message": "I need it for video editing and gaming, budget around $2500"}'

test_api "Assistant Comparison" "http://localhost:8005/api/v1/chat/message" "POST" \
    '{"session_id": "conv_test", "message": "Can you compare MacBook Pro vs Dell XPS for my needs?"}'

echo ""
echo "🎉 All API tests completed!"
echo ""
echo "💡 Tips for further testing:"
echo "   • Use browser tools to inspect JSON responses"
echo "   • Try different user IDs (1-5) for personalized results"
echo "   • Test various search queries and filters"
echo "   • Monitor response times and accuracy"
echo ""
echo "🔗 Quick API URLs for manual testing:"
echo "   POST http://localhost:8001/api/v1/search/"
echo "   POST http://localhost:8002/api/v1/recommendations/"
echo "   POST http://localhost:8004/api/v1/events/track"
echo "   POST http://localhost:8005/api/v1/chat/message"