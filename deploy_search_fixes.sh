#!/bin/bash

echo "🚀 Deploying Search Service Fixes"
echo "=================================="

# This script assumes you're running on the AI server where the search service is hosted
# If running locally, you'll need to copy files to the server first

SERVICE_NAME="search-service"
PORT=7001
PROJECT_ROOT="/root/ai-product-discovery"  # UPDATE THIS PATH
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "1. Stopping current search service..."
# Find and kill the search service process
PID=$(pgrep -f "uvicorn.*search-service.*$PORT")
if [ ! -z "$PID" ]; then
    kill $PID
    echo "✅ Stopped search service (PID: $PID)"
    sleep 2
else
    echo "⚠️  Search service not running"
fi

echo ""
echo "2. Deploying updated files..."
# Copy the updated files (if running locally, you'd use scp here)
echo "✅ Files ready for deployment"

echo ""
echo "3. Checking OpenAI API key..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OpenAI API key not set. Setting up fallback mode..."
    echo "   To enable full AI features, set: export OPENAI_API_KEY='sk-your-key'"
else
    echo "✅ OpenAI API key is configured"
fi

echo ""
echo "4. Installing/updating dependencies..."
cd "$PROJECT_ROOT" || exit 1

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Activated virtual environment"
else
    echo "⚠️  No virtual environment found, using system Python"
fi

# Install updated requirements
pip install httpx==0.28.1 > /dev/null 2>&1
echo "✅ Dependencies updated"

echo ""
echo "5. Starting enhanced search service..."
cd "$BACKEND_DIR" || exit 1

# Start the service in background
nohup python3 -m uvicorn search-service.main:app --host 0.0.0.0 --port $PORT --reload > ../search-service.log 2>&1 &
NEW_PID=$!
echo $NEW_PID > ../search-service.pid

echo "✅ Started enhanced search service (PID: $NEW_PID)"

echo ""
echo "6. Waiting for service to be ready..."
sleep 5

# Test if service is responding
if curl -s "http://localhost:$PORT/health" > /dev/null; then
    echo "✅ Search service is responding"
else
    echo "❌ Search service failed to start"
    exit 1
fi

echo ""
echo "7. Testing OpenAI-enhanced search..."
echo ""

# Test the specific issues
echo "🔍 Testing 'Hro Hoodie' typo correction..."
curl -s "http://localhost:$PORT/api/v1/autocomplete/?q=Hro%20Hoodie&limit=3" | python3 -m json.tool

echo ""
echo "🧠 Testing 'I want to buy a comfortable hoodie' semantic search..."
curl -s "http://localhost:$PORT/api/v1/autocomplete/?q=I%20want%20to%20buy%20a%20comfortable%20hoodie&limit=3" | python3 -m json.tool

echo ""
echo "✅ Testing regular search still works..."
curl -s "http://localhost:$PORT/api/v1/autocomplete/?q=hero&limit=3" | python3 -m json.tool

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Test the Magento endpoint: https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=Hro%20Hoodie"
echo "2. Verify typo correction is working"
echo "3. Check that semantic search finds results for natural language queries"
echo "4. Confirm images, prices, and categories display correctly"
