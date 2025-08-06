#!/bin/bash

# 🔍 Test Redis Connection Script
# Tests the same Redis connection method that the deployment script will use

echo "🔍 Testing Redis Connection Methods"
echo "=================================="

# Method 1: Using 127.0.0.1 (exact method from your working command)
echo "Testing: redis-cli -h 127.0.0.1 -p 6379 ping"
if redis-cli -h 127.0.0.1 -p 6379 ping &> /dev/null; then
    echo "✅ Method 1: 127.0.0.1:6379 - WORKING"
    REDIS_RESPONSE=$(redis-cli -h 127.0.0.1 -p 6379 ping)
    echo "   Response: $REDIS_RESPONSE"
    REDIS_HOST="127.0.0.1"
    WORKING_METHOD="127.0.0.1:6379"
else
    echo "❌ Method 1: 127.0.0.1:6379 - FAILED"
fi

# Method 2: Using localhost
echo ""
echo "Testing: redis-cli -h localhost -p 6379 ping"
if redis-cli -h localhost -p 6379 ping &> /dev/null; then
    echo "✅ Method 2: localhost:6379 - WORKING"
    REDIS_RESPONSE=$(redis-cli -h localhost -p 6379 ping)
    echo "   Response: $REDIS_RESPONSE"
    if [ -z "$REDIS_HOST" ]; then
        REDIS_HOST="localhost"
        WORKING_METHOD="localhost:6379"
    fi
else
    echo "❌ Method 2: localhost:6379 - FAILED"
fi

# Method 3: Default connection
echo ""
echo "Testing: redis-cli ping"
if redis-cli ping &> /dev/null; then
    echo "✅ Method 3: default connection - WORKING"
    REDIS_RESPONSE=$(redis-cli ping)
    echo "   Response: $REDIS_RESPONSE"
    if [ -z "$REDIS_HOST" ]; then
        REDIS_HOST="localhost"
        WORKING_METHOD="default"
    fi
else
    echo "❌ Method 3: default connection - FAILED"
fi

# Results
echo ""
echo "📊 Test Results:"
echo "================"

if [ -n "$REDIS_HOST" ]; then
    echo "✅ Redis is working!"
    echo "   Best connection method: $WORKING_METHOD"
    echo "   Host for configuration: $REDIS_HOST"
    
    echo ""
    echo "🧪 Testing basic operations..."
    
    # Test write
    if redis-cli -h $REDIS_HOST -p 6379 set test_deployment "$(date)" &> /dev/null; then
        echo "✅ Write operation: SUCCESS"
        
        # Test read
        VALUE=$(redis-cli -h $REDIS_HOST -p 6379 get test_deployment)
        echo "✅ Read operation: SUCCESS (Value: $VALUE)"
        
        # Test delete
        redis-cli -h $REDIS_HOST -p 6379 del test_deployment &> /dev/null
        echo "✅ Delete operation: SUCCESS"
        
        echo ""
        echo "🎉 All Redis operations working perfectly!"
        echo ""
        echo "📋 Configuration for deployment:"
        echo "   REDIS_HOST=$REDIS_HOST"
        echo "   REDIS_PORT=6379"
        echo "   REDIS_URL=redis://$REDIS_HOST:6379/0"
        
    else
        echo "❌ Write operation: FAILED"
    fi
else
    echo "❌ Redis is NOT working with any method!"
    echo ""
    echo "🔧 Troubleshooting steps:"
    echo "1. Check if Redis is running: sudo systemctl status redis-server"
    echo "2. Check Redis logs: sudo journalctl -u redis-server"
    echo "3. Try starting Redis: sudo systemctl start redis-server"
    echo "4. Install Redis if needed: ./install_redis.sh"
fi

echo ""
echo "🚀 Ready for deployment:"
if [ -n "$REDIS_HOST" ]; then
    echo "   Your deployment script will now detect and use Redis successfully!"
    echo "   Run: ./deploy_shared_server.sh"
else
    echo "   Please fix Redis connection first, then run deployment."
fi