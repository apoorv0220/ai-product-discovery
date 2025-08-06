#!/bin/bash

# 🎯 AI Product Discovery Suite - Deployment Step Manager
# Run specific deployment steps individually

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

show_help() {
    echo -e "${BLUE}"
    cat << "EOF"
   _____ _             __  __                                   
  / ___/| |_ ___  ___ |  \/  | __ _ _ __   __ _  __ _  ___ _ __ 
  \___ \| __/ _ \/ _ \| |\/| |/ _` | '_ \ / _` |/ _` |/ _ \ '__|
   ___) | ||  __/ (_) | |  | | (_| | | | | (_| | (_| |  __/ |   
  |____/ \__\___|\___/|_|  |_|\__,_|_| |_|\__,_|\__, |\___|_|   
                                                |___/           
EOF
    echo -e "${NC}"
    
    echo "🎯 Deployment Step Manager"
    echo "=========================="
    echo ""
    echo "Available steps:"
    echo "  1. prereq     - Check prerequisites"
    echo "  2. setup      - Setup application directory"
    echo "  3. venv       - Create virtual environment"
    echo "  4. deps       - Install dependencies"
    echo "  5. config     - Create environment configuration"
    echo "  6. database   - Initialize database tables"
    echo "  7. services   - Create service scripts"
    echo "  8. start      - Start all services"
    echo "  9. test       - Test deployment"
    echo "  10. nginx     - Create Nginx configuration"
    echo ""
    echo "Usage:"
    echo "  $0 <step_number>     # Run specific step"
    echo "  $0 6-9               # Run steps 6 through 9"
    echo "  $0 from-6            # Run from step 6 to end"
    echo "  $0 status            # Check current status"
    echo "  $0 help              # Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 6                 # Run only database initialization"
    echo "  $0 from-6            # Resume from step 6"
    echo "  $0 7-9               # Run steps 7, 8, and 9"
}

check_status() {
    echo "📊 Current Deployment Status:"
    echo "============================="
    
    # Step 1: Prerequisites
    if command -v python3 &> /dev/null && command -v pip3 &> /dev/null; then
        echo "✅ Step 1: Prerequisites - COMPLETE"
    else
        echo "❌ Step 1: Prerequisites - MISSING"
    fi
    
    # Step 2: Application directory
    if [ -d "$HOME/apps/ai-product-discovery" ]; then
        echo "✅ Step 2: Application directory - COMPLETE"
    else
        echo "❌ Step 2: Application directory - MISSING"
    fi
    
    # Step 3: Virtual environment
    if [ -d "venv" ]; then
        echo "✅ Step 3: Virtual environment - COMPLETE"
    else
        echo "❌ Step 3: Virtual environment - MISSING"
    fi
    
    # Step 4: Dependencies
    if [ -d "venv" ] && source venv/bin/activate && python -c "import fastapi" &> /dev/null; then
        echo "✅ Step 4: Dependencies - COMPLETE"
    else
        echo "❌ Step 4: Dependencies - MISSING"
    fi
    
    # Step 5: Configuration
    if [ -f ".env.production" ]; then
        echo "✅ Step 5: Configuration - COMPLETE"
    else
        echo "❌ Step 5: Configuration - MISSING"
    fi
    
    # Step 6: Database
    if [ -f ".env.production" ] && grep -q "DATABASE_URL" .env.production; then
        echo "✅ Step 6: Database config - COMPLETE"
    else
        echo "❌ Step 6: Database - MISSING"
    fi
    
    # Step 7: Service scripts
    if [ -f "start_search.sh" ] && [ -f "control_services.sh" ]; then
        echo "✅ Step 7: Service scripts - COMPLETE"
    else
        echo "❌ Step 7: Service scripts - MISSING"
    fi
    
    # Step 8: Services running
    if [ -f "control_services.sh" ]; then
        if ./control_services.sh status | grep -q "Running.*Healthy" &> /dev/null; then
            echo "✅ Step 8: Services - RUNNING"
        else
            echo "⚠️  Step 8: Services - NOT RUNNING"
        fi
    else
        echo "❌ Step 8: Services - MISSING"
    fi
    
    # Step 9: Test scripts
    if [ -f "test_deployment.sh" ]; then
        echo "✅ Step 9: Test scripts - COMPLETE"
    else
        echo "❌ Step 9: Test scripts - MISSING"
    fi
    
    # Step 10: Nginx config
    if [ -f "nginx_ai_discovery.conf" ]; then
        echo "✅ Step 10: Nginx config - COMPLETE"
    else
        echo "❌ Step 10: Nginx config - MISSING"
    fi
}

run_step() {
    case $1 in
        1|prereq)
            log "Step 1: Checking prerequisites..."
            # Add prerequisite checks here
            ;;
        2|setup)
            log "Step 2: Setting up application directory..."
            # Add setup logic here
            ;;
        3|venv)
            log "Step 3: Creating virtual environment..."
            python3 -m venv venv
            source venv/bin/activate
            pip install --upgrade pip
            ;;
        4|deps)
            log "Step 4: Installing dependencies..."
            source venv/bin/activate
            pip install -r backend/requirements-base.txt
            pip install -r backend/requirements.txt
            pip install gunicorn supervisor
            ;;
        5|config)
            log "Step 5: Creating environment configuration..."
            # Add config creation logic
            ;;
        6|database)
            log "Step 6: Initializing database..."
            ./deploy_from_step6.sh
            ;;
        7|services)
            log "Step 7: Creating service scripts..."
            # Service script creation is included in step 6 script
            ;;
        8|start)
            log "Step 8: Starting services..."
            if [ -f "control_services.sh" ]; then
                ./control_services.sh start
            else
                error "Service scripts not found. Run step 7 first."
            fi
            ;;
        9|test)
            log "Step 9: Testing deployment..."
            if [ -f "test_deployment.sh" ]; then
                ./test_deployment.sh
            else
                error "Test script not found. Run step 6-8 first."
            fi
            ;;
        10|nginx)
            log "Step 10: Creating Nginx configuration..."
            # Nginx config is created in the main script
            ;;
        *)
            error "Unknown step: $1"
            ;;
    esac
}

# Main script
case "$1" in
    help|--help|-h)
        show_help
        ;;
    status)
        check_status
        ;;
    from-6)
        log "Running deployment from Step 6..."
        ./deploy_from_step6.sh
        ;;
    6)
        log "Running Step 6 (Database + Services + Start + Test)..."
        ./deploy_from_step6.sh
        ;;
    [1-9]|10)
        run_step "$1"
        ;;
    [1-9]-[1-9]|[1-9]-10|10-[1-9])
        # Handle ranges like 6-9
        IFS='-' read -ra RANGE <<< "$1"
        START=${RANGE[0]}
        END=${RANGE[1]}
        log "Running steps $START through $END..."
        for i in $(seq $START $END); do
            run_step $i
        done
        ;;
    "")
        echo "❌ No step specified. Use '$0 help' for usage information."
        exit 1
        ;;
    *)
        echo "❌ Invalid option: $1"
        echo "Use '$0 help' for usage information."
        exit 1
        ;;
esac