#!/bin/bash

# 🧪 Test Deployment Dependencies
# Local test for deployment script dependencies to ensure they work before deploying to server

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
   🧪 Testing Deployment Dependencies
   =================================
   Testing the exact dependencies used in deployment script
EOF
echo -e "${NC}"

# Step 1: Create test virtual environment
log "Step 1: Creating test virtual environment..."
rm -rf test_deploy_deps 2>/dev/null || true
python3 -m venv test_deploy_deps

# Step 2: Activate and upgrade pip
log "Step 2: Activating virtual environment and upgrading pip..."
source test_deploy_deps/bin/activate
python -m pip install --upgrade pip

# Step 3: Install exact dependencies from deployment script
log "Step 3: Installing exact dependencies from deployment script..."
pip install sqlalchemy[asyncio]==2.0.36 asyncpg==0.30.0 psycopg2-binary==2.9.9 alembic==1.14.0 structlog==24.4.0 pydantic-settings==2.8.0 pydantic==2.9.2

# Step 4: Test imports
log "Step 4: Testing critical imports..."

# Test pydantic_settings import
python3 -c "
import sys
try:
    from pydantic_settings import BaseSettings
    print('✅ pydantic_settings import successful')
except ImportError as e:
    print(f'❌ pydantic_settings import failed: {e}')
    sys.exit(1)
"

# Test our settings module
python3 -c "
import sys
import os
sys.path.insert(0, '$(pwd)')

try:
    from backend.shared.config.settings import Settings
    print('✅ Settings import successful')
except ImportError as e:
    print(f'❌ Settings import failed: {e}')
    sys.exit(1)
"

# Test database imports
python3 -c "
import sys
import os
sys.path.insert(0, '$(pwd)')

try:
    from backend.shared.database.base import init_database
    print('✅ Database imports successful')
except ImportError as e:
    print(f'❌ Database imports failed: {e}')
    sys.exit(1)
"

# Step 5: Test database initialization logic (without actually connecting)
log "Step 5: Testing database initialization logic..."

python3 -c "
import sys
import os
sys.path.insert(0, '$(pwd)')

# Set dummy environment variables for testing
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_DB'] = 'test'
os.environ['POSTGRES_USER'] = 'test'
os.environ['POSTGRES_PASSWORD'] = 'test'

try:
    from backend.shared.database.base import init_database, get_database_session
    from backend.shared.config.settings import get_settings
    print('✅ All database modules loaded successfully')
    
    settings = get_settings()
    print(f'✅ Settings loaded: {settings.__class__.__name__}')
    
except Exception as e:
    print(f'❌ Database module test failed: {e}')
    sys.exit(1)
"

# Step 6: Cleanup
log "Step 6: Cleaning up test environment..."
deactivate
rm -rf test_deploy_deps

log "🎉 All dependency tests passed!"
echo ""
echo "✅ The deployment script dependencies are working correctly"
echo "✅ pydantic-settings is properly included"
echo "✅ All imports are successful"
echo "✅ Settings module loads correctly"
echo ""
echo "🚀 Ready for server deployment!"