#!/bin/bash

# Clean AI Implementation Deployment Script
# Deploys AI features without dummy data - proper error handling only

echo "🧹 Deploying Clean AI Implementation"
echo "===================================="
echo "✅ No dummy/sample data"
echo "✅ Proper error handling"
echo "✅ Real AI service responses only"
echo ""

# Configuration
MAGENTO_ROOT="/home/magentotests/public_html"
PROJECT_ROOT="/Users/apple/Desktop/ai-product-discovery"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log steps
log_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: Backup current files
log_step "Step 1: Creating backup of current implementation"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -d "$MAGENTO_ROOT" ]; then
    cp -r "$MAGENTO_ROOT/app/code/Vendor/DiscoverySuite" "$BACKUP_DIR/" 2>/dev/null || echo "No existing module found"
    log_success "Backup created in $BACKUP_DIR"
else
    log_warning "Magento root not found - skipping backup"
fi

# Step 2: Deploy updated files
log_step "Step 2: Deploying updated Magento files"

# Updated files with clean implementation
UPDATED_FILES=(
    "magento2-module/Vendor/DiscoverySuite/Model/Search/SearchService.php"
    "magento2-module/Vendor/DiscoverySuite/Model/Recommendations/RecommendationService.php"
    "magento2-module/Vendor/DiscoverySuite/Helper/Data.php"
    "magento2-module/Vendor/DiscoverySuite/Console/Command/TestAdvancedAi.php"
)

for file in "${UPDATED_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        # Calculate target path
        target_path="$MAGENTO_ROOT/app/code/${file#magento2-module/}"
        target_dir=$(dirname "$target_path")
        
        # Create directory if it doesn't exist
        mkdir -p "$target_dir"
        
        # Copy file
        cp "$PROJECT_ROOT/$file" "$target_path"
        log_success "Deployed: $(basename $file)"
    else
        log_error "Source file not found: $file"
    fi
done

# Step 3: Update backend files
log_step "Step 3: Deploying updated backend files"

BACKEND_FILES=(
    "backend/search-service/api/autocomplete.py"
)

for file in "${BACKEND_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        log_success "Backend file ready: $(basename $file)"
    else
        log_error "Backend file not found: $file"
    fi
done

# Step 4: Magento compilation and cache
log_step "Step 4: Compiling Magento module"

if [ -d "$MAGENTO_ROOT" ]; then
    cd "$MAGENTO_ROOT"
    
    # Compile dependency injection
    php bin/magento setup:di:compile
    if [ $? -eq 0 ]; then
        log_success "DI compilation completed"
    else
        log_error "DI compilation failed"
        exit 1
    fi
    
    # Clear cache
    php bin/magento cache:flush
    if [ $? -eq 0 ]; then
        log_success "Cache cleared"
    else
        log_error "Cache clear failed"
    fi
else
    log_warning "Skipping Magento compilation - not on Magento server"
fi

# Step 5: Deployment summary
echo ""
echo "🎯 Clean AI Implementation Deployment Summary"
echo "============================================="
echo ""
echo "✅ REMOVED: All dummy/sample data"
echo "✅ REMOVED: Hardcoded default values"
echo "✅ ADDED: Proper error handling"
echo "✅ ADDED: Service availability checks"
echo ""
echo "📋 What happens now when AI services are unavailable:"
echo "   • Search: Returns empty results with error message"
echo "   • Recommendations: Returns empty array with error message"
echo "   • Autocomplete: Returns empty suggestions with error message"
echo ""
echo "🔍 Testing Commands:"
echo "   php bin/magento discovery:test:advanced-ai"
echo "   php bin/magento discovery:test:connection"
echo "   php bin/magento discovery:sync:catalog"
echo ""
echo "⚠️  IMPORTANT NOTES:"
echo "   • Tests will show REAL service status (no fake data)"
echo "   • Empty results = AI services are not running"
echo "   • Error messages = Clear indication of what's wrong"
echo "   • All responses are authentic from AI services"
echo ""
echo "🚀 To start AI services:"
echo "   ./start_ai_services_simple.sh"
echo ""
echo "✅ Clean implementation deployed successfully!"
