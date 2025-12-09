# PowerShell script to run personalization test with venv activated
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\activate"

Write-Host "Running personalization integration test..." -ForegroundColor Green
& python simple_personalization_test.py

Write-Host "Test completed." -ForegroundColor Cyan
