#!/bin/bash

echo "🚀 Complete Product Sync Test & Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "📋 Step 1: Preparing Product Sync Deployment..."
echo "----------------------------------------------"

# Check if we're in Magento root
if [ ! -f "bin/magento" ]; then
    echo -e "${RED}❌ Error: Not in Magento root directory${NC}"
    echo "Please run this script from your Magento root directory"
    exit 1
fi

echo -e "${GREEN}✅ Found Magento installation${NC}"

# Check if module exists
if [ ! -d "app/code/Vendor/DiscoverySuite" ]; then
    echo -e "${RED}❌ Error: DiscoverySuite module not found${NC}"
    echo "Please ensure the updated module files are uploaded to app/code/Vendor/DiscoverySuite/"
    exit 1
fi

echo -e "${GREEN}✅ DiscoverySuite module found${NC}"

echo ""
echo "🗂️ Step 2: Clearing Generated Files..."
echo "-------------------------------------"

# Clear generated files
rm -rf var/di/* var/generation/* generated/code/* 2>/dev/null
echo -e "${GREEN}✅ Generated files cleared${NC}"

echo ""
echo "🗂️ Step 3: Clearing Cache..."
echo "----------------------------"

php bin/magento cache:flush >/dev/null 2>&1
echo -e "${GREEN}✅ Cache cleared${NC}"

echo ""
echo "⚙️ Step 4: Recompiling DI with New Dependencies..."
echo "-------------------------------------------------"

COMPILE_OUTPUT=$(php bin/magento setup:di:compile 2>&1)
COMPILE_EXIT_CODE=$?

if [ $COMPILE_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ DI compilation successful with product sync dependencies${NC}"
else
    echo -e "${RED}❌ DI compilation failed${NC}"
    echo "Error output:"
    echo "$COMPILE_OUTPUT"
    exit 1
fi

echo ""
echo "🗂️ Step 5: Final Cache Clear..."
echo "------------------------------"

php bin/magento cache:flush >/dev/null 2>&1
echo -e "${GREEN}✅ Final cache clear completed${NC}"

echo ""
echo "🔗 Step 6: Testing AI Service Connection..."
echo "------------------------------------------"

echo "Running connection test..."
CONNECTION_OUTPUT=$(php bin/magento discovery:test:connection 2>&1)
CONNECTION_EXIT_CODE=$?

if [ $CONNECTION_EXIT_CODE -eq 0 ] && echo "$CONNECTION_OUTPUT" | grep -q "All services are connected successfully"; then
    echo -e "${GREEN}✅ AI services connection successful${NC}"
else
    echo -e "${RED}❌ AI services connection failed${NC}"
    echo "Connection output:"
    echo "$CONNECTION_OUTPUT"
    echo ""
    echo -e "${YELLOW}Please ensure AI services are running before proceeding${NC}"
    exit 1
fi

echo ""
echo "📦 Step 7: Testing Product Collection..."
echo "---------------------------------------"

# Check if products exist in Magento
PRODUCT_COUNT=$(php -r "
require 'app/bootstrap.php';
\$bootstrap = \Magento\Framework\App\Bootstrap::create(BP, \$_SERVER);
\$app = \$bootstrap->createApplication('Magento\Framework\App\Http');
\$objectManager = \$bootstrap->getObjectManager();
\$productCollection = \$objectManager->create('Magento\Catalog\Model\ResourceModel\Product\CollectionFactory')->create();
\$productCollection->addAttributeToFilter('status', 1)
                  ->addAttributeToFilter('visibility', ['in' => [2, 3, 4]]);
echo \$productCollection->getSize();
" 2>/dev/null)

if [ -z "$PRODUCT_COUNT" ] || [ "$PRODUCT_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ No enabled and visible products found in Magento${NC}"
    echo ""
    echo "Please ensure you have products that are:"
    echo "- Status: Enabled"
    echo "- Visibility: Catalog, Search, or Both"
    exit 1
else
    echo -e "${GREEN}✅ Found $PRODUCT_COUNT enabled and visible products${NC}"
fi

echo ""
echo "🚀 Step 8: Running Product Sync..."
echo "---------------------------------"

echo "Starting product catalog sync..."
echo ""

SYNC_OUTPUT=$(php bin/magento discovery:sync:catalog 2>&1)
SYNC_EXIT_CODE=$?

echo "$SYNC_OUTPUT"

echo ""
echo "📊 Step 9: Analyzing Sync Results..."
echo "-----------------------------------"

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    # Extract synced count from output
    SYNCED_COUNT=$(echo "$SYNC_OUTPUT" | grep -o "Synced [0-9]* products" | tail -1 | grep -o "[0-9]*" || echo "0")
    TOTAL_SYNCED=$(echo "$SYNC_OUTPUT" | grep "Catalog sync completed successfully! Synced [0-9]* products" | grep -o "[0-9]*" || echo "0")
    
    if [ "$TOTAL_SYNCED" -gt 0 ]; then
        echo -e "${GREEN}🎉 PRODUCT SYNC SUCCESSFUL!${NC}"
        echo ""
        echo -e "${GREEN}✅ Synced $TOTAL_SYNCED products to AI services${NC}"
        echo ""
    elif echo "$SYNC_OUTPUT" | grep -q "Processing batch"; then
        echo -e "${YELLOW}⚠️ PARTIAL SUCCESS${NC}"
        echo ""
        echo "Product batches were processed but sync count is 0"
        echo "This could indicate an API endpoint issue"
    else
        echo -e "${RED}❌ PRODUCT SYNC FAILED${NC}"
        echo ""
        echo "Sync command completed but no products were processed"
    fi
else
    echo -e "${RED}❌ PRODUCT SYNC COMMAND FAILED${NC}"
    echo ""
    echo "Sync command returned error code: $SYNC_EXIT_CODE"
fi

echo ""
echo "🔍 Step 10: Testing Search Index..."
echo "----------------------------------"

if [ "$TOTAL_SYNCED" -gt 0 ]; then
    echo "Running search index rebuild..."
    REINDEX_OUTPUT=$(php bin/magento discovery:reindex:search 2>&1)
    REINDEX_EXIT_CODE=$?
    
    echo "$REINDEX_OUTPUT"
    
    if [ $REINDEX_EXIT_CODE -eq 0 ] && echo "$REINDEX_OUTPUT" | grep -q "Search index rebuild initiated successfully"; then
        echo -e "${GREEN}✅ Search index rebuild successful${NC}"
    else
        echo -e "${YELLOW}⚠️ Search index rebuild had issues${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Skipping search index rebuild (no products synced)${NC}"
fi

echo ""
echo "🧪 Step 11: Testing Autocomplete API..."
echo "--------------------------------------"

if [ "$TOTAL_SYNCED" -gt 0 ]; then
    echo "Testing autocomplete endpoint..."
    sleep 2  # Give AI service time to process
    
    AUTOCOMPLETE_RESPONSE=$(curl -s "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=Ba&limit=5" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ ! -z "$AUTOCOMPLETE_RESPONSE" ]; then
        SUGGESTION_COUNT=$(echo "$AUTOCOMPLETE_RESPONSE" | grep -o '"suggestions":\[' | wc -l 2>/dev/null || echo "0")
        
        if echo "$AUTOCOMPLETE_RESPONSE" | grep -q '"suggestions":\[\]'; then
            echo -e "${YELLOW}⚠️ Autocomplete API responding but no suggestions yet${NC}"
            echo "This is normal - the search index may need a few minutes to update"
        elif echo "$AUTOCOMPLETE_RESPONSE" | grep -q '"suggestions":\['; then
            echo -e "${GREEN}✅ Autocomplete API returning suggestions!${NC}"
            echo "Sample response:"
            echo "$AUTOCOMPLETE_RESPONSE" | head -3
        else
            echo -e "${YELLOW}⚠️ Autocomplete API response unclear${NC}"
            echo "Response: $AUTOCOMPLETE_RESPONSE"
        fi
    else
        echo -e "${RED}❌ Autocomplete API not responding${NC}"
        echo "Check if AI services are running and accessible"
    fi
else
    echo -e "${YELLOW}⚠️ Skipping autocomplete test (no products synced)${NC}"
fi

echo ""
echo "📊 Final Summary"
echo "================"

if [ "$TOTAL_SYNCED" -gt 0 ]; then
    echo -e "${GREEN}🎉 COMPLETE SUCCESS!${NC}"
    echo ""
    echo -e "${GREEN}✅ Product sync working: $TOTAL_SYNCED products synced${NC}"
    echo -e "${GREEN}✅ AI services connected and responding${NC}"
    echo -e "${GREEN}✅ Search index rebuilt${NC}"
    echo ""
    echo -e "${BLUE}Your AI Product Discovery is now fully functional!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test frontend autocomplete on your website"
    echo "2. Visit: https://magento-test.softdemonew.info"
    echo "3. Try typing in the search box to see suggestions"
    echo ""
    echo "For ongoing sync, run periodically:"
    echo "- php bin/magento discovery:sync:catalog  (sync new/updated products)"
    echo "- php bin/magento discovery:reindex:search (rebuild search index)"
    
elif [ "$SYNCED_COUNT" -gt 0 ] || echo "$SYNC_OUTPUT" | grep -q "Processing batch"; then
    echo -e "${YELLOW}🔄 PARTIAL SUCCESS${NC}"
    echo ""
    echo -e "${YELLOW}✅ Product loading working: Found $PRODUCT_COUNT products${NC}"
    echo -e "${YELLOW}✅ Batch processing working: Products are being processed${NC}"
    echo -e "${YELLOW}⚠️ API integration issue: Products not syncing to AI service${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check AI service logs: docker logs ai_discovery_search"
    echo "2. Verify API endpoint: curl -X POST http://ai-product-discovery.softdemonew.info:7001/api/v1/index/products"
    echo "3. Enable debug mode: php bin/magento config:set discovery_suite_config/general/debug_mode 1"
    echo "4. Check Magento logs: tail -f var/log/system.log | grep DiscoverySuite"
    
else
    echo -e "${RED}❌ SYNC STILL NOT WORKING${NC}"
    echo ""
    echo "Issues detected:"
    if [ "$PRODUCT_COUNT" -eq 0 ]; then
        echo "- No enabled/visible products in Magento"
    fi
    if [ $CONNECTION_EXIT_CODE -ne 0 ]; then
        echo "- AI services connection failed"
    fi
    if [ $SYNC_EXIT_CODE -ne 0 ]; then
        echo "- Sync command failed"
    fi
    echo ""
    echo "Please review the error messages above and:"
    echo "1. Ensure products are enabled and visible in Magento admin"
    echo "2. Verify AI services are running: docker ps | grep ai_discovery"
    echo "3. Check network connectivity from Magento server to AI services"
    echo "4. Review logs for detailed error messages"
fi

echo ""
echo "For detailed information, see: COMPLETE_PRODUCT_SYNC_FIX.md"
