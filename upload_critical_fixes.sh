#!/bin/bash

echo "📤 Uploading critical fixes to server..."

# Manual upload commands - run these one by one
echo "Run these commands manually:"
echo ""
echo "1. Upload autocomplete fix:"
echo "scp backend/search-service/api/autocomplete.py root@ai-product-discovery.softdemonew.info:/root/ai-product-discovery/backend/search-service/api/"
echo ""
echo "2. Upload search fix:"
echo "scp backend/search-service/api/search.py root@ai-product-discovery.softdemonew.info:/root/ai-product-discovery/backend/search-service/api/"
echo ""
echo "3. SSH into server and restart:"
echo "ssh root@ai-product-discovery.softdemonew.info"
echo "cd /root/ai-product-discovery"
echo "pkill -f 'search-service.*7001'"
echo "cd backend"
echo "nohup python3 -m uvicorn search-service.main:app --host 0.0.0.0 --port 7001 > ../search-service.log 2>&1 &"
echo ""
echo "4. Test the fixes:"
echo "curl 'http://ai-product-discovery.softdemonew.info:7001/api/v1/autocomplete/?q=Hro%20Hoodie&limit=3' | jq ."
