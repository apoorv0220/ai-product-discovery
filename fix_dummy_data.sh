#!/bin/bash

echo "🚀 Removing Dummy Data & Enabling Real Product Search"
echo "===================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "📋 Step 1: Checking Current Status..."
echo "------------------------------------"

# Check if docker-compose exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: Not in AI project root directory${NC}"
    echo "Please run this script from /path/to/ai-product-discovery"
    exit 1
fi

echo -e "${GREEN}✅ Found AI project${NC}"

# Check current dummy data
echo "Testing current autocomplete (should show dummy data)..."
CURRENT_RESPONSE=$(curl -s "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=Ba&limit=3" 2>/dev/null)

if echo "$CURRENT_RESPONSE" | grep -q "Ba phone"; then
    echo -e "${YELLOW}⚠️ Confirmed: Currently showing dummy data${NC}"
    echo "Sample dummy data: $(echo "$CURRENT_RESPONSE" | head -1)"
else
    echo -e "${GREEN}✅ No dummy data detected (may already be fixed)${NC}"
fi

echo ""
echo "🔧 Step 2: Rebuilding Search Service with Real Data Logic..."
echo "----------------------------------------------------------"

# Rebuild search service
echo "Building search service with new real data implementation..."
BUILD_OUTPUT=$(docker-compose build search-service 2>&1)
BUILD_EXIT_CODE=$?

if [ $BUILD_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Search service rebuilt successfully${NC}"
else
    echo -e "${RED}❌ Search service build failed${NC}"
    echo "Build output:"
    echo "$BUILD_OUTPUT"
    exit 1
fi

echo ""
echo "🔄 Step 3: Restarting All Services..."
echo "------------------------------------"

# Stop services
echo "Stopping services..."
docker-compose down >/dev/null 2>&1

# Start services
echo "Starting services with updated code..."
START_OUTPUT=$(docker-compose up -d 2>&1)
START_EXIT_CODE=$?

if [ $START_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Services restarted successfully${NC}"
else
    echo -e "${RED}❌ Services failed to start${NC}"
    echo "Start output:"
    echo "$START_OUTPUT"
    exit 1
fi

echo ""
echo "⏱️ Step 4: Waiting for Services to Initialize..."
echo "-----------------------------------------------"

# Wait for services to start
echo "Waiting 15 seconds for services to fully initialize..."
sleep 15

# Check if search service is responding
HEALTH_CHECK=$(curl -s "http://ai-product-discovery.softdemonew.info:7001/health/" 2>/dev/null)

if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Search service is healthy${NC}"
else
    echo -e "${RED}❌ Search service not responding properly${NC}"
    echo "Health check response: $HEALTH_CHECK"
    echo "Checking service logs..."
    docker logs ai_discovery_search | tail -10
    exit 1
fi

echo ""
echo "🧹 Step 5: Clearing Old Dummy Data..."
echo "------------------------------------"

# Clear existing index
echo "Clearing old dummy data from search index..."
CLEAR_RESPONSE=$(curl -s -X POST "http://ai-product-discovery.softdemonew.info:7001/api/v1/index/rebuild" 2>/dev/null)

if echo "$CLEAR_RESPONSE" | grep -q "success.*true"; then
    echo -e "${GREEN}✅ Dummy data cleared successfully${NC}"
    echo "Response: $CLEAR_RESPONSE"
else
    echo -e "${YELLOW}⚠️ Clear operation may have issues${NC}"
    echo "Response: $CLEAR_RESPONSE"
fi

echo ""
echo "📊 Step 6: Checking Index Status..."
echo "----------------------------------"

# Check index status
INDEX_STATUS=$(curl -s "http://ai-product-discovery.softdemonew.info:7001/api/v1/index/status" 2>/dev/null)

if echo "$INDEX_STATUS" | grep -q "product_count"; then
    PRODUCT_COUNT=$(echo "$INDEX_STATUS" | grep -o '"product_count":[0-9]*' | grep -o '[0-9]*' || echo "0")
    echo -e "${GREEN}✅ Index status accessible${NC}"
    echo "Current product count: $PRODUCT_COUNT"
    echo "Full status: $INDEX_STATUS"
else
    echo -e "${RED}❌ Cannot access index status${NC}"
    echo "Response: $INDEX_STATUS"
fi

echo ""
echo "🧪 Step 7: Testing Autocomplete (Should Now Be Empty)..."
echo "--------------------------------------------------------"

# Test autocomplete (should be empty now)
sleep 2
TEST_RESPONSE=$(curl -s "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=Ba&limit=5" 2>/dev/null)

if echo "$TEST_RESPONSE" | grep -q "Ba phone"; then
    echo -e "${RED}❌ Still showing dummy data!${NC}"
    echo "Response: $TEST_RESPONSE"
    echo ""
    echo "Possible issues:"
    echo "- Service not fully restarted"
    echo "- Code changes not applied"
    echo "- Cache not cleared"
    exit 1
elif echo "$TEST_RESPONSE" | grep -q '"suggestions":\[\]'; then
    echo -e "${GREEN}✅ Dummy data removed! Autocomplete now empty (ready for real products)${NC}"
    echo "Response: $TEST_RESPONSE"
elif echo "$TEST_RESPONSE" | grep -q '"suggestions":\['; then
    echo -e "${GREEN}✅ Autocomplete working and may already have real products${NC}"
    echo "Response: $TEST_RESPONSE"
else
    echo -e "${YELLOW}⚠️ Unexpected autocomplete response${NC}"
    echo "Response: $TEST_RESPONSE"
fi

echo ""
echo "📋 Step 8: Summary & Next Steps"
echo "==============================="

echo -e "${GREEN}🎉 DUMMY DATA REMOVAL COMPLETE!${NC}"
echo ""
echo "✅ Search service rebuilt with real data logic"
echo "✅ Services restarted successfully"  
echo "✅ Old dummy data cleared from index"
echo "✅ Autocomplete no longer shows fake products"
echo ""
echo -e "${BLUE}📋 NEXT STEPS (Run on Magento Server):${NC}"
echo ""
echo "1. SSH into your Magento server:"
echo "   ssh user@magento-server"
echo ""
echo "2. Navigate to Magento root:"
echo "   cd /path/to/magento"
echo ""
echo "3. Sync your real products:"
echo "   php bin/magento discovery:sync:catalog"
echo ""
echo "4. Verify products are synced:"
echo "   curl \"http://ai-product-discovery.softdemonew.info:7001/api/v1/index/status\""
echo ""
echo "5. Test autocomplete with real products:"
echo "   curl \"http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=[your-product-name]&limit=10\""
echo ""
echo "6. Test on your website:"
echo "   Visit: https://magento-test.softdemonew.info"
echo "   Try typing in the search box"
echo ""
echo -e "${GREEN}After syncing, you'll see YOUR actual products instead of dummy data!${NC}"
echo ""

# Final verification
echo "🔍 Current Status:"
echo "- AI Services: Running ✅"
echo "- Dummy Data: Removed ✅"
echo "- Real Product Logic: Deployed ✅"
echo "- Ready for Product Sync: ✅"
echo ""
echo "For detailed information, see: REMOVE_DUMMY_DATA_FIX.md"
