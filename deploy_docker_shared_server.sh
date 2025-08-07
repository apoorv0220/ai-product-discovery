#!/bin/bash

# 🐳 AI Product Discovery Suite - Docker Deployment for Shared Server
# Deploys services in Docker while using host PostgreSQL and Redis

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
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
   🐳 AI Product Discovery Suite - Docker Deployment
   ================================================
   
   Architecture:
   - PostgreSQL: Host server
   - Redis: Host server  
   - Services: Docker containers
   - Nginx: Docker reverse proxy
EOF
echo -e "${NC}"

log "Starting Docker deployment for shared server..."

# Step 1: Prerequisites Check
log "Step 1: Checking prerequisites..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose is not installed. Please install Docker Compose first."
fi

# Check if we're in the right directory
if [ ! -f "docker-compose.shared-server.yml" ]; then
    error "docker-compose.shared-server.yml not found. Please run from the correct directory."
fi

log "✅ Docker prerequisites check passed"

# Step 2: Test Host Services
log "Step 2: Testing host PostgreSQL and Redis connectivity..."

# Test PostgreSQL connection
log "Testing PostgreSQL connection..."
read -p "Enter PostgreSQL username (default: ai_discovery): " PG_USER
PG_USER=${PG_USER:-ai_discovery}

read -s -p "Enter PostgreSQL password: " PG_PASS
echo

read -p "Enter PostgreSQL database name (default: ai_discovery): " PG_DB
PG_DB=${PG_DB:-ai_discovery}

# Test PostgreSQL
if PGPASSWORD="$PG_PASS" psql -h localhost -p 5432 -U "$PG_USER" -d "$PG_DB" -c "SELECT 1;" &> /dev/null; then
    log "✅ PostgreSQL connection successful"
else
    error "❌ PostgreSQL connection failed. Please check your credentials and ensure PostgreSQL is running."
fi

# Test Redis connection
log "Testing Redis connection..."
if redis-cli -h 127.0.0.1 -p 6379 ping &> /dev/null; then
    log "✅ Redis connection successful"
    REDIS_HOST="127.0.0.1"
elif redis-cli -h localhost -p 6379 ping &> /dev/null; then
    log "✅ Redis connection successful"
    REDIS_HOST="localhost"
else
    error "❌ Redis connection failed. Please ensure Redis is running on port 6379."
fi

# Step 3: Create Environment Configuration
log "Step 3: Creating Docker environment configuration..."

# URL encode password for DATABASE_URL
PG_PASS_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${PG_PASS}', safe=''))")

# Generate secret keys
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Get server information
read -p "Enter your domain/IP for APIs (e.g., api.yourdomain.com or your-server-ip): " API_DOMAIN

# Create Docker environment file
cat > .env.docker-shared-server << EOF
# ===============================
# AI PRODUCT DISCOVERY SUITE
# Docker Shared Server Configuration
# Generated on $(date)
# ===============================

# Database Configuration (Host PostgreSQL)
DATABASE_URL=postgresql://${PG_USER}:${PG_PASS_ENCODED}@host.docker.internal:5432/${PG_DB}
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=5432
POSTGRES_DB=${PG_DB}
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASS}

# Redis Configuration (Host Redis)
REDIS_URL=redis://host.docker.internal:6379/0
REDIS_HOST=host.docker.internal
REDIS_PORT=6379
REDIS_DB=0

# Service Configuration (Docker Internal)
SEARCH_SERVICE_HOST=0.0.0.0
SEARCH_SERVICE_PORT=8000
RECOMMENDATION_SERVICE_HOST=0.0.0.0
RECOMMENDATION_SERVICE_PORT=8000
ANALYTICS_SERVICE_HOST=0.0.0.0
ANALYTICS_SERVICE_PORT=8000
SHOPPING_ASSISTANT_HOST=0.0.0.0
SHOPPING_ASSISTANT_PORT=8000

