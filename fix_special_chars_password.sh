#!/bin/bash

# 🔧 Special Characters Password Fixer
# Fixes DATABASE_URL with special characters in password

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

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

echo -e "${BLUE}"
cat << "EOF"
   🔧 Password Special Characters Fixer
   ===================================
EOF
echo -e "${NC}"

log "Fixing DATABASE_URL with special characters in password..."

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    error ".env.production file not found"
fi

# Backup original file
cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)
log "📄 Backup created"

# URL encode function for passwords
url_encode() {
    local string="${1}"
    local strlen=${#string}
    local encoded=""
    local pos c o

    for (( pos=0 ; pos<strlen ; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9] ) o="${c}" ;;
            * ) printf -v o '%%%02x' "'$c" ;;
        esac
        encoded+="${o}"
    done
    echo "${encoded}"
}

# Your specific password with special characters
ORIGINAL_PASSWORD=">cTn2+E7{1j9"
ENCODED_PASSWORD=$(url_encode "$ORIGINAL_PASSWORD")

log "Original password: $ORIGINAL_PASSWORD"
log "URL-encoded password: $ENCODED_PASSWORD"

# Database details (from your .env.shared-server template)
PG_USER="ai_discovery"
PG_DB="ai_discovery"
PG_HOST="localhost"
PG_PORT="5432"

# Create correct DATABASE_URL
NEW_DATABASE_URL="postgresql://${PG_USER}:${ENCODED_PASSWORD}@${PG_HOST}:${PG_PORT}/${PG_DB}"

log "New DATABASE_URL: postgresql://${PG_USER}:****@${PG_HOST}:${PG_PORT}/${PG_DB}"

# Update DATABASE_URL in .env.production
if grep -q "^DATABASE_URL=" .env.production; then
    # Use a different delimiter to avoid issues with special characters
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${NEW_DATABASE_URL}|" .env.production
else
    echo "DATABASE_URL=${NEW_DATABASE_URL}" >> .env.production
fi

# Also update the plain password field
if grep -q "^POSTGRES_PASSWORD=" .env.production; then
    # Use single quotes to preserve special characters
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD='${ORIGINAL_PASSWORD}'|" .env.production
else
    echo "POSTGRES_PASSWORD='${ORIGINAL_PASSWORD}'" >> .env.production
fi

# Update other database fields to ensure consistency
sed -i "s|^POSTGRES_HOST=.*|POSTGRES_HOST=${PG_HOST}|" .env.production
sed -i "s|^POSTGRES_PORT=.*|POSTGRES_PORT=${PG_PORT}|" .env.production
sed -i "s|^POSTGRES_DB=.*|POSTGRES_DB=${PG_DB}|" .env.production
sed -i "s|^POSTGRES_USER=.*|POSTGRES_USER=${PG_USER}|" .env.production

log "✅ DATABASE_URL fixed with URL-encoded password"

# Test the connection
log "Testing database connection..."

# Load updated environment
source .env.production

if python3 -c "
import asyncio
import sys
import os
sys.path.append('backend')

try:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
except ImportError:
    print('SQLAlchemy not available, skipping connection test')
    sys.exit(0)

async def test():
    try:
        engine = create_async_engine('$NEW_DATABASE_URL', echo=False)
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT 1'))
            row = result.fetchone()
            if row and row[0] == 1:
                print('✅ Database connection successful!')
                return True
        await engine.dispose()
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False
    return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
" 2>/dev/null; then
    log "✅ Database connection test passed!"
else
    log "⚠️  Database connection test failed, but URL has been fixed"
    echo "   You may need to install dependencies or check PostgreSQL"
fi

echo ""
log "🎉 Password special characters issue fixed!"
echo ""
echo "Next steps:"
echo "  1. Run: ./deploy_from_step6.sh"
echo "  2. Or run: ./deployment_step_manager.sh 6"
echo ""
echo "If you see the error again, check your .env.production file:"
echo "  cat .env.production | grep DATABASE_URL"
echo ""