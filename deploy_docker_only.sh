#!/bin/bash

# 🐳 Docker-Only Deployment Script
# Alternative deployment that uses Docker for all Python operations (no host Python dependencies)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

echo -e "${BLUE}"
cat << "EOF"
   🐳 AI Product Discovery Suite - Docker-Only Deployment
   =====================================================
   Deploying using Docker for all operations (no host Python dependencies)
EOF
echo -e "${NC}"

# Step 1: Check Prerequisites
log "Step 1: Checking prerequisites..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    error "Please do not run this script as root. Use a regular user with sudo privileges."
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose is not installed. Please install Docker Compose first."
fi

# Check if user is in docker group
if ! groups $USER | grep -q docker; then
    warning "User $USER is not in the docker group. You may need to use sudo for Docker commands."
fi

log "✅ Prerequisites check completed"

# Step 2: Check Host Services
log "Step 2: Checking host services (PostgreSQL and Redis)..."

# Test PostgreSQL connection
PG_HOST="localhost"
PG_PORT="5432"
PG_WORKING=false

if nc -z $PG_HOST $PG_PORT 2>/dev/null; then
    log "✅ PostgreSQL connection successful ($PG_HOST:$PG_PORT)"
    PG_WORKING=true
else
    error "❌ PostgreSQL connection failed. Please ensure PostgreSQL is running on port $PG_PORT"
fi

# Test Redis connection
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_WORKING=false

if nc -z $REDIS_HOST $REDIS_PORT 2>/dev/null; then
    log "✅ Redis connection successful ($REDIS_HOST:$REDIS_PORT)"
    REDIS_WORKING=true
else
    error "❌ Redis connection failed. Please ensure Redis is running on port $REDIS_PORT"
fi

# Step 3: Configure Environment
log "Step 3: Configuring environment..."

# Prompt for required configuration
read -p "Enter your API domain (e.g., ai-discovery.yourdomain.com): " API_DOMAIN
read -p "Enter your Magento base URL (e.g., https://magento.yourdomain.com): " MAGENTO_BASE_URL
read -p "Enter your Magento API token: " MAGENTO_API_TOKEN

# Generate secure keys
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

# Get PostgreSQL credentials
read -p "Enter PostgreSQL database name: " PG_DB
read -p "Enter PostgreSQL username: " PG_USER
read -s -p "Enter PostgreSQL password: " PG_PASS
echo ""

# URL encode password for DATABASE_URL
PG_PASS_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${PG_PASS}', safe=''))" 2>/dev/null || echo "$PG_PASS")

# Create environment file
cat > .env.docker-shared-server << EOF
# PostgreSQL Configuration (Host Service)
DATABASE_URL=postgresql://${PG_USER}:${PG_PASS_ENCODED}@host.docker.internal:5432/${PG_DB}
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=5432
POSTGRES_DB=${PG_DB}
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASS}

# Redis Configuration (Host Service)
REDIS_URL=redis://host.docker.internal:6379/0
REDIS_HOST=host.docker.internal
REDIS_PORT=6379
REDIS_DB=0

# Celery Configuration
CELERY_BROKER_URL=redis://host.docker.internal:6379/1
CELERY_RESULT_BACKEND=redis://host.docker.internal:6379/2

# Service Ports (External - accessible from host)
SEARCH_SERVICE_EXTERNAL_PORT=7001
RECOMMENDATION_EXTERNAL_PORT=7002
ANALYTICS_EXTERNAL_PORT=7004
SHOPPING_ASSISTANT_EXTERNAL_PORT=7005
FLOWER_EXTERNAL_PORT=7006

# API Configuration
API_V1_PREFIX=/api/v1
API_TITLE="AI Product Discovery Suite"
API_VERSION=1.0.0
API_DOMAIN=${API_DOMAIN}

# Security
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Elasticsearch Configuration
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_INDEX_PREFIX=ai_discovery

# Weaviate Configuration
WEAVIATE_URL=http://weaviate:8080
WEAVIATE_CLASS_PREFIX=AiDiscovery

# OpenAI Configuration (optional - add your keys)
OPENAI_API_KEY=your-openai-api-key-here

# Environment
ENVIRONMENT=production
DEBUG=false

# CORS
CORS_ORIGINS='["http://localhost:3000", "https://${API_DOMAIN}"]'

# Magento Integration
MAGENTO_BASE_URL=${MAGENTO_BASE_URL}
MAGENTO_API_TOKEN=${MAGENTO_API_TOKEN}

