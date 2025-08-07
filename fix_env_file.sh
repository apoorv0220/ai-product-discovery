#!/bin/bash

# 🔧 Environment File Fixer
# Fixes common issues in .env files that cause shell parsing errors

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

# Function to fix environment file
fix_env_file() {
    local env_file="$1"
    
    if [ ! -f "$env_file" ]; then
        error "Environment file $env_file not found"
    fi
    
    log "Fixing environment file: $env_file"
    
    # Create backup
    cp "$env_file" "${env_file}.backup.$(date +%Y%m%d_%H%M%S)"
    log "📄 Backup created: ${env_file}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Create temporary file for fixes
    local temp_file=$(mktemp)
    
    # Process line by line
    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*$ ]]; then
            echo "$line" >> "$temp_file"
            continue
        fi
        
        # Check if line contains = (environment variable)
        if [[ "$line" =~ ^[^=]+= ]]; then
            # Extract key and value
            key="${line%%=*}"
            value="${line#*=}"
            
            # Check if value contains spaces and is not already quoted
            if [[ "$value" =~ [[:space:]] ]] && [[ ! "$value" =~ ^[\'\"].*[\'\"]$ ]]; then
                # Special handling for JSON arrays
                if [[ "$value" =~ ^\[.*\]$ ]]; then
                    echo "${key}='${value}'" >> "$temp_file"
                    info "Fixed JSON array: $key"
                else
                    echo "${key}=\"${value}\"" >> "$temp_file"
                    info "Fixed spaced value: $key"
                fi
            else
                echo "$line" >> "$temp_file"
            fi
        else
            echo "$line" >> "$temp_file"
        fi
    done < "$env_file"
    
    # Replace original file
    mv "$temp_file" "$env_file"
    
    log "✅ Environment file fixed: $env_file"
}

# Function to validate environment file
validate_env_file() {
    local env_file="$1"
    
    log "Validating environment file: $env_file"
    
    # Try to source the file in a subshell
    if (set -e; source "$env_file") 2>/dev/null; then
        log "✅ Environment file validation passed"
        return 0
    else
        error "❌ Environment file validation failed"
        return 1
    fi
}

# Function to test specific problematic lines
test_problematic_patterns() {
    local env_file="$1"
    
    log "Testing for problematic patterns in: $env_file"
    
    local issues_found=0
    
    # Check for unquoted values with spaces
    while IFS= read -r line; do
        if [[ "$line" =~ ^[^=]+=.*[[:space:]].*$ ]] && [[ ! "$line" =~ ^[^=]+=[\'\"].*[\'\"]$ ]] && [[ ! "$line" =~ ^[[:space:]]*# ]]; then
            warning "Unquoted value with spaces: $line"
            ((issues_found++))
        fi
    done < "$env_file"
    
    if [ $issues_found -eq 0 ]; then
        log "✅ No problematic patterns found"
    else
        warning "Found $issues_found potential issues"
    fi
    
    return $issues_found
}

echo -e "${BLUE}"
cat << "EOF"
   🔧 Environment File Fixer
   ========================
EOF
echo -e "${NC}"

# Default to .env.docker-shared-server if no argument provided
ENV_FILE="${1:-.env.docker-shared-server}"

if [ ! -f "$ENV_FILE" ]; then
    error "Environment file $ENV_FILE not found"
fi

log "Processing environment file: $ENV_FILE"

# Test for issues first
if ! test_problematic_patterns "$ENV_FILE"; then
    warning "Found issues in environment file"
    
    read -p "Do you want to fix these issues automatically? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        fix_env_file "$ENV_FILE"
    fi
fi

# Validate the file
if validate_env_file "$ENV_FILE"; then
    log "🎉 Environment file is ready for use!"
else
    error "Environment file still has issues after fixing"
fi

echo ""
log "✅ Environment file processing completed"
echo ""
echo "You can now safely run:"
echo "  ./deploy_docker_shared_server.sh"
echo ""
echo "If you need to revert changes:"
echo "  mv ${ENV_FILE}.backup.* ${ENV_FILE}"