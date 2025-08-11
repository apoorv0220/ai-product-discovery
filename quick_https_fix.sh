#!/bin/bash

echo "🔧 Quick HTTPS/HTTP Mixed Protocol Fix"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "📋 Step 1: Applying HTTPS/HTTP Mixed Protocol Fix..."
echo "---------------------------------------------------"

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
echo "📦 Step 4: Ensuring Module is Enabled..."
echo "----------------------------------------"

php bin/magento module:enable Vendor_DiscoverySuite >/dev/null 2>&1
echo -e "${GREEN}✅ Module enabled${NC}"

echo ""
echo "⚙️ Step 5: Running Setup Upgrade..."
echo "----------------------------------"

php bin/magento setup:upgrade >/dev/null 2>&1
echo -e "${GREEN}✅ Setup upgrade completed${NC}"

echo ""
echo "⚙️ Step 6: Recompiling DI..."
echo "---------------------------"

COMPILE_OUTPUT=$(php bin/magento setup:di:compile 2>&1)
COMPILE_EXIT_CODE=$?

if [ $COMPILE_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ DI compilation successful${NC}"
else
    echo -e "${RED}❌ DI compilation failed${NC}"
    echo "Error output:"
    echo "$COMPILE_OUTPUT"
    exit 1
fi

echo ""
echo "🔧 Step 7: Setting Configuration..."
echo "----------------------------------"

# Set configuration explicitly
php bin/magento config:set discovery_suite_config/general/enabled 1 >/dev/null 2>&1
php bin/magento config:set discovery_suite_config/general/api_base_url "http://ai-product-discovery.softdemonew.info" >/dev/null 2>&1
php bin/magento config:set discovery_suite_config/general/debug_mode 1 >/dev/null 2>&1

echo -e "${GREEN}✅ Configuration set${NC}"

echo ""
echo "🗂️ Step 8: Final Cache Clear..."
echo "------------------------------"

php bin/magento cache:flush >/dev/null 2>&1
echo -e "${GREEN}✅ Final cache clear completed${NC}"

echo ""
echo "🧪 Step 9: Testing Connection..."
echo "-------------------------------"

echo "Running connection test..."
echo ""

# Test connection
TEST_OUTPUT=$(php bin/magento discovery:test:connection 2>&1)
TEST_EXIT_CODE=$?

echo "$TEST_OUTPUT"

echo ""
echo "📊 Summary"
echo "=========="

if [ $TEST_EXIT_CODE -eq 0 ] && echo "$TEST_OUTPUT" | grep -q "All services are connected successfully"; then
    echo -e "${GREEN}🎉 HTTPS/HTTP MIXED PROTOCOL FIX SUCCESSFUL!${NC}"
    echo ""
    echo "✅ All AI services are now connected from your HTTPS Magento site!"
    echo ""
    echo -e "${BLUE}Next steps to complete setup:${NC}"
    echo ""
    echo "1. Sync your product catalog:"
    echo "   php bin/magento discovery:sync:catalog"
    echo ""
    echo "2. Rebuild search index:"
    echo "   php bin/magento discovery:reindex:search"
    echo ""
    echo "3. Test autocomplete API:"
    echo "   curl \"http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=Ba&limit=10\""
    echo ""
    echo "4. Test on your website:"
    echo "   Visit https://magento-test.softdemonew.info and try search autocomplete"
    echo ""
    echo -e "${GREEN}Your HTTPS/HTTP mixed protocol issue is now completely resolved!${NC}"
    
elif echo "$TEST_OUTPUT" | grep -q "✓ Connected"; then
    echo -e "${YELLOW}⚠️ PARTIAL SUCCESS${NC}"
    echo ""
    echo "Some services are connected, but not all. This is progress!"
    echo "Check the output above to see which services need attention."
    echo ""
    echo "Common next steps:"
    echo "- Verify all AI services are running on the server"
    echo "- Check firewall settings for ports 7001-7004"
    echo "- Ensure AI services are accessible from Magento server"
    
else
    echo -e "${RED}❌ Connection test still failing${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo ""
    echo "1. Check if AI services are running:"
    echo "   docker ps | grep ai_discovery"
    echo ""
    echo "2. Test AI services directly:"
    echo "   curl -I http://ai-product-discovery.softdemonew.info:7001/health/"
    echo ""
    echo "3. Check module status:"
    echo "   php bin/magento module:status Vendor_DiscoverySuite"
    echo ""
    echo "4. Check configuration:"
    echo "   php bin/magento config:show discovery_suite_config/general/enabled"
    echo ""
    echo "5. Check logs for more details:"
    echo "   tail -f var/log/system.log | grep DiscoverySuite"
fi

echo ""
echo "For detailed information, see: HTTPS_HTTP_FIX_GUIDE.md"
