#!/bin/bash

# 🚀 AI Product Discovery Suite - Shared Server Deployment Script
# This script automates the deployment process for beginners

set -e  # Exit on any error

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

# Banner
echo -e "${BLUE}"
cat << "EOF"
   _____ _____   _____               _            _     
  |  _  |     | |  _  |___ ___ ___ _| |_ _ ___   _| |___ 
  |     |-   -| |   __|  _| . | . | . | | |  _| |  _| .'|
  |__|__|_____| |__|  |_| |___|___|___|___|_|   |_| |__,|
                                                        
         Discovery Suite - Shared Server Deployment
EOF
echo -e "${NC}"

log "Starting AI Product Discovery Suite deployment..."

# Step 1: Verify Prerequisites
log "Step 1: Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed. Please install Python 3.8+"
fi

python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
info "Python version: $python_version"

# Check pip
if ! command -v pip3 &> /dev/null; then
    error "pip3 is not installed. Please install pip3"
fi

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    warning "PostgreSQL client tools not found. Installing..."
    sudo apt update && sudo apt install -y postgresql-client libpq-dev
fi

# Check Redis
if ! command -v redis-cli &> /dev/null; then
    warning "Redis tools not found. Installing..."
    sudo apt update && sudo apt install -y redis-tools
fi

# Test PostgreSQL connection
log "Testing PostgreSQL connection..."
read -p "Enter PostgreSQL username: " PG_USER
read -s -p "Enter PostgreSQL password: " PG_PASS
echo
read -p "Enter PostgreSQL database name (or press Enter for 'ai_discovery'): " PG_DB
PG_DB=${PG_DB:-ai_discovery}

# Test connection
if PGPASSWORD="$PG_PASS" psql -h localhost -p 5432 -U "$PG_USER" -d "$PG_DB" -c "SELECT 1;" &> /dev/null; then
    log "✅ PostgreSQL connection successful"
else
    warning "❌ PostgreSQL connection failed. Will create database..."
    
    # Try to create database
    if PGPASSWORD="$PG_PASS" createdb -h localhost -p 5432 -U "$PG_USER" "$PG_DB" &> /dev/null; then
        log "✅ Database '$PG_DB' created successfully"
    else
        error "Failed to create database. Please create it manually or check permissions"
    fi
fi

# Test Redis connection
log "Testing Redis connection..."
if redis-cli -h localhost -p 6379 ping &> /dev/null; then
    log "✅ Redis connection successful"
else
    error "❌ Redis connection failed. Please ensure Redis is running on port 6379"
fi

# Step 2: Setup Application Directory
log "Step 2: Setting up application directory..."

APP_DIR="$HOME/apps/ai-product-discovery"
LOG_DIR="$HOME/logs"
DATA_DIR="$HOME/data"

# Create directories
mkdir -p "$HOME/apps" "$LOG_DIR" "$DATA_DIR"

# Check if already exists
if [ -d "$APP_DIR" ]; then
    read -p "Application directory already exists. Remove and reinstall? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$APP_DIR"
    else
        error "Please remove existing installation or choose different directory"
    fi
fi

# Copy current directory to app directory
log "Copying application files..."
cp -r "$(pwd)" "$APP_DIR"
cd "$APP_DIR"

# Step 3: Create Virtual Environment
log "Step 3: Creating Python virtual environment..."

if [ -d "venv" ]; then
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Step 4: Install Dependencies
log "Step 4: Installing Python dependencies..."

# Install base requirements first
if [ -f "backend/requirements-base.txt" ]; then
    pip install -r backend/requirements-base.txt
fi

# Install full requirements
if [ -f "backend/requirements.txt" ]; then
    log "Installing Python dependencies (this may take a few minutes)..."
    pip install -r backend/requirements.txt || {
        warning "Dependencies installation failed. Trying with compatible versions..."
        # Fix common dependency conflicts
        pip install "httpx==0.27.0" "weaviate-client==4.8.1"
        pip install -r backend/requirements.txt
    }
fi

# Install production dependencies
pip install gunicorn supervisor

# Step 5: Create Environment Configuration
log "Step 5: Creating environment configuration..."

# Generate secret keys
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Get server information
read -p "Enter your domain/IP for APIs (e.g., api.yourdomain.com or your-server-ip): " API_DOMAIN

# Create production environment file
cat > .env.production << EOF
# ===============================
# AI PRODUCT DISCOVERY SUITE
# Shared Server Configuration
# Generated on $(date)
# ===============================

# Database Configuration
DATABASE_URL=postgresql://${PG_USER}:${PG_PASS}@localhost:5432/${PG_DB}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=${PG_DB}
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASS}

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Service Configuration
SEARCH_SERVICE_HOST=0.0.0.0
SEARCH_SERVICE_PORT=7001
RECOMMENDATION_SERVICE_HOST=0.0.0.0
RECOMMENDATION_SERVICE_PORT=7002
ANALYTICS_SERVICE_HOST=0.0.0.0
ANALYTICS_SERVICE_PORT=7004
SHOPPING_ASSISTANT_HOST=0.0.0.0
SHOPPING_ASSISTANT_PORT=7005

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

