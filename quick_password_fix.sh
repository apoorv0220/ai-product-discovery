#!/bin/bash

# 🚀 Quick Password Fix for >cTn2+E7{1j9
# One-liner to fix your specific DATABASE_URL issue

echo "🔧 Quick fix for DATABASE_URL with special characters..."

# Your password with URL encoding
# > becomes %3E
# + becomes %2B
# { becomes %7B
# } becomes %7D

# Create the correct DATABASE_URL
FIXED_URL="postgresql://ai_discovery:%3EcTn2%2BE7%7B1j9@localhost:5432/ai_discovery"

# Backup and update .env.production
cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)

# Replace the DATABASE_URL line
sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${FIXED_URL}|" .env.production

echo "✅ Fixed! Your DATABASE_URL now uses URL-encoded password"
echo "📄 Backup created: .env.production.backup.*"
echo ""
echo "New DATABASE_URL: postgresql://ai_discovery:****@localhost:5432/ai_discovery"
echo ""
echo "Now run: ./deploy_from_step6.sh"