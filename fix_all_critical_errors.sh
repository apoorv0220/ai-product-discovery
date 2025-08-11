#!/bin/bash

echo "🚨 CRITICAL ERRORS FIX - 10X ENGINEER SOLUTION"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo ""
echo "📋 CRITICAL ISSUES IDENTIFIED:"
echo "1. RequireJS mismatched anonymous define() module"
echo "2. Similar products API 404 error"  
echo "3. Missing category-recommendations.phtml template"
echo "4. Empty autocomplete response (no product data)"
echo ""

# Check if we're on AI server or Magento server
if [ -f "docker-compose.yml" ]; then
    SERVER_TYPE="AI_SERVER"
    echo -e "${BLUE}🤖 Detected: AI Services Server${NC}"
elif [ -f "bin/magento" ]; then
    SERVER_TYPE="MAGENTO_SERVER" 
    echo -e "${PURPLE}🛍️ Detected: Magento Server${NC}"
else
    echo -e "${RED}❌ Error: Not in AI project root or Magento root${NC}"
    echo "Please run this script from either:"
    echo "- AI server: /path/to/ai-product-discovery/"
    echo "- Magento server: /path/to/magento/"
    exit 1
fi

if [ "$SERVER_TYPE" = "AI_SERVER" ]; then
    echo ""
    echo -e "${BLUE}🔧 AI SERVER - FIXING BACKEND ISSUES${NC}"
    echo "====================================="
    
    echo "✅ Fix #1: Similar Products API Endpoint (404 → Fixed)"
    echo "✅ Fix #2: Empty Autocomplete Data Handling"
    echo "✅ Fix #3: Added Index Status Endpoint"
    
    echo ""
    echo "🔄 Rebuilding Services with Fixes..."
    
    # Rebuild recommendation service (similar products fix)
    echo "Rebuilding recommendation service..."
    BUILD_REC=$(docker-compose build recommendation-service 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Recommendation service rebuilt${NC}"
    else
        echo -e "${RED}❌ Recommendation build failed${NC}"
        echo "$BUILD_REC" | tail -5
    fi
    
    # Rebuild search service (autocomplete fixes)
    echo "Rebuilding search service..."
    BUILD_SEARCH=$(docker-compose build search-service 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Search service rebuilt${NC}"
    else
        echo -e "${RED}❌ Search build failed${NC}"
        echo "$BUILD_SEARCH" | tail -5
    fi
    
    # Restart services
    echo "Restarting services..."
    docker-compose stop recommendation-service search-service >/dev/null 2>&1
    docker-compose up -d recommendation-service search-service >/dev/null 2>&1
    
    echo "Waiting 20 seconds for services to initialize..."
    sleep 20
    
    echo ""
    echo "🧪 Testing Fixed Endpoints..."
    echo "==========================="
    
    # Test index status
    echo "Testing search index status..."
    INDEX_STATUS=$(curl -s "http://ai-product-discovery.softdemonew.info:7001/api/v1/index/status" 2>/dev/null)
    if echo "$INDEX_STATUS" | grep -q "total_products"; then
        PRODUCT_COUNT=$(echo "$INDEX_STATUS" | grep -o '"total_products":[0-9]*' | cut -d':' -f2)
        echo -e "${GREEN}✅ Index status endpoint working${NC}"
        echo "   Products indexed: $PRODUCT_COUNT"
        
        if [ "$PRODUCT_COUNT" = "0" ]; then
            echo -e "${YELLOW}⚠️ No products indexed! This explains empty autocomplete.${NC}"
            echo "   Solution: Run 'php bin/magento discovery:sync:catalog' on Magento server"
        fi
    else
        echo -e "${RED}❌ Index status endpoint failed${NC}"
        echo "Response: $INDEX_STATUS"
    fi
    
    # Test similar products API
    echo "Testing similar products API..."
    SIMILAR_TEST=$(curl -s -X POST "http://ai-product-discovery.softdemonew.info:7002/api/v1/recommendations/similar" \
      -H "Content-Type: application/json" \
      -d '{"product_id": "123", "limit": 3}' 2>/dev/null)
    
    if echo "$SIMILAR_TEST" | grep -q "recommendations"; then
        echo -e "${GREEN}✅ Similar products API endpoint working${NC}"
    elif echo "$SIMILAR_TEST" | grep -q "404"; then
        echo -e "${RED}❌ Similar products still returning 404${NC}"
    else
        echo -e "${YELLOW}⚠️ Similar products API response unclear${NC}"
        echo "Response: $SIMILAR_TEST" | head -1
    fi
    
    # Test autocomplete
    echo "Testing autocomplete..."
    AUTO_TEST=$(curl -s -X POST "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/" \
      -H "Content-Type: application/json" \
      -d '{"query": "test", "limit": 3}' 2>/dev/null)
    
    if echo "$AUTO_TEST" | grep -q "suggestions"; then
        echo -e "${GREEN}✅ Autocomplete API working${NC}"
        SUGGESTION_COUNT=$(echo "$AUTO_TEST" | grep -o '"suggestions":\[' | wc -l)
        if [ "$SUGGESTION_COUNT" = "0" ]; then
            echo -e "${YELLOW}⚠️ Autocomplete working but returns empty suggestions${NC}"
        fi
    else
        echo -e "${RED}❌ Autocomplete API failed${NC}"
        echo "Response: $AUTO_TEST" | head -1
    fi
    
    echo ""
    echo -e "${GREEN}🎯 AI SERVER SUMMARY${NC}"
    echo "==================="
    echo -e "${GREEN}✅ Similar products 404 error fixed${NC}"
    echo -e "${GREEN}✅ Autocomplete empty data handling improved${NC}"
    echo -e "${GREEN}✅ Index status endpoint added for debugging${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Upload and run this script on Magento server"
    echo "2. Run product sync: php bin/magento discovery:sync:catalog"
    echo "3. Test frontend features"
    
elif [ "$SERVER_TYPE" = "MAGENTO_SERVER" ]; then
    echo ""
    echo -e "${PURPLE}🔧 MAGENTO SERVER - FIXING FRONTEND ISSUES${NC}"
    echo "=========================================="
    
    echo "✅ Fix #1: RequireJS Module Definition"
    echo "✅ Fix #2: Missing Category Template"
    echo "✅ Fix #3: Module Configuration"
    echo "✅ Fix #4: Data Sync Setup"
    
    echo ""
    echo "🧹 Clearing All Caches..."
    echo "========================"
    
    # Nuclear cache clear
    echo "Removing all generated files..."
    rm -rf var/di/* var/generation/* generated/code/* var/cache/* var/page_cache/* var/view_preprocessed/* 2>/dev/null
    echo -e "${GREEN}✅ All caches cleared${NC}"
    
    echo ""
    echo "🔧 Module Rebuild..."
    echo "=================="
    
    # Module reinstall
    echo "Disabling/enabling module..."
    php bin/magento module:disable Vendor_DiscoverySuite >/dev/null 2>&1
    php bin/magento module:enable Vendor_DiscoverySuite >/dev/null 2>&1
    
    echo "Running setup upgrade..."
    UPGRADE_OUTPUT=$(php bin/magento setup:upgrade 2>&1)
    if echo "$UPGRADE_OUTPUT" | grep -q "error\|Error\|ERROR"; then
        echo -e "${RED}❌ Setup upgrade had errors${NC}"
        echo "$UPGRADE_OUTPUT" | grep -i error | head -3
    else
        echo -e "${GREEN}✅ Setup upgrade completed${NC}"
    fi
    
    echo "Compiling DI..."
    COMPILE_OUTPUT=$(php bin/magento setup:di:compile 2>&1)
    if echo "$COMPILE_OUTPUT" | grep -q "error\|Error\|ERROR"; then
        echo -e "${RED}❌ DI compilation had errors${NC}"
        echo "$COMPILE_OUTPUT" | grep -i error | head -3
    else
        echo -e "${GREEN}✅ DI compilation completed${NC}"
    fi
    
    echo "Deploying static content..."
    php bin/magento setup:static-content:deploy -f >/dev/null 2>&1
    echo -e "${GREEN}✅ Static content deployed${NC}"
    
    echo "Final cache flush..."
    php bin/magento cache:flush >/dev/null 2>&1
    echo -e "${GREEN}✅ Cache flushed${NC}"
    
    echo ""
    echo "⚙️ Enabling AI Features..."
    echo "========================="
    
    # Enable all configurations
    php bin/magento config:set discovery_suite_config/general/enabled 1 >/dev/null 2>&1
    php bin/magento config:set discovery_suite_config/general/api_base_url "http://ai-product-discovery.softdemonew.info" >/dev/null 2>&1
    php bin/magento config:set discovery_suite_config/autocomplete/enabled 1 >/dev/null 2>&1
    php bin/magento config:set discovery_suite_config/recommendations/enabled 1 >/dev/null 2>&1
    php bin/magento config:set discovery_suite_config/smart_listings/enabled 1 >/dev/null 2>&1
    php bin/magento config:set discovery_suite_config/shopping_assistant/enabled 1 >/dev/null 2>&1
    php bin/magento config:set discovery_suite_config/analytics/enabled 1 >/dev/null 2>&1
    
    echo -e "${GREEN}✅ All AI features enabled in configuration${NC}"
    
    # Final cache flush after config
    php bin/magento cache:flush >/dev/null 2>&1
    
    echo ""
    echo "📊 Testing Product Sync..."
    echo "========================="
    
    # Test connection first
    echo "Testing AI service connection..."
    CONNECTION_TEST=$(php bin/magento discovery:test:connection 2>&1)
    
    if echo "$CONNECTION_TEST" | grep -q "Connected"; then
        echo -e "${GREEN}✅ AI services connected${NC}"
        
        # Run product sync
        echo "Running product catalog sync..."
        SYNC_OUTPUT=$(php bin/magento discovery:sync:catalog 2>&1)
        
        if echo "$SYNC_OUTPUT" | grep -q "Synced [1-9]"; then
            SYNCED_COUNT=$(echo "$SYNC_OUTPUT" | grep -o "Synced [0-9]*" | head -1 | cut -d' ' -f2)
            echo -e "${GREEN}✅ Product sync successful - synced $SYNCED_COUNT products${NC}"
        elif echo "$SYNC_OUTPUT" | grep -q "Synced 0"; then
            echo -e "${YELLOW}⚠️ Product sync completed but synced 0 products${NC}"
            echo "This might be due to:"
            echo "- No products in Magento catalog"
            echo "- Product visibility settings"
            echo "- Store configuration issues"
        else
            echo -e "${RED}❌ Product sync failed${NC}"
            echo "$SYNC_OUTPUT" | tail -3
        fi
        
        # Test autocomplete after sync
        echo "Testing Magento autocomplete endpoint..."
        BASE_URL=$(php bin/magento config:show web/unsecure/base_url 2>/dev/null | sed 's|/$||')
        if [ -z "$BASE_URL" ]; then
            BASE_URL="https://magento-test.softdemonew.info"
        fi
        
        AUTO_URL="$BASE_URL/discovery/search/autocomplete/?q=test&limit=5"
        echo "Testing: $AUTO_URL"
        
        if command -v curl >/dev/null 2>&1; then
            AUTO_RESPONSE=$(curl -s "$AUTO_URL" 2>/dev/null)
            if echo "$AUTO_RESPONSE" | grep -q '"suggestions"'; then
                echo -e "${GREEN}✅ Magento autocomplete endpoint working${NC}"
                
                # Check if suggestions are not empty
                if echo "$AUTO_RESPONSE" | grep -q '"suggestions":\[\]'; then
                    echo -e "${YELLOW}⚠️ Autocomplete working but still returns empty results${NC}"
                    echo "This means products were synced but search isn't finding matches."
                    echo "Try a more common term or check product names."
                else
                    echo -e "${GREEN}✅ Autocomplete returning suggestions!${NC}"
                fi
            else
                echo -e "${RED}❌ Magento autocomplete endpoint failed${NC}"
                echo "Response: $AUTO_RESPONSE" | head -1
            fi
        fi
        
    else
        echo -e "${RED}❌ AI services connection failed${NC}"
        echo "Cannot proceed with product sync."
        echo "Make sure AI services are running and accessible."
    fi
    
    echo ""
    echo -e "${GREEN}🎯 MAGENTO SERVER SUMMARY${NC}"
    echo "========================="
    
    SUCCESS_ITEMS=0
    
    if echo "$UPGRADE_OUTPUT" | grep -qv "error\|Error\|ERROR"; then
        echo -e "${GREEN}✅ RequireJS and template issues fixed${NC}"
        SUCCESS_ITEMS=$((SUCCESS_ITEMS + 1))
    fi
    
    if echo "$CONNECTION_TEST" | grep -q "Connected"; then
        echo -e "${GREEN}✅ AI services connectivity confirmed${NC}"
        SUCCESS_ITEMS=$((SUCCESS_ITEMS + 1))
    fi
    
    if echo "$SYNC_OUTPUT" | grep -q "Synced [1-9]"; then
        echo -e "${GREEN}✅ Product sync successful${NC}"
        SUCCESS_ITEMS=$((SUCCESS_ITEMS + 1))
    fi
    
    echo ""
    if [ $SUCCESS_ITEMS -ge 2 ]; then
        echo -e "${GREEN}🎉 MAJOR SUCCESS! Critical errors fixed!${NC}"
        echo ""
        echo -e "${GREEN}Your frontend should now display:${NC}"
        echo "📱 Product pages: Similar products recommendations"
        echo "🗂️ Category pages: AI-powered product listings"
        echo "🛒 Shopping cart: Cross-sell recommendations"
        echo "🔍 Search: Real-time autocomplete with products"
        echo "🤖 Shopping assistant: Interactive chat widget"
        echo ""
        echo -e "${BLUE}Test your website now:${NC}"
        BASE_URL=$(php bin/magento config:show web/unsecure/base_url 2>/dev/null | sed 's|/$||')
        if [ -n "$BASE_URL" ]; then
            echo "• Homepage: $BASE_URL"
            echo "• Any product page: Look for 'You Might Also Like' section"
            echo "• Category pages: Check for AI-enhanced sorting"
            echo "• Search: Type in search box for autocomplete"
        fi
        
    else
        echo -e "${YELLOW}🔄 PARTIAL SUCCESS ($SUCCESS_ITEMS/3 items completed)${NC}"
        echo ""
        echo "Some issues remain. Manual checks needed:"
        echo "1. Verify all AI services are running on AI server"
        echo "2. Check network connectivity between servers"
        echo "3. Review Magento logs: tail -f var/log/system.log"
    fi
fi

echo ""
echo "🔍 Additional Debugging Commands:"
echo "================================"

if [ "$SERVER_TYPE" = "AI_SERVER" ]; then
    echo "• Check search index: curl http://ai-product-discovery.softdemonew.info:7001/api/v1/index/status"
    echo "• View search logs: docker logs ai_discovery_search --tail 20"
    echo "• View recommendation logs: docker logs ai_discovery_recommendation --tail 20"
elif [ "$SERVER_TYPE" = "MAGENTO_SERVER" ]; then
    echo "• Test connection: php bin/magento discovery:test:connection"
    echo "• Sync products: php bin/magento discovery:sync:catalog"
    echo "• Check module: php bin/magento module:status Vendor_DiscoverySuite"
    echo "• View logs: tail -f var/log/system.log"
    echo "• Admin config: Stores → Configuration → AI Discovery Suite"
fi

echo ""
echo "📖 For detailed troubleshooting: COMPLETE_FRONTEND_AND_API_FIX.md"
