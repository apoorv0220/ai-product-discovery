#!/bin/bash

echo "🔍 Testing Search Service Fixes"
echo "==============================="

# Test 1: Direct backend API test for "Hro Hoodie"
echo "1. Testing 'Hro Hoodie' on backend API..."
curl -s "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=Hro%20Hoodie&limit=5" | python3 -m json.tool

echo ""
echo "2. Testing 'I want to buy a comfortable hoodie' on backend API..."
curl -s "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=I%20want%20to%20buy%20a%20comfortable%20hoodie&limit=5" | python3 -m json.tool

echo ""
echo "3. Testing 'hero' on backend API..."
curl -s "http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=hero&limit=5" | python3 -m json.tool

echo ""
echo "4. Testing Magento endpoint with 'Hro Hoodie'..."
curl -s "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=Hro%20Hoodie&limit=5" | python3 -m json.tool

echo ""
echo "5. Testing Magento endpoint with 'I want to buy a comfortable hoodie'..."
curl -s "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=I%20want%20to%20buy%20a%20comfortable%20hoodie&limit=5" | python3 -m json.tool

echo ""
echo "✅ Testing complete!"
