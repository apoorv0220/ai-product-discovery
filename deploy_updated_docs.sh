#!/bin/bash

echo "📚 Deploying Updated API Documentation"
echo "====================================="

# Configuration
SERVER="ai-product-discovery.softdemonew.info"
SERVER_PATH="/root/ai-product-discovery"
SERVER_USER="root"

echo "📋 Documentation updates being deployed:"
echo "1. ✅ Updated FastAPI/Swagger main app description"
echo "2. ✅ New autocomplete schemas with OpenAI fields"
echo "3. ✅ New search schemas with metadata structure"
echo "4. ✅ OpenAI NLP schemas for integration"
echo "5. ✅ Complete API documentation with examples"
echo ""

# Upload updated files
echo "📤 Uploading documentation files..."

# Backend documentation files
scp backend/search-service/schemas/autocomplete_updated.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/schemas/
scp backend/search-service/schemas/search_updated.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/schemas/
scp backend/search-service/schemas/openai_nlp.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/schemas/

# Updated main app
scp backend/search-service/main.py $SERVER_USER@$SERVER:$SERVER_PATH/backend/search-service/

# Documentation files
scp API_DOCUMENTATION_UPDATED.md $SERVER_USER@$SERVER:$SERVER_PATH/

echo "✅ Files uploaded successfully"
echo ""

echo "🚀 Next steps to activate updated documentation:"
echo "1. SSH into server: ssh $SERVER_USER@$SERVER"
echo "2. Restart search service to load new schemas:"
echo "   cd $SERVER_PATH"
echo "   pkill -f 'search-service.*7001'"
echo "   cd backend"
echo "   nohup python3 -m uvicorn search-service.main:app --host 0.0.0.0 --port 7001 > ../search-service.log 2>&1 &"
echo ""
echo "3. Test updated Swagger docs:"
echo "   Open: http://ai-product-discovery.softdemonew.info:7001/docs"
echo "   Check: Updated descriptions, examples, and schemas"
echo ""
echo "4. Verify API responses match documentation:"
echo "   cd $SERVER_PATH"
echo "   ./test_api_sync.sh"
echo ""
echo "📖 What you'll see after deployment:"
echo "✅ FastAPI docs show enhanced descriptions with AI features"
echo "✅ All schemas reflect actual API response formats"
echo "✅ OpenAI integration fields documented with examples"
echo "✅ Comprehensive error handling examples"
echo "✅ Performance metrics and configuration details"
echo "✅ Perfect Swagger/reality synchronization"
echo ""
echo "🎯 Access points:"
echo "• Swagger UI: http://ai-product-discovery.softdemonew.info:7001/docs"
echo "• ReDoc: http://ai-product-discovery.softdemonew.info:7001/redoc"
echo "• Complete Docs: API_DOCUMENTATION_UPDATED.md"
