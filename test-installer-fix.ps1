# Quick Test Script for Installer Fix
# This script verifies the installer will create the launcher batch file

Write-Host "=== Testing Installer Fix ===" -ForegroundColor Cyan
Write-Host ""

# Check if NSIS is installed
Write-Host "[1/3] Checking NSIS installation..." -ForegroundColor Yellow
$nsisPath = Get-Command makensis -ErrorAction SilentlyContinue

if (-not $nsisPath) {
    Write-Host "❌ NSIS not found. Please install NSIS first." -ForegroundColor Red
    exit 1
}
Write-Host "✅ NSIS found" -ForegroundColor Green
Write-Host ""

# Check if the installer script has the fix
Write-Host "[2/3] Verifying installer script has the fix..." -ForegroundColor Yellow
$installerScript = "installer\windows\installer_enhanced.nsi"

if (-not (Test-Path $installerScript)) {
    Write-Host "❌ Installer script not found: $installerScript" -ForegroundColor Red
    exit 1
}

$content = Get-Content $installerScript -Raw

if ($content -match "!insertmacro ConfigureRuntimeEnvironment") {
    Write-Host "✅ Installer script has the fix" -ForegroundColor Green
} else {
    Write-Host "❌ Installer script is missing the ConfigureRuntimeEnvironment macro call" -ForegroundColor Red
    Write-Host "   Expected to find: !insertmacro ConfigureRuntimeEnvironment" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Check if runtime_config.nsh has the improved launcher
Write-Host "[3/3] Verifying launcher improvements..." -ForegroundColor Yellow
$runtimeConfig = "installer\windows\config\runtime_config.nsh"

if (-not (Test-Path $runtimeConfig)) {
    Write-Host "❌ Runtime config not found: $runtimeConfig" -ForegroundColor Red
    exit 1
}

$runtimeContent = Get-Content $runtimeConfig -Raw

$checks = @(
    @{Pattern = "tasklist.*python\.exe"; Description = "Check for running instance"},
    @{Pattern = "timeout /t 3"; Description = "Startup delay"},
    @{Pattern = "start http://localhost:8000"; Description = "Browser auto-launch"}
)

$allPassed = $true
foreach ($check in $checks) {
    if ($runtimeContent -match $check.Pattern) {
        Write-Host "  ✅ $($check.Description)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Missing: $($check.Description)" -ForegroundColor Red
        $allPassed = $false
    }
}

if (-not $allPassed) {
    Write-Host ""
    Write-Host "❌ Some launcher improvements are missing" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== All Checks Passed ===" -ForegroundColor Green
Write-Host ""
Write-Host "The installer fix is properly applied!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Build the installer: .\build-and-release.ps1" -ForegroundColor White
Write-Host "2. Test the installer locally" -ForegroundColor White
Write-Host "3. Upload to GitHub releases" -ForegroundColor White
Write-Host "4. Have your friend test it" -ForegroundColor White
Write-Host ""
