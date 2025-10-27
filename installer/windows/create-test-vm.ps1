# ============================================================================
# Create Windows Test VM for Installer Testing
# ============================================================================
# This script creates a Hyper-V VM for testing the installer on a clean system
#
# Prerequisites:
# - Hyper-V enabled (Windows Pro/Enterprise)
# - Windows ISO file downloaded
# - Run as Administrator
#
# Usage: .\create-test-vm.ps1 -IsoPath "C:\path\to\windows.iso"
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$IsoPath,
    
    [string]$VMName = "InstallerTest",
    [int]$MemoryGB = 4,
    [int]$DiskSizeGB = 60,
    [string]$VMPath = "C:\VMs"
)

$ErrorActionPreference = "Stop"

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if Hyper-V is enabled
Write-Host "Checking Hyper-V status..." -ForegroundColor Cyan
$hyperv = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V
if ($hyperv.State -ne "Enabled") {
    Write-Host "ERROR: Hyper-V is not enabled" -ForegroundColor Red
    Write-Host ""
    Write-Host "To enable Hyper-V, run this command as Administrator:" -ForegroundColor Yellow
    Write-Host "  Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All" -ForegroundColor White
    Write-Host ""
    Write-Host "Then restart your computer and run this script again." -ForegroundColor Yellow
    exit 1
}

# Check if ISO exists
if (-not (Test-Path $IsoPath)) {
    Write-Host "ERROR: ISO file not found: $IsoPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Download Windows ISO from:" -ForegroundColor Yellow
    Write-Host "  https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  Creating Test VM for Installer Testing" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "VM Name: $VMName" -ForegroundColor White
Write-Host "Memory: $MemoryGB GB" -ForegroundColor White
Write-Host "Disk: $DiskSizeGB GB" -ForegroundColor White
Write-Host "ISO: $IsoPath" -ForegroundColor White
Write-Host "Location: $VMPath" -ForegroundColor White
Write-Host ""

# Create VM directory
if (-not (Test-Path $VMPath)) {
    Write-Host "Creating VM directory: $VMPath" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $VMPath -Force | Out-Null
}

# Check if VM already exists
$existingVM = Get-VM -Name $VMName -ErrorAction SilentlyContinue
if ($existingVM) {
    Write-Host "WARNING: VM '$VMName' already exists" -ForegroundColor Yellow
    $response = Read-Host "Delete and recreate? (yes/no)"
    if ($response -eq "yes") {
        Write-Host "Stopping and removing existing VM..." -ForegroundColor Yellow
        Stop-VM -Name $VMName -Force -ErrorAction SilentlyContinue
        Remove-VM -Name $VMName -Force
        Write-Host "Existing VM removed" -ForegroundColor Green
    }
    else {
        Write-Host "Cancelled" -ForegroundColor Yellow
        exit 0
    }
}

try {
    # Create VM
    Write-Host "Creating virtual machine..." -ForegroundColor Cyan
    $vm = New-VM -Name $VMName `
        -MemoryStartupBytes ($MemoryGB * 1GB) `
        -Generation 2 `
        -NewVHDPath "$VMPath\$VMName\$VMName.vhdx" `
        -NewVHDSizeBytes ($DiskSizeGB * 1GB) `
        -Path $VMPath
    
    Write-Host "VM created successfully" -ForegroundColor Green
    
    # Configure VM
    Write-Host "Configuring VM settings..." -ForegroundColor Cyan
    
    # Set processor count
    Set-VMProcessor -VMName $VMName -Count 2
    
    # Enable dynamic memory
    Set-VMMemory -VMName $VMName -DynamicMemoryEnabled $true -MinimumBytes 2GB -MaximumBytes ($MemoryGB * 1GB)
    
    # Add DVD drive and mount ISO
    Add-VMDvdDrive -VMName $VMName -Path $IsoPath
    
    # Get the DVD drive
    $dvd = Get-VMDvdDrive -VMName $VMName
    
    # Set boot order (DVD first)
    Set-VMFirmware -VMName $VMName -FirstBootDevice $dvd
    
    # Disable Secure Boot (for compatibility)
    Set-VMFirmware -VMName $VMName -EnableSecureBoot Off
    
    # Connect to Default Switch
    $switch = Get-VMSwitch | Where-Object { $_.SwitchType -eq "Internal" -or $_.SwitchType -eq "External" } | Select-Object -First 1
    if ($switch) {
        Connect-VMNetworkAdapter -VMName $VMName -SwitchName $switch.Name
        Write-Host "Connected to network switch: $($switch.Name)" -ForegroundColor Green
    }
    else {
        Write-Host "WARNING: No network switch found. VM will not have network access." -ForegroundColor Yellow
        Write-Host "Create a virtual switch in Hyper-V Manager if needed." -ForegroundColor Yellow
    }
    
    Write-Host "VM configuration completed" -ForegroundColor Green
    
    # Create shared folder for installer
    Write-Host ""
    Write-Host "Setting up installer transfer..." -ForegroundColor Cyan
    $installerPath = Join-Path $PSScriptRoot "..\..\distribution"
    if (Test-Path $installerPath) {
        Write-Host "Installer location: $installerPath" -ForegroundColor White
        Write-Host ""
        Write-Host "To transfer the installer to the VM:" -ForegroundColor Yellow
        Write-Host "  1. Start the VM and install Windows" -ForegroundColor White
        Write-Host "  2. In the VM, open Edge browser" -ForegroundColor White
        Write-Host "  3. Navigate to this host machine using network share" -ForegroundColor White
        Write-Host "  4. Or use Enhanced Session to copy/paste files" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Green
    Write-Host "  VM Created Successfully!" -ForegroundColor Green
    Write-Host "============================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Start the VM: Start-VM -Name $VMName" -ForegroundColor White
    Write-Host "  2. Connect to VM: vmconnect localhost $VMName" -ForegroundColor White
    Write-Host "  3. Install Windows (follow on-screen prompts)" -ForegroundColor White
    Write-Host "  4. After Windows setup, copy installer to VM" -ForegroundColor White
    Write-Host "  5. Run installer and test" -ForegroundColor White
    Write-Host ""
    Write-Host "Quick start command:" -ForegroundColor Yellow
    Write-Host "  Start-VM -Name $VMName; vmconnect localhost $VMName" -ForegroundColor White
    Write-Host ""
    
    # Ask if user wants to start VM now
    $startNow = Read-Host "Start VM now? (yes/no)"
    if ($startNow -eq "yes") {
        Write-Host "Starting VM..." -ForegroundColor Cyan
        Start-VM -Name $VMName
        Start-Sleep -Seconds 2
        vmconnect localhost $VMName
    }
}
catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create VM" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
