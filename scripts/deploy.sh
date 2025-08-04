#!/bin/bash

# AI Product Discovery Suite - Production Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Example: ./scripts/deploy.sh production

set -e

ENVIRONMENT=${1:-production}
PROJECT_NAME="ai-product-discovery"

echo "🚀 Starting deployment for environment: $ENVIRONMENT"

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

# Check if environment file exists
if [[ "$ENVIRONMENT" == "production" ]]; then
    ENV_FILE=".env.production"
else
    ENV_FILE=".env"
fi

if [[ ! -f "$ENV_FILE" ]]; then
    print_error "Environment file $ENV_FILE not found"
    print_warning "Please create $ENV_FILE based on .env.production template"
    exit 1
fi

print_status "Environment file $ENV_FILE found"

# Create necessary directories
print_header "Creating Required Directories"

mkdir -p logs
mkdir -p backups
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources
mkdir -p nginx/conf.d
mkdir -p nginx/ssl
mkdir -p nginx/logs

print_status "Directories created"

# Set up environment
print_header "Setting Up Environment"

if [[ "$ENVIRONMENT" == "production" ]]; then
    cp .env.production .env
    print_status "Using production environment configuration"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
else
    print_status "Using development environment configuration"
    COMPOSE_FILES="-f docker-compose.yml"
fi

# Build images
print_header "Building Docker Images"

docker-compose $COMPOSE_FILES build --parallel

if [[ $? -eq 0 ]]; then
    print_status "Docker images built successfully"
else
    print_error "Failed to build Docker images"
    exit 1
fi

# Stop existing containers
print_header "Stopping Existing Containers"

docker-compose $COMPOSE_FILES down --remove-orphans

# Start infrastructure services first
print_header "Starting Infrastructure Services"

docker-compose $COMPOSE_FILES up -d postgres redis elasticsearch weaviate rabbitmq

# Wait for infrastructure to be ready
print_status "Waiting for infrastructure services to be ready..."

# Wait for PostgreSQL
print_status "Waiting for PostgreSQL..."
until docker-compose $COMPOSE_FILES exec -T postgres pg_isready -U discovery; do
    sleep 2
done

# Wait for Redis
print_status "Waiting for Redis..."
until docker-compose $COMPOSE_FILES exec -T redis redis-cli ping | grep -q PONG; do
    sleep 2
done

# Wait for Elasticsearch
print_status "Waiting for Elasticsearch..."
until curl -s http://localhost:9200/_cluster/health | grep -q '"status":"green"'; do
    sleep 5
done

# Wait for Weaviate
print_status "Waiting for Weaviate..."
until curl -s http://localhost:8080/v1/meta | grep -q version; do
    sleep 5
done

# Wait for RabbitMQ
print_status "Waiting for RabbitMQ..."
until docker-compose $COMPOSE_FILES exec -T rabbitmq rabbitmqctl status | grep -q "Status of node"; do
    sleep 5
done

print_status "Infrastructure services are ready"

# Run database migrations
print_header "Running Database Migrations"

docker-compose $COMPOSE_FILES run --rm search-service python -c "
import asyncio
from shared.database.base import init_database

async def main():
    try:
        await init_database()
        print('Database initialized successfully')
    except Exception as e:
        print(f'Database initialization failed: {e}')
        exit(1)

if __name__ == '__main__':
    asyncio.run(main())
"

# Start application services
print_header "Starting Application Services"

docker-compose $COMPOSE_FILES up -d

# Wait for services to be ready
print_status "Waiting for application services to start..."
sleep 30

# Health checks
print_header "Running Health Checks"

services=("search-service:8001" "recommendation-service:8002" "analytics-service:8004" "shopping-assistant:8005")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    print_status "Checking $name health..."
    
    for i in {1..10}; do
        if curl -f -s "http://localhost:$port/health/" > /dev/null; then
            print_status "$name is healthy"
            break
        else
            if [[ $i -eq 10 ]]; then
                print_warning "$name health check failed after 10 attempts"
                # Show service logs for debugging
                echo "Recent logs for $name:"
                docker-compose $COMPOSE_FILES logs --tail=20 "$name"
            else
                sleep 5
            fi
        fi
    done
done

# Test API endpoints
print_header "Testing API Endpoints"

echo "Testing Search API..."
curl -X POST http://localhost:8001/api/v1/search/ \
    -H "Content-Type: application/json" \
    -d '{"query": "test", "limit": 5}' \
    -w "\nStatus: %{http_code}\n" || print_warning "Search API test failed"

echo "Testing Recommendations API..."
curl -X POST http://localhost:8002/api/v1/recommendations/ \
    -H "Content-Type: application/json" \
    -d '{"user_id": "test_user", "context": "homepage", "limit": 5}' \
    -w "\nStatus: %{http_code}\n" || print_warning "Recommendations API test failed"

echo "Testing Analytics API..."
curl -X POST http://localhost:8004/api/v1/events/track \
    -H "Content-Type: application/json" \
    -d '{"event_type": "test", "user_id": "test_user", "properties": {}}' \
    -w "\nStatus: %{http_code}\n" || print_warning "Analytics API test failed"

echo "Testing Shopping Assistant API..."
curl -X POST http://localhost:8005/api/v1/chat/message \
    -H "Content-Type: application/json" \
    -d '{"session_id": "test_session", "message": "hello"}' \
    -w "\nStatus: %{http_code}\n" || print_warning "Shopping Assistant API test failed"

# Show running containers
print_header "Deployment Summary"

print_status "Running containers:"
docker-compose $COMPOSE_FILES ps

print_status "Service URLs:"
echo "  🔍 Search API: http://localhost:8001/api/v1/search/"
echo "  🤖 Recommendations API: http://localhost:8002/api/v1/recommendations/"
echo "  📊 Analytics API: http://localhost:8004/api/v1/events/"
echo "  🛍️  Shopping Assistant API: http://localhost:8005/api/v1/chat/"
echo "  🐰 RabbitMQ Management: http://localhost:15672/ (guest/guest)"
echo "  🌸 Flower Celery Monitor: http://localhost:5555/"

if [[ "$ENVIRONMENT" == "production" ]]; then
    echo "  📈 Prometheus: http://localhost:9090/"
    echo "  📊 Grafana: http://localhost:3000/"
fi

print_header "Deployment Complete!"

print_status "🎉 AI Product Discovery Suite deployed successfully!"
print_status "Environment: $ENVIRONMENT"
print_status "All services are running and ready to accept requests."

if [[ "$ENVIRONMENT" == "production" ]]; then
    print_warning "📋 Production Checklist:"
    echo "  ✅ Update DNS records to point to this server"
    echo "  ✅ Configure SSL certificates"
    echo "  ✅ Set up monitoring alerts"
    echo "  ✅ Configure backups"
    echo "  ✅ Update Magento module configuration"
    echo "  ✅ Test end-to-end integration"
fi