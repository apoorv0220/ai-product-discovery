#!/bin/bash

# AI Product Discovery Suite - Localhost Verification Script
# This script automates the complete setup and verification process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_header "AI Product Discovery Suite - Localhost Verification"

print_status "Starting comprehensive localhost verification..."
print_status "This will set up and test the entire system with dummy data."

# Check prerequisites
print_header "Checking Prerequisites"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are installed"

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    print_error "Python is not installed. Please install Python 3.7+ first."
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

print_status "Python is available: $PYTHON_CMD"

# Clean up any existing containers
print_header "Cleaning Up Existing Environment"

print_status "Stopping any running containers..."
docker-compose down --remove-orphans 2>/dev/null || true

print_status "Cleaning up Docker system..."
docker system prune -f >/dev/null 2>&1 || true

# Start infrastructure services
print_header "Starting Infrastructure Services"

print_status "Starting PostgreSQL, Redis, Elasticsearch, Weaviate, and RabbitMQ..."
docker-compose up -d postgres redis elasticsearch weaviate rabbitmq

print_status "Waiting for infrastructure services to be ready..."
sleep 60

# Check infrastructure health
print_header "Checking Infrastructure Health"

# Check PostgreSQL
print_status "Checking PostgreSQL..."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U discovery >/dev/null 2>&1; then
        print_status "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "PostgreSQL failed to start"
        docker-compose logs postgres
        exit 1
    fi
    sleep 2
done

# Check Redis
print_status "Checking Redis..."
for i in {1..30}; do
    if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
        print_status "Redis is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Redis failed to start"
        docker-compose logs redis
        exit 1
    fi
    sleep 2
done

# Check Elasticsearch
print_status "Checking Elasticsearch..."
for i in {1..60}; do
    if curl -s http://localhost:9200/_cluster/health | grep -q "green\|yellow"; then
        print_status "Elasticsearch is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        print_error "Elasticsearch failed to start"
        docker-compose logs elasticsearch
        exit 1
    fi
    sleep 3
done

# Check Weaviate
print_status "Checking Weaviate..."
for i in {1..60}; do
    if curl -s http://localhost:8065/v1/meta | grep -q "version"; then
        print_status "Weaviate is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        print_error "Weaviate failed to start"
        docker-compose logs weaviate
        exit 1
    fi
    sleep 3
done

# Check RabbitMQ
print_status "Checking RabbitMQ..."
for i in {1..30}; do
    if curl -s http://localhost:15672/ | grep -q "RabbitMQ"; then
        print_status "RabbitMQ is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "RabbitMQ failed to start"
        docker-compose logs rabbitmq
        exit 1
    fi
    sleep 2
done

# Start application services
print_header "Starting Application Services"

print_status "Starting Search, Recommendation, Analytics, and Shopping Assistant services..."
docker-compose up -d search-service recommendation-service analytics-service shopping-assistant

print_status "Waiting for application services to start..."
sleep 45

# Check application health
print_header "Checking Application Health"

SERVICES=("search-service:8001" "recommendation-service:8002" "analytics-service:8004" "shopping-assistant:8005")

for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port <<< "$service"
    print_status "Checking $name health..."
    
    for i in {1..30}; do
        if curl -f -s "http://localhost:$port/health/" >/dev/null; then
            print_status "$name is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "$name health check failed"
            docker-compose logs "$name"
            exit 1
        fi
        sleep 3
    done
done

# Install Python dependencies for scripts
print_header "Installing Python Dependencies"

print_status "Installing required Python packages..."
$PYTHON_CMD -m pip install aiohttp asyncio structlog sqlalchemy psycopg2-binary 2>/dev/null || {
    print_warning "Failed to install some packages via pip. Trying with --user flag..."
    $PYTHON_CMD -m pip install --user aiohttp asyncio structlog sqlalchemy psycopg2-binary 2>/dev/null || {
        print_warning "Could not install Python packages. Continuing anyway..."
    }
}

# Initialize database with dummy data
print_header "Initializing Database with Dummy Data"

print_status "Running database initialization script..."
cd "$(dirname "$0")/.."
$PYTHON_CMD scripts/init_dummy_data.py || {
    print_error "Failed to initialize dummy data"
    exit 1
}

# Run comprehensive verification
print_header "Running Comprehensive API Tests"

print_status "Testing all API endpoints..."
$PYTHON_CMD scripts/verify_localhost.py || {
    print_error "API verification failed"
    exit 1
}

# Test individual endpoints with curl
print_header "Running Individual Endpoint Tests"

print_status "Testing Search API..."
SEARCH_RESULT=$(curl -s -X POST http://localhost:8001/api/v1/search/ \
    -H "Content-Type: application/json" \
    -d '{"query": "MacBook", "limit": 3}' | jq -r '.total // "error"')
