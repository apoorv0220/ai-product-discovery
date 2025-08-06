#!/bin/bash

# 🔍 Quick Redis Status Checker
# Check if Redis is installed and running

echo "🔍 Checking Redis Status..."
echo "=========================="

# Check if Redis is installed
if command -v redis-server &> /dev/null; then
    echo "✅ Redis server is installed"
    redis-server --version
else
    echo "❌ Redis server is NOT installed"
    echo ""
    echo "To install Redis, run:"
    echo "  ./install_redis.sh"
    exit 1
fi

# Check if Redis CLI is available
if command -v redis-cli &> /dev/null; then
    echo "✅ Redis CLI is available"
else
    echo "❌ Redis CLI is NOT available"
    exit 1
fi

# Check if Redis service is running
echo ""
echo "📊 Service Status:"
if systemctl is-active --quiet redis-server; then
    echo "✅ redis-server service is running"
    REDIS_SERVICE="redis-server"
elif systemctl is-active --quiet redis; then
    echo "✅ redis service is running"
    REDIS_SERVICE="redis"
else
    echo "❌ Redis service is NOT running"
    echo ""
    echo "To start Redis:"
    echo "  sudo systemctl start redis-server"
    echo "  # OR"
    echo "  sudo systemctl start redis"
    exit 1
fi

# Test Redis connection
echo ""
echo "🔗 Connection Test:"
if redis-cli ping &> /dev/null; then
    RESPONSE=$(redis-cli ping)
    echo "✅ Redis is responding: $RESPONSE"
else
    echo "❌ Redis is NOT responding"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check if Redis is running: sudo systemctl status $REDIS_SERVICE"
    echo "2. Check Redis logs: sudo journalctl -u $REDIS_SERVICE"
    echo "3. Try restarting: sudo systemctl restart $REDIS_SERVICE"
    exit 1
fi

# Show Redis info
echo ""
echo "📋 Redis Information:"
redis-cli info server | grep -E "(redis_version|process_id|tcp_port|uptime_in_seconds)" | while read line; do
    echo "  $line"
done

# Test basic operations
echo ""
echo "🧪 Basic Operations Test:"
redis-cli set test_connection "$(date)" > /dev/null
if [ "$(redis-cli exists test_connection)" = "1" ]; then
    echo "✅ Write operation successful"
    VALUE=$(redis-cli get test_connection)
    echo "✅ Read operation successful: $VALUE"
    redis-cli del test_connection > /dev/null
    echo "✅ Delete operation successful"
else
    echo "❌ Basic operations failed"
    exit 1
fi

echo ""
echo "🎉 Redis is fully operational!"
echo ""
echo "You can now proceed with your deployment:"
echo "  ./deploy_shared_server.sh"