# Quick Setup Script for AI Product Discovery Suite
# Run this to set up your local development environment in one command

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "AI Product Discovery Suite - Quick Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check prerequisites
Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

# Check Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Green

# Check Docker
$dockerVersion = docker --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker not found. Please install Docker Desktop" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Docker found: $dockerVersion" -ForegroundColor Green

# Check Docker Compose
$composeVersion = docker-compose --version 2>&1
if ($LASTEXITCODE -ne 0) {
    # Try docker compose (new syntax)
    $composeVersion = docker compose version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker Compose not found" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  ✓ Docker Compose found: $composeVersion" -ForegroundColor Green

# Start infrastructure
Write-Host "`n[2/7] Starting infrastructure services..." -ForegroundColor Yellow
docker-compose up -d postgres redis elasticsearch qdrant

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start infrastructure" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Infrastructure started" -ForegroundColor Green

# Wait for services to be ready
Write-Host "`n[3/7] Waiting for services to be ready (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
Write-Host "  ✓ Services should be ready" -ForegroundColor Green

# Create virtual environment
Write-Host "`n[4/7] Creating Python virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "  ℹ Virtual environment already exists, skipping creation" -ForegroundColor Yellow
} else {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment and install dependencies
Write-Host "`n[5/7] Installing Python dependencies..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Dependencies installed" -ForegroundColor Green

# Run migrations
Write-Host "`n[6/7] Running database migrations..." -ForegroundColor Yellow
python scripts/run_migrations.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Migrations failed" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Migrations completed" -ForegroundColor Green

# Seed test data
Write-Host "`n[7/7] Seeding test data..." -ForegroundColor Yellow
python scripts/seed_test_data.py | Tee-Object -Variable seedOutput

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to seed test data" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Test data seeded" -ForegroundColor Green

# Success message
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "🚀 Your development environment is ready!`n" -ForegroundColor Cyan

Write-Host "📋 API Keys have been generated (save these!):" -ForegroundColor Yellow
Write-Host "   Check the output above for API keys`n" -ForegroundColor White

Write-Host "🧪 Run tests:" -ForegroundColor Yellow
Write-Host "   pytest`n" -ForegroundColor White

Write-Host "🔍 Verify infrastructure:" -ForegroundColor Yellow
Write-Host "   python scripts/verify_infrastructure.py`n" -ForegroundColor White

Write-Host "🎯 Start a service:" -ForegroundColor Yellow
Write-Host "   `$env:PYTHONPATH=`"$PWD\backend`"" -ForegroundColor White
Write-Host "   cd backend\search-service" -ForegroundColor White
Write-Host "   python main.py`n" -ForegroundColor White

Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "   LOCAL_DEVELOPMENT_SETUP.md - Complete development guide" -ForegroundColor White
Write-Host "   TESTING_GUIDE.md - Testing strategies" -ForegroundColor White
Write-Host "   IMPLEMENTATION_STATUS.md - What's implemented`n" -ForegroundColor White

Write-Host "💡 Tip: Keep this PowerShell window open (venv is activated)" -ForegroundColor Cyan

# Keep venv activated
Write-Host "`n========================================`n" -ForegroundColor Cyan