# External Services (Optional)
ELASTICSEARCH_URL=http://localhost:9200
WEAVIATE_URL=http://localhost:8080

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Environment
ENVIRONMENT=production
DEBUG=false
EOF

# Secure environment file
chmod 600 .env.production
ln -sf .env.production .env

log "✅ Environment configuration created"

# Step 6: Initialize Database
log "Step 6: Initializing database tables..."

export $(cat .env.production | xargs)

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

# Step 7: Create Service Scripts
log "Step 7: Creating service startup scripts..."

# Search Service
cat > start_search.sh << 'EOF'
#!/bin/bash
cd $(dirname $0)
source venv/bin/activate
export $(cat .env.production | xargs)

echo "Starting Search Service on port 7001..."
cd backend/search-service
exec gunicorn main:app \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:7001 \
    --access-logfile ${HOME}/logs/search_access.log \
    --error-logfile ${HOME}/logs/search_error.log \
    --pid ${HOME}/logs/search.pid \
    --daemon
EOF

# Recommendation Service
cat > start_recommendation.sh << 'EOF'
#!/bin/bash
cd $(dirname $0)
source venv/bin/activate
export $(cat .env.production | xargs)

echo "Starting Recommendation Service on port 7002..."
cd backend/recommendation-service
exec gunicorn main:app \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:7002 \
    --access-logfile ${HOME}/logs/recommendation_access.log \
    --error-logfile ${HOME}/logs/recommendation_error.log \
    --pid ${HOME}/logs/recommendation.pid \
    --daemon
EOF

# Analytics Service
cat > start_analytics.sh << 'EOF'
#!/bin/bash
cd $(dirname $0)
source venv/bin/activate
export $(cat .env.production | xargs)

echo "Starting Analytics Service on port 7004..."
cd backend/analytics-service
exec gunicorn main:app \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:7004 \
    --access-logfile ${HOME}/logs/analytics_access.log \
    --error-logfile ${HOME}/logs/analytics_error.log \
    --pid ${HOME}/logs/analytics.pid \
    --daemon
EOF

# Shopping Assistant Service
cat > start_shopping_assistant.sh << 'EOF'
#!/bin/bash
cd $(dirname $0)
source venv/bin/activate
export $(cat .env.production | xargs)

echo "Starting Shopping Assistant Service on port 7005..."
cd backend/shopping-assistant
exec gunicorn main:app \
    -w 2 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:7005 \
    --access-logfile ${HOME}/logs/shopping_assistant_access.log \
    --error-logfile ${HOME}/logs/shopping_assistant_error.log \
    --pid ${HOME}/logs/shopping_assistant.pid \
    --daemon
EOF

# Master control script
cat > control_services.sh << 'EOF'
#!/bin/bash

SERVICES=("search" "recommendation" "analytics" "shopping_assistant")
PORTS=("7001" "7002" "7004" "7005")

start_all() {
    echo "🚀 Starting all AI Discovery services..."
    for service in "${SERVICES[@]}"; do
        echo "Starting $service service..."
        ./start_${service}.sh
        sleep 2
    done
    echo "✅ All services started!"
}

stop_all() {
    echo "🛑 Stopping all AI Discovery services..."
    for service in "${SERVICES[@]}"; do
        if [ -f "${HOME}/logs/${service}.pid" ]; then
            PID=$(cat "${HOME}/logs/${service}.pid")
            if kill -0 "$PID" 2>/dev/null; then
                echo "Stopping $service service (PID: $PID)..."
                kill "$PID"
                rm -f "${HOME}/logs/${service}.pid"
            fi
        fi
    done
    echo "✅ All services stopped!"
}

status_all() {
    echo "📊 Service Status:"
    echo "=================="
    for i in "${!SERVICES[@]}"; do
        service="${SERVICES[$i]}"
        port="${PORTS[$i]}"
        
        if [ -f "${HOME}/logs/${service}.pid" ]; then
            PID=$(cat "${HOME}/logs/${service}.pid")
            if kill -0 "$PID" 2>/dev/null; then
                if curl -s http://localhost:${port}/health > /dev/null 2>&1; then
                    echo "✅ $service: Running (PID: $PID, Port: $port) - Healthy"
                else
                    echo "⚠️  $service: Running (PID: $PID, Port: $port) - Not responding"
                fi
            else
                echo "❌ $service: Dead (stale PID file)"
                rm -f "${HOME}/logs/${service}.pid"
            fi
        else
            echo "❌ $service: Not running"
        fi
    done
}

restart_all() {
    stop_all
    sleep 3
    start_all
}

case "$1" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        status_all
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
EOF

# Make scripts executable
chmod +x start_*.sh control_services.sh

