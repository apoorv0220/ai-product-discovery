#!/bin/bash

echo "🔧 Fixing Search Service Import & Method Errors"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "📋 Step 1: Identifying Current Issues..."
echo "---------------------------------------"

# Check if docker-compose exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: Not in AI project root directory${NC}"
    echo "Please run this script from /path/to/ai-product-discovery"
    exit 1
fi

echo -e "${GREEN}✅ Found AI project${NC}"

# Check current issues
echo "Checking current search service logs for issues..."
RECENT_LOGS=$(docker logs ai_discovery_search --tail 20 2>/dev/null)

if echo "$RECENT_LOGS" | grep -q "No module named 'shared.models'"; then
    echo -e "${RED}❌ Confirmed: Import error - No module named 'shared.models'${NC}"
    IMPORT_ERROR=true
else
    echo -e "${GREEN}✅ No import errors detected${NC}"
    IMPORT_ERROR=false
fi

if echo "$RECENT_LOGS" | grep -q "405 Method Not Allowed"; then
    echo -e "${RED}❌ Confirmed: Method not allowed error (POST to autocomplete)${NC}"
    METHOD_ERROR=true
else
    echo -e "${GREEN}✅ No method errors detected${NC}"
    METHOD_ERROR=false
fi

echo ""
echo "🔧 Step 2: Rebuilding Search Service with Fixes..."
echo "-------------------------------------------------"

# Rebuild search service with fixes
echo "Building search service with import and method fixes..."
BUILD_OUTPUT=$(docker-compose build search-service 2>&1)
BUILD_EXIT_CODE=$?

if [ $BUILD_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Search service rebuilt successfully with fixes${NC}"
else
    echo -e "${RED}❌ Search service build failed${NC}"
    echo "Build output:"
    echo "$BUILD_OUTPUT"
    exit 1
fi

echo ""
echo "🔄 Step 3: Restarting Search Service..."
echo "--------------------------------------"

# Stop and restart search service specifically
echo "Restarting search service..."
docker-compose stop search-service >/dev/null 2>&1
docker-compose up -d search-service >/dev/null 2>&1

# Wait for service to start
echo "Waiting 10 seconds for service to initialize..."
sleep 10

echo ""
echo "🔍 Step 4: Verifying Import Error Fix..."
echo "---------------------------------------"

# Check for import errors
STARTUP_LOGS=$(docker logs ai_discovery_search --tail 30 2>/dev/null)

if echo "$STARTUP_LOGS" | grep -q "No module named 'shared.models'"; then
    echo -e "${RED}❌ Import error still present${NC}"
    echo "Recent logs:"
    echo "$STARTUP_LOGS" | grep -A2 -B2 "shared.models"
else
    echo -e "${GREEN}✅ Import error fixed - no 'shared.models' errors in recent logs${NC}"
fi

# Check if service started successfully
if echo "$STARTUP_LOGS" | grep -q "Skipping model imports for service.*search"; then
    echo -e "${GREEN}✅ Search service correctly skipping model imports${NC}"
elif echo "$STARTUP_LOGS" | grep -q "Database initialized successfully"; then
    echo -e "${GREEN}✅ Database initialization successful${NC}"
else
    echo -e "${YELLOW}⚠️ Database initialization status unclear${NC}"
fi

echo ""
echo "🧪 Step 5: Testing Autocomplete Methods..."
echo "-----------------------------------------"

# Test GET method (should work)
echo "Testing GET method..."
GET_RESPONSE=$(curl -s "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=test&limit=3" 2>/dev/null)

if [ $? -eq 0 ] && echo "$GET_RESPONSE" | grep -q "suggestions"; then
    echo -e "${GREEN}✅ GET method working${NC}"
    echo "Response: $(echo "$GET_RESPONSE" | head -1)"
else
    echo -e "${RED}❌ GET method failed${NC}"
    echo "Response: $GET_RESPONSE"
fi

# Test POST method with JSON body
echo "Testing POST method with JSON body..."
POST_JSON_RESPONSE=$(curl -s -X POST "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/" \
  -H "Content-Type: application/json" \
  -d '{"q": "test", "limit": 3}' 2>/dev/null)

if [ $? -eq 0 ] && echo "$POST_JSON_RESPONSE" | grep -q "suggestions"; then
    echo -e "${GREEN}✅ POST method with JSON body working${NC}"
    echo "Response: $(echo "$POST_JSON_RESPONSE" | head -1)"
else
    echo -e "${YELLOW}⚠️ POST method with JSON may have issues${NC}"
    echo "Response: $POST_JSON_RESPONSE"
fi

# Test POST method with query parameters
echo "Testing POST method with query parameters..."
POST_FORM_RESPONSE=$(curl -s -X POST "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/form?q=test&limit=3" 2>/dev/null)

if [ $? -eq 0 ] && echo "$POST_FORM_RESPONSE" | grep -q "suggestions"; then
    echo -e "${GREEN}✅ POST method with query parameters working${NC}"
    echo "Response: $(echo "$POST_FORM_RESPONSE" | head -1)"
else
    echo -e "${YELLOW}⚠️ POST method with query parameters may have issues${NC}"
    echo "Response: $POST_FORM_RESPONSE"
fi

echo ""
echo "🔍 Step 6: Checking Service Health..."
echo "------------------------------------"

# Check health endpoint
HEALTH_RESPONSE=$(curl -s "http://ai-product-discovery.softdemonew.info:7001/health/" 2>/dev/null)

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Search service is healthy${NC}"
    echo "Health status: $HEALTH_RESPONSE"
else
    echo -e "${RED}❌ Search service health check failed${NC}"
    echo "Health response: $HEALTH_RESPONSE"
fi

echo ""
echo "📊 Step 7: Final Verification..."
echo "-------------------------------"

# Check recent logs for any remaining errors
FINAL_LOGS=$(docker logs ai_discovery_search --tail 10 2>/dev/null)

echo "Recent service logs:"
echo "$FINAL_LOGS"

echo ""
echo "📋 Summary"
echo "=========="

# Count success indicators
SUCCESS_COUNT=0

if ! echo "$FINAL_LOGS" | grep -q "No module named 'shared.models'"; then
    echo -e "${GREEN}✅ Import error fixed${NC}"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}❌ Import error persists${NC}"
