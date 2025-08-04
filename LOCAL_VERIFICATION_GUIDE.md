# 🏠 AI Product Discovery Suite - Localhost Verification Guide

This guide provides step-by-step instructions to run and verify the entire AI Product Discovery Suite on your localhost with dummy data.

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start (One Command)](#quick-start)
3. [Step-by-Step Verification](#step-by-step-verification)
4. [Testing Each Feature](#testing-each-feature)
5. [Troubleshooting](#troubleshooting)
6. [API Examples](#api-examples)

---

## 🛠️ Prerequisites

### System Requirements
- **macOS/Linux/Windows** with Docker support
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **RAM**: Minimum 8GB (Recommended 12GB+)
- **Storage**: 5GB+ free space

### Verify Prerequisites
```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Check available RAM
free -h  # Linux
# or
system_profiler SPHardwareDataType | grep Memory  # macOS
```

---

## 🚀 Quick Start (One Command)

### Option 1: Automated Setup
```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

# Run the complete localhost verification
./scripts/verify_localhost.sh
```

### Option 2: Manual Steps
If the automated script doesn't work, follow the step-by-step guide below.

---

## 📖 Step-by-Step Verification

### Step 1: Clean Environment
```bash
# Stop any running containers
docker-compose down

# Remove old containers (optional - for clean start)
docker system prune -f

# Remove old volumes (optional - will delete data)
docker volume prune -f
```

### Step 2: Start Infrastructure Services
```bash
# Start infrastructure services first (in order)
docker-compose up -d postgres redis elasticsearch weaviate rabbitmq

# Wait for services to be ready (2-3 minutes)
echo "⏳ Waiting for infrastructure services to start..."
sleep 120

# Check infrastructure health
docker-compose ps
```

### Step 3: Verify Infrastructure
```bash
# Test PostgreSQL
docker-compose exec postgres pg_isready -U discovery

# Test Redis
docker-compose exec redis redis-cli ping

# Test Elasticsearch
curl -X GET "http://localhost:9200/_cluster/health?pretty"

# Test Weaviate
curl -X GET "http://localhost:8080/v1/meta"

# Test RabbitMQ
curl -X GET "http://localhost:15672/"
```

### Step 4: Start Application Services
```bash
# Start all application services
docker-compose up -d search-service recommendation-service analytics-service shopping-assistant

# Wait for services to start
echo "⏳ Waiting for application services to start..."
sleep 60

# Check all services
docker-compose ps
```

### Step 5: Initialize Database with Dummy Data
```bash
# Install Python dependencies (if running locally)
pip install aiohttp asyncio

# Initialize database and create dummy data
python scripts/init_dummy_data.py
```

### Step 6: Run Comprehensive Verification
```bash
# Run the verification script
python scripts/verify_localhost.py
```

---

## 🧪 Testing Each Feature

### 🔍 Search Functionality

#### Basic Search Test
```bash
curl -X POST http://localhost:8001/api/v1/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MacBook laptop",
    "limit": 5,
    "filters": {}
  }' | jq '.'
```

**Expected Response:**
```json
{
  "results": [
    {
      "id": 1,
      "name": "MacBook Pro 16-inch",
      "price": 2499.00,
      "score": 0.95
    }
  ],
  "total": 1,
  "query": "MacBook laptop",
  "response_time_ms": 45
}
```

#### Autocomplete Test
```bash
curl -X GET "http://localhost:8001/api/v1/autocomplete/?q=iPhone&limit=5" | jq '.'
```

#### Advanced Search with Filters
```bash
curl -X POST http://localhost:8001/api/v1/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "laptop",
    "limit": 10,
    "filters": {
      "category": "Laptops",
      "price_range": [1000, 3000],
      "brand": "Apple"
    }
  }' | jq '.'
```

### 🤖 Recommendation Engine

#### Homepage Recommendations
```bash
curl -X POST http://localhost:8002/api/v1/recommendations/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1",
    "context": "home",
    "limit": 8
  }' | jq '.'
```

**Expected Response:**
```json
{
  "recommendations": [
    {
      "product_id": 1,
      "name": "MacBook Pro 16-inch",
      "price": 2499.00,
      "score": 0.89,
      "reason": "Based on your preferences"
    }
  ],
  "user_id": "1",
  "context": "home",
  "algorithm": "hybrid"
}
```

#### Product Page Recommendations
```bash
curl -X POST http://localhost:8002/api/v1/recommendations/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1",
    "context": "product_detail",
    "product_ids": ["1"],
    "limit": 6
  }' | jq '.'
```

### 📊 Analytics & Tracking

#### Track Product View Event
```bash
curl -X POST http://localhost:8004/api/v1/events/track \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "product_view",
    "user_id": "1",
    "properties": {
      "product_id": "1",
      "page": "product_detail",
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'"
    }
  }' | jq '.'
```

#### Track Purchase Event
```bash
curl -X POST http://localhost:8004/api/v1/events/track \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "purchase",
    "user_id": "1",
    "properties": {
      "product_id": "1",
      "quantity": 1,
      "price": 2499.00,
      "order_id": "order_123"
    }
  }' | jq '.'
```

#### Get Analytics Dashboard
```bash
curl -X GET "http://localhost:8004/api/v1/dashboard/overview" | jq '.'
```

### 🛍️ Shopping Assistant

#### Start Chat Session
```bash
curl -X POST http://localhost:8005/api/v1/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "1"
  }' | jq '.'
```

#### Send Chat Message
```bash
curl -X POST http://localhost:8005/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_123",
    "message": "I need a laptop for programming and gaming under $2000"
  }' | jq '.'
```

**Expected Response:**
```json
{
  "response": "Based on your requirements, I'd recommend the Dell XPS 13 for $1,399. It has excellent performance for programming with Intel Core i7 and would handle light gaming well. Would you like to see similar options?",
  "session_id": "test_session_123",
  "recommendations": [
    {
      "product_id": 2,
      "name": "Dell XPS 13",
      "price": 1399.00
    }
  ]
}
```

---

## 🌐 Web Interface Testing

### Create Simple Demo Pages

#### 1. Search Demo Page
Create `demo/search.html`:
```html
<!DOCTYPE html>
<html>
<head>
    <title>AI Search Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .search-box { margin: 20px 0; }
        .results { margin: 20px 0; }
        .product { border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px; }
        input[type="text"] { width: 300px; padding: 10px; }
        button { padding: 10px 20px; background: #007cba; color: white; border: none; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>🔍 AI Product Search Demo</h1>
    
    <div class="search-box">
        <input type="text" id="searchInput" placeholder="Search for products..." value="MacBook">
        <button onclick="performSearch()">Search</button>
    </div>
    
    <div id="results" class="results"></div>

    <script>
        async function performSearch() {
            const query = document.getElementById('searchInput').value;
            const resultsDiv = document.getElementById('results');
            
            try {
                resultsDiv.innerHTML = '<p>Searching...</p>';
                
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
                        <h3>Found ${data.total} results in ${data.response_time_ms}ms</h3>
                        ${data.results.map(product => `
                            <div class="product">
                                <h4>${product.name}</h4>
                                <p>${product.description}</p>
                                <p><strong>Price: $${product.price}</strong></p>
                                <p>Score: ${product.score?.toFixed(2) || 'N/A'}</p>
                            </div>
                        `).join('')}
                    `;
                } else {
                    resultsDiv.innerHTML = '<p>No results found.</p>';
                }
            } catch (error) {
                resultsDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            }
        }
        
        // Search on Enter key
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
```

#### 2. Recommendations Demo Page
Create `demo/recommendations.html`:
```html
<!DOCTYPE html>
<html>
<head>
    <title>AI Recommendations Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .recommendations { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .product { border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #f9f9f9; }
        .controls { margin: 20px 0; }
        select, button { padding: 10px; margin: 5px; }
        button { background: #28a745; color: white; border: none; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>🤖 AI Recommendations Demo</h1>
    
    <div class="controls">
        <label>User ID: </label>
        <select id="userSelect">
            <option value="1">John Doe (Electronics, Laptops)</option>
            <option value="2">Jane Smith (Smartphones, Audio)</option>
            <option value="3">Mike Wilson (Gaming, Electronics)</option>
            <option value="4">Sarah Johnson (Cameras, Tablets)</option>
            <option value="5">Alex Brown (Smart Home, Audio)</option>
        </select>
        
        <label>Context: </label>
        <select id="contextSelect">
            <option value="home">Homepage</option>
            <option value="product_detail">Product Page</option>
            <option value="cart">Shopping Cart</option>
            <option value="checkout">Checkout</option>
        </select>
        
        <button onclick="getRecommendations()">Get Recommendations</button>
    </div>
    
    <div id="recommendations" class="recommendations"></div>

    <script>
        async function getRecommendations() {
            const userId = document.getElementById('userSelect').value;
            const context = document.getElementById('contextSelect').value;
            const recommendationsDiv = document.getElementById('recommendations');
            
            try {
                recommendationsDiv.innerHTML = '<p>Loading recommendations...</p>';
                
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
                            <h4>${product.name}</h4>
                            <p>${product.description}</p>
                            <p><strong>Price: $${product.price}</strong></p>
                            <p>Confidence: ${product.score?.toFixed(2) || 'N/A'}</p>
                            <p><em>${product.reason || 'Recommended for you'}</em></p>
                        </div>
                    `).join('');
                } else {
                    recommendationsDiv.innerHTML = '<p>No recommendations available.</p>';
                }
            } catch (error) {
                recommendationsDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            }
        }
        
        // Load initial recommendations
        getRecommendations();
    </script>
</body>
</html>
```

### Serve Demo Pages
```bash
# Create demo directory
mkdir -p demo

# Start a simple HTTP server
cd demo
python -m http.server 3000

# Open demo pages
open http://localhost:3000/search.html
open http://localhost:3000/recommendations.html
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Containers Not Starting
```bash
# Check Docker daemon
sudo systemctl status docker  # Linux
# or 
brew services list | grep docker  # macOS

# Check available ports
sudo lsof -i :8001,8002,8004,8005,5432,6379,9200,8080,15672

# Check logs
docker-compose logs [service-name]
```

#### 2. Weaviate Health Check Failing
```bash
# Check Weaviate logs
docker-compose logs weaviate

# Try alternative health check
curl -f http://localhost:8080/v1/meta

# Restart Weaviate
docker-compose restart weaviate
```

#### 3. Search Service Import Errors
```bash
# Check service logs
docker-compose logs search-service

# Rebuild with no cache
docker-compose build --no-cache search-service
docker-compose up -d search-service
```

#### 4. Database Connection Issues
```bash
# Check PostgreSQL
docker-compose exec postgres psql -U discovery -d discovery_suite -c "\dt"

# Check database logs
docker-compose logs postgres

# Reset database
docker-compose down
docker volume rm ai-product-discovery_postgres_data
docker-compose up -d postgres
```

#### 5. Python Dependencies Issues
```bash
# Install required packages
pip install aiohttp asyncio psycopg2-binary

# If using conda
conda install aiohttp asyncio psycopg2

# Check Python path
python -c "import sys; print(sys.path)"
```

### Memory Issues
```bash
# Check Docker memory usage
docker stats

# Increase Docker memory limit (Docker Desktop)
# Settings → Resources → Memory → 8GB+

# Clean up Docker
docker system prune -f
docker image prune -f
```

### Performance Optimization
```bash
# Monitor resource usage
htop  # or top on macOS

# Check disk space
df -h

# Optimize Docker
docker system df
docker system prune -f
```

---

## 📚 API Examples

### Complete API Testing Script
Create `test_all_apis.sh`:
```bash
#!/bin/bash

BASE_URL="http://localhost"
SEARCH_PORT="8001"
REC_PORT="8002"
ANALYTICS_PORT="8004"
ASSISTANT_PORT="8005"

echo "🧪 Testing All API Endpoints"
echo "================================"

# Test Search API
echo "🔍 Testing Search API..."
curl -s -X POST ${BASE_URL}:${SEARCH_PORT}/api/v1/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "MacBook", "limit": 3}' | jq '.results | length'

# Test Autocomplete
echo "📝 Testing Autocomplete..."
curl -s "${BASE_URL}:${SEARCH_PORT}/api/v1/autocomplete/?q=iPhone" | jq '.suggestions | length'

# Test Recommendations
echo "🤖 Testing Recommendations..."
curl -s -X POST ${BASE_URL}:${REC_PORT}/api/v1/recommendations/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "context": "home", "limit": 5}' | jq '.recommendations | length'

# Test Analytics
echo "📊 Testing Analytics..."
curl -s -X POST ${BASE_URL}:${ANALYTICS_PORT}/api/v1/events/track \
  -H "Content-Type: application/json" \
  -d '{"event_type": "test", "user_id": "1", "properties": {}}' | jq '.success'

# Test Shopping Assistant
echo "🛍️ Testing Shopping Assistant..."
curl -s -X POST ${BASE_URL}:${ASSISTANT_PORT}/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "message": "hello"}' | jq '.response'

echo "✅ All API tests completed!"
```

Make it executable and run:
```bash
chmod +x test_all_apis.sh
./test_all_apis.sh
```

---

## 🎯 Success Criteria

### ✅ All Services Healthy
- PostgreSQL responding on port 5432
- Redis responding on port 6379  
- Elasticsearch responding on port 9200
- Weaviate responding on port 8080
- RabbitMQ responding on port 15672
- All 4 application services responding

### ✅ Dummy Data Loaded
- 8 product categories created
- 10 sample products created
- 5 test users created
- Search logs with sample queries
- Analytics events and user sessions
- Recommendation logs with different contexts

### ✅ API Endpoints Working
- Search API returns relevant results
- Autocomplete provides suggestions
- Recommendations generate personalized results
- Analytics tracks events successfully
- Shopping Assistant responds to queries

### ✅ Web Demo Working
- Search demo page loads and functions
- Recommendations demo shows products
- Real-time API responses
- Proper error handling

---

## 🚀 Next Steps

Once localhost verification is complete:

1. **Magento Integration**: Test with actual Magento store
2. **Production Deployment**: Use production deployment guide
3. **Custom Data**: Replace dummy data with real product catalog
4. **Performance Testing**: Load testing with larger datasets
5. **Feature Enhancement**: Add custom AI features

---

## 📞 Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review Docker logs: `docker-compose logs [service]`
3. Verify all prerequisites are met
4. Check port availability
5. Ensure sufficient system resources

**Success!** 🎉 Your AI Product Discovery Suite is now running on localhost with dummy data and ready for testing!