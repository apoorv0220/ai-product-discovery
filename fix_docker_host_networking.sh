#!/bin/bash

# 🔧 Fix Docker Host Networking for Linux Servers
# Ensures Docker containers can access host PostgreSQL and Redis

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

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

log "Fixing Docker host networking for Linux servers..."

# Detect host IP that Docker containers should use
DOCKER_HOST_IP=""

# Method 1: Try to get Docker bridge gateway IP
DOCKER_GATEWAY=$(docker network inspect bridge --format='{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || echo "")

if [ -n "$DOCKER_GATEWAY" ]; then
    DOCKER_HOST_IP="$DOCKER_GATEWAY"
    log "Using Docker bridge gateway IP: $DOCKER_HOST_IP"
else
    # Method 2: Try to get host IP from default route
    HOST_IP=$(ip route get 1 | grep -oP 'src \K\S+' 2>/dev/null || echo "")
    
    if [ -n "$HOST_IP" ]; then
        DOCKER_HOST_IP="$HOST_IP"
        log "Using host IP from route: $DOCKER_HOST_IP"
    else
        # Method 3: Fallback to common Docker host IP
        DOCKER_HOST_IP="172.17.0.1"
        log "Using fallback Docker host IP: $DOCKER_HOST_IP"
    fi
fi

# Test connectivity to host services
log "Testing connectivity to host services..."

# Test PostgreSQL
if ! nc -z "$DOCKER_HOST_IP" 5432 2>/dev/null; then
    error "Cannot reach PostgreSQL on $DOCKER_HOST_IP:5432. Please check PostgreSQL is running and accessible."
else
    log "✅ PostgreSQL reachable on $DOCKER_HOST_IP:5432"
fi

# Test Redis
if ! nc -z "$DOCKER_HOST_IP" 6379 2>/dev/null; then
    error "Cannot reach Redis on $DOCKER_HOST_IP:6379. Please check Redis is running and accessible."
else
    log "✅ Redis reachable on $DOCKER_HOST_IP:6379"
fi

# Update Docker Compose file with correct host IP
log "Updating Docker Compose configuration..."

# Backup original file
cp docker-compose.shared-server.yml docker-compose.shared-server.yml.backup

# Replace host.docker.internal with actual host IP
sed -i "s/host\.docker\.internal/$DOCKER_HOST_IP/g" docker-compose.shared-server.yml

# Update environment file
if [ -f ".env.docker-shared-server" ]; then
    cp .env.docker-shared-server .env.docker-shared-server.backup
    sed -i "s/host\.docker\.internal/$DOCKER_HOST_IP/g" .env.docker-shared-server
    log "✅ Environment file updated"
fi

log "✅ Docker host networking fixed"

# Create a test script to verify connectivity from inside containers
cat > test_container_connectivity.sh << EOF
#!/bin/bash

echo "🔍 Testing container-to-host connectivity..."

# Test from a temporary container
docker run --rm --network discovery-network alpine:latest sh -c "
    # Install required tools
    apk add --no-cache postgresql-client redis
    
    echo 'Testing PostgreSQL connectivity...'
    if pg_isready -h $DOCKER_HOST_IP -p 5432; then
        echo '✅ PostgreSQL connection successful'
    else
        echo '❌ PostgreSQL connection failed'
        exit 1
    fi
    
    echo 'Testing Redis connectivity...'
    if redis-cli -h $DOCKER_HOST_IP -p 6379 ping | grep -q PONG; then
        echo '✅ Redis connection successful'
    else
        echo '❌ Redis connection failed'
        exit 1
    fi
    
    echo '🎉 All host services reachable from container!'
" || {
    echo "❌ Container connectivity test failed"
    echo "Host IP used: $DOCKER_HOST_IP"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check if PostgreSQL allows connections from Docker network"
    echo "2. Check if Redis bind address allows Docker connections"
    echo "3. Check firewall rules"
    echo "4. Manually test: docker run --rm alpine nc -zv $DOCKER_HOST_IP 5432"
    echo "5. Manually test: docker run --rm alpine nc -zv $DOCKER_HOST_IP 6379"
    exit 1
}

echo "✅ Container connectivity verified!"
EOF

chmod +x test_container_connectivity.sh

echo ""
log "🎉 Docker host networking fix completed!"
echo ""
echo "Configuration updated:"
echo "  • Host IP: $DOCKER_HOST_IP"
echo "  • PostgreSQL: $DOCKER_HOST_IP:5432"
echo "  • Redis: $DOCKER_HOST_IP:6379"
echo ""
echo "Next steps:"
echo "  1. Test connectivity: ./test_container_connectivity.sh"
echo "  2. Deploy services: ./deploy_docker_shared_server.sh"
echo ""
echo "If you need to revert changes:"
echo "  • Docker Compose: mv docker-compose.shared-server.yml.backup docker-compose.shared-server.yml"
echo "  • Environment: mv .env.docker-shared-server.backup .env.docker-shared-server"