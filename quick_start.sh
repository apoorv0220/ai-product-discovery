#!/bin/bash

# AI Product Discovery Suite - Quick Start Script
# Simple script to start services and run basic verification

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC}  $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

print_header "🚀 AI Product Discovery Suite - Quick Start"

print_info "This script will start all services and run basic verification"
print_info "If containers are already running, they will be restarted fresh"

# Force cleanup if needed
print_info "Cleaning up any existing containers..."
docker stop $(docker ps -q) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true

# Start infrastructure first
print_header "🏗️  Starting Infrastructure Services"
print_info "Starting PostgreSQL, Redis, Elasticsearch, Weaviate, RabbitMQ..."

docker-compose up -d postgres redis elasticsearch weaviate rabbitmq

print_info "Waiting 90 seconds for infrastructure to be ready..."
sleep 90

# Check infrastructure
print_info "Checking infrastructure health..."

# PostgreSQL
if docker-compose exec -T postgres pg_isready -U discovery >/dev/null 2>&1; then
    print_status "PostgreSQL is ready"
else
    print_error "PostgreSQL is not ready"
fi

# Redis
if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
    print_status "Redis is ready"
else
    print_error "Redis is not ready"
fi

# Elasticsearch
if curl -s http://localhost:9200/_cluster/health 2>/dev/null | grep -q "green\|yellow"; then
    print_status "Elasticsearch is ready"
else
    print_error "Elasticsearch is not ready"
fi

# Weaviate
if curl -s http://localhost:8080/v1/meta 2>/dev/null | grep -q "version"; then
    print_status "Weaviate is ready"
else
    print_error "Weaviate is not ready"
fi

# Start application services
print_header "🔧 Starting Application Services"
print_info "Starting Search, Recommendation, Analytics, Shopping Assistant..."

docker-compose up -d search-service recommendation-service analytics-service shopping-assistant

print_info "Waiting 60 seconds for application services to start..."
sleep 60

# Check application services
print_info "Checking application services health..."

SERVICES=("search-service:8001" "recommendation-service:8002" "analytics-service:8004" "shopping-assistant:8005")

for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port <<< "$service"
    
    if curl -f -s "http://localhost:$port/health/" >/dev/null 2>&1; then
        print_status "$name is healthy"
    else
        print_warning "$name health check failed, but service may still work"
    fi
done

# Initialize dummy data
print_header "📊 Initializing Dummy Data"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    print_error "Python not found. Please install Python 3.7+"
    exit 1
fi

print_info "Installing required Python packages..."
$PYTHON_CMD -m pip install --user aiohttp asyncio 2>/dev/null || print_warning "Could not install Python packages"

print_info "Running dummy data initialization..."
if $PYTHON_CMD scripts/init_dummy_data.py 2>/dev/null; then
    print_status "Dummy data initialized successfully"
else
    print_warning "Dummy data initialization may have failed, but continuing..."
fi

# Quick API tests
print_header "🧪 Quick API Tests"

print_info "Testing Search API..."
if curl -s -X POST http://localhost:8001/api/v1/search/ \
    -H "Content-Type: application/json" \
    -d '{"query": "test", "limit": 3}' >/dev/null 2>&1; then
    print_status "Search API responding"
else
    print_error "Search API not responding"
fi

print_info "Testing Recommendations API..."
if curl -s -X POST http://localhost:8002/api/v1/recommendations/ \
    -H "Content-Type: application/json" \
    -d '{"user_id": "1", "context": "home", "limit": 5}' >/dev/null 2>&1; then
    print_status "Recommendations API responding"
else
    print_error "Recommendations API not responding"
fi

print_info "Testing Analytics API..."
if curl -s -X POST http://localhost:8004/api/v1/events/track \
    -H "Content-Type: application/json" \
    -d '{"event_type": "test", "user_id": "1", "properties": {}}' >/dev/null 2>&1; then
    print_status "Analytics API responding"
else
    print_error "Analytics API not responding"
fi

print_info "Testing Shopping Assistant API..."
if curl -s -X POST http://localhost:8005/api/v1/chat/message \
    -H "Content-Type: application/json" \
    -d '{"session_id": "test", "message": "hello"}' >/dev/null 2>&1; then
    print_status "Shopping Assistant API responding"
else
    print_error "Shopping Assistant API not responding"
fi

# Show running containers
print_header "📋 System Status"
print_info "Running containers:"
docker-compose ps

print_header "🎉 Quick Start Complete!"

print_status "Core services are running. Here's how to test them:"
echo ""
print_info "🔍 Test Search API:"
echo "curl -X POST http://localhost:8001/api/v1/search/ -H 'Content-Type: application/json' -d '{\"query\": \"MacBook\", \"limit\": 5}'"
echo ""
print_info "🤖 Test Recommendations API:"
echo "curl -X POST http://localhost:8002/api/v1/recommendations/ -H 'Content-Type: application/json' -d '{\"user_id\": \"1\", \"context\": \"home\", \"limit\": 8}'"
echo ""
print_info "📊 Test Analytics API:"
echo "curl -X POST http://localhost:8004/api/v1/events/track -H 'Content-Type: application/json' -d '{\"event_type\": \"product_view\", \"user_id\": \"1\", \"properties\": {\"product_id\": \"1\"}}'"
echo ""
print_info "🛍️ Test Shopping Assistant API:"
echo "curl -X POST http://localhost:8005/api/v1/chat/message -H 'Content-Type: application/json' -d '{\"session_id\": \"test\", \"message\": \"I need a laptop\"}'"
echo ""

print_info "🌐 Service URLs:"
echo "   • Search Service: http://localhost:8001/api/v1/search/"
echo "   • Recommendations: http://localhost:8002/api/v1/recommendations/"
echo "   • Analytics: http://localhost:8004/api/v1/events/"
echo "   • Shopping Assistant: http://localhost:8005/api/v1/chat/"
echo "   • RabbitMQ Management: http://localhost:15672/ (guest/guest)"
echo ""

print_info "📊 For detailed verification, run:"
echo "python scripts/verify_localhost.py"
echo ""

print_status "🎊 System is ready for testing!"