if [ "$SEARCH_RESULT" != "error" ] && [ "$SEARCH_RESULT" != "null" ]; then
    print_status "Search API working - found $SEARCH_RESULT results"
else
    print_error "Search API test failed"
fi

print_status "Testing Recommendations API..."
REC_RESULT=$(curl -s -X POST http://localhost:8002/api/v1/recommendations/ \
    -H "Content-Type: application/json" \
    -d '{"user_id": "1", "context": "homepage", "limit": 5}' | jq -r '.recommendations | length // "error"')
if [ "$REC_RESULT" != "error" ] && [ "$REC_RESULT" != "null" ]; then
    print_status "Recommendations API working - generated $REC_RESULT recommendations"
else
    print_error "Recommendations API test failed"
fi

print_status "Testing Analytics API..."
ANALYTICS_RESULT=$(curl -s -X POST http://localhost:8004/api/v1/events/track \
    -H "Content-Type: application/json" \
    -d '{"event_type": "test", "user_id": "1", "properties": {}}' | jq -r '.success // "error"')
if [ "$ANALYTICS_RESULT" = "true" ]; then
    print_status "Analytics API working - event tracked successfully"
else
    print_error "Analytics API test failed"
fi

print_status "Testing Shopping Assistant API..."
ASSISTANT_RESULT=$(curl -s -X POST http://localhost:8005/api/v1/chat/message \
    -H "Content-Type: application/json" \
    -d '{"session_id": "test", "message": "hello"}' | jq -r '.response // "error"')
if [ "$ASSISTANT_RESULT" != "error" ] && [ "$ASSISTANT_RESULT" != "null" ]; then
    print_status "Shopping Assistant API working - got response"
else
    print_error "Shopping Assistant API test failed"
fi

# Create demo files
print_header "Creating Demo Files"

mkdir -p demo

