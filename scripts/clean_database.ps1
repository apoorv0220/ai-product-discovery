# Clean Database Script
# Drops and recreates the ai_discovery database to ensure a clean slate

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Database Cleanup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "  1. Drop the 'ai_discovery' database (if it exists)" -ForegroundColor White
Write-Host "  2. Create a fresh 'ai_discovery' database" -ForegroundColor White
Write-Host "  3. Verify the database is empty" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "Continue? (Y/N)"
if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "Dropping database..." -ForegroundColor Yellow
$drop_result = docker exec ai_discovery_postgres psql -U ai_user -d postgres -c "DROP DATABASE IF EXISTS ai_discovery;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Database dropped" -ForegroundColor Green
} else {
    Write-Host "  [WARNING] Drop command returned non-zero exit code" -ForegroundColor Yellow
    Write-Host "  Output: $drop_result" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Creating fresh database..." -ForegroundColor Yellow
$create_result = docker exec ai_discovery_postgres psql -U ai_user -d postgres -c "CREATE DATABASE ai_discovery;" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Database created" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Failed to create database" -ForegroundColor Red
    Write-Host "  Output: $create_result" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Verifying database is empty..." -ForegroundColor Yellow
$table_check = docker exec ai_discovery_postgres psql -U ai_user -d ai_discovery -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>&1
$index_check = docker exec ai_discovery_postgres psql -U ai_user -d ai_discovery -t -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';" 2>&1

$table_count = $table_check.Trim()
$index_count = $index_check.Trim()

if (($table_count -eq "0" -or $table_count -eq "") -and ($index_count -eq "0" -or $index_count -eq "")) {
    Write-Host "  [OK] Database is empty (no tables or indexes)" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Database cleanup complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can now run migrations:" -ForegroundColor Green
    Write-Host "  cd backend" -ForegroundColor White
    Write-Host "  alembic upgrade head" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "  [WARNING] Database may not be completely empty:" -ForegroundColor Yellow
    Write-Host "    Tables: $table_count" -ForegroundColor Gray
    Write-Host "    Indexes: $index_count" -ForegroundColor Gray
}

