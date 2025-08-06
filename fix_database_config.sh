#!/bin/bash

# 🔧 Database Configuration Fixer
# Fixes DATABASE_URL issues in .env.production

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
   ____  ____     _____      
  |  _ \|  _ \   |  ___|     
  | | | | |_) |  | |_  _____ 
  | |_| |  _ <   |  _||_____|
  |____/|_| \_\  |_|         
                             
    Database Config Fixer
EOF
echo -e "${NC}"

log "Checking database configuration..."

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    error ".env.production file not found. Please run the full deployment script first."
fi

# Load current configuration
source .env.production 2>/dev/null || {
    error "Failed to load .env.production file"
}

echo "Current DATABASE_URL: $DATABASE_URL"

# Check if DATABASE_URL is empty or malformed
if [ -z "$DATABASE_URL" ] || [[ ! "$DATABASE_URL" =~ ^postgresql://[^:]+:[^@]+@[^:]+:[0-9]+/[^/]+$ ]]; then
    warning "DATABASE_URL is empty or malformed. Let's fix it!"
    
    echo ""
    echo "Please provide your PostgreSQL connection details:"
    read -p "PostgreSQL username: " PG_USER
    read -s -p "PostgreSQL password: " PG_PASS
    echo ""
    read -p "PostgreSQL database name (default: ai_discovery): " PG_DB
    PG_DB=${PG_DB:-ai_discovery}
    read -p "PostgreSQL host (default: localhost): " PG_HOST
    PG_HOST=${PG_HOST:-localhost}
    read -p "PostgreSQL port (default: 5432): " PG_PORT
    PG_PORT=${PG_PORT:-5432}
    
    echo ""
    log "Testing database connection..."
    
    # Test connection
    if PGPASSWORD="$PG_PASS" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "SELECT 1;" &> /dev/null; then
        log "✅ Database connection successful"
    else
        warning "Database connection failed. Please check your credentials."
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Create new DATABASE_URL
    NEW_DATABASE_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${PG_DB}"
    
    # Backup original file
    cp .env.production .env.production.backup
    log "📄 Backup created: .env.production.backup"
    
    # Update DATABASE_URL in .env.production
    if grep -q "^DATABASE_URL=" .env.production; then
        sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${NEW_DATABASE_URL}|" .env.production
    else
        echo "DATABASE_URL=${NEW_DATABASE_URL}" >> .env.production
    fi
    
    # Update other database fields
    sed -i "s|^POSTGRES_HOST=.*|POSTGRES_HOST=${PG_HOST}|" .env.production
    sed -i "s|^POSTGRES_PORT=.*|POSTGRES_PORT=${PG_PORT}|" .env.production
    sed -i "s|^POSTGRES_DB=.*|POSTGRES_DB=${PG_DB}|" .env.production
    sed -i "s|^POSTGRES_USER=.*|POSTGRES_USER=${PG_USER}|" .env.production
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${PG_PASS}|" .env.production
    
    log "✅ Database configuration updated"
    echo "New DATABASE_URL: $NEW_DATABASE_URL"
    
else
    log "✅ DATABASE_URL appears to be correctly formatted"
fi

echo ""
log "🎉 Database configuration check completed!"
echo ""
echo "Next steps:"
echo "  1. Run: ./deploy_from_step6.sh"
echo "  2. Or run: ./deployment_step_manager.sh 6"
echo ""