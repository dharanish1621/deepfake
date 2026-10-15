@echo off
cd /d "%~dp0"

echo ==========================================================
echo   Deepfake Video Forensics - Auto Launcher
echo ==========================================================

:: Prefer Python quickstart.py
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python quickstart.py %*
    exit /b %ERRORLEVEL%
)

:: Fallback to Node.js
where node >nul 2>nul
if %ERRORLEVEL% equ 0 (
    node run.js
    exit /b %ERRORLEVEL%
)

echo [ERROR] Neither Python (3.10+) nor Node.js was found on your system PATH!
echo Please install Python 3.10+ from: https://www.python.org/downloads/
pause
exit /b 1