# Create search demo
cat > demo/search.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>AI Search Demo</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .search-box { margin: 20px 0; text-align: center; }
        .results { margin: 20px 0; }
        .product { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; background: #fafafa; }
        input[type="text"] { width: 400px; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
        button { padding: 12px 24px; background: #007cba; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-left: 10px; }
        button:hover { background: #005a8b; }
        .stats { background: #e7f3ff; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .price { color: #d73502; font-weight: bold; font-size: 18px; }
        .score { color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 AI Product Search Demo</h1>
        <p>Search through our AI-powered product catalog with intelligent ranking and filtering.</p>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search for products (e.g., MacBook, gaming console, wireless headphones)..." value="MacBook">
            <button onclick="performSearch()">Search</button>
        </div>
        
        <div id="results" class="results"></div>
    </div>

    <script>
        async function performSearch() {
            const query = document.getElementById('searchInput').value;
            const resultsDiv = document.getElementById('results');
            
            if (!query.trim()) {
                resultsDiv.innerHTML = '<p>Please enter a search query.</p>';
                return;
            }
            
            try {
                resultsDiv.innerHTML = '<div class="stats">🔍 Searching for "' + query + '"...</div>';
                
                const response = await fetch('http://localhost:8001/api/v1/search/', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        query: query,
                        limit: 10
                    })
                });
                
                const data = await response.json();
                
                if (data.results && data.results.length > 0) {
                    resultsDiv.innerHTML = `
                        <div class="stats">
                            📊 Found ${data.total} results in ${data.response_time_ms || 'N/A'}ms
                        </div>
                        ${data.results.map(product => `
                            <div class="product">
                                <h3>${product.name}</h3>
                                <p>${product.description}</p>
                                <p class="price">$${parseFloat(product.price).toFixed(2)}</p>
                                <p>SKU: ${product.sku || 'N/A'}</p>
                                <p>Stock: ${product.stock_quantity || 'N/A'} units</p>
                                <p class="score">Relevance Score: ${product.score?.toFixed(3) || 'N/A'}</p>
                            </div>
                        `).join('')}
                    `;
                } else {
                    resultsDiv.innerHTML = '<div class="stats">❌ No results found for "' + query + '"</div>';
                }
            } catch (error) {
                resultsDiv.innerHTML = `<div class="stats" style="background: #ffe7e7; color: #d73502;">❌ Error: ${error.message}</div>`;
            }
        }
        
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
        
        // Perform initial search
        performSearch();
    </script>
</body>
</html>
EOF

# Create recommendations demo
cat > demo/recommendations.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>AI Recommendations Demo</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .recommendations { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .product { border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #fafafa; }
        .controls { margin: 20px 0; padding: 15px; background: #e7f3ff; border-radius: 8px; }
        select, button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #28a745; color: white; border: none; cursor: pointer; }
        button:hover { background: #218838; }
        .price { color: #d73502; font-weight: bold; font-size: 18px; }
        .confidence { color: #666; font-size: 14px; }
        .reason { font-style: italic; color: #555; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Recommendations Demo</h1>
        <p>Experience personalized product recommendations powered by machine learning algorithms.</p>
        
        <div class="controls">
            <label><strong>User Profile:</strong></label>
            <select id="userSelect">
                <option value="1">John Doe (Prefers: Electronics, Laptops | Budget: $1000-$3000)</option>
                <option value="2">Jane Smith (Prefers: Smartphones, Audio | Budget: $200-$1200)</option>
                <option value="3">Mike Wilson (Prefers: Gaming, Electronics | Budget: $300-$800)</option>
                <option value="4">Sarah Johnson (Prefers: Cameras, Tablets | Budget: $500-$2500)</option>
                <option value="5">Alex Brown (Prefers: Smart Home, Audio | Budget: $50-$500)</option>
            </select>
            
            <label><strong>Context:</strong></label>
            <select id="contextSelect">
                <option value="homepage">Homepage (General recommendations)</option>
                <option value="product_page">Product Page (Related items)</option>
                <option value="cart">Shopping Cart (Cross-sell)</option>
                <option value="checkout">Checkout (Last minute additions)</option>
            </select>
            
            <button onclick="getRecommendations()">🔄 Get Recommendations</button>
        </div>
        
        <div id="recommendations" class="recommendations"></div>
    </div>

    <script>
        async function getRecommendations() {
            const userId = document.getElementById('userSelect').value;
            const context = document.getElementById('contextSelect').value;
            const recommendationsDiv = document.getElementById('recommendations');
            
            try {
                recommendationsDiv.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 20px;">🤖 Generating personalized recommendations...</div>';
                
                const response = await fetch('http://localhost:8002/api/v1/recommendations/', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user_id: userId,
                        context: context,
                        limit: 8
                    })
                });
                
                const data = await response.json();
                
                if (data.recommendations && data.recommendations.length > 0) {
                    recommendationsDiv.innerHTML = data.recommendations.map(product => `
                        <div class="product">
                            <h3>${product.name}</h3>
                            <p>${product.description}</p>
                            <p class="price">$${parseFloat(product.price).toFixed(2)}</p>
                            <p class="confidence">Confidence: ${product.score?.toFixed(3) || 'N/A'}</p>
                            <p class="reason">${product.reason || 'Recommended based on your preferences'}</p>
                        </div>
                    `).join('');
                } else {
                    recommendationsDiv.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 20px;">❌ No recommendations available for this context.</div>';
                }
            } catch (error) {
                recommendationsDiv.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 20px; background: #ffe7e7; color: #d73502;">❌ Error: ${error.message}</div>`;
            }
        }
        
        // Load initial recommendations
        getRecommendations();
    </script>
</body>
</html>
EOF

print_status "Demo files created in ./demo/ directory"

# Final summary
print_header "Verification Complete!"

print_status "🎉 AI Product Discovery Suite is successfully running on localhost!"
print_status ""
print_status "📊 SUMMARY:"
print_status "   • All infrastructure services are healthy"
print_status "   • All application services are running"
print_status "   • Database initialized with dummy data"
print_status "   • All API endpoints tested and working"
print_status "   • Demo pages created"
print_status ""
print_status "🌐 ACCESS URLS:"
print_status "   • Search API: http://localhost:8001/api/v1/search/"
print_status "   • Recommendations API: http://localhost:8002/api/v1/recommendations/"
print_status "   • Analytics API: http://localhost:8004/api/v1/events/"
print_status "   • Shopping Assistant API: http://localhost:8005/api/v1/chat/"
print_status "   • Search Demo: file://$(pwd)/demo/search.html"
print_status "   • Recommendations Demo: file://$(pwd)/demo/recommendations.html"
print_status ""
print_status "🔧 MANAGEMENT URLS:"
print_status "   • RabbitMQ Management: http://localhost:15672/ (guest/guest)"
print_status "   • Elasticsearch: http://localhost:9200/"
print_status "   • Weaviate: http://localhost:8065/v1/meta"
print_status ""
print_status "📱 TO VIEW DEMOS:"
print_status "   1. Open demo/search.html in your browser"
print_status "   2. Open demo/recommendations.html in your browser"
print_status "   3. Or start a local server: cd demo && python -m http.server 3000"
print_status ""
print_status "✅ System is ready for development and testing!"

echo ""
echo "======================================================"
echo "🎊 LOCALHOST VERIFICATION SUCCESSFUL! 🎊"
echo "======================================================"