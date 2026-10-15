@echo off
cd /d "%~dp0"

echo ==========================================================
echo   Deepfake Video Forensics - Quick Setup & Run
echo ==========================================================
echo.

:: Prefer python quickstart.py if python is available
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python quickstart.py %*
    exit /b %ERRORLEVEL%
)

:: Fallback to Node.js setup if python is not in system PATH
where node >nul 2>nul
if %ERRORLEVEL% equ 0 (
    node setup.js
    exit /b %ERRORLEVEL%
)

echo [ERROR] Neither Python (3.10+) nor Node.js was found on your system PATH!
echo Please install Python 3.10+ from: https://www.python.org/downloads/
echo.
pause
exit /b 1
