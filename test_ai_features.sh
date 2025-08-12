#!/bin/bash

# AI Product Discovery - Feature Testing Script
# Tests typo tolerance, autocomplete, and all AI features

echo "🚀 Testing AI Product Discovery Features..."
echo "=========================================="

# Configuration
MAGENTO_URL="https://magento-test.softdemonew.info"
AI_SERVER="ai-product-discovery.softdemonew.info"

echo ""
echo "📍 Testing Backend AI Services..."
echo "================================="

# Test AI services
for port in 7001 7002 7003 7004; do
    echo "Testing service on port $port..."
    curl -s --connect-timeout 5 "http://$AI_SERVER:$port/health" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Service on port $port is running"
    else
        echo "❌ Service on port $port is not responding"
    fi
done

echo ""
echo "🔍 Testing Autocomplete Endpoints..."
echo "===================================="

# Test 1: Regular Hero Hoodie search
echo "Test 1: Searching for 'hero'..."
RESPONSE1=$(curl -s "$MAGENTO_URL/discovery/search/autocomplete/?q=hero&limit=5")
echo "Response: $RESPONSE1"
echo ""

# Test 2: Typo tolerance - "Hro Hoodie" should find "Hero Hoodie"
echo "Test 2: Testing typo tolerance - 'Hro Hoodie'..."
RESPONSE2=$(curl -s "$MAGENTO_URL/discovery/search/autocomplete/?q=Hro%20Hoodie&limit=5")
echo "Response: $RESPONSE2"

# Check if we got corrections
if echo "$RESPONSE2" | grep -q "correction_message"; then
    echo "✅ Typo tolerance is working!"
else
    echo "⚠️  Typo tolerance may not be working properly"
fi
echo ""

# Test 3: Tank search
echo "Test 3: Searching for 'tank'..."
RESPONSE3=$(curl -s "$MAGENTO_URL/discovery/search/autocomplete/?q=tank&limit=5")
echo "Response: $RESPONSE3"
echo ""

# Test 4: Advanced autocomplete endpoint
echo "Test 4: Testing advanced autocomplete..."
RESPONSE4=$(curl -s "$MAGENTO_URL/discoverysuite/search/autocompleteadvanced?q=hero&limit=5")
echo "Response: $RESPONSE4"
echo ""

echo "🧪 Testing Magento Commands..."
echo "=============================="

# Only run if we're on the Magento server
if [ -f "bin/magento" ]; then
    echo "Testing advanced AI features..."
    php bin/magento discovery:test:advanced-ai
    echo ""
    
    echo "Testing connection..."
    php bin/magento discovery:test:connection
    echo ""
else
    echo "Not on Magento server - skipping Magento commands"
fi

echo "🎯 Summary"
echo "=========="
echo "1. Backend AI services: Check output above"
echo "2. Autocomplete endpoint: $MAGENTO_URL/discovery/search/autocomplete/"
echo "3. Advanced autocomplete: $MAGENTO_URL/discoverysuite/search/autocompleteadvanced"
echo "4. Typo tolerance: Should correct 'Hro Hoodie' to 'Hero Hoodie'"
echo ""
echo "✅ Testing complete!"
