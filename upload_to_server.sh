#!/bin/bash

# Upload Enhanced Search Files to Production Server
echo "📤 Uploading Enhanced Search Files to Production Server"
echo "======================================================="

# Configuration
SERVER="ai-product-discovery.softdemonew.info"
SERVER_PATH="/root/ai-product-discovery"
SERVER_USER="root"

echo "Target server: $SERVER"
echo "Target path: $SERVER_PATH"
echo ""

# Check if files exist
echo "🔍 Checking files..."
if [ ! -f "backend/search-service/core/openai_nlp.py" ]; then
    echo "❌ OpenAI NLP file not found"
    exit 1
fi

if [ ! -f "backend/search-service/api/autocomplete.py" ]; then
    echo "❌ Autocomplete API file not found"
    exit 1
fi

echo "✅ All files found"
echo ""

# Upload files
echo "📤 Uploading files to server..."

# Upload backend files
echo "Uploading OpenAI NLP processor..."
scp backend/search-service/core/openai_nlp.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/core/

echo "Uploading enhanced autocomplete API..."
scp backend/search-service/api/autocomplete.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/api/

echo "Uploading updated requirements..."
scp backend/requirements.txt $SERVER_USER@$SERVER:$SERVER_PATH/backend/

# Upload deployment scripts
echo "Uploading deployment script..."
scp deploy_search_fixes.sh $SERVER_USER@$SERVER:$SERVER_PATH/

echo "Uploading test script..."
scp test_search_fixes.sh $SERVER_USER@$SERVER:$SERVER_PATH/

echo "Uploading deployment guide..."
scp PRODUCTION_DEPLOYMENT_STEPS.md $SERVER_USER@$SERVER:$SERVER_PATH/

echo ""
echo "✅ All files uploaded successfully!"
echo ""
echo "📋 Next steps:"
echo "1. SSH into the server: ssh $SERVER_USER@$SERVER"
echo "2. Navigate to project: cd $SERVER_PATH"
echo "3. Set OpenAI API key: export OPENAI_API_KEY='sk-your-key'"
echo "4. Run deployment: chmod +x deploy_search_fixes.sh && ./deploy_search_fixes.sh"
echo "5. Test the enhanced search: ./test_search_fixes.sh"
echo ""
echo "📖 Full deployment guide: PRODUCTION_DEPLOYMENT_STEPS.md"
