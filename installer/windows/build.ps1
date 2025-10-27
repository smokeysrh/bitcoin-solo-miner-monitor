# ============================================================================
# Bitcoin Solo Miner Monitor - Unified Build Script
# ============================================================================
# This script orchestrates the complete build process from source code to
# installer executable.
#
# Usage: .\build.ps1 [-Version "0.9.1"] [-SkipFrontend] [-OutputDir "path"] [-Verbose]
#
# Prerequisites:
# - NSIS installed and in PATH
# - Python bundle prepared (run prepare-bundle.ps1 first)
# - Node.js and npm installed (for frontend build)
#
# Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
# ============================================================================

param(
    [string]$Version = "",
    [switch]$SkipFrontend,
    [string]$OutputDir = "",
    [switch]$Verbose
)

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$BuildDir = Join-Path $RootDir "build\windows"
$StagingDir = Join-Path $BuildDir "staging"
$DistributionDir = if ($OutputDir) { $OutputDir } else { Join-Path $RootDir "distribution" }
$BundleDir = Join-Path $ScriptDir "bundle\python"
$InstallerScript = Join-Path $ScriptDir "installer.nsi"

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
        "Step"    { Write-Host "[$timestamp] [STEP] $Message" -ForegroundColor Magenta }
        default   { Write-Host "[$timestamp] [INFO] $Message" -ForegroundColor Cyan }
    }
}

function Write-StepHeader {
    param([string]$StepNumber, [string]$StepName)
    
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host "  Step $StepNumber : $StepName" -ForegroundColor Cyan
    Write-Host "============================================================================" -ForegroundColor Cyan
}

function Get-VersionFromFile {
    Write-Status "Reading version from src/backend/version.py..."
    
    $versionFile = Join-Path $RootDir "src\backend\version.py"
    
    if (-not (Test-Path $versionFile)) {
        Write-Status "Version file not found: $versionFile" "Error"
        Write-Status "Cannot determine application version" "Error"
        throw "Version file missing"
    }
    
    try {
        $content = Get-Content $versionFile -Raw
        
        # Extract version using regex: __version__ = "x.y.z"
        if ($content -match '__version__\s*=\s*"([^"]+)"') {
            $extractedVersion = $matches[1]
            Write-Status "Version extracted: $extractedVersion" "Success"
            return $extractedVersion
        }
        else {
            throw "Could not parse version from file"
        }
    }
    catch {
        Write-Status "Failed to extract version: $_" "Error"
        throw
    }
}

