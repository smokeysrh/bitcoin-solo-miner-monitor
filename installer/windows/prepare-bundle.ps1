# ============================================================================
# Bitcoin Solo Miner Monitor - Python Bundle Preparation Script
# ============================================================================
# This script downloads and prepares a complete Python runtime bundle with
# all dependencies for offline installation.
#
# Usage: .\prepare-bundle.ps1 [-PythonVersion "3.11.7"] [-Force] [-Verify]
#
# Requirements:
# - Internet connection (for initial download)
# - PowerShell 5.1 or later
# - At least 500MB free disk space
# ============================================================================

param(
    [string]$PythonVersion = "3.11.7",
    [switch]$Force,
    [switch]$Verify
)

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Faster downloads

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BundleDir = Join-Path $ScriptDir "bundle"
$PythonDir = Join-Path $BundleDir "python"
$TempDir = Join-Path $BundleDir "temp"

# Python download URLs
$PythonVersionShort = $PythonVersion -replace '\.', ''
$PythonVersionShort = $PythonVersionShort.Substring(0, [Math]::Min(4, $PythonVersionShort.Length))
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    switch ($Type) {
        "Success" { Write-Host "[$timestamp] [OK] $Message" -ForegroundColor Green }
        "Error"   { Write-Host "[$timestamp] [ERROR] $Message" -ForegroundColor Red }
        "Warning" { Write-Host "[$timestamp] [WARN] $Message" -ForegroundColor Yellow }
        default   { Write-Host "[$timestamp] [INFO] $Message" -ForegroundColor Cyan }
    }
}

function Test-InternetConnection {
    Write-Status "Checking internet connectivity..."
    try {
        $null = Test-Connection -ComputerName "www.python.org" -Count 1 -Quiet
        Write-Status "Internet connection verified" "Success"
        return $true
    }
    catch {
        Write-Status "No internet connection detected" "Error"
        return $false
    }
}

function Get-FileWithProgress {
    param(
        [string]$Url,
        [string]$OutputPath,
        [string]$Description
    )
    
    Write-Status "Downloading $Description..."
    Write-Status "URL: $Url"
    
    try {
        # Use Invoke-WebRequest with progress
        $ProgressPreference = "Continue"
        Invoke-WebRequest -Uri $Url -OutFile $OutputPath -UseBasicParsing
        $ProgressPreference = "SilentlyContinue"
        
        Write-Status "Downloaded successfully: $OutputPath" "Success"
        return $true
    }
    catch {
        Write-Status "Download failed: $_" "Error"
        return $false
    }
}

function Expand-ZipFile {
    param(
        [string]$ZipPath,
        [string]$DestinationPath,
        [string]$Description
    )
    
    Write-Status "Extracting $Description..."
    
    try {
        # Create destination directory if it doesn't exist
        if (-not (Test-Path $DestinationPath)) {
            New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
        }
        
        # Extract using .NET
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $DestinationPath)
        
        Write-Status "Extraction completed successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Extraction failed: $_" "Error"
        return $false
    }
}

function Install-Pip {
    param([string]$PythonExe)
    
    Write-Status "Installing pip into embedded Python..."
    
    try {
        # Download get-pip.py
        $getPipPath = Join-Path $TempDir "get-pip.py"
        if (-not (Get-FileWithProgress -Url $GetPipUrl -OutputPath $getPipPath -Description "get-pip.py")) {
            throw "Failed to download get-pip.py"
        }
        
        # Run get-pip.py
        Write-Status "Running pip installer (this may show warnings about PATH, which are normal)..."
        Start-Process -FilePath $PythonExe -ArgumentList $getPipPath -Wait -NoNewWindow
        
        # Give it a moment to complete file operations
        Start-Sleep -Seconds 1
        
        # Check if pip was actually installed
        $pythonRoot = Split-Path -Parent $PythonExe
        $pipExe = Join-Path $pythonRoot "Scripts\pip.exe"
        
        if (-not (Test-Path $pipExe)) {
            throw "Pip executable not found after installation at: $pipExe"
        }
        
        Write-Status "Pip installed successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Pip installation failed: $_" "Error"
        return $false
    }
}

