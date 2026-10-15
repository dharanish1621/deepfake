# setup.ps1 - Automated Setup & Launcher for PowerShell
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "`n==========================================================" -ForegroundColor Magenta
Write-Host "  🛡️  Deepfake Video Forensics - Auto Installer & Runner" -ForegroundColor Magenta
Write-Host "==========================================================" -ForegroundColor Magenta

# 1. Detect Python command
$pyCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pyCmd = "python3"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pyCmd = "py"
}

# 2. Check standard Windows installation paths if not in active PATH
if (-not $pyCmd) {
    $candidatePaths = @(
        "$env:LocalAppData\Programs\Python\Python313\python.exe",
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:LocalAppData\Programs\Python\Python311\python.exe",
        "C:\Python311\python.exe"
    )
    foreach ($p in $candidatePaths) {
        if (Test-Path -LiteralPath $p) {
            $dir = Split-Path -LiteralPath $p
            $env:Path = "$dir;$dir\Scripts;$env:Path"
            $pyCmd = $p
            break
        }
    }
}

# 3. If Python is still missing, auto-install Python 3.11
if (-not $pyCmd) {
    Write-Host "[*] Python not detected. Installing Python 3.11 automatically..." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "[*] Installing Python via Windows Package Manager (winget)..." -ForegroundColor Cyan
        winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    } else {
        $installer = "$env:TEMP\python_installer.exe"
        Write-Host "[*] Downloading official Python 3.11 installer..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $installer
        Write-Host "[*] Installing Python silently..." -ForegroundColor Cyan
        Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 SimpleInstall=1 Include_pip=1 Include_test=0" -Wait
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    }

    $installedPy = "$env:LocalAppData\Programs\Python\Python311\python.exe"
    if (Test-Path -LiteralPath $installedPy) {
        $env:Path = "$env:LocalAppData\Programs\Python\Python311;$env:LocalAppData\Programs\Python\Python311\Scripts;$env:Path"
        $pyCmd = $installedPy
    } else {
        $pyCmd = "python"
    }
}

# 4. Delegate to quickstart.py
Write-Host "[*] Launching Quickstart Pipeline..." -ForegroundColor Green
& $pyCmd quickstart.py @ScriptArgs
