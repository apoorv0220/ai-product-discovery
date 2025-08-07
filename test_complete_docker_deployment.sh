#!/bin/bash

# 🧪 Complete Docker Deployment Test
# Comprehensive testing for hybrid Docker deployment

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
   🧪 Complete Docker Deployment Test
   =================================
   
   Testing:
   ├── Host services (PostgreSQL, Redis)
   ├── Docker services (Search, Recommendation, etc.)
   ├── Network connectivity
   ├── API functionality
   └── Overall system health
EOF
echo -e "${NC}"

# Test counters
PASSED=0
FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo "✅ PASSED"
        ((PASSED++))
    else
        echo "❌ FAILED"
        ((FAILED++))
    fi
}

# Test 1: Prerequisites
log "Test 1: Checking prerequisites..."

echo -n "Docker installed: "
if command -v docker &> /dev/null; then
    test_result 0
else
    test_result 1
fi

echo -n "Docker Compose available: "
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    test_result 0
else
    test_result 1
fi

echo -n "Docker daemon running: "
if docker info &> /dev/null; then
    test_result 0
else
    test_result 1
fi

# Test 2: Configuration Files
log "Test 2: Checking configuration files..."

REQUIRED_FILES=(
    "docker-compose.shared-server.yml"
    ".env.docker-shared-server"
    "nginx/shared-server.conf"
    "deploy_docker_shared_server.sh"
    "fix_docker_host_networking.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
    echo -n "$file exists: "
    if [ -f "$file" ]; then
        test_result 0
    else
        test_result 1
    fi
done

# Test 3: Host Services
log "Test 3: Testing host services..."

echo -n "PostgreSQL reachable: "
if nc -z localhost 5432 2>/dev/null; then
    test_result 0
else
    test_result 1
fi

echo -n "Redis reachable: "
if nc -z localhost 6379 2>/dev/null; then
    test_result 0
else
    test_result 1
fi

echo -n "Redis responding: "
if redis-cli ping 2>/dev/null | grep -q PONG; then
    test_result 0
else
    test_result 1
fi

# Test 4: Docker Network Configuration
log "Test 4: Testing Docker network configuration..."

echo -n "Docker bridge network exists: "
if docker network ls | grep -q bridge; then
    test_result 0
else
    test_result 1
fi

echo -n "Docker host IP detection: "
DOCKER_HOST_IP=$(docker network inspect bridge --format='{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null || echo "")
if [ -n "$DOCKER_HOST_IP" ]; then
    echo "✅ PASSED (IP: $DOCKER_HOST_IP)"
    ((PASSED++))
else
    test_result 1
fi

# Test 5: Docker Images
log "Test 5: Checking Docker images..."

echo -n "Docker Compose configuration valid: "
if docker-compose -f docker-compose.shared-server.yml config &> /dev/null; then
    test_result 0
else
    test_result 1
fi

# Test 6: Container Connectivity (if services are running)
log "Test 6: Testing container connectivity..."

if docker ps --format "table {{.Names}}" | grep -q discovery_; then
    echo "Docker services are running, testing connectivity..."
    
    SERVICES=("search-service:7001" "recommendation-service:7002" "analytics-service:7004" "shopping-assistant:7005")
    
    for service_port in "${SERVICES[@]}"; do
        IFS=':' read -ra ADDR <<< "$service_port"
        service="${ADDR[0]}"
        port="${ADDR[1]}"
        
        echo -n "$service health check: "
        if curl -s -f http://localhost:$port/health &> /dev/null; then
            test_result 0
        else
            test_result 1
        fi
    done
    
    # Test API endpoints
    log "Testing API endpoints..."
    
    echo -n "Search API: "
    if curl -s -X POST "http://localhost:7001/api/v1/search/" \
        -H "Content-Type: application/json" \
        -d '{"query": "test", "limit": 3}' | grep -q "results"; then
        test_result 0
    else
        test_result 1
    fi
    
    echo -n "Recommendation API: "
    if curl -s -X POST "http://localhost:7002/api/v1/recommendations/" \
        -H "Content-Type: application/json" \
        -d '{"user_id": "1", "context": "home", "limit": 5}' | grep -q "recommendations"; then
        test_result 0
    else
        test_result 1
    fi
    
else
    info "Docker services not running, skipping connectivity tests"
    info "To test connectivity after deployment, run: ./test_docker_apis.sh"
fi

# Test 7: Environment Configuration
log "Test 7: Validating environment configuration..."

if [ -f ".env.docker-shared-server" ]; then
    echo -n "Environment file readable: "
    if [ -r ".env.docker-shared-server" ]; then
        test_result 0
    else
        test_result 1
    fi
    
    echo -n "Database URL configured: "
    if grep -q "DATABASE_URL=postgresql://" .env.docker-shared-server; then
        test_result 0
    else
        test_result 1
    fi
    
    echo -n "Redis URL configured: "
    if grep -q "REDIS_URL=redis://" .env.docker-shared-server; then
        test_result 0
    else
        test_result 1
    fi
    
    echo -n "Secret keys configured: "
    if grep -q "SECRET_KEY=" .env.docker-shared-server && grep -q "JWT_SECRET_KEY=" .env.docker-shared-server; then
        test_result 0
    else
        test_result 1
    fi
else
    warning "Environment file not found, skipping environment tests"
    ((FAILED += 4))
fi

# Test 8: Management Scripts
log "Test 8: Checking management scripts..."

SCRIPTS=("docker_control.sh" "test_docker_apis.sh" "test_container_connectivity.sh")

for script in "${SCRIPTS[@]}"; do
    echo -n "$script exists and executable: "
    if [ -x "$script" ]; then
        test_result 0
    else
        test_result 1
    fi
done

# Test 9: Nginx Configuration
log "Test 9: Validating Nginx configuration..."

echo -n "Nginx config file exists: "
if [ -f "nginx/shared-server.conf" ]; then
    test_result 0
else
    test_result 1
fi

echo -n "Nginx config syntax: "
if [ -f "nginx/shared-server.conf" ]; then
    # Basic syntax check
    if grep -q "upstream.*service" nginx/shared-server.conf && grep -q "location /api" nginx/shared-server.conf; then
        test_result 0
    else
        test_result 1
    fi
else
    test_result 1
fi

# Test 10: Resource Requirements
log "Test 10: Checking system resources..."

echo -n "Sufficient disk space: "
AVAILABLE_SPACE=$(df / | tail -1 | awk '{print $4}')
if [ "$AVAILABLE_SPACE" -gt 2000000 ]; then  # 2GB in KB
    test_result 0
else
    test_result 1
fi

echo -n "Sufficient memory: "
AVAILABLE_MEMORY=$(free -m | grep '^Mem:' | awk '{print $7}')
if [ "$AVAILABLE_MEMORY" -gt 1000 ]; then  # 1GB
    test_result 0
else
    test_result 1
fi

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    TEST SUMMARY                              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! ($PASSED/$((PASSED + FAILED)))${NC}"
    echo ""
    echo -e "${GREEN}✅ Your system is ready for Docker deployment!${NC}"
    echo ""
    echo "🚀 Next steps:"
    echo "  1. Run: ./deploy_docker_shared_server.sh"
    echo "  2. Test APIs: ./test_docker_apis.sh"
    echo "  3. Monitor: ./docker_control.sh status"
    
elif [ $PASSED -gt $FAILED ]; then
    echo -e "${YELLOW}⚠️  MOSTLY READY ($PASSED passed, $FAILED failed)${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Some tests failed but deployment might still work${NC}"
    echo ""
    echo "🔧 Recommended actions:"
    echo "  1. Review failed tests above"
    echo "  2. Try: ./fix_docker_host_networking.sh"
    echo "  3. Then: ./deploy_docker_shared_server.sh"
    
else
    echo -e "${RED}❌ MULTIPLE ISSUES FOUND ($PASSED passed, $FAILED failed)${NC}"
    echo ""
    echo -e "${RED}❌ System needs attention before deployment${NC}"
    echo ""
    echo "🛠️  Required fixes:"
    echo "  1. Review all failed tests above"
    echo "  2. Install missing dependencies"
    echo "  3. Fix configuration issues"
    echo "  4. Re-run this test"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Exit with appropriate code
if [ $FAILED -eq 0 ]; then
    exit 0
elif [ $PASSED -gt $FAILED ]; then
    exit 1
else
    exit 2
fi