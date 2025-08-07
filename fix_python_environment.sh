#!/bin/bash

# 🐍 Python Environment Fixer for PEP 668 Systems
# Fixes externally-managed-environment errors by ensuring proper virtual environment usage

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
   🐍 Python Environment Fixer
   ===========================
   Fixing PEP 668 externally-managed-environment issues
EOF
echo -e "${NC}"

# Check if running on a system with externally-managed-environment
check_external_management() {
    log "Checking Python environment management..."
    
    if python3 -m pip install --help 2>&1 | grep -q "externally-managed-environment"; then
        info "✅ System has PEP 668 protection (externally-managed-environment)"
        return 0
    elif [ -f "/usr/lib/python*/EXTERNALLY-MANAGED" ] 2>/dev/null; then
        info "✅ System has PEP 668 protection (EXTERNALLY-MANAGED file found)"
        return 0
    else
        info "ℹ️ System does not have PEP 668 protection"
        return 1
    fi
}

# Install required system packages
install_system_requirements() {
    log "Installing system requirements..."
    
    # Update package list
    sudo apt update || {
        warning "Failed to update package list, continuing anyway..."
    }
    
    # Install required packages
    sudo apt install -y python3-full python3-venv python3-pip python3-dev build-essential || {
        error "Failed to install required system packages"
    }
    
    log "✅ System requirements installed"
}

# Test virtual environment creation
test_venv_creation() {
    log "Testing virtual environment creation..."
    
    # Remove any existing test environment
    rm -rf test_venv 2>/dev/null || true
    
    # Create test virtual environment
    if python3 -m venv test_venv; then
        log "✅ Virtual environment creation successful"
        
        # Test activation and pip installation
        source test_venv/bin/activate
        
        # Upgrade pip
        python -m pip install --upgrade pip
        
        # Test package installation
        pip install requests
        
        # Deactivate and cleanup
        deactivate
        rm -rf test_venv
        
        log "✅ Virtual environment test completed successfully"
        return 0
    else
        error "❌ Virtual environment creation failed"
        return 1
    fi
}

# Fix common issues
fix_common_issues() {
    log "Fixing common Python environment issues..."
    
    # Ensure python3-distutils is installed (sometimes needed)
    sudo apt install -y python3-distutils python3-setuptools || {
        warning "Failed to install distutils/setuptools, continuing..."
    }
    
    # Fix any broken packages
    sudo apt --fix-broken install -y || {
        warning "Failed to fix broken packages, continuing..."
    }
    
    log "✅ Common issues fixed"
}

# Create a deployment-specific virtual environment
create_deployment_venv() {
    log "Creating deployment virtual environment..."
    
    # Remove existing deployment environment
    rm -rf ai_discovery_venv 2>/dev/null || true
    
    # Create new virtual environment
    python3 -m venv ai_discovery_venv
    
    # Activate environment
    source ai_discovery_venv/bin/activate
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install deployment dependencies
    pip install sqlalchemy[asyncio]==2.0.36 asyncpg==0.30.0 psycopg2-binary==2.9.9 alembic==1.14.0 structlog==24.4.0
    
    # Deactivate
    deactivate
    
    log "✅ Deployment virtual environment created: ai_discovery_venv"
    info "You can now use this environment for database operations"
}

# Main execution
main() {
    log "Starting Python environment fix..."
    
    # Check current status
    if check_external_management; then
        info "PEP 668 protection detected - virtual environments required"
    fi
    
    # Install system requirements
    install_system_requirements
    
    # Fix common issues
    fix_common_issues
    
    # Test virtual environment functionality
    if test_venv_creation; then
        log "✅ Virtual environment functionality confirmed"
    else
        error "Virtual environment functionality test failed"
    fi
    
    # Create deployment-specific environment
    create_deployment_venv
    
    log "🎉 Python environment fix completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Your deployment script will now work properly"
    echo "2. Run: ./deploy_docker_shared_server.sh"
    echo ""
    echo "If you need to manually use the environment:"
    echo "  source ai_discovery_venv/bin/activate"
    echo "  # do your work"
    echo "  deactivate"
}

# Run main function
main