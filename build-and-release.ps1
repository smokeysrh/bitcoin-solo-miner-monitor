# Bitcoin Solo Miner Monitor - Build and Release Script
# Version: 0.9.1

Write-Host "=== Bitcoin Solo Miner Monitor - Build and Release ===" -ForegroundColor Cyan
Write-Host ""

# Check if NSIS is installed
Write-Host "[1/5] Checking for NSIS..." -ForegroundColor Yellow
$nsisPath = Get-Command makensis -ErrorAction SilentlyContinue

if (-not $nsisPath) {
    Write-Host "❌ NSIS not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install NSIS:" -ForegroundColor Yellow
    Write-Host "1. Download from: https://nsis.sourceforge.io/Download" -ForegroundColor White
    Write-Host "2. Run the installer" -ForegroundColor White
    Write-Host "3. Make sure to check 'Add NSIS to PATH'" -ForegroundColor White
    Write-Host "4. Restart PowerShell and run this script again" -ForegroundColor White
    Write-Host ""
    
    $download = Read-Host "Would you like to open the download page? (Y/N)"
    if ($download -eq "Y" -or $download -eq "y") {
        Start-Process "https://nsis.sourceforge.io/Download"
    }
    
    exit 1
}

Write-Host "✅ NSIS found at: $($nsisPath.Source)" -ForegroundColor Green
Write-Host ""

# Check version in installer script
Write-Host "[2/5] Checking version in installer script..." -ForegroundColor Yellow
$installerScript = "installer\windows\installer_enhanced.nsi"

if (Test-Path $installerScript) {
    $content = Get-Content $installerScript
    $versionLine = $content | Select-String '!define VERSION'
    
    Write-Host "Current version line: $versionLine" -ForegroundColor White
    
    if ($versionLine -match '"0\.1\.0"') {
        Write-Host "⚠️  Version is still 0.1.0" -ForegroundColor Yellow
        $update = Read-Host "Update to 0.9.1? (Y/N)"
        
        if ($update -eq "Y" -or $update -eq "y") {
            $content = $content -replace '!define VERSION "0\.1\.0"', '!define VERSION "0.9.1"'
            $content | Set-Content $installerScript
            Write-Host "✅ Version updated to 0.9.1" -ForegroundColor Green
        }
    } else {
        Write-Host "✅ Version looks good" -ForegroundColor Green
    }
} else {
    Write-Host "❌ Installer script not found: $installerScript" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Build frontend
Write-Host "[3/5] Building frontend..." -ForegroundColor Yellow
Push-Location "src\frontend"

if (Test-Path "package.json") {
    Write-Host "Installing dependencies..." -ForegroundColor White
    npm install
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install frontend dependencies" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    
    Write-Host "Building frontend..." -ForegroundColor White
    npm run build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to build frontend" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    
    Write-Host "✅ Frontend built successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  No package.json found, skipping frontend build" -ForegroundColor Yellow
}

Pop-Location
Write-Host ""

# Build installer
Write-Host "[4/5] Building Windows installer..." -ForegroundColor Yellow
Push-Location "installer\windows"

Write-Host "Running NSIS..." -ForegroundColor White
makensis installer_enhanced.nsi

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to build installer" -ForegroundColor Red
    Pop-Location
    exit 1
}

Pop-Location
Write-Host "✅ Installer built successfully" -ForegroundColor Green
Write-Host ""

# Check output
Write-Host "[5/5] Checking output..." -ForegroundColor Yellow

$installerPath = "distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe"

if (Test-Path $installerPath) {
    $fileInfo = Get-Item $installerPath
    $fileSizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
    
    Write-Host "✅ Installer created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📦 Installer Details:" -ForegroundColor Cyan
    Write-Host "   Location: $installerPath" -ForegroundColor White
    Write-Host "   Size: $fileSizeMB MB" -ForegroundColor White
    Write-Host "   Created: $($fileInfo.LastWriteTime)" -ForegroundColor White
    Write-Host ""
    
    # Generate checksum
    Write-Host "Generating SHA256 checksum..." -ForegroundColor Yellow
    $hash = Get-FileHash $installerPath -Algorithm SHA256
    $hash.Hash | Out-File "$installerPath.sha256"
    Write-Host "✅ Checksum saved to: $installerPath.sha256" -ForegroundColor Green
    Write-Host "   SHA256: $($hash.Hash)" -ForegroundColor White
    Write-Host ""
    
    # Test option
    Write-Host "=== Next Steps ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Test the installer:" -ForegroundColor Yellow
    Write-Host "   .\$installerPath" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Upload to GitHub Releases:" -ForegroundColor Yellow
    Write-Host "   - Go to: https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases" -ForegroundColor White
    Write-Host "   - Click 'Draft a new release'" -ForegroundColor White
    Write-Host "   - Select tag: v0.9.1" -ForegroundColor White
    Write-Host "   - Upload: $installerPath" -ForegroundColor White
    Write-Host "   - Upload: $installerPath.sha256" -ForegroundColor White
    Write-Host "   - Publish release" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Share with your friend:" -ForegroundColor Yellow
    Write-Host "   https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/v0.9.1" -ForegroundColor White
    Write-Host ""
    
    $test = Read-Host "Would you like to test the installer now? (Y/N)"
    if ($test -eq "Y" -or $test -eq "y") {
        Write-Host "Launching installer..." -ForegroundColor Yellow
        Start-Process $installerPath
    }
    
    $openGitHub = Read-Host "Would you like to open GitHub Releases page? (Y/N)"
    if ($openGitHub -eq "Y" -or $openGitHub -eq "y") {
        Start-Process "https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases"
    }
    
} else {
    Write-Host "❌ Installer not found at expected location" -ForegroundColor Red
    Write-Host "Expected: $installerPath" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Green
