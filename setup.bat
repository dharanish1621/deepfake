@echo off
cd /d "%~dp0"

echo ==========================================================
echo   Deepfake Video Forensics - One-Click Setup
echo ==========================================================
echo.

:: Check Node.js
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not found on your system PATH!
    echo Please download and install Node.js (v18+) from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

:: Run one-line setup orchestrator
node setup.js
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Setup encountered an issue. See details above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
pause