# Step 8: Start Services
log "Step 8: Starting all services..."

./control_services.sh start
sleep 5

# Check status
./control_services.sh status

# Step 9: Create Test Script
log "Step 9: Creating test script..."

cat > test_deployment.sh << EOF
#!/bin/bash

echo "🧪 Testing AI Product Discovery Suite Deployment"
echo "==============================================="

# Test services
SERVICES=("search:7001" "recommendation:7002" "analytics:7004" "shopping_assistant:7005")

for service_port in "\${SERVICES[@]}"; do
    IFS=':' read -ra ADDR <<< "\$service_port"
    service="\${ADDR[0]}"
    port="\${ADDR[1]}"
    
    echo -n "Testing \$service service on port \$port... "
    if curl -s http://localhost:\$port/health > /dev/null; then
        echo "✅ OK"
    else
        echo "❌ FAILED"
    fi
done

# Test actual APIs
echo ""
echo "🔍 Testing Search API..."
curl -X POST "http://localhost:7001/api/v1/search/" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "test", "limit": 3}' | jq '.' || echo "Search API test failed"

echo ""
echo "🤖 Testing Recommendations API..."
curl -X POST "http://localhost:7002/api/v1/recommendations/" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "1", "context": "home", "limit": 5}' | jq '.' || echo "Recommendations API test failed"

echo ""
echo "📊 Testing Analytics API..."
curl -X POST "http://localhost:7004/api/v1/events/track" \\
  -H "Content-Type: application/json" \\
  -d '{"event_type": "test", "user_id": "1", "properties": {"test": true}}' | jq '.' || echo "Analytics API test failed"

echo ""
echo "🛍️ Testing Shopping Assistant API..."
curl -X POST "http://localhost:7005/api/v1/chat/message" \\
  -H "Content-Type: application/json" \\
  -d '{"session_id": "test", "message": "Hello"}' | jq '.' || echo "Shopping Assistant API test failed"

echo ""
echo "✅ Deployment testing complete!"
EOF

chmod +x test_deployment.sh

# Step 10: Load Demo Data (Optional)
log "Step 10: Loading demo data..."
read -p "Load demo data for testing? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    python3 scripts/init_dummy_data.py || warning "Demo data loading failed - continuing anyway"
fi

# Step 11: Create Nginx Configuration
log "Step 11: Creating Nginx configuration..."

cat > nginx_ai_discovery.conf << EOF
# Nginx Configuration for AI Product Discovery Suite
# Copy this to /etc/nginx/sites-available/ai-discovery
# Then run: sudo ln -s /etc/nginx/sites-available/ai-discovery /etc/nginx/sites-enabled/

server {
    listen 80;
    server_name ${API_DOMAIN};

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # API Routes
    location /api/v1/search/ {
        proxy_pass http://localhost:7001/api/v1/search/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    location /api/v1/recommendations/ {
        proxy_pass http://localhost:7002/api/v1/recommendations/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    location /api/v1/analytics/ {
        proxy_pass http://localhost:7004/api/v1/analytics/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    location /api/v1/chat/ {
        proxy_pass http://localhost:7005/api/v1/chat/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # Health checks
    location /health {
        proxy_pass http://localhost:7001/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # Handle CORS
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Final test
log "Running final deployment test..."
./test_deployment.sh

echo -e "${GREEN}"
cat << "EOF"

🎉 DEPLOYMENT COMPLETE! 🎉
========================

Your AI Product Discovery Suite is now running on your shared server!

📍 Services Status:
EOF
echo -e "${NC}"

./control_services.sh status

echo -e "${GREEN}"
cat << EOF

🌐 API Endpoints:
- Search: http://${API_DOMAIN}/api/v1/search/
- Recommendations: http://${API_DOMAIN}/api/v1/recommendations/
- Analytics: http://${API_DOMAIN}/api/v1/analytics/
- Shopping Assistant: http://${API_DOMAIN}/api/v1/chat/

📁 Important Files:
- App Directory: ${APP_DIR}
- Logs Directory: ${LOG_DIR}
- Environment Config: ${APP_DIR}/.env.production
- Control Script: ${APP_DIR}/control_services.sh

🛠️ Management Commands:
- Start services: ./control_services.sh start
- Stop services: ./control_services.sh stop
- Restart services: ./control_services.sh restart
- Check status: ./control_services.sh status
- Test deployment: ./test_deployment.sh

🌐 Next Steps:
1. Setup Nginx (copy nginx_ai_discovery.conf to /etc/nginx/sites-available/)
2. Install SSL certificate (recommended)
3. Install Magento 2 module
4. Configure domain DNS

📚 Documentation:
- Full guide: ${APP_DIR}/SHARED_SERVER_DEPLOYMENT.md
- Troubleshooting: Check logs in ${LOG_DIR}/

🎊 Your AI Product Discovery Suite is ready to use!
EOF
echo -e "${NC}"