function Install-Dependencies {
    param(
        [string]$PythonExe,
        [string]$RequirementsPath
    )
    
    Write-Status "Installing dependencies from requirements.txt..."
    
    try {
        # Find pip in Scripts directory
        $pythonRoot = Split-Path -Parent $PythonExe
        $pipExe = Join-Path $pythonRoot "Scripts\pip.exe"
        
        if (-not (Test-Path $pipExe)) {
            throw "Pip executable not found at: $pipExe"
        }
        
        Write-Status "Using pip: $pipExe"
        Write-Status "Requirements file: $RequirementsPath"
        
        # Install dependencies with progress
        Write-Status "This may take several minutes..."
        $installOutput = & $pipExe install -r $RequirementsPath --no-warn-script-location 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Status "Dependency installation output:" "Warning"
            $installOutput | ForEach-Object { Write-Host "  $_" }
            throw "Dependency installation failed with exit code $LASTEXITCODE"
        }
        
        # Show summary
        $installedPackages = $installOutput | Select-String "Successfully installed" | Select-Object -Last 1
        if ($installedPackages) {
            Write-Status "$installedPackages" "Success"
        }
        
        Write-Status "All dependencies installed successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Dependency installation failed: $_" "Error"
        return $false
    }
}

function Set-PythonPath {
    param([string]$PythonDir)
    
    Write-Status "Configuring Python path file..."
    
    try {
        # Find the actual ._pth file (python311._pth for Python 3.11)
        $pthFiles = Get-ChildItem -Path $PythonDir -Filter "python*._pth"
        
        if ($pthFiles.Count -eq 0) {
            throw "No ._pth file found in $PythonDir"
        }
        
        $pthFile = $pthFiles[0].FullName
        Write-Status "Found path file: $pthFile"
        
        # Create path configuration for embedded Python
        # This enables site-packages and pip
        $pathContent = @"
python311.zip
.
Lib
Lib/site-packages

# Enable site module for pip support
import site
"@
        
        Set-Content -Path $pthFile -Value $pathContent -Encoding ASCII
        Write-Status "Python path configured successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Path configuration failed: $_" "Error"
        return $false
    }
}

function Test-PythonBundle {
    param([string]$PythonExe)
    
    Write-Status "Verifying Python bundle..."
    
    try {
        # Test 1: Python version
        Write-Status "Testing Python execution..."
        $versionOutput = & $PythonExe --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python execution failed"
        }
        Write-Status "Python version: $versionOutput" "Success"
        
        # Test 2: Import core dependencies
        Write-Status "Testing dependency imports..."
        $testScript = @"
import sys
try:
    import fastapi
    import uvicorn
    import aiohttp
    import aiosqlite
    import jwt
    import pydantic
    import bcrypt
    import psutil
    import bs4
    import aiosmtplib
    import jinja2
    import websockets
    print('All core dependencies imported successfully')
    sys.exit(0)
except ImportError as e:
    print(f'Import failed: {e}')
    sys.exit(1)
"@
        
        $testScriptPath = Join-Path $TempDir "test_imports.py"
        Set-Content -Path $testScriptPath -Value $testScript -Encoding UTF8
        
        $importOutput = & $PythonExe $testScriptPath 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Status "Import test output:" "Warning"
            $importOutput | ForEach-Object { Write-Host "  $_" }
            throw "Dependency import test failed"
        }
        
        Write-Status "$importOutput" "Success"
        
        # Test 3: List installed packages
        Write-Status "Listing installed packages..."
        $pythonRoot = Split-Path -Parent $PythonExe
        $pipExe = Join-Path $pythonRoot "Scripts\pip.exe"
        
        if (Test-Path $pipExe) {
            $packagesOutput = & $pipExe list --format=columns 2>&1
            Write-Host ""
            Write-Host "Installed packages:" -ForegroundColor Cyan
            $packagesOutput | ForEach-Object { Write-Host "  $_" }
            Write-Host ""
        }
        
        Write-Status "Bundle verification completed successfully" "Success"
        return $true
    }
    catch {
        Write-Status "Bundle verification failed: $_" "Error"
        return $false
    }
}

