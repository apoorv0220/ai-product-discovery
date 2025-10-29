#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Starts the AI Product Discovery Suite backend services using Docker Compose.
.DESCRIPTION
    This script performs the following actions:
    1. Checks if Docker Desktop is running. If not, it attempts to start it.
    2. Verifies the existence of the .env file.
    3. Checks for port availability to prevent conflicts.
    4. Runs 'docker-compose up -d' to start all services.
    5. Monitors the health of all Docker containers until they are ready.
    6. Displays service URLs and next steps.
.NOTES
    Requires PowerShell 5.1 or newer (or pwsh for cross-platform).
    Ensure Docker Desktop is installed and configured for WSL2 (recommended).
#>

# Enable strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-HostGreen {
    param([string]$Message)
    Write-Host -ForegroundColor Green $Message
}

function Write-HostRed {
    param([string]$Message)
    Write-Host -ForegroundColor Red $Message
}

function Write-HostYellow {
    param([string]$Message)
    Write-Host -ForegroundColor Yellow $Message
}

function Test-PortAvailability {
    param([int]$Port)
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connectTask = $tcpClient.ConnectAsync("localhost", $Port)
        $connectTask.Wait(100) | Out-Null # Wait a short period to see if connection is refused

        if ($tcpClient.Connected) {
            Write-HostRed "❌ Port $Port is already in use. Please free up the port or change it in .env."
            Write-HostYellow "   Run 'netstat -ano | findstr :$Port' in Command Prompt to find the process using it."
            return $false
        }
        return $true
    } catch {
        # If connection is refused, the port is available
        return $true
    } finally {
        if ($tcpClient -ne $null) { $tcpClient.Dispose() }
    }
}

Write-HostGreen "🚀 Starting AI Product Discovery Suite Backend Services..."
Write-Host ""

# --- 1. Check and Start Docker Desktop ---
Write-HostYellow "🔍 Checking Docker Desktop status..."
try {
    $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
    if (-not $dockerProcess) {
        Write-HostYellow "Docker Desktop is not running. Attempting to start it..."
        Start-Process "Docker Desktop"
        $i = 0
        while ($i -lt 30) { # Wait up to 300 seconds (5 minutes)
            Write-HostYellow ("Waiting for Docker Desktop to start (" + ($i*10) + "s / 300s)...")
            Start-Sleep -Seconds 10
            $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
            if ($dockerProcess) {
                Write-HostGreen "✅ Docker Desktop is running."
                break
            }
            $i++
        }
        if (-not $dockerProcess) {
            Write-HostRed "❌ Failed to start Docker Desktop. Please start it manually and rerun the script."
            exit 1
        }
    } else {
        Write-HostGreen "✅ Docker Desktop is already running."
    }
} catch {
    Write-HostRed "❌ An error occurred while checking/starting Docker Desktop: $($_.Exception.Message)"
    exit 1
}

# --- 2. Verify .env file existence ---
Write-HostYellow "🔍 Checking for .env file..."
$envFile = Join-Path (Get-Location) ".env"
if (-not (Test-Path $envFile)) {
    Write-HostRed "❌ .env file not found in the root directory. Please create it with the necessary environment variables."
    Write-HostRed "   Refer to LOCAL_SETUP_GUIDE.md for details on required variables."
    exit 1
}
Write-HostGreen "✅ .env file found."

# --- 3. Check for Port Availability ---
Write-HostYellow "🔍 Checking for port availability..."
$portsToCheck = @(7001, 7002, 7004, 7005, 7010, 7011, 9200, 8065)
foreach ($port in $portsToCheck) {
    if (-not (Test-PortAvailability $port)) {
        Write-HostRed "Stopping script due to port conflict."
        exit 1
    }
    Write-HostGreen "✅ Port $port is available."
}
Write-HostGreen "All required ports are available."

# --- 4. Start Docker Compose Services ---
Write-HostYellow "🐳 Starting Docker Compose services..."
try {
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-HostRed "❌ Docker Compose failed to start services. Check logs for details."
        Write-HostRed "   Run 'docker-compose logs' for more information."
        exit 1
    }
    Write-HostGreen "✅ Docker Compose services started in detached mode."
} catch {
    Write-HostRed "❌ An error occurred during docker-compose up -d: $($_.Exception.Message)"
    exit 1
}

# --- 5. Monitor Container Health ---
Write-HostYellow "💖 Monitoring container health. This might take a few minutes..."
$services = @("ai_discovery_postgres", "ai_discovery_redis", "ai_discovery_elasticsearch", "ai_discovery_weaviate", "ai_discovery_search", "ai_discovery_recommendation", "ai_discovery_analytics", "ai_discovery_assistant")
$timeoutSeconds = 300 # 5 minutes
$startTime = Get-Date

foreach ($service in $services) {
    Write-HostYellow "Waiting for service '$service' to be healthy..."
    $i = 0
    $isHealthy = $false
    while ($isHealthy -eq $false -and ((Get-Date) - $startTime).TotalSeconds -lt $timeoutSeconds) {
        $status = (docker inspect --format='{{.State.Health.Status}}' $service 2>$null).Trim()
        if ($status -eq "healthy") {
            Write-HostGreen "✅ Service '$service' is healthy."
            $isHealthy = $true
            break
        }
        if ($i % 6 -eq 0) { # Print every 30 seconds
            Write-HostYellow ("Still waiting for '$service' to be healthy (" + (((Get-Date) - $startTime).TotalSeconds -as [int]) + "s / " + $timeoutSeconds + "s)... Status: " + $status)
        }
        Start-Sleep -Seconds 5
        $i++
    }
    if (-not $isHealthy) {
        Write-HostRed "❌ Service '$service' did not become healthy within the timeout ($timeoutSeconds s)."
        Write-HostRed "   Please check logs for service '$service' using: docker-compose logs $service"
        exit 1
    }
}
Write-HostGreen "✅ All core services are healthy."

# --- 6. Display Service URLs ---
Write-Host ""
Write-HostGreen "🎉 AI Product Discovery Suite Backend Services are running!"
Write-HostGreen "Access them at the following URLs:"
Write-HostYellow "  - Search Service API (Swagger UI): http://localhost:7001/docs"
Write-HostYellow "  - Recommendation Service API (Swagger UI): http://localhost:7002/docs"
Write-HostYellow "  - Analytics Service API (Swagger UI): http://localhost:7004/docs"
Write-HostYellow "  - Shopping Assistant API (Swagger UI): http://localhost:7005/docs"
Write-HostYellow "  - PostgreSQL (External Port): localhost:7010"
Write-HostYellow "  - Redis (External Port): localhost:7011"
Write-HostYellow "  - Elasticsearch (External Port): http://localhost:9200"
Write-HostYellow "  - Weaviate (External Port): http://localhost:8065/v1/meta"
Write-Host ""

# --- 7. Next Steps ---
Write-HostYellow "Next Steps:"
Write-HostGreen "1. Run the quick verification script: python scripts/quick_verify.py"
Write-HostGreen "2. Load dummy data (if not already loaded): python scripts/init_dummy_data.py"
Write-HostGreen "3. Explore the API documentation (Swagger UI) at the links above."
Write-HostGreen "4. For detailed guidance, refer to LOCAL_SETUP_GUIDE.md."

# Open Swagger UI for Search Service (optional)
# Start-Process "http://localhost:7001/docs"

Write-Host ""
Write-HostGreen "Script finished."
