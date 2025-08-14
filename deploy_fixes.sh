#!/bin/bash

echo "🔧 Deploying Critical API Fixes"
echo "==============================="

# Configuration
SERVER="144.217.68.58"
SERVER_PATH="/var/www/html/ai-product-discovery"
SERVER_USER="ubuntu"

echo "📋 Fixes being deployed:"
echo "1. ✅ Fixed relative import errors in OpenAI NLP"
echo "2. ✅ Fixed filters validation (array vs dict)"
echo "3. 🔄 Updated price and image processing logic"
echo ""

# Upload fixed files
echo "📤 Uploading fixed files..."

# Fixed API files
scp backend/search-service/api/autocomplete.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/api/
scp backend/search-service/api/search.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/api/

# Debug script
scp debug_product_data.py $SERVER_USER@$SERVER:$SERVER_PATH/

echo "✅ Files uploaded successfully"
echo ""

echo "🚀 Now restart the search service:"
echo "ssh $SERVER_USER@$SERVER"
echo "cd $SERVER_PATH"
echo "pkill -f 'search-service.*7001'"
echo "cd backend"
echo "nohup python3 -m uvicorn search-service.main:app --host 0.0.0.0 --port 7001 > ../search-service.log 2>&1 &"
echo ""
echo "🧪 Test after restart:"
echo "curl 'http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=Hro%20Hoodie&limit=3'"
echo ""
echo "Expected improvements:"
echo "✅ nlp_enhanced: true (if OpenAI key is set)"
echo "✅ is_corrected: true (for 'Hro Hoodie' → 'Hero Hoodie')"
echo "✅ No more import errors in logs"
echo "✅ Search API accepts both array and dict filters"