function Get-DirectorySize {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        return 0
    }
    
    $size = (Get-ChildItem -Path $Path -Recurse -File | Measure-Object -Property Length -Sum).Sum
    return [Math]::Round($size / 1MB, 2)
}

# ============================================================================
# Main Script
# ============================================================================

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Bitcoin Solo Miner Monitor - Python Bundle Preparation" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if bundle already exists
if ((Test-Path $PythonDir) -and -not $Force) {
    Write-Status "Python bundle already exists at: $PythonDir" "Warning"
    Write-Status "Use -Force to rebuild the bundle" "Warning"
    
    if ($Verify) {
        $pythonExe = Join-Path $PythonDir "python.exe"
        if (Test-Path $pythonExe) {
            Test-PythonBundle -PythonExe $pythonExe
        }
    }
    
    exit 0
}

# Check internet connection
if (-not (Test-InternetConnection)) {
    Write-Status "Internet connection required for bundle preparation" "Error"
    exit 1
}

# Create directories
Write-Status "Creating bundle directories..."
if (Test-Path $BundleDir) {
    if ($Force) {
        Write-Status "Removing existing bundle..." "Warning"
        Remove-Item -Path $BundleDir -Recurse -Force
    }
}

New-Item -ItemType Directory -Path $BundleDir -Force | Out-Null
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
Write-Status "Directories created" "Success"

# Download Python
$pythonZip = Join-Path $TempDir "python-$PythonVersion-embed-amd64.zip"
if (-not (Get-FileWithProgress -Url $PythonUrl -OutputPath $pythonZip -Description "Python $PythonVersion embeddable package")) {
    Write-Status "Failed to download Python" "Error"
    exit 1
}

# Extract Python
if (-not (Expand-ZipFile -ZipPath $pythonZip -DestinationPath $PythonDir -Description "Python runtime")) {
    Write-Status "Failed to extract Python" "Error"
    exit 1
}

# Verify Python executable
$pythonExe = Join-Path $PythonDir "python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Status "Python executable not found after extraction: $pythonExe" "Error"
    exit 1
}
Write-Status "Python executable verified: $pythonExe" "Success"

# Configure Python path
if (-not (Set-PythonPath -PythonDir $PythonDir)) {
    Write-Status "Failed to configure Python path" "Error"
    exit 1
}

# Install pip
if (-not (Install-Pip -PythonExe $pythonExe)) {
    Write-Status "Failed to install pip" "Error"
    exit 1
}

# Install dependencies
$requirementsPath = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "requirements.txt"
if (-not (Test-Path $requirementsPath)) {
    Write-Status "Requirements file not found: $requirementsPath" "Error"
    exit 1
}

if (-not (Install-Dependencies -PythonExe $pythonExe -RequirementsPath $requirementsPath)) {
    Write-Status "Failed to install dependencies" "Error"
    exit 1
}

# Verify bundle
if (-not (Test-PythonBundle -PythonExe $pythonExe)) {
    Write-Status "Bundle verification failed" "Error"
    exit 1
}

# Cleanup temp directory
Write-Status "Cleaning up temporary files..."
Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue

# Show summary
$bundleSize = Get-DirectorySize -Path $PythonDir
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Green
Write-Host "  Bundle Preparation Complete!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Bundle location: $PythonDir" -ForegroundColor Cyan
Write-Host "  Bundle size: $bundleSize MB" -ForegroundColor Cyan
Write-Host "  Python version: $PythonVersion" -ForegroundColor Cyan
Write-Host ""
Write-Host "  The bundle is ready to be used in installer builds." -ForegroundColor Green
Write-Host "  Run .\build.ps1 to create the installer." -ForegroundColor Green
Write-Host ""

exit 0
