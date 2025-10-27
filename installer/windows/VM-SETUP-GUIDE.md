# Windows VM Setup Guide for Installer Testing

This guide will help you set up a clean Windows VM to test the installer.

## Prerequisites

- Windows 10/11 Pro or Enterprise (for Hyper-V)
- At least 8GB RAM on your host machine
- 60GB free disk space
- Administrator access

## Quick Start (Recommended)

### Step 1: Download Windows ISO

1. Go to [Windows 11 Evaluation Center](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise)
2. Click "Download the ISO - Enterprise"
3. Fill out the form (use any valid info)
4. Select language and download (64-bit)
5. Save to a known location (e.g., `C:\ISOs\Windows11.iso`)

**Alternative:** [Windows 10 Enterprise Evaluation](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-10-enterprise)

### Step 2: Enable Hyper-V

Open PowerShell as Administrator and run:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

**Restart your computer** after this completes.

### Step 3: Create the VM

After restart, open PowerShell as Administrator in the installer/windows directory and run:

```powershell
.\create-test-vm.ps1 -IsoPath "C:\ISOs\Windows11.iso"
```

This will:
- Create a VM named "InstallerTest"
- Allocate 4GB RAM and 60GB disk
- Mount the Windows ISO
- Configure boot settings

### Step 4: Install Windows

The script will ask if you want to start the VM. Say "yes" or manually start it:

```powershell
Start-VM -Name InstallerTest
vmconnect localhost InstallerTest
```

Follow the Windows installation wizard:
1. Select language and region
2. Click "Install Now"
3. Select "I don't have a product key"
4. Choose "Windows 11 Enterprise Evaluation"
5. Accept license terms
6. Choose "Custom: Install Windows only"
7. Select the virtual disk and click "Next"
8. Wait for installation (10-15 minutes)
9. Set up user account (use simple credentials for testing)
10. Skip all privacy/telemetry options for faster setup

### Step 5: Transfer Installer to VM

**Option A: Enhanced Session (Easiest)**

1. In Hyper-V Manager, right-click the VM → Settings
2. Enable "Guest services" under Integration Services
3. Connect to VM
4. You can now copy/paste files between host and VM

**Option B: Network Share**

1. On host machine, share the `distribution` folder:
   ```powershell
   # In the project root
   New-SmbShare -Name "Installer" -Path ".\distribution" -ReadAccess "Everyone"
   ```

2. In the VM, open File Explorer and navigate to:
   ```
   \\<your-host-computer-name>\Installer
   ```

3. Copy the installer to VM desktop

**Option C: ISO/Virtual DVD**

1. In Hyper-V Manager, right-click VM → Settings
2. DVD Drive → Browse
3. Select the installer .exe file (or create an ISO containing it)
4. In VM, open DVD drive and copy installer

### Step 6: Run the Installer

1. In the VM, double-click the installer
2. Follow the installation wizard
3. Verify all steps complete successfully
4. Launch the application
5. Test basic functionality

## Alternative: VirtualBox (If No Hyper-V)

If you don't have Windows Pro/Enterprise:

### 1. Install VirtualBox

Download from [virtualbox.org](https://www.virtualbox.org/wiki/Downloads)

### 2. Create VM

1. Open VirtualBox
2. Click "New"
3. Settings:
   - Name: InstallerTest
   - Type: Microsoft Windows
   - Version: Windows 10/11 (64-bit)
   - Memory: 4096 MB
   - Hard disk: Create virtual hard disk (VDI, 60GB, dynamically allocated)

4. Before starting:
   - Settings → System → Processor → Set to 2 CPUs
   - Settings → Storage → Empty → Click disk icon → Choose your Windows ISO
   - Settings → Network → Adapter 1 → Enable, NAT

5. Click "Start"

### 3. Install Windows

Same as Hyper-V steps above.

### 4. Transfer Installer

VirtualBox has built-in shared folders:

1. In VM menu: Devices → Insert Guest Additions CD
2. In VM, install Guest Additions
3. Restart VM
4. In VirtualBox: Devices → Shared Folders → Add
5. Select your `distribution` folder
6. Enable "Auto-mount"
7. In VM, access via Network locations

## Testing Checklist

Once you have the VM set up and installer copied:

- [ ] Run installer as normal user (not admin)
- [ ] Verify installation completes without errors
- [ ] Check Start Menu shortcut created
- [ ] Check Desktop shortcut created (if applicable)
- [ ] Launch application from Start Menu
- [ ] Verify application starts successfully
- [ ] Test basic functionality (connect to miner)
- [ ] Close application
- [ ] Uninstall via Windows Settings
- [ ] Verify all files removed
- [ ] Verify shortcuts removed

## Troubleshooting

### Hyper-V Not Available

**Error:** "Hyper-V cannot be enabled"

**Solution:** You need Windows 10/11 Pro, Enterprise, or Education. Home edition doesn't support Hyper-V. Use VirtualBox instead.

### VM Won't Start

**Error:** "Failed to start virtual machine"

**Solution:** 
- Check if virtualization is enabled in BIOS
- Ensure no other hypervisor is running (VMware, VirtualBox)
- Try disabling and re-enabling Hyper-V

### Can't Connect to Network Share

**Error:** "Network path not found"

**Solution:**
- Ensure both machines are on same network
- Check Windows Firewall settings
- Enable "File and Printer Sharing" on host
- Use IP address instead of computer name

### VM is Slow

**Solution:**
- Increase RAM allocation (6-8GB if available)
- Increase CPU cores (2-4)
- Ensure host machine has enough free resources
- Use SSD for VM storage if possible

## Quick Commands Reference

```powershell
# List all VMs
Get-VM

# Start VM
Start-VM -Name InstallerTest

# Stop VM
Stop-VM -Name InstallerTest

# Connect to VM
vmconnect localhost InstallerTest

# Take snapshot (before testing)
Checkpoint-VM -Name InstallerTest -SnapshotName "Clean Install"

# Restore snapshot (after testing)
Restore-VMSnapshot -Name "Clean Install" -VMName InstallerTest -Confirm:$false

# Delete VM
Remove-VM -Name InstallerTest -Force
```

## Tips for Efficient Testing

1. **Take Snapshots:** Before running the installer, take a VM snapshot. You can quickly restore to test again.

2. **Use Multiple VMs:** Create snapshots at different stages:
   - Fresh Windows install
   - After first installer run
   - After application configuration

3. **Automate:** Once you verify manual installation works, consider automating tests with PowerShell scripts.

4. **Network Testing:** If testing network features, ensure VM has network access and can reach your test miner (192.168.1.156).

## Next Steps

After VM setup, proceed with Task 7 testing:
- Fresh installation test
- Upgrade installation test
- Uninstallation test
- Installation time verification
- File placement verification