# External Access Ports (Host)
SEARCH_EXTERNAL_PORT=7001
RECOMMENDATION_EXTERNAL_PORT=7002
ANALYTICS_EXTERNAL_PORT=7004
SHOPPING_ASSISTANT_EXTERNAL_PORT=7005
FLOWER_EXTERNAL_PORT=7006

# API Configuration
API_V1_PREFIX=/api/v1
API_TITLE=AI Product Discovery Suite
API_VERSION=1.0.0
API_DOMAIN=${API_DOMAIN}

# Security
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Celery Configuration (Host Redis)
CELERY_BROKER_URL=redis://host.docker.internal:6379/1
CELERY_RESULT_BACKEND=redis://host.docker.internal:6379/2

# Flower Configuration
FLOWER_PASSWORD=admin123

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Environment
ENVIRONMENT=production
DEBUG=false

# CORS (adjust for your domain)
CORS_ORIGINS=["http://localhost:3000", "https://${API_DOMAIN}"]

# Magento Integration (update with your details)
MAGENTO_BASE_URL=https://your-magento-site.com
MAGENTO_API_TOKEN=your-magento-api-token

# Docker Specific
COMPOSE_PROJECT_NAME=ai-discovery
EOF

log "✅ Environment configuration created"

# Step 4: Initialize Database
log "Step 4: Initializing database schema..."

# Create a temporary Python environment for database initialization
python3 -m venv temp_env
source temp_env/bin/activate

# Install required packages
pip install sqlalchemy[asyncio]==2.0.36 asyncpg==0.30.0 psycopg2-binary==2.9.9 alembic==1.14.0

# Load environment variables
set -o allexport
source .env.docker-shared-server
set +o allexport

# Initialize database
cd backend
python3 -c "
import asyncio
import sys
sys.path.append('.')

from shared.database.base import init_database

async def setup():
    try:
        await init_database()
        print('✅ Database tables initialized successfully!')
    except Exception as e:
        print(f'❌ Database initialization failed: {e}')
        sys.exit(1)

asyncio.run(setup())
"

cd ..
deactivate
rm -rf temp_env

log "✅ Database initialized"

# Step 5: Build Docker Images
log "Step 5: Building Docker images..."

# Clean up any existing containers
docker-compose -f docker-compose.shared-server.yml down --remove-orphans 2>/dev/null || true

# Build images
log "Building Docker images (this may take a few minutes)..."
docker-compose -f docker-compose.shared-server.yml build --parallel

log "✅ Docker images built successfully"

# Step 6: Start Services
log "Step 6: Starting Docker services..."

# Start services
docker-compose -f docker-compose.shared-server.yml up -d

# Wait for services to be ready
log "Waiting for services to be ready..."
sleep 30

# Step 7: Health Checks
log "Step 7: Performing health checks..."

# Check service health
SERVICES=("search-service:7001" "recommendation-service:7002" "analytics-service:7004" "shopping-assistant:7005")

for service_port in "${SERVICES[@]}"; do
    IFS=':' read -ra ADDR <<< "$service_port"
    service="${ADDR[0]}"
    port="${ADDR[1]}"
    
    echo -n "Checking $service on port $port... "
    if curl -s -f http://localhost:$port/health > /dev/null; then
        echo "✅ OK"
    else
        echo "❌ FAILED"
        warning "$service is not responding on port $port"
    fi
done

# Step 8: Create Management Scripts
log "Step 8: Creating management scripts..."

# Docker control script
cat > docker_control.sh << 'EOF'
#!/bin/bash

COMPOSE_FILE="docker-compose.shared-server.yml"

start_services() {
    echo "🚀 Starting AI Discovery services..."
    docker-compose -f $COMPOSE_FILE up -d
    echo "✅ Services started!"
}

stop_services() {
    echo "🛑 Stopping AI Discovery services..."
    docker-compose -f $COMPOSE_FILE down
    echo "✅ Services stopped!"
}

restart_services() {
    echo "🔄 Restarting AI Discovery services..."
    docker-compose -f $COMPOSE_FILE restart
    echo "✅ Services restarted!"
}

