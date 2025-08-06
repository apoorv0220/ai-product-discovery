#!/bin/bash

# 🔧 Redis Installation Script for AI Product Discovery Suite
# This script installs and configures Redis on Ubuntu/Debian servers

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
   ____          _ _     
  |  _ \ ___  __| (_)___ 
  |  _ \/ _ \/ _` | / __|
  | |_| |  __/ (_| | \__ \
  |____/ \___|\__,_|_|___/
                         
     Installation Script
EOF
echo -e "${NC}"

log "Starting Redis installation..."

# Step 1: Check if Redis is already installed
log "Step 1: Checking if Redis is already installed..."

if command -v redis-server &> /dev/null; then
    info "Redis is already installed. Checking if it's running..."
    
    if systemctl is-active --quiet redis-server || systemctl is-active --quiet redis; then
        log "✅ Redis is already running!"
        redis-cli ping && {
            log "✅ Redis is working correctly!"
            log "No installation needed. You can proceed with deployment."
            exit 0
        }
    else
        warning "Redis is installed but not running. Starting it..."
        sudo systemctl start redis-server || sudo systemctl start redis
        sudo systemctl enable redis-server || sudo systemctl enable redis
        
        if redis-cli ping &> /dev/null; then
            log "✅ Redis is now running!"
            exit 0
        fi
    fi
fi

# Step 2: Update system packages
log "Step 2: Updating system packages..."
if ! sudo apt update; then
    warning "Package update failed due to repository issues"
    echo "This is likely due to broken repositories. Run this first:"
    echo "  ./fix_ubuntu_repos.sh"
    echo "Then try Redis installation again."
    exit 1
fi

# Step 3: Install Redis
log "Step 3: Installing Redis server..."

# Check Ubuntu/Debian version and install accordingly
if command -v apt &> /dev/null; then
    # Ubuntu/Debian
    sudo apt install -y redis-server redis-tools
elif command -v yum &> /dev/null; then
    # CentOS/RHEL/Amazon Linux
    sudo yum install -y epel-release
    sudo yum install -y redis
elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf install -y redis
else
    error "Unsupported package manager. Please install Redis manually."
fi

# Step 4: Configure Redis
log "Step 4: Configuring Redis..."

# Backup original config
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup 2>/dev/null || \
sudo cp /etc/redis.conf /etc/redis.conf.backup 2>/dev/null || \
true

# Find Redis config file
REDIS_CONF=""
if [ -f "/etc/redis/redis.conf" ]; then
    REDIS_CONF="/etc/redis/redis.conf"
elif [ -f "/etc/redis.conf" ]; then
    REDIS_CONF="/etc/redis.conf"
else
    warning "Redis config file not found in standard locations"
fi

if [ -n "$REDIS_CONF" ]; then
    info "Configuring Redis at: $REDIS_CONF"
    
    # Configure Redis for production use
    sudo tee "$REDIS_CONF" > /dev/null << 'EOF'
# Redis Configuration for AI Product Discovery Suite
# Generated automatically - modify carefully

# Network
bind 127.0.0.1
port 6379
timeout 0
tcp-keepalive 300

# General
daemonize yes
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log

# Snapshotting
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Replication
# (No replication settings for single server)

# Security
# requirepass your_redis_password_here
# Comment out the requirepass line above and set a password if needed

# Memory management
maxmemory-policy allkeys-lru
# maxmemory 256mb

# Append only file
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Client output buffer limits
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
EOF

    log "✅ Redis configuration updated"
else
    warning "Could not configure Redis automatically. Using default settings."
fi

# Step 5: Start and enable Redis
log "Step 5: Starting Redis service..."

# Create redis user and directories if needed
sudo useradd --system --home /var/lib/redis --shell /bin/false redis 2>/dev/null || true
sudo mkdir -p /var/lib/redis /var/log/redis /var/run/redis
sudo chown redis:redis /var/lib/redis /var/log/redis /var/run/redis
sudo chmod 750 /var/lib/redis /var/log/redis /var/run/redis

# Start Redis
if systemctl list-unit-files redis-server.service &> /dev/null; then
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    REDIS_SERVICE="redis-server"
elif systemctl list-unit-files redis.service &> /dev/null; then
    sudo systemctl start redis
    sudo systemctl enable redis
    REDIS_SERVICE="redis"
else
    error "Redis service not found. Manual configuration may be required."
fi

# Step 6: Test Redis connection
log "Step 6: Testing Redis connection..."

sleep 2

if redis-cli ping &> /dev/null; then
    log "✅ Redis is running and responding!"
    
    # Test basic operations
    redis-cli set test_key "test_value" > /dev/null
    if [ "$(redis-cli get test_key)" = "test_value" ]; then
        log "✅ Redis read/write operations working!"
        redis-cli del test_key > /dev/null
    else
        warning "Redis basic operations test failed"
    fi
else
    error "Redis is not responding. Please check the logs: sudo journalctl -u $REDIS_SERVICE"
fi

# Step 7: Configure firewall (if needed)
log "Step 7: Checking firewall configuration..."

if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    info "UFW firewall is active. Redis port 6379 is only accessible locally by default."
elif command -v firewall-cmd &> /dev/null; then
    info "Firewalld detected. Redis port 6379 is only accessible locally by default."
else
    info "No active firewall detected or firewall configuration not needed."
fi

# Step 8: Show Redis information
log "Step 8: Redis installation complete!"

echo -e "${GREEN}"
cat << "EOF"
✅ Redis Installation Successful!
================================

EOF
echo -e "${NC}"

echo "🔧 Redis Configuration:"
echo "  • Port: 6379"
echo "  • Bind: 127.0.0.1 (localhost only)"
echo "  • Service: $REDIS_SERVICE"
echo "  • Config: $REDIS_CONF"
echo "  • Data Dir: /var/lib/redis"
echo "  • Log File: /var/log/redis/redis-server.log"

echo ""
echo "📋 Useful Commands:"
echo "  • Check status: sudo systemctl status $REDIS_SERVICE"
echo "  • Start Redis: sudo systemctl start $REDIS_SERVICE"
echo "  • Stop Redis: sudo systemctl stop $REDIS_SERVICE"
echo "  • Restart Redis: sudo systemctl restart $REDIS_SERVICE"
echo "  • Test Redis: redis-cli ping"
echo "  • Redis CLI: redis-cli"
echo "  • View logs: sudo journalctl -u $REDIS_SERVICE"

echo ""
echo "🚀 Next Steps:"
echo "  1. Redis is now ready for your AI Product Discovery Suite"
echo "  2. Run your deployment script: ./deploy_shared_server.sh"
echo "  3. The script should now detect Redis successfully"

echo ""
echo "📊 Redis Status:"
redis-cli info server | grep -E "(redis_version|os|arch|process_id|uptime_in_seconds)"

echo ""
log "🎉 Redis installation completed successfully!"