function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    $allGood = $true
    
    # Check NSIS
    Write-Status "Checking for NSIS installation..."
    $script:nsisPath = $null
    
    # First try to find in PATH
    try {
        $nsisCmd = Get-Command makensis -ErrorAction Stop
        $script:nsisPath = $nsisCmd.Source
        Write-Status "NSIS found in PATH: $($script:nsisPath)" "Success"
    }
    catch {
        # Not in PATH, check common installation locations
        Write-Status "NSIS not in PATH, checking common installation locations..." "Warning"
        
        $commonPaths = @(
            "C:\Program Files (x86)\NSIS\makensis.exe",
            "C:\Program Files\NSIS\makensis.exe"
        )
        
        foreach ($path in $commonPaths) {
            if (Test-Path $path) {
                $script:nsisPath = $path
                Write-Status "NSIS found: $path" "Success"
                break
            }
        }
        
        if (-not $script:nsisPath) {
            Write-Status "NSIS not found in PATH or common locations" "Error"
            Write-Status "Please install NSIS from https://nsis.sourceforge.io/" "Error"
            $allGood = $false
        }
    }
    
    # Check Python bundle
    Write-Status "Checking for Python bundle..."
    if (Test-Path $BundleDir) {
        $pythonExe = Join-Path $BundleDir "python.exe"
        if (Test-Path $pythonExe) {
            Write-Status "Python bundle found: $BundleDir" "Success"
        }
        else {
            Write-Status "Python bundle incomplete (python.exe not found)" "Error"
            Write-Status "Run prepare-bundle.ps1 to create the Python bundle" "Error"
            $allGood = $false
        }
    }
    else {
        Write-Status "Python bundle not found: $BundleDir" "Error"
        Write-Status "Run prepare-bundle.ps1 to create the Python bundle" "Error"
        $allGood = $false
    }
    
    # Check Node.js (if not skipping frontend)
    if (-not $SkipFrontend) {
        Write-Status "Checking for Node.js installation..."
        try {
            $nodePath = Get-Command node -ErrorAction Stop
            $nodeVersion = & node --version
            Write-Status "Node.js found: $nodeVersion" "Success"
        }
        catch {
            Write-Status "Node.js not found in PATH" "Error"
            Write-Status "Please install Node.js from https://nodejs.org/" "Error"
            Write-Status "Or use -SkipFrontend to skip frontend build" "Warning"
            $allGood = $false
        }
        
        # Check npm
        Write-Status "Checking for npm installation..."
        try {
            $npmPath = Get-Command npm -ErrorAction Stop
            $npmVersion = & npm --version
            Write-Status "npm found: v$npmVersion" "Success"
        }
        catch {
            Write-Status "npm not found in PATH" "Error"
            $allGood = $false
        }
    }
    
    # Check installer script exists
    Write-Status "Checking for installer script..."
    if (Test-Path $InstallerScript) {
        Write-Status "Installer script found: $InstallerScript" "Success"
    }
    else {
        Write-Status "Installer script not found: $InstallerScript" "Error"
        Write-Status "The installer.nsi file must exist before building" "Error"
        $allGood = $false
    }
    
    if (-not $allGood) {
        throw "Prerequisites check failed"
    }
    
    Write-Status "All prerequisites satisfied" "Success"
}

function Build-Frontend {
    Write-Status "Building frontend application..."
    
    $frontendDir = Join-Path $RootDir "src\frontend"
    
    if (-not (Test-Path $frontendDir)) {
        Write-Status "Frontend directory not found: $frontendDir" "Error"
        throw "Frontend directory missing"
    }
    
    Push-Location $frontendDir
    
    try {
        # Always install/update dependencies to ensure clean build
        Write-Status "Installing frontend dependencies..."
        Write-Status "Running: npm ci (clean install)"
        
        # Temporarily allow npm warnings (they write to stderr but aren't errors)
        $previousErrorAction = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        
        # Use npm ci for reproducible builds, fallback to npm install if no package-lock
        $packageLock = Join-Path $frontendDir "package-lock.json"
        if (Test-Path $packageLock) {
            $null = & npm ci 2>&1
        }
        else {
            Write-Status "No package-lock.json found, using npm install" "Warning"
            $null = & npm install 2>&1
        }
        
        if ($LASTEXITCODE -ne 0) {
            $ErrorActionPreference = $previousErrorAction
            throw "npm dependency installation failed with exit code $LASTEXITCODE"
        }
        Write-Status "Dependencies installed successfully" "Success"
        
        # Build frontend
        Write-Status "Running: npm run build"
        $null = & npm run build 2>&1
        
        $ErrorActionPreference = $previousErrorAction
        
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend build failed with exit code $LASTEXITCODE"
        }
        
        # Verify build output
        $distDir = Join-Path $frontendDir "dist"
        if (Test-Path $distDir) {
            $fileCount = (Get-ChildItem -Path $distDir -Recurse -File).Count
            Write-Status "Frontend build completed successfully ($fileCount files)" "Success"
        }
        else {
            throw "Frontend build output directory not found"
        }
    }
    catch {
        Write-Status "Frontend build failed: $_" "Error"
        throw
    }
    finally {
        Pop-Location
    }
}

