# Interactive script to reindex products from Magento
$ErrorActionPreference = "Stop"

Write-Host "`n=== Magento Product Reindex - Interactive Guide ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify search service is running
Write-Host "[STEP 1] Checking if search service is running..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:7099/health" -TimeoutSec 2
    Write-Host "[OK] Search service is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Search service is not running on localhost:7099" -ForegroundColor Red
    Write-Host "Please start the search service first!" -ForegroundColor Yellow
    exit 1
}

# Step 2: Get public IP
Write-Host "`n[STEP 2] Getting your public IP..." -ForegroundColor Yellow
try {
    $publicIP = (Invoke-RestMethod -Uri "https://api.ipify.org").Trim()
    Write-Host "[OK] Your public IP: $publicIP" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Could not get public IP automatically" -ForegroundColor Yellow
    $publicIP = Read-Host "Please enter your public IP (or visit https://whatismyip.com)"
}

$apiUrl = "http://$publicIP:7099"
Write-Host "Magento server will access: $apiUrl" -ForegroundColor Cyan

# Step 3: Check if port is accessible (optional)
Write-Host "`n[STEP 3] Checking port accessibility..." -ForegroundColor Yellow
Write-Host "[INFO] Make sure port 7099 is open in your firewall!" -ForegroundColor Yellow
Write-Host "[INFO] Windows Firewall: Allow port 7099 for incoming connections" -ForegroundColor Yellow
$continue = Read-Host "`nContinue anyway? (y/n)"
if ($continue -ne "y") {
    Write-Host "Exiting. Please configure firewall first." -ForegroundColor Yellow
    exit 0
}

# Step 4: SSH connection instructions
Write-Host "`n[STEP 4] SSH Connection Instructions" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Please open a NEW PowerShell window and run:" -ForegroundColor Cyan
Write-Host "  ssh magentotests@magento-test.softdemonew.info" -ForegroundColor Green
Write-Host ""
Write-Host "Password: I*~WO144rHm4CutA" -ForegroundColor Gray
Write-Host ""
Write-Host "Once connected, run these commands on the remote server:" -ForegroundColor Cyan
Write-Host ""
Write-Host "# Find Magento directory:" -ForegroundColor White
Write-Host "find /var/www -name 'bin/magento' 2>/dev/null" -ForegroundColor Green
Write-Host ""
Write-Host "# Navigate to Magento (replace PATH with result above):" -ForegroundColor White
Write-Host "cd /path/to/magento" -ForegroundColor Green
Write-Host ""
Write-Host "# Configure API URL:" -ForegroundColor White
Write-Host "php bin/magento config:set discovery_suite_config/general/api_base_url `"$apiUrl`"" -ForegroundColor Green
Write-Host "php bin/magento config:set discovery_suite_config/general/api_key `"ak_live_7hr8f6rhtk64jimhlzgtdez7d7gvh5b3`"" -ForegroundColor Green
Write-Host ""
Write-Host "# Test connection:" -ForegroundColor White
Write-Host "curl $apiUrl/health" -ForegroundColor Green
Write-Host ""
Write-Host "# Run sync:" -ForegroundColor White
Write-Host "php bin/magento discovery:sync:catalog --store-id=1 --batch-size=100" -ForegroundColor Green
Write-Host ""
Write-Host "Press Enter after you've completed the sync on the remote server..." -ForegroundColor Yellow
Read-Host

# Step 5: Verify results
Write-Host "`n[STEP 5] Verifying results..." -ForegroundColor Yellow
Write-Host "Running diagnostic..." -ForegroundColor Cyan

$diagnosticScript = "scripts/diagnose_data_flow.py"
if (Test-Path $diagnosticScript) {
    python $diagnosticScript --merchant-id 1 --api-key "ak_live_7hr8f6rhtk64jimhlzgtdez7d7gvh5b3"
} else {
    Write-Host "[WARNING] Diagnostic script not found. Run manually:" -ForegroundColor Yellow
    Write-Host "python scripts/diagnose_data_flow.py --merchant-id 1 --api-key `"ak_live_7hr8f6rhtk64jimhlzgtdez7d7gvh5b3`"" -ForegroundColor Green
}

Write-Host "`n=== Reindex Complete! ===" -ForegroundColor Green




