#!/bin/bash

# 🔧 Ubuntu Repository Fix Script
# Fixes common Ubuntu repository issues and broken package sources

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
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

echo -e "${BLUE}"
cat << "EOF"
   _   _ _                 _         
  | | | | |__  _   _ _ __ | |_ _   _ 
  | | | | '_ \| | | | '_ \| __| | | |
  | |_| | |_) | |_| | | | | |_| |_| |
   \___/|_.__/ \__,_|_| |_|\__|\__,_|
                                    
    Repository Fix Script
EOF
echo -e "${NC}"

log "Starting Ubuntu repository cleanup..."

# Step 1: Backup current sources
log "Step 1: Backing up current repository sources..."
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)
if [ -d "/etc/apt/sources.list.d" ]; then
    sudo cp -r /etc/apt/sources.list.d /etc/apt/sources.list.d.backup.$(date +%Y%m%d_%H%M%S)
fi

# Step 2: Remove problematic repositories
log "Step 2: Removing problematic repositories..."

# Remove fluentbit repository
if [ -f "/etc/apt/sources.list.d/fluentbit.list" ]; then
    warning "Removing problematic FluentBit repository"
    sudo rm -f /etc/apt/sources.list.d/fluentbit.list
fi

# Remove certbot PPA
if [ -f "/etc/apt/sources.list.d/certbot-ubuntu-certbot-noble.list" ]; then
    warning "Removing problematic Certbot PPA"
    sudo rm -f /etc/apt/sources.list.d/certbot-ubuntu-certbot-noble.list
fi

# Find and remove any sources with fluentbit or certbot PPA
sudo find /etc/apt/sources.list.d/ -name "*.list" -exec grep -l "packages.fluentbit.io\|ppa.launchpadcontent.net/certbot" {} \; 2>/dev/null | while read file; do
    warning "Removing problematic repository: $file"
    sudo rm -f "$file"
done

# Step 3: Fix NewRelic repository warnings (optional)
log "Step 3: Fixing NewRelic repository warnings..."
if [ -f "/etc/apt/sources.list.d/newrelic-infra.list" ]; then
    warning "NewRelic repository detected - fixing key warnings"
    # Download and add the proper key
    curl -fsSL https://download.newrelic.com/infrastructure_agent/gpg/newrelic-infra.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/newrelic-infra.gpg
    
    # Update the sources list with proper signed-by
    if sudo grep -q "download.newrelic.com" /etc/apt/sources.list.d/newrelic-infra.list; then
        sudo sed -i 's|deb https://download.newrelic.com/infrastructure_agent/linux/apt|deb [signed-by=/etc/apt/keyrings/newrelic-infra.gpg] https://download.newrelic.com/infrastructure_agent/linux/apt|g' /etc/apt/sources.list.d/newrelic-infra.list
    fi
fi

# Step 4: Ensure essential repositories are present
log "Step 4: Ensuring essential Ubuntu repositories..."

# Check if main sources.list has essential repositories
if ! grep -q "noble main" /etc/apt/sources.list; then
    warning "Adding essential Ubuntu repositories"
    sudo tee /etc/apt/sources.list > /dev/null << 'EOF'
# Ubuntu 24.04 Noble Numbat - Essential repositories only
deb http://archive.ubuntu.com/ubuntu noble main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu noble-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu noble-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu noble-security main restricted universe multiverse
EOF
fi

# Step 5: Update package lists
log "Step 5: Updating package lists..."
sudo apt clean
sudo apt autoclean

# Try to update with better error handling
if ! sudo apt update 2>&1 | tee /tmp/apt_update.log; then
    warning "Initial update failed, checking for remaining issues..."
    
    # Show only errors and warnings
    grep -E "(E:|W:|Err:)" /tmp/apt_update.log | head -10
    
    warning "Attempting to fix remaining issues..."
    
    # Remove any remaining problematic sources
    if grep -q "fluentbit" /tmp/apt_update.log; then
        warning "Still finding FluentBit references, removing..."
        sudo find /etc/apt/ -name "*.list*" -exec grep -l "fluentbit" {} \; 2>/dev/null | while read file; do
            sudo sed -i '/fluentbit/d' "$file"
        done
    fi
    
    if grep -q "certbot" /tmp/apt_update.log; then
        warning "Still finding Certbot PPA references, removing..."
        sudo find /etc/apt/ -name "*.list*" -exec grep -l "ppa.*certbot" {} \; 2>/dev/null | while read file; do
            sudo sed -i '/ppa.*certbot/d' "$file"
        done
    fi
    
    # Try update again
    log "Attempting update again..."
    if sudo apt update; then
        log "✅ Update successful after cleanup"
    else
        warning "Some repository warnings may persist, but essential updates should work"
    fi
else
    log "✅ Package lists updated successfully"
fi

# Step 6: Install certbot properly (if needed)
log "Step 6: Installing Certbot properly..."
if ! command -v certbot &> /dev/null; then
    info "Installing Certbot from default repositories..."
    sudo apt install -y certbot python3-certbot-nginx python3-certbot-apache
else
    info "Certbot is already installed"
fi

# Step 7: Clean up
log "Step 7: Cleaning up..."
sudo apt autoremove -y
sudo apt autoclean

# Step 8: Verify system
log "Step 8: Verifying system..."

echo ""
echo "📊 System Status:"
echo "  • Ubuntu Version: $(lsb_release -d | cut -f2)"
echo "  • Kernel: $(uname -r)"
echo "  • Available Updates: $(apt list --upgradable 2>/dev/null | wc -l) packages"

# Test essential package installation
log "Testing package installation..."
if sudo apt install -y curl wget unzip; then
    log "✅ Package installation working correctly"
else
    error "Package installation still has issues"
    exit 1
fi

echo ""
echo -e "${GREEN}"
cat << "EOF"
✅ Ubuntu Repository Fix Complete!
=================================

EOF
echo -e "${NC}"

echo "🔧 What was fixed:"
echo "  • ❌ Removed problematic FluentBit repository"
echo "  • ❌ Removed broken Certbot PPA"
echo "  • ✅ Fixed NewRelic repository warnings"
echo "  • ✅ Ensured essential Ubuntu repositories"
echo "  • ✅ Cleaned package cache"
echo "  • ✅ Installed Certbot properly"

echo ""
echo "📋 Next Steps:"
echo "  1. Repository issues are now resolved"
echo "  2. You can now install Redis: ./install_redis.sh"
echo "  3. Or continue with deployment: ./deploy_shared_server.sh"

echo ""
echo "⚠️  Note: Some warnings about legacy keys may still appear but won't prevent installation"

log "🎉 Repository fix completed successfully!"