function New-StagingDirectory {
    Write-Status "Creating staging directory..."
    
    # Clean up existing staging directory
    if (Test-Path $StagingDir) {
        Write-Status "Removing existing staging directory..."
        Remove-Item -Path $StagingDir -Recurse -Force
    }
    
    # Create fresh staging directory
    New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null
    Write-Status "Staging directory created: $StagingDir" "Success"
}

function Copy-ApplicationFiles {
    Write-Status "Copying application files to staging..."
    
    try {
        # Copy src directory (excluding node_modules)
        Write-Status "Copying src/..."
        $srcSource = Join-Path $RootDir "src"
        $srcDest = Join-Path $StagingDir "src"
        
        # Use robocopy to exclude node_modules and other unnecessary files
        $robocopyArgs = @(
            $srcSource,
            $srcDest,
            "/E",                    # Copy subdirectories including empty ones
            "/XD", "node_modules",   # Exclude node_modules directories
            "/XD", "__pycache__",    # Exclude Python cache
            "/XD", ".pytest_cache",  # Exclude pytest cache
            "/XF", "*.pyc",          # Exclude compiled Python files
            "/NFL", "/NDL", "/NJH", "/NJS", "/nc", "/ns", "/np"  # Minimal output
        )
        
        $robocopyResult = & robocopy @robocopyArgs
        
        # Robocopy exit codes: 0-7 are success, 8+ are errors
        if ($LASTEXITCODE -ge 8) {
            throw "Robocopy failed with exit code $LASTEXITCODE"
        }
        
        Write-Status "src/ copied successfully (excluding node_modules)" "Success"
        
        # Copy config directory
        Write-Status "Copying config/..."
        $configSource = Join-Path $RootDir "config"
        $configDest = Join-Path $StagingDir "config"
        if (Test-Path $configSource) {
            Copy-Item -Path $configSource -Destination $configDest -Recurse -Force
            Write-Status "config/ copied successfully" "Success"
        }
        else {
            Write-Status "config/ directory not found, skipping" "Warning"
        }
        
        # Copy Python bundle
        Write-Status "Copying Python bundle..."
        $pythonDest = Join-Path $StagingDir "python"
        Copy-Item -Path $BundleDir -Destination $pythonDest -Recurse -Force
        
        # Verify Python executable
        $pythonExe = Join-Path $pythonDest "python.exe"
        if (Test-Path $pythonExe) {
            Write-Status "Python bundle copied successfully" "Success"
        }
        else {
            throw "Python executable not found after copy"
        }
        
        # Copy run.py
        Write-Status "Copying run.py..."
        $runPySource = Join-Path $RootDir "run.py"
        $runPyDest = Join-Path $StagingDir "run.py"
        if (Test-Path $runPySource) {
            Copy-Item -Path $runPySource -Destination $runPyDest -Force
            Write-Status "run.py copied successfully" "Success"
        }
        else {
            Write-Status "run.py not found: $runPySource" "Error"
            throw "run.py missing"
        }
        
        # Copy requirements.txt
        Write-Status "Copying requirements.txt..."
        $reqSource = Join-Path $RootDir "requirements.txt"
        $reqDest = Join-Path $StagingDir "requirements.txt"
        if (Test-Path $reqSource) {
            Copy-Item -Path $reqSource -Destination $reqDest -Force
            Write-Status "requirements.txt copied successfully" "Success"
        }
        else {
            Write-Status "requirements.txt not found, skipping" "Warning"
        }
        
        # Copy README.md
        Write-Status "Copying README.md..."
        $readmeSource = Join-Path $RootDir "README.md"
        $readmeDest = Join-Path $StagingDir "README.md"
        if (Test-Path $readmeSource) {
            Copy-Item -Path $readmeSource -Destination $readmeDest -Force
            Write-Status "README.md copied successfully" "Success"
        }
        else {
            Write-Status "README.md not found, skipping" "Warning"
        }
        
        # Calculate staging directory size
        $stagingSize = (Get-ChildItem -Path $StagingDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
        $stagingSizeMB = [Math]::Round($stagingSize / 1MB, 2)
        Write-Status "Total staging size: $stagingSizeMB MB" "Success"
    }
    catch {
        Write-Status "File copying failed: $_" "Error"
        throw
    }
}

function Invoke-NSISBuild {
    param([string]$AppVersion)
    
    Write-Status "Building installer with NSIS..."
    Write-Status "Version: $AppVersion"
    Write-Status "Installer script: $InstallerScript"
    
    try {
        # Build NSIS command
        $nsisArgs = @(
            "/DVERSION=$AppVersion",
            "/DAPP_DIR=$StagingDir",
            $InstallerScript
        )
        
        if ($Verbose) {
            $nsisArgs += "/V4"  # Verbose output
        }
        
        Write-Status "Running: $script:nsisPath $($nsisArgs -join ' ')"
        
        # Run NSIS using the path we found in prerequisites
        $nsisOutput = & $script:nsisPath $nsisArgs 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Status "NSIS output:" "Error"
            $nsisOutput | ForEach-Object { Write-Host "  $_" }
            throw "NSIS build failed with exit code $LASTEXITCODE"
        }
        
        if ($Verbose) {
            Write-Status "NSIS output:" "Info"
            $nsisOutput | ForEach-Object { Write-Host "  $_" }
        }
        
        Write-Status "NSIS build completed successfully" "Success"
    }
    catch {
        Write-Status "NSIS build failed: $_" "Error"
        throw
    }
}

