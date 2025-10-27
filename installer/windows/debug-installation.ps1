# ============================================================================
# Debug Installation Script
# ============================================================================
# This script helps debug issues with the installed application
# ============================================================================

param(
    [string]$InstallDir = "$env:ProgramFiles\Bitcoin Solo Miner Monitor"
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Bitcoin Solo Miner Monitor - Installation Debugger" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if installation directory exists
Write-Host "1. Checking installation directory..." -ForegroundColor Yellow
if (Test-Path $InstallDir) {
    Write-Host "   [OK] Installation directory found: $InstallDir" -ForegroundColor Green
} else {
    Write-Host "   [ERROR] Installation directory not found: $InstallDir" -ForegroundColor Red
    Write-Host "   Please provide the correct path using -InstallDir parameter" -ForegroundColor Yellow
    exit 1
}

# Check critical files
Write-Host ""
Write-Host "2. Checking critical files..." -ForegroundColor Yellow

$criticalFiles = @(
    "BitcoinSoloMinerMonitor.bat",
    "run.py",
    "python\python.exe",
    "src\main.py",
    "src\backend\version.py"
)

$allFilesExist = $true
foreach ($file in $criticalFiles) {
    $fullPath = Join-Path $InstallDir $file
    if (Test-Path $fullPath) {
        Write-Host "   [OK] $file" -ForegroundColor Green
    } else {
        Write-Host "   [ERROR] Missing: $file" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host ""
    Write-Host "   [ERROR] Some critical files are missing!" -ForegroundColor Red
    Write-Host "   The installation may be corrupted. Try reinstalling." -ForegroundColor Yellow
    exit 1
}

# Check Python runtime
Write-Host ""
Write-Host "3. Testing Python runtime..." -ForegroundColor Yellow
$pythonExe = Join-Path $InstallDir "python\python.exe"
try {
    $pythonVersion = & $pythonExe --version 2>&1
    Write-Host "   [OK] Python version: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   [ERROR] Python runtime failed to execute" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Red
    exit 1
}

# Check Python packages
Write-Host ""
Write-Host "4. Checking Python packages..." -ForegroundColor Yellow
try {
    $packages = & $pythonExe -m pip list 2>&1
    $requiredPackages = @("flask", "requests")
    
    foreach ($pkg in $requiredPackages) {
        if ($packages -match $pkg) {
            Write-Host "   [OK] $pkg installed" -ForegroundColor Green
        } else {
            Write-Host "   [WARNING] $pkg not found" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "   [WARNING] Could not check packages: $_" -ForegroundColor Yellow
}

# Test if port 8000 is available
Write-Host ""
Write-Host "5. Checking if port 8000 is available..." -ForegroundColor Yellow
$portInUse = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "   [WARNING] Port 8000 is already in use!" -ForegroundColor Yellow
    Write-Host "   Process using port:" -ForegroundColor Yellow
    $portInUse | ForEach-Object {
        $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "     - $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Yellow
        }
    }
    Write-Host "   You may need to stop this process before running the app" -ForegroundColor Yellow
} else {
    Write-Host "   [OK] Port 8000 is available" -ForegroundColor Green
}

# Check if app is currently running
Write-Host ""
Write-Host "6. Checking if application is running..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "   [INFO] Found Python processes:" -ForegroundColor Cyan
    $pythonProcesses | ForEach-Object {
        Write-Host "     - PID: $($_.Id), Path: $($_.Path)" -ForegroundColor Cyan
    }
} else {
    Write-Host "   [OK] No Python processes running" -ForegroundColor Green
}

# Try to manually start the application
Write-Host ""
Write-Host "7. Testing manual application start..." -ForegroundColor Yellow
Write-Host "   Attempting to start application manually..." -ForegroundColor Cyan

Push-Location $InstallDir

try {
    Write-Host "   Running: python\python.exe run.py" -ForegroundColor Cyan
    Write-Host "   (This will run for 10 seconds to test startup)" -ForegroundColor Cyan
    Write-Host ""
    
    # Start the process and capture output
    $process = Start-Process -FilePath "$InstallDir\python\python.exe" `
        -ArgumentList "run.py" `
        -WorkingDirectory $InstallDir `
        -PassThru `
        -RedirectStandardOutput "$env:TEMP\btc_miner_stdout.txt" `
        -RedirectStandardError "$env:TEMP\btc_miner_stderr.txt" `
        -NoNewWindow
    
    Write-Host "   [INFO] Process started with PID: $($process.Id)" -ForegroundColor Cyan
    Write-Host "   Waiting 10 seconds for startup..." -ForegroundColor Cyan
    
    Start-Sleep -Seconds 10
    
    # Check if process is still running
    if (-not $process.HasExited) {
        Write-Host "   [OK] Application is running!" -ForegroundColor Green
        
        # Try to connect to localhost:8000
        Write-Host "   Testing connection to http://localhost:8000..." -ForegroundColor Cyan
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000" -TimeoutSec 5 -UseBasicParsing
            Write-Host "   [OK] Successfully connected! Status: $($response.StatusCode)" -ForegroundColor Green
        } catch {
            Write-Host "   [ERROR] Could not connect to http://localhost:8000" -ForegroundColor Red
            Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
        }
        
        # Stop the process
        Write-Host "   Stopping test process..." -ForegroundColor Cyan
        Stop-Process -Id $process.Id -Force
        Write-Host "   [OK] Test process stopped" -ForegroundColor Green
    } else {
        Write-Host "   [ERROR] Application exited unexpectedly!" -ForegroundColor Red
        Write-Host "   Exit code: $($process.ExitCode)" -ForegroundColor Red
    }
    
    # Show output
    Write-Host ""
    Write-Host "   === STDOUT ===" -ForegroundColor Cyan
    if (Test-Path "$env:TEMP\btc_miner_stdout.txt") {
        Get-Content "$env:TEMP\btc_miner_stdout.txt" | ForEach-Object { Write-Host "   $_" }
    } else {
        Write-Host "   (no output)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "   === STDERR ===" -ForegroundColor Cyan
    if (Test-Path "$env:TEMP\btc_miner_stderr.txt") {
        $stderr = Get-Content "$env:TEMP\btc_miner_stderr.txt"
        if ($stderr) {
            $stderr | ForEach-Object { Write-Host "   $_" -ForegroundColor Yellow }
        } else {
            Write-Host "   (no errors)" -ForegroundColor Gray
        }
    } else {
        Write-Host "   (no errors)" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "   [ERROR] Failed to start application" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Red
} finally {
    Pop-Location
}

# Check launcher batch file
Write-Host ""
Write-Host "8. Analyzing launcher batch file..." -ForegroundColor Yellow
$launcherPath = Join-Path $InstallDir "BitcoinSoloMinerMonitor.bat"
if (Test-Path $launcherPath) {
    Write-Host "   [OK] Launcher exists" -ForegroundColor Green
    Write-Host "   Content preview:" -ForegroundColor Cyan
    Get-Content $launcherPath | Select-Object -First 20 | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
} else {
    Write-Host "   [ERROR] Launcher not found!" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Debug Summary" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

if ($allFilesExist) {
    Write-Host "Installation appears to be complete." -ForegroundColor Green
    Write-Host ""
    Write-Host "If the application still doesn't work:" -ForegroundColor Yellow
    Write-Host "  1. Check the STDERR output above for errors" -ForegroundColor White
    Write-Host "  2. Check if port 8000 is blocked by firewall" -ForegroundColor White
    Write-Host "  3. Try running as administrator" -ForegroundColor White
    Write-Host "  4. Check Windows Event Viewer for errors" -ForegroundColor White
    Write-Host "  5. Review logs in: $InstallDir\logs" -ForegroundColor White
} else {
    Write-Host "Installation is incomplete or corrupted." -ForegroundColor Red
    Write-Host "Please reinstall the application." -ForegroundColor Yellow
}

Write-Host ""
