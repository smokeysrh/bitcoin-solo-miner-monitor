# Rebuild and Test Installer
# This script rebuilds the installer and helps you test it

Write-Host "=== Rebuild and Test Installer ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify the fix is in place
Write-Host "[1/4] Verifying fix is in place..." -ForegroundColor Yellow
& .\test-installer-fix.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Fix verification failed. Please check the installer files." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/4] Building installer..." -ForegroundColor Yellow
Write-Host ""

# Step 2: Build the installer
& .\build-and-release.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Build failed. Please check the error messages above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3/4] Verifying installer was created..." -ForegroundColor Yellow

$installerPath = "distribution\BitcoinSoloMinerMonitor-0.9.1-Setup.exe"

if (Test-Path $installerPath) {
    $fileInfo = Get-Item $installerPath
    $fileSizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
    
    Write-Host "✅ Installer created successfully!" -ForegroundColor Green
    Write-Host "   Location: $installerPath" -ForegroundColor White
    Write-Host "   Size: $fileSizeMB MB" -ForegroundColor White
    Write-Host "   Created: $($fileInfo.LastWriteTime)" -ForegroundColor White
} else {
    Write-Host "❌ Installer not found at: $installerPath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[4/4] Ready to test!" -ForegroundColor Yellow
Write-Host ""

# Step 3: Offer to test
Write-Host "=== Testing Instructions ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Before testing, you should:" -ForegroundColor Yellow
Write-Host "1. Uninstall any existing version of Bitcoin Solo Miner Monitor" -ForegroundColor White
Write-Host "   - Go to Settings > Apps" -ForegroundColor White
Write-Host "   - Find 'Bitcoin Solo Miner Monitor'" -ForegroundColor White
Write-Host "   - Click Uninstall" -ForegroundColor White
Write-Host ""

$uninstalled = Read-Host "Have you uninstalled the existing version? (Y/N)"

if ($uninstalled -ne "Y" -and $uninstalled -ne "y") {
    Write-Host ""
    Write-Host "Please uninstall the existing version first, then run this script again." -ForegroundColor Yellow
    Write-Host "Or manually run the installer: $installerPath" -ForegroundColor White
    exit 0
}

Write-Host ""
Write-Host "Launching installer..." -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  IMPORTANT: On the finish page, make sure to check 'Launch Bitcoin Solo Miner Monitor'" -ForegroundColor Yellow
Write-Host ""

Start-Sleep -Seconds 2

# Launch the installer
Start-Process $installerPath -Wait

Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Did the app launch automatically? (Y/N)" -ForegroundColor Yellow
$launched = Read-Host

if ($launched -eq "Y" -or $launched -eq "y") {
    Write-Host ""
    Write-Host "✅ SUCCESS! The fix is working!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Push to GitHub: git push origin main" -ForegroundColor White
    Write-Host "2. Upload installer to GitHub Releases" -ForegroundColor White
    Write-Host "3. Share with your friend" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ The app didn't launch automatically" -ForegroundColor Red
    Write-Host ""
    Write-Host "Let's troubleshoot:" -ForegroundColor Yellow
    Write-Host ""
    
    $installPath = "C:\Program Files\Bitcoin Solo Miner Monitor"
    
    Write-Host "Checking if batch file exists..." -ForegroundColor Yellow
    if (Test-Path "$installPath\BitcoinSoloMinerMonitor.bat") {
        Write-Host "✅ Batch file exists" -ForegroundColor Green
        Write-Host ""
        Write-Host "Try running it manually:" -ForegroundColor Yellow
        Write-Host "cd `"$installPath`"" -ForegroundColor White
        Write-Host ".\BitcoinSoloMinerMonitor.bat" -ForegroundColor White
        Write-Host ""
        
        $tryManual = Read-Host "Would you like to try running it now? (Y/N)"
        if ($tryManual -eq "Y" -or $tryManual -eq "y") {
            Start-Process "$installPath\BitcoinSoloMinerMonitor.bat"
        }
    } else {
        Write-Host "❌ Batch file not found!" -ForegroundColor Red
        Write-Host "   Expected: $installPath\BitcoinSoloMinerMonitor.bat" -ForegroundColor White
        Write-Host ""
        Write-Host "This means the installer didn't create the launcher file." -ForegroundColor Yellow
        Write-Host "Please check the installer logs for errors." -ForegroundColor Yellow
    }
}

Write-Host ""