fi

if echo "$GET_RESPONSE" | grep -q "suggestions"; then
    echo -e "${GREEN}✅ GET autocomplete working${NC}"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}❌ GET autocomplete failed${NC}"
fi

if echo "$POST_JSON_RESPONSE" | grep -q "suggestions" || echo "$POST_FORM_RESPONSE" | grep -q "suggestions"; then
    echo -e "${GREEN}✅ POST autocomplete working${NC}"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}❌ POST autocomplete failed${NC}"
fi

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Service health OK${NC}"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo -e "${RED}❌ Service health issues${NC}"
fi

echo ""
if [ $SUCCESS_COUNT -eq 4 ]; then
    echo -e "${GREEN}🎉 ALL ISSUES FIXED SUCCESSFULLY!${NC}"
    echo ""
    echo "✅ Import error resolved"
    echo "✅ Method not allowed error resolved"
    echo "✅ Autocomplete supports both GET and POST"
    echo "✅ Service is healthy and running"
    echo ""
    echo -e "${BLUE}Your search service is now ready for:${NC}"
    echo "- Magento frontend requests (both GET and POST)"
    echo "- Product synchronization"
    echo "- Real autocomplete suggestions"
    echo ""
    echo "Next steps:"
    echo "1. Re-sync your products: php bin/magento discovery:sync:catalog"
    echo "2. Test frontend autocomplete on your website"
    echo "3. Verify real product suggestions are displayed"
    
elif [ $SUCCESS_COUNT -ge 2 ]; then
    echo -e "${YELLOW}🔄 PARTIAL SUCCESS ($SUCCESS_COUNT/4 issues fixed)${NC}"
    echo ""
    echo "Some issues resolved, but manual verification needed."
    echo "Check the detailed output above for remaining issues."
    
else
    echo -e "${RED}❌ FIXES NOT SUCCESSFUL ($SUCCESS_COUNT/4 issues fixed)${NC}"
    echo ""
    echo "Multiple issues remain. Please check:"
    echo "1. Service logs: docker logs ai_discovery_search"
    echo "2. Service status: docker ps | grep search"
    echo "3. Network connectivity: curl http://ai-product-discovery.softdemonew.info:7001/health/"
fi

echo ""
echo "🔧 Troubleshooting Commands:"
echo "- View logs: docker logs ai_discovery_search"
echo "- Restart service: docker-compose restart search-service"
echo "- Check API docs: http://ai-product-discovery.softdemonew.info:7001/docs"
echo "- Test autocomplete: curl 'http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=test'"
echo ""
echo "For detailed information, see the fix documentation above."