# Docker Specific
COMPOSE_PROJECT_NAME=ai-discovery
EOF

log "✅ Environment configuration created"

# Step 4: Initialize Database Using Docker
log "Step 4: Initializing database schema using Docker..."

# Build a temporary image for database initialization
cat > Dockerfile.db-init << EOF
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \\
    sqlalchemy[asyncio]==2.0.36 \\
    asyncpg==0.30.0 \\
    psycopg2-binary==2.9.9 \\
    alembic==1.14.0 \\
    structlog==24.4.0 \\
    pydantic-settings==2.8.0 \\
    pydantic==2.9.2

# Copy backend code
COPY backend/ /app/backend/

# Set Python path
ENV PYTHONPATH=/app

CMD ["python3", "-c", "\\
import asyncio\\
import sys\\
import os\\
sys.path.insert(0, '/app')\\
from backend.shared.database.base import init_database\\
\\
async def setup():\\
    try:\\
        await init_database()\\
        print('✅ Database tables initialized successfully!')\\
    except Exception as e:\\
        print(f'❌ Database initialization failed: {e}')\\
        sys.exit(1)\\
\\
asyncio.run(setup())\\
"]
EOF

# Build and run database initialization
log "Building database initialization image..."
docker build -f Dockerfile.db-init -t ai-discovery-db-init .

log "Running database initialization..."
docker run --rm --env-file .env.docker-shared-server --add-host=host.docker.internal:host-gateway ai-discovery-db-init

# Cleanup
rm Dockerfile.db-init

log "✅ Database initialized"

# Step 5: Build Docker Images
log "Step 5: Building Docker images..."

# Use the shared server compose file
docker-compose -f docker-compose.shared-server.yml --env-file .env.docker-shared-server build

log "✅ Docker images built"

# Step 6: Start Services
log "Step 6: Starting Docker services..."

# Start all services
docker-compose -f docker-compose.shared-server.yml --env-file .env.docker-shared-server up -d

log "✅ Services started"

# Step 7: Wait for Services
log "Step 7: Waiting for services to be ready..."

# Wait function
wait_for_service() {
    local service_name="$1"
    local url="$2"
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            log "✅ $service_name is ready"
            return 0
        fi
        
        info "Waiting for $service_name... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    warning "❌ $service_name did not become ready in time"
    return 1
}

# Wait for all services
wait_for_service "Search Service" "http://localhost:7001/health"
wait_for_service "Recommendation Service" "http://localhost:7002/health"
wait_for_service "Analytics Service" "http://localhost:7004/health"
wait_for_service "Shopping Assistant" "http://localhost:7005/health"

log "✅ All services are ready"

# Step 8: Test APIs
log "Step 8: Testing API endpoints..."

# Test function
test_api() {
    local name="$1"
    local url="$2"
    
    if curl -s "$url" > /dev/null 2>&1; then
        log "✅ $name API is working"
        return 0
    else
        warning "❌ $name API test failed"
        return 1
    fi
}

# Test all APIs
test_api "Search Service" "http://localhost:7001/health"
test_api "Recommendation Service" "http://localhost:7002/health"
test_api "Analytics Service" "http://localhost:7004/health"
test_api "Shopping Assistant" "http://localhost:7005/health"

log "✅ API testing completed"

# Step 9: Display Summary
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo "Services are running on the following ports:"
echo "  🔍 Search Service:      http://localhost:7001"
echo "  🤖 Recommendation:     http://localhost:7002"
echo "  📊 Analytics:          http://localhost:7004"
echo "  🛍️  Shopping Assistant: http://localhost:7005"
echo "  🌸 Flower (Celery):    http://localhost:7006"
echo ""
echo "API Documentation:"
echo "  🔍 Search API:      http://localhost:7001/docs"
echo "  🤖 Recommendation: http://localhost:7002/docs"
echo "  📊 Analytics:      http://localhost:7004/docs"
echo "  🛍️  Assistant:      http://localhost:7005/docs"
echo ""
echo "Management Commands:"
echo "  📊 View logs:       docker-compose -f docker-compose.shared-server.yml logs -f"
echo "  🛑 Stop services:   docker-compose -f docker-compose.shared-server.yml down"
echo "  🔄 Restart:         docker-compose -f docker-compose.shared-server.yml restart"
echo ""
echo "🎯 Your AI Product Discovery Suite is ready for integration with Magento!"