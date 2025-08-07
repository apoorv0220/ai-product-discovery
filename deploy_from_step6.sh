# Activate virtual environment
log "Activating virtual environment..."
source venv/bin/activate

# Step 5.5: Install missing database drivers if needed
log "Step 5.5: Installing missing database drivers..."

# Check and install psycopg2-binary if missing
if ! python3 -c "import psycopg2" 2>/dev/null; then
    log "Installing psycopg2-binary..."
    pip install psycopg2-binary==2.9.9
fi

# Check and install asyncpg if missing
if ! python3 -c "import asyncpg" 2>/dev/null; then
    log "Installing asyncpg..."
    pip install asyncpg==0.30.0
fi

# Install any other missing critical dependencies
log "Installing/updating critical dependencies..."
pip install sqlalchemy[asyncio] alembic structlog

# Step 6: Initialize Database
log "Step 6: Initializing database tables..."

# Re-load environment variables for database initialization
set -o allexport
source .env.production 2>/dev/null || {
    error "Failed to load .env.production file"
    exit 1
}
set +o allexport

log "Using DATABASE_URL: ${DATABASE_URL}"on" ]; then
    error "Not in correct directory or .env.production not found. Please run from the ai-product-discovery directory."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    error "Virtual environment not found. Please run the full deployment script first."
fi

# Load environment variables safely first for validation
log "Validating configuration..."
set -o allexport
source .env.production 2>/dev/null || {
    error "Failed to load .env.production file"
    exit 1
}
set +o allexport

# Validate .env.production has required database configuration
if [ -z "$DATABASE_URL" ]; then
    error "DATABASE_URL not found in .env.production. Please run the full deployment script first."
fi

# Validate DATABASE_URL format
if [[ ! "$DATABASE_URL" =~ ^postgresql://[^:]+:[^@]+@[^:]+:[0-9]+/[^/]+$ ]]; then
    error "Invalid DATABASE_URL format in .env.production: $DATABASE_URL"
    echo "Expected format: postgresql://username:password@host:port/database"
    echo ""
    echo "Please either:"
    echo "1. Run the full deployment script: ./deploy_shared_server.sh"
    echo "2. Or manually check/fix the DATABASE_URL in .env.production"
    echo "3. Current DATABASE_URL: $DATABASE_URL"
    exit 1
fi

log "✅ Configuration validated successfully"

# Activate virtual environment
log "Activating virtual environment..."
source venv/bin/activate

# Step 5.5: Install missing database drivers if needed
log "Step 5.5: Installing missing database drivers..."

# Check and install psycopg2-binary if missing
if ! python3 -c "import psycopg2" 2>/dev/null; then
    log "Installing psycopg2-binary..."
    pip install psycopg2-binary==2.9.9
fi

# Check and install asyncpg if missing
if ! python3 -c "import asyncpg" 2>/dev/null; then
    log "Installing asyncpg..."
    pip install asyncpg==0.30.0
fi

# Install any other missing critical dependencies
log "Installing/updating critical dependencies..."
pip install sqlalchemy[asyncio] alembic structlog

# Step 6: Initialize Database
log "Step 6: Initializing database tables..."

# Re-load environment variables for database initialization
set -o allexport
source .env.production 2>/dev/null || {
    error "Failed to load .env.production file"
    exit 1
}
set +o allexport

log "Using DATABASE_URL: ${DATABASE_URL}"

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
set -o allexport
source .env.production 2>/dev/null
set +o allexport

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
set -o allexport
source .env.production 2>/dev/null
set +o allexport

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
set -o allexport
source .env.production 2>/dev/null
set +o allexport

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
set -o allexport
source .env.production 2>/dev/null
set +o allexport

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

cat > test_deployment.sh << 'EOF'
#!/bin/bash

echo "🧪 Testing AI Product Discovery Suite Deployment"
echo "==============================================="

# Test services
SERVICES=("search:7001" "recommendation:7002" "analytics:7004" "shopping_assistant:7005")

for service_port in "${SERVICES[@]}"; do
    IFS=':' read -ra ADDR <<< "$service_port"
    service="${ADDR[0]}"
    port="${ADDR[1]}"
    
    echo -n "Testing $service service on port $port... "
    if curl -s http://localhost:$port/health > /dev/null; then
        echo "✅ OK"
    else
        echo "❌ FAILED"
    fi
done

# Test actual APIs
echo ""
echo "🔍 Testing Search API..."
curl -X POST "http://localhost:7001/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 3}' | jq '.' || echo "Search API test failed"

echo ""
echo "🤖 Testing Recommendations API..."
curl -X POST "http://localhost:7002/api/v1/recommendations/" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "context": "home", "limit": 5}' | jq '.' || echo "Recommendations API test failed"

echo ""
echo "📊 Testing Analytics API..."
curl -X POST "http://localhost:7004/api/v1/events/track" \
  -H "Content-Type: application/json" \
  -d '{"event_type": "test", "user_id": "1", "properties": {"test": true}}' | jq '.' || echo "Analytics API test failed"

echo ""
echo "🛍️ Testing Shopping Assistant API..."
curl -X POST "http://localhost:7005/api/v1/chat/message" \
  -H "Content-Type: application/json" \
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

# Final test
log "Running final deployment test..."
./test_deployment.sh

echo -e "${GREEN}"
cat << "EOF"

🎉 DEPLOYMENT RESUMED AND COMPLETED! 🎉
=====================================

EOF
echo -e "${NC}"

echo "🌐 Your APIs are now running:"
echo "  • Search: http://your-domain.com/api/v1/search/"
echo "  • Recommendations: http://your-domain.com/api/v1/recommendations/"
echo "  • Analytics: http://your-domain.com/api/v1/analytics/"
echo "  • Shopping Assistant: http://your-domain.com/api/v1/chat/"

echo ""
echo "🛠️ Management Commands:"
echo "  • Check status: ./control_services.sh status"
echo "  • Stop services: ./control_services.sh stop"
echo "  • Start services: ./control_services.sh start"
echo "  • Test deployment: ./test_deployment.sh"

echo ""
log "🎊 Deployment from Step 6 completed successfully!"