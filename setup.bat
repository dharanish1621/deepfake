@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================================
echo   Deepfake Video Forensics - Auto Installer & Runner
echo ==========================================================
echo.

:: 1. Check if Python is already accessible in PATH
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    goto :RUN_QUICKSTART
)

:: 2. Check standard Python installation directories
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;!PATH!"
    goto :RUN_QUICKSTART
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PATH=%LocalAppData%\Programs\Python\Python312;%LocalAppData%\Programs\Python\Python312\Scripts;!PATH!"
    goto :RUN_QUICKSTART
)
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
    set "PATH=%LocalAppData%\Programs\Python\Python313;%LocalAppData%\Programs\Python\Python313\Scripts;!PATH!"
    goto :RUN_QUICKSTART
)
if exist "C:\Python311\python.exe" (
    set "PATH=C:\Python311;C:\Python311\Scripts;!PATH!"
    goto :RUN_QUICKSTART
)

:: 3. Python is missing. Automatically install Python 3.11
echo [*] Python not detected. Installing Python 3.11 automatically...
where winget >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [*] Installing Python via Windows Package Manager (winget)...
    winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
) else (
    echo [*] Downloading official Python 3.11 installer via PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '$env:TEMP\python_installer.exe'"
    echo [*] Installing Python silently...
    start /wait "" "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 SimpleInstall=1 Include_pip=1 Include_test=0
    del "%TEMP%\python_installer.exe" 2>nul
)

:: Refresh PATH for new install
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;!PATH!"
    goto :RUN_QUICKSTART
)

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python installation finished, but python is not yet in the active session PATH.
    echo Please reopen your terminal/VS Code and run setup.bat again.
    pause
    exit /b 1
)

:RUN_QUICKSTART
python quickstart.py %*
exit /b %ERRORLEVEL%
