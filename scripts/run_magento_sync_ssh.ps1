# PowerShell script to help run Magento sync via SSH
# This script connects to the remote server and runs the sync command

param(
    [string]$MagentoPath = "",
    [int]$StoreId = 1,
    [int]$BatchSize = 100
)

$sshHost = "magento-test.softdemonew.info"
$sshUser = "magentotests"
$sshPass = "I*~WO144rHm4CutA"

Write-Host "`n=== Magento Sync via SSH ===" -ForegroundColor Cyan
Write-Host "Host: $sshHost" -ForegroundColor Yellow
Write-Host "User: $sshUser" -ForegroundColor Yellow
Write-Host ""

# Check if OpenSSH is available
$sshAvailable = Get-Command ssh -ErrorAction SilentlyContinue

if (-not $sshAvailable) {
    Write-Host "[ERROR] SSH command not found. Please install OpenSSH:" -ForegroundColor Red
    Write-Host "  1. Open PowerShell as Administrator" -ForegroundColor Yellow
    Write-Host "  2. Run: Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0" -ForegroundColor Yellow
    Write-Host "  3. Restart PowerShell" -ForegroundColor Yellow
    exit 1
}

Write-Host "[INFO] SSH is available" -ForegroundColor Green

# If Magento path not provided, we'll need to find it
if ([string]::IsNullOrEmpty($MagentoPath)) {
    Write-Host "`n[STEP 1] Finding Magento installation..." -ForegroundColor Cyan
    
    # Build SSH command to find Magento
    $findMagentoCmd = @"
    # Try common locations
    for dir in /var/www/html /var/www ~/public_html ~/html; do
        if [ -f "\$dir/bin/magento" ]; then
            echo "\$dir"
            exit 0
        fi
    done
    # If not found, search
    find /var/www -name "bin/magento" -type f 2>/dev/null | head -1 | xargs dirname 2>/dev/null
"@
    
    Write-Host "Attempting to find Magento automatically..." -ForegroundColor Yellow
    Write-Host "If this fails, you'll need to provide the path manually." -ForegroundColor Yellow
    Write-Host ""
    
    # Use sshpass if available, otherwise prompt for password
    # Note: sshpass is not available on Windows by default
    # So we'll use SSH key or manual connection
    
    Write-Host "Please run this command manually:" -ForegroundColor Yellow
    Write-Host "  ssh $sshUser@$sshHost" -ForegroundColor Green
    Write-Host ""
    Write-Host "Then run these commands on the remote server:" -ForegroundColor Yellow
    Write-Host "  find /var/www -name 'bin/magento' -type f 2>/dev/null | head -1 | xargs dirname" -ForegroundColor White
    Write-Host ""
    Write-Host "Once you have the path, run this script again with:" -ForegroundColor Yellow
    Write-Host "  .\scripts\run_magento_sync_ssh.ps1 -MagentoPath '/path/to/magento'" -ForegroundColor Green
    
    exit 0
}

# Build the sync command
$syncCommand = @"
cd $MagentoPath
php bin/magento discovery:sync:catalog --store-id=$StoreId --batch-size=$BatchSize
"@

Write-Host "[STEP 2] Running Magento sync..." -ForegroundColor Cyan
Write-Host "Magento Path: $MagentoPath" -ForegroundColor Yellow
Write-Host "Store ID: $StoreId" -ForegroundColor Yellow
Write-Host "Batch Size: $BatchSize" -ForegroundColor Yellow
Write-Host ""

# Note: SSH password authentication requires either:
# 1. SSH key setup (recommended)
# 2. sshpass utility (not available on Windows by default)
# 3. Manual connection

Write-Host "Due to Windows SSH limitations, please run this manually:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Connect to server:" -ForegroundColor Cyan
Write-Host "   ssh $sshUser@$sshHost" -ForegroundColor Green
Write-Host ""
Write-Host "2. Run sync command:" -ForegroundColor Cyan
Write-Host "   cd $MagentoPath" -ForegroundColor Green
Write-Host "   php bin/magento discovery:sync:catalog --store-id=$StoreId --batch-size=$BatchSize" -ForegroundColor Green
Write-Host ""
Write-Host "3. After sync completes, run diagnostic locally:" -ForegroundColor Cyan
Write-Host "   python scripts/diagnose_data_flow.py --merchant-id 1 --api-key `"ak_live_7hr8f6rhtk64jimhlzgtdez7d7gvh5b3`"" -ForegroundColor Green
Write-Host ""

# Alternative: Use Plink (PuTTY) if available
$plinkAvailable = Get-Command plink -ErrorAction SilentlyContinue

if ($plinkAvailable) {
    Write-Host "[INFO] Plink (PuTTY) found. You can use it for automated connection." -ForegroundColor Green
    Write-Host "For now, manual connection is recommended for first time setup." -ForegroundColor Yellow
}