function New-SHA256Checksum {
    param(
        [string]$FilePath,
        [string]$OutputPath
    )
    
    Write-Status "Generating SHA256 checksum..."
    
    try {
        $hash = Get-FileHash -Path $FilePath -Algorithm SHA256
        $hashString = $hash.Hash.ToLower()
        $fileName = Split-Path -Leaf $FilePath
        
        # Create checksum file content
        $checksumContent = "$hashString  $fileName"
        Set-Content -Path $OutputPath -Value $checksumContent -Encoding ASCII
        
        Write-Status "SHA256: $hashString" "Success"
        Write-Status "Checksum saved to: $OutputPath" "Success"
        
        return $hashString
    }
    catch {
        Write-Status "Checksum generation failed: $_" "Error"
        throw
    }
}

function Move-InstallerToDistribution {
    param([string]$AppVersion)
    
    Write-Status "Moving installer to distribution directory..."
    
    try {
        # Create distribution directory if it doesn't exist
        if (-not (Test-Path $DistributionDir)) {
            New-Item -ItemType Directory -Path $DistributionDir -Force | Out-Null
            Write-Status "Created distribution directory: $DistributionDir" "Success"
        }
        
        # Expected installer output from NSIS (in installer/windows directory)
        $installerName = "BitcoinSoloMinerMonitor-$AppVersion-Setup.exe"
        $installerSource = Join-Path $ScriptDir $installerName
        $installerDest = Join-Path $DistributionDir $installerName
        
        # Check if installer was created
        if (-not (Test-Path $installerSource)) {
            Write-Status "Installer not found at expected location: $installerSource" "Error"
            Write-Status "Checking for any .exe files in installer directory..." "Warning"
            
            $exeFiles = Get-ChildItem -Path $ScriptDir -Filter "*.exe" | Where-Object { $_.Name -like "*Setup.exe" }
            if ($exeFiles) {
                Write-Status "Found installer files:" "Info"
                $exeFiles | ForEach-Object { Write-Status "  $($_.Name)" "Info" }
                $installerSource = $exeFiles[0].FullName
                Write-Status "Using: $installerSource" "Warning"
            }
            else {
                throw "Installer executable not found"
            }
        }
        
        # Move installer to distribution
        Write-Status "Moving: $installerSource"
        Write-Status "To: $installerDest"
        Move-Item -Path $installerSource -Destination $installerDest -Force
        Write-Status "Installer moved successfully" "Success"
        
        # Generate checksum
        $checksumPath = "$installerDest.sha256"
        $checksum = New-SHA256Checksum -FilePath $installerDest -OutputPath $checksumPath
        
        # Get installer size
        $installerSize = (Get-Item $installerDest).Length
        $installerSizeMB = [Math]::Round($installerSize / 1MB, 2)
        
        Write-Status "Installer size: $installerSizeMB MB" "Success"
        
        return @{
            Path = $installerDest
            Checksum = $checksum
            Size = $installerSizeMB
        }
    }
    catch {
        Write-Status "Failed to move installer: $_" "Error"
        throw
    }
}

