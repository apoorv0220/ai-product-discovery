@echo off

:: AI Product Discovery Suite - Local Startup Script (Batch Wrapper)
:: This script is a simple wrapper to run the PowerShell startup script.
:: It requires PowerShell 5.1 or higher.

SET "POWERSHELL_SCRIPT=%~dp0start-local.ps1"

IF NOT EXIST "%POWERSHELL_SCRIPT%" (
    echo ERROR: PowerShell script not found at %POWERSHELL_SCRIPT%
    GOTO :EOF
)

:: Execute the PowerShell script
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%POWERSHELL_SCRIPT%"

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell script exited with error code %ERRORLEVEL%.
) ELSE (
    echo PowerShell script completed successfully.
)