status_services() {
    echo "📊 Service Status:"
    echo "=================="
    docker-compose -f $COMPOSE_FILE ps
}

logs_services() {
    echo "📝 Service Logs:"
    echo "================"
    docker-compose -f $COMPOSE_FILE logs -f
}

build_services() {
    echo "🔨 Building services..."
    docker-compose -f $COMPOSE_FILE build --parallel
    echo "✅ Build complete!"
}

case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        status_services
        ;;
    logs)
        logs_services
        ;;
    build)
        build_services
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|build}"
        exit 1
        ;;
esac
EOF

chmod +x docker_control.sh

# API test script
cat > test_docker_apis.sh << 'EOF'
#!/bin/bash

echo "🧪 Testing AI Product Discovery Suite APIs"
echo "=========================================="

test_api() {
    local name="$1"
    local url="$2"
    local method="${3:-GET}"
    local data="$4"
    
    echo -n "Testing $name... "
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null)
    else
        response=$(curl -s -w "%{http_code}" "$url" 2>/dev/null)
    fi
    
    http_code="${response: -3}"
    
    if [[ "$http_code" =~ ^[2][0-9][0-9]$ ]]; then
        echo "✅ OK ($http_code)"
    else
        echo "❌ FAILED ($http_code)"
    fi
}

# Test health endpoints
test_api "Search Health" "http://localhost:7001/health"
test_api "Recommendation Health" "http://localhost:7002/health"
test_api "Analytics Health" "http://localhost:7004/health"
test_api "Shopping Assistant Health" "http://localhost:7005/health"

echo ""

# Test API endpoints
test_api "Search API" "http://localhost:7001/api/v1/search/" "POST" \
    '{"query": "test", "limit": 3}'

test_api "Autocomplete API" "http://localhost:7001/api/v1/autocomplete/?q=test&limit=5"

test_api "Recommendations API" "http://localhost:7002/api/v1/recommendations/" "POST" \
    '{"user_id": "1", "context": "home", "limit": 8}'

test_api "Analytics API" "http://localhost:7004/api/v1/events/track" "POST" \
    '{"event_type": "test", "user_id": "1", "properties": {"test": true}}'

test_api "Shopping Assistant API" "http://localhost:7005/api/v1/chat/message" "POST" \
    '{"session_id": "test", "message": "Hello"}'

echo ""
echo "✅ API testing complete!"
echo ""
echo "🌐 Your services are running on:"
echo "  • Search: http://localhost:7001/api/v1/search/"
echo "  • Recommendations: http://localhost:7002/api/v1/recommendations/"
echo "  • Analytics: http://localhost:7004/api/v1/analytics/"
echo "  • Shopping Assistant: http://localhost:7005/api/v1/chat/"
echo "  • Flower (Celery): http://localhost:7006/"
EOF

chmod +x test_docker_apis.sh

log "✅ Management scripts created"

# Success summary
echo ""
echo -e "${GREEN}"
cat << "EOF"
🎉 DOCKER DEPLOYMENT COMPLETED! 🎉
==================================
EOF
echo -e "${NC}"

echo "🐳 Services running in Docker:"
echo "  • Search Service: http://localhost:7001"
echo "  • Recommendation Service: http://localhost:7002"  
echo "  • Analytics Service: http://localhost:7004"
echo "  • Shopping Assistant: http://localhost:7005"
echo "  • Celery Flower: http://localhost:7006"
echo "  • Nginx Reverse Proxy: http://localhost:80"

echo ""
echo "🖥️ Host services:"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"

echo ""
echo "🛠️ Management commands:"
echo "  • Control services: ./docker_control.sh {start|stop|restart|status|logs|build}"
echo "  • Test APIs: ./test_docker_apis.sh"
echo "  • View logs: docker-compose -f docker-compose.shared-server.yml logs -f"

echo ""
log "🎊 Docker deployment completed successfully!"

# Run initial API test
log "Running initial API test..."
./test_docker_apis.sh