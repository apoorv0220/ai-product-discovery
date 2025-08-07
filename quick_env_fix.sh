#!/bin/bash

# 🚀 Quick Environment File Fix
# One-liner to fix the immediate issue

echo "🔧 Quick fix for .env.docker-shared-server..."

# Create backup
cp .env.docker-shared-server .env.docker-shared-server.backup.$(date +%Y%m%d_%H%M%S)

# Fix the problematic lines
sed -i 's/^API_TITLE=AI Product Discovery Suite$/API_TITLE="AI Product Discovery Suite"/' .env.docker-shared-server
sed -i 's/^CORS_ORIGINS=\[.*\]$/CORS_ORIGINS='\''["http:\/\/localhost:3000", "https:\/\/ai-product-discovery.softdemonew.info", "http:\/\/ai-product-discovery.softdemonew.info", "https:\/\/magento-test.softdemonew.info"]'\''/' .env.docker-shared-server

echo "✅ Fixed .env.docker-shared-server"
echo "📄 Backup created: .env.docker-shared-server.backup.*"
echo ""
echo "You can now run: ./deploy_docker_shared_server.sh"