function Remove-StagingDirectory {
    Write-Status "Cleaning up staging directory..."
    
    try {
        if (Test-Path $StagingDir) {
            Remove-Item -Path $StagingDir -Recurse -Force
            Write-Status "Staging directory removed" "Success"
        }
    }
    catch {
        Write-Status "Failed to remove staging directory: $_" "Warning"
        Write-Status "You may need to manually delete: $StagingDir" "Warning"
    }
}

# ============================================================================
# Main Build Process
# ============================================================================

$buildStartTime = Get-Date

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Bitcoin Solo Miner Monitor - Unified Build Script" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

try {
    # Step 1: Check Prerequisites
    Write-StepHeader "1" "Checking Prerequisites"
    Test-Prerequisites
    
    # Step 2: Extract Version
    Write-StepHeader "2" "Extracting Version"
    $appVersion = if ($Version) {
        Write-Status "Using provided version: $Version" "Info"
        $Version
    } else {
        Get-VersionFromFile
    }
    
    # Step 3: Build Frontend (if not skipped)
    if (-not $SkipFrontend) {
        Write-StepHeader "3" "Building Frontend"
        Build-Frontend
    }
    else {
        Write-StepHeader "3" "Building Frontend (SKIPPED)"
        Write-Status "Frontend build skipped by user" "Warning"
    }
    
    # Step 4: Create Staging Directory
    Write-StepHeader "4" "Creating Staging Directory"
    New-StagingDirectory
    
    # Step 5: Copy Files
    Write-StepHeader "5" "Copying Application Files"
    Copy-ApplicationFiles
    
    # Step 6: Build Installer with NSIS
    Write-StepHeader "6" "Building Installer with NSIS"
    Invoke-NSISBuild -AppVersion $appVersion
    
    # Step 7: Generate Checksum and Move to Distribution
    Write-StepHeader "7" "Finalizing Installer"
    $installerInfo = Move-InstallerToDistribution -AppVersion $appVersion
    
    # Step 8: Cleanup
    Write-StepHeader "8" "Cleaning Up"
    Remove-StagingDirectory
    
    # Calculate build time
    $buildEndTime = Get-Date
    $buildDuration = ($buildEndTime - $buildStartTime).TotalSeconds
    
    # Success summary
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Green
    Write-Host "  Build Completed Successfully!" -ForegroundColor Green
    Write-Host "============================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Version: $appVersion" -ForegroundColor Cyan
    Write-Host "  Installer: $($installerInfo.Path)" -ForegroundColor Cyan
    Write-Host "  Size: $($installerInfo.Size) MB" -ForegroundColor Cyan
    Write-Host "  SHA256: $($installerInfo.Checksum)" -ForegroundColor Cyan
    Write-Host "  Build time: $([Math]::Round($buildDuration, 1)) seconds" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  The installer is ready for distribution!" -ForegroundColor Green
    Write-Host ""
    
    exit 0
}
catch {
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Red
    Write-Host "  Build Failed!" -ForegroundColor Red
    Write-Host "============================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Status "Error: $_" "Error"
    Write-Host ""
    Write-Host "  Please fix the errors above and try again." -ForegroundColor Yellow
    Write-Host ""
    
    # Cleanup on failure
    if (Test-Path $StagingDir) {
        Write-Status "Cleaning up staging directory..." "Info"
        Remove-Item -Path $StagingDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    exit 1
}
