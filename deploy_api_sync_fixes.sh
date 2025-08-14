#!/bin/bash

echo "🔄 Deploying API Synchronization Fixes"
echo "======================================="

# Configuration
SERVER="ai-product-discovery.softdemonew.info"
SERVER_PATH="/root/ai-product-discovery"
SERVER_USER="root"

echo "📋 Changes being deployed:"
echo "1. ✅ Fixed backend autocomplete response format"
echo "2. ✅ Updated search API to use OpenAI NLP"
echo "3. ✅ Synchronized metadata structures"
echo "4. ✅ Fixed index endpoint path"
echo "5. ✅ Enhanced error handling"
echo ""

# Upload updated files
echo "📤 Uploading synchronized API files..."

# Backend files
scp backend/search-service/api/autocomplete.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/api/
scp backend/search-service/api/search.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/api/

# Magento files  
scp magento2-module/Vendor/DiscoverySuite/Model/Search/SearchService.php $SERVER_USER@$SERVER:$SERVER_PATH/../magento/app/code/Vendor/DiscoverySuite/Model/Search/

# Test script
scp test_api_sync.sh $SERVER_USER@$SERVER:$SERVER_PATH/

echo "✅ Files uploaded successfully"
echo ""

echo "🚀 Next steps to complete deployment:"
echo "1. SSH into server: ssh $SERVER_USER@$SERVER"
echo "2. Set OpenAI API key: export OPENAI_API_KEY='sk-your-key'"
echo "3. Restart search service:"
echo "   cd $SERVER_PATH"
echo "   pkill -f 'search-service.*7001'"
echo "   cd backend"
echo "   nohup python3 -m uvicorn search-service.main:app --host 0.0.0.0 --port 7001 > ../search-service.log 2>&1 &"
echo ""
echo "4. Update Magento module:"
echo "   cd /home/magentotests/public_html"
echo "   php bin/magento setup:di:compile"
echo "   php bin/magento cache:flush"
echo ""
echo "5. Test API synchronization:"
echo "   cd $SERVER_PATH"
echo "   ./test_api_sync.sh"
echo ""
echo "📖 Expected results after deployment:"
echo "✅ Backend autocomplete returns proper format with all required fields"
echo "✅ Magento autocomplete receives and processes data correctly"
echo "✅ Search API returns synchronized metadata"
echo "✅ Typo correction works: 'Hro Hoodie' → 'Hero Hoodie'"
echo "✅ Semantic search works: 'I want comfortable hoodie' → finds hoodies"
echo "✅ All endpoints return consistent data structures"
