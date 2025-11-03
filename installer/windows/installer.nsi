; ============================================================================
; Bitcoin Solo Miner Monitor - Windows Installer Script
; ============================================================================
; 
; This is the unified NSIS installer script for Bitcoin Solo Miner Monitor.
; It creates a Windows installer that bundles the application with a complete
; Python runtime and all dependencies for fast, offline installation.
;
; ARCHITECTURE:
; - Single unified installer script (no external macros or includes)
; - Pre-bundled Python runtime (no internet required during installation)
; - Inline launcher creation (ensures launcher is always created correctly)
; - Comprehensive error handling and verification
; - Clean uninstallation with user data preservation option
;
; BUILD PROCESS:
; 1. Run prepare-bundle.ps1 once to create Python bundle
; 2. Run build.ps1 to build the installer
; 3. Installer is created in distribution/ directory
;
; REQUIREMENTS:
; - NSIS 3.0 or later
; - Windows 10 or later (checked at runtime)
; - Administrator privileges (requested at runtime)
;
; VERSION MANAGEMENT:
; - Version is passed as command-line parameter: /DVERSION=x.x.x
; - Version is read from src/backend/version.py by build.ps1
; - Single source of truth for version number
;
; INSTALLATION COMPONENTS:
; - Core Application (required): Application files, Python runtime, launcher
; - Start Menu Shortcuts (optional): Shortcuts in Start Menu
; - Desktop Shortcut (optional): Shortcut on Desktop
; - Start with Windows (optional): Auto-start on Windows login
;
; REGISTRY KEYS:
; - HKLM\Software\Bitcoin Solo Miner Monitor: Application settings
; - HKLM\...\Uninstall\Bitcoin Solo Miner Monitor: Add/Remove Programs entry
; - HKLM\...\Run\Bitcoin Solo Miner Monitor: Auto-start (if selected)
;
; DIRECTORIES:
; - Installation: C:\Program Files\Bitcoin Solo Miner Monitor
; - User Data: %APPDATA%\Bitcoin Solo Miner Monitor
; - Logs: Installation directory\logs
;
; REQUIREMENTS ADDRESSED:
; - 1.1, 1.2, 1.3: Single unified installer script
; - 1.4: Core installation with registry configuration
; - 1.5, 5.1-5.6: Inline launcher creation
; - 8.1-8.6: Installation verification and error handling
; - 9.1-9.7: Maintainable code structure with comments
; - 10.1-10.6: Backward compatibility and clean uninstallation
;
; ============================================================================

; ============================================================================
; SECTION 1: CONFIGURATION
; ============================================================================
; This section defines all constants, includes necessary libraries, and
; configures the installer's basic settings.
; ============================================================================

; ----------------------------------------------------------------------------
; Define Application Constants
; ----------------------------------------------------------------------------
; These constants define the application name, version, publisher, and
; registry keys used throughout the installer.
; ----------------------------------------------------------------------------
!define APP_NAME "Bitcoin Solo Miner Monitor"
!define PUBLISHER "Bitcoin Solo Miner Monitor"
; VERSION is passed as a command line parameter via /DVERSION=x.x.x
!ifndef VERSION
  !define VERSION "0.1.0"
!endif
!define WEBSITE "https://github.com/smokeysrh/bitcoin-solo-miner-monitor"
!define REGKEY "Software\${APP_NAME}"
!define UNINSTALL_REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

; ----------------------------------------------------------------------------
; Include Necessary NSIS Libraries
; ----------------------------------------------------------------------------
; MUI2.nsh: Modern UI 2 for professional installer interface
; LogicLib.nsh: Logical operations (If, While, etc.)
; FileFunc.nsh: File and directory functions (GetSize, etc.)
; WinVer.nsh: Windows version detection
; StrFunc.nsh: String manipulation functions
; ----------------------------------------------------------------------------
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "WinVer.nsh"
!include "StrFunc.nsh"

; ----------------------------------------------------------------------------
; Initialize String Functions
; ----------------------------------------------------------------------------
; Declare string functions that will be used in the installer
; ----------------------------------------------------------------------------
${Using:StrFunc} StrLoc

; ----------------------------------------------------------------------------
; Set Basic Installer Information
; ----------------------------------------------------------------------------
; Configure installer name, output file, installation directory, and
; execution level. The installer requires administrator privileges to
; install to Program Files and write to HKLM registry.
; ----------------------------------------------------------------------------
Name "${APP_NAME}"
; Use OUTPUT_FILE if provided, otherwise use default naming
!ifdef OUTPUT_FILE
  OutFile "${OUTPUT_FILE}"
!else
  OutFile "BitcoinSoloMinerMonitor-${VERSION}-Setup.exe"
!endif
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKLM "${REGKEY}" "InstallDir"
RequestExecutionLevel admin  ; Require administrator privileges
SetCompressor /SOLID lzma   ; Use LZMA compression for smaller installer size

; ============================================================================
; SECTION 2: UI CONFIGURATION
; ============================================================================
; This section configures the Modern UI 2 interface, including icons,
; welcome page, license page, and finish page settings.
; ============================================================================

; ----------------------------------------------------------------------------
; Define Modern UI Settings
; ----------------------------------------------------------------------------
; Configure the visual appearance and behavior of the installer interface.
; ----------------------------------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON "..\common\assets\bitcoin-symbol.ico"
!define MUI_UNICON "..\common\assets\bitcoin-symbol.ico"
; Temporarily commented out due to BMP format issues
; !define MUI_WELCOMEFINISHPAGE_BITMAP "..\common\assets\welcome_image.bmp"
; !define MUI_HEADERIMAGE
; !define MUI_HEADERIMAGE_BITMAP "..\common\assets\header_image.bmp"
!define MUI_HEADERIMAGE_RIGHT

; Define welcome page
!define MUI_WELCOMEPAGE_TITLE "Welcome to the ${APP_NAME} Setup Wizard"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of ${APP_NAME}, a unified monitoring and management solution for Bitcoin mining hardware.$\r$\n$\r$\nBefore continuing, make sure you have administrator privileges on this computer.$\r$\n$\r$\nClick Next to continue."

; Define license page
!define MUI_LICENSEPAGE_CHECKBOX

; Define finish page
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_FINISHPAGE_RUN "$INSTDIR\BitcoinSoloMinerMonitor.bat"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_LINK "Visit ${WEBSITE} for more information"
!define MUI_FINISHPAGE_LINK_LOCATION "${WEBSITE}"

; ============================================================================
; SECTION 3: INSTALLER PAGES
; ============================================================================
; This section defines the sequence of pages shown during installation
; and uninstallation. Each page is displayed in the order listed.
; ============================================================================

; ----------------------------------------------------------------------------
; Define Installer Page Sequence
; ----------------------------------------------------------------------------
; Welcome: Introduction and system requirements
; License: Display license agreement (must be accepted)
; Components: Select optional components (shortcuts, auto-start)
; Directory: Choose installation directory
; Install: Perform installation with progress display
; Finish: Completion message with option to launch application
; ----------------------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\common\assets\LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ----------------------------------------------------------------------------
; Define Uninstaller Page Sequence
; ----------------------------------------------------------------------------
; Confirm: Ask user to confirm uninstallation
; Uninstall: Perform uninstallation with progress display
; ----------------------------------------------------------------------------
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ----------------------------------------------------------------------------
; Set Language
; ----------------------------------------------------------------------------
; Currently only English is supported. Additional languages can be added
; by including additional MUI_LANGUAGE macros.
; ----------------------------------------------------------------------------
!insertmacro MUI_LANGUAGE "English"



; ============================================================================
; SECTION 4: CORE INSTALLATION
; ============================================================================
; This section installs the core application files and is required.
; It copies all application files from the staging directory, creates
; necessary data directories, and registers the application with Windows.
;
; Requirements: 1.4
; ============================================================================

Section "!Core Application (required)" SecCore
  SectionIn RO  ; Read-only - this section is required and cannot be deselected
  
  DetailPrint "Installing ${APP_NAME} ${VERSION}..."
  
  ; --------------------------------------------------------------------------
  ; Copy Application Files
  ; --------------------------------------------------------------------------
  DetailPrint "Copying application files..."
  
  ; Set output directory to installation directory
  SetOutPath "$INSTDIR"
  
  ; Copy all files from staging directory
  ; The staging directory is prepared by build.ps1 and contains:
  ; - src/ (application source code)
  ; - config/ (configuration files)
  ; - python/ (embedded Python runtime with dependencies)
  ; - run.py (application entry point)
  ; - requirements.txt (dependency list)
  ; - README.md (documentation)
  !ifdef APP_DIR
    DetailPrint "Copying from staging: ${APP_DIR}"
    File /r "${APP_DIR}\*.*"
  !else
    ; Fallback to default build directory if APP_DIR not specified
    DetailPrint "Copying from default build directory"
    File /r "..\build\windows\staging\*.*"
  !endif
  
  DetailPrint "Application files copied successfully"
  
  ; --------------------------------------------------------------------------
  ; Create Data Directories
  ; --------------------------------------------------------------------------
  DetailPrint "Creating data directories..."
  
  ; Create application data directory in user's AppData
  ; This stores user-specific configuration, database, and runtime data
  CreateDirectory "$APPDATA\${APP_NAME}"
  DetailPrint "Created: $APPDATA\${APP_NAME}"
  
  ; Create logs directory in installation directory
  ; This stores application logs for debugging and monitoring
  CreateDirectory "$INSTDIR\logs"
  DetailPrint "Created: $INSTDIR\logs"
  
  DetailPrint "Data directories created successfully"
  
  ; --------------------------------------------------------------------------
  ; Create Launcher Batch File (Inline)
  ; --------------------------------------------------------------------------
  ; This creates the launcher batch file that starts the application.
  ; The launcher is created inline (not via macros) to ensure it's always
  ; created correctly and can't be accidentally forgotten.
  ;
  ; The launcher performs the following:
  ; 1. Checks if the application is already running
  ; 2. Starts the Python backend in a minimized window
  ; 3. Waits 3 seconds for the server to initialize
  ; 4. Opens the default browser to http://localhost:8000
  ;
  ; Requirements: 1.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
  ; --------------------------------------------------------------------------
  DetailPrint "Creating application launcher..."
  
  ; Open file handle for writing the launcher batch file
  FileOpen $0 "$INSTDIR\BitcoinSoloMinerMonitor.bat" w
  
  ; Write batch file header and comments
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM Bitcoin Solo Miner Monitor - Application Launcher$\r$\n"
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM This script starts the Bitcoin Solo Miner Monitor application.$\r$\n"
  FileWrite $0 "REM It checks if the application is already running, starts the Python$\r$\n"
  FileWrite $0 "REM backend server, waits for initialization, and opens the web browser.$\r$\n"
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "$\r$\n"
  
  ; Change to the installation directory
  FileWrite $0 "REM Change to installation directory$\r$\n"
  FileWrite $0 "cd /d $\"%~dp0$\"$\r$\n"
  FileWrite $0 "$\r$\n"
  
  ; Write instance checking logic
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM Check if application is already running$\r$\n"
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM Check if port 8000 is in use (server already running)$\r$\n"
  FileWrite $0 "netstat -ano | findstr $\":8000.*LISTENING$\" >nul 2>&1$\r$\n"
  FileWrite $0 "if $\"%ERRORLEVEL%$\"==$\"0$\" ($\r$\n"
  FileWrite $0 "  echo Bitcoin Solo Miner Monitor is already running.$\r$\n"
  FileWrite $0 "  echo Opening browser to existing instance...$\r$\n"
  FileWrite $0 "  start http://localhost:8000$\r$\n"
  FileWrite $0 "  exit /b 0$\r$\n"
  FileWrite $0 ")$\r$\n"
  FileWrite $0 "$\r$\n"
  
  ; Write application startup command
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM Start the application$\r$\n"
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM Start Python backend in minimized window$\r$\n"
  FileWrite $0 "echo Starting Bitcoin Solo Miner Monitor...$\r$\n"
  FileWrite $0 "start $\"Bitcoin Solo Miner Monitor$\" /MIN python\python.exe run.py$\r$\n"
  FileWrite $0 "$\r$\n"
  
  ; Write 3-second delay for server initialization
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM Wait for server to initialize$\r$\n"
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM Give the server 3 seconds to start up$\r$\n"
  FileWrite $0 "echo Waiting for server to start...$\r$\n"
  FileWrite $0 "timeout /t 3 /nobreak >nul$\r$\n"
  FileWrite $0 "$\r$\n"
  
  ; Write browser launch command
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM Open browser to application$\r$\n"
  FileWrite $0 "REM ========================================================================$\r$\n"
  FileWrite $0 "REM Launch default browser to localhost:8000$\r$\n"
  FileWrite $0 "echo Opening browser...$\r$\n"
  FileWrite $0 "start http://localhost:8000$\r$\n"
  FileWrite $0 "$\r$\n"
  FileWrite $0 "REM Application started successfully$\r$\n"
  FileWrite $0 "exit /b 0$\r$\n"
  
  ; Close file handle
  FileClose $0
  
  ; --------------------------------------------------------------------------
  ; Verify Launcher Creation
  ; --------------------------------------------------------------------------
  ; Verify that the launcher file was created successfully.
  ; If the file doesn't exist, display an error and abort installation.
  ; This ensures we never have a broken installation without a launcher.
  ; --------------------------------------------------------------------------
  DetailPrint "Verifying launcher creation..."
  
  ${If} ${FileExists} "$INSTDIR\BitcoinSoloMinerMonitor.bat"
    DetailPrint "✓ Launcher created successfully: BitcoinSoloMinerMonitor.bat"
  ${Else}
    DetailPrint "✗ FAILED: Launcher file was not created!"
    MessageBox MB_OK|MB_ICONSTOP "Failed to create application launcher!$\r$\n$\r$\nThe launcher batch file could not be created. This may be due to:$\r$\n- Insufficient disk space$\r$\n- File system permissions$\r$\n- Antivirus interference$\r$\n$\r$\nInstallation cannot continue."
    Abort
  ${EndIf}
  
  DetailPrint "Launcher creation completed successfully"
  
  ; --------------------------------------------------------------------------
  ; Verify Installation Components
  ; --------------------------------------------------------------------------
  ; Verify that all critical components were installed successfully.
  ; This ensures we never have a broken installation missing key files.
  ; If any critical component is missing, display a specific error message
  ; and abort the installation.
  ;
  ; Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
  ; --------------------------------------------------------------------------
  DetailPrint "Verifying installation components..."
  
  ; Verify Python runtime exists
  DetailPrint "Checking Python runtime..."
  ${If} ${FileExists} "$INSTDIR\python\python.exe"
    DetailPrint "✓ Python runtime verified: python\python.exe"
  ${Else}
    DetailPrint "✗ FAILED: Python runtime not found!"
    MessageBox MB_OK|MB_ICONSTOP "Python runtime is missing!$\r$\n$\r$\nThe Python interpreter (python\python.exe) was not found in the installation directory. This is a critical component required to run the application.$\r$\n$\r$\nPossible causes:$\r$\n- Corrupted installer package$\r$\n- Insufficient disk space during extraction$\r$\n- Antivirus software blocked the file$\r$\n$\r$\nPlease try:$\r$\n1. Re-download the installer$\r$\n2. Temporarily disable antivirus$\r$\n3. Ensure sufficient disk space (at least 500MB)$\r$\n$\r$\nInstallation cannot continue."
    Abort
  ${EndIf}
  
  ; Verify application entry point exists
  DetailPrint "Checking application entry point..."
  ${If} ${FileExists} "$INSTDIR\run.py"
    DetailPrint "✓ Application entry point verified: run.py"
  ${Else}
    DetailPrint "✗ FAILED: Application entry point not found!"
    MessageBox MB_OK|MB_ICONSTOP "Application entry point is missing!$\r$\n$\r$\nThe main application file (run.py) was not found in the installation directory. This file is required to start the application.$\r$\n$\r$\nPossible causes:$\r$\n- Corrupted installer package$\r$\n- Insufficient disk space during extraction$\r$\n- File system permissions issue$\r$\n$\r$\nPlease try:$\r$\n1. Re-download the installer$\r$\n2. Run installer as administrator$\r$\n3. Check disk space and permissions$\r$\n$\r$\nInstallation cannot continue."
    Abort
  ${EndIf}
  
  ; Verify application source code exists
  DetailPrint "Checking application source code..."
  ${If} ${FileExists} "$INSTDIR\src\main.py"
    DetailPrint "✓ Application source code verified: src\main.py"
  ${Else}
    DetailPrint "✗ FAILED: Application source code not found!"
    MessageBox MB_OK|MB_ICONSTOP "Application source code is missing!$\r$\n$\r$\nThe main application module (src\main.py) was not found. This is a critical component of the application.$\r$\n$\r$\nPossible causes:$\r$\n- Corrupted installer package$\r$\n- Incomplete file extraction$\r$\n- Insufficient disk space$\r$\n$\r$\nPlease try:$\r$\n1. Re-download the installer$\r$\n2. Ensure sufficient disk space (at least 500MB)$\r$\n3. Check antivirus logs for blocked files$\r$\n$\r$\nInstallation cannot continue."
    Abort
  ${EndIf}
  
  ; Verify launcher was created (already checked above, but included for completeness)
  DetailPrint "Checking application launcher..."
  ${If} ${FileExists} "$INSTDIR\BitcoinSoloMinerMonitor.bat"
    DetailPrint "✓ Application launcher verified: BitcoinSoloMinerMonitor.bat"
  ${Else}
    DetailPrint "✗ FAILED: Application launcher not found!"
    MessageBox MB_OK|MB_ICONSTOP "Application launcher is missing!$\r$\n$\r$\nThe launcher batch file (BitcoinSoloMinerMonitor.bat) was not created. This file is required to start the application.$\r$\n$\r$\nPossible causes:$\r$\n- Insufficient disk space$\r$\n- File system permissions issue$\r$\n- Antivirus interference$\r$\n$\r$\nPlease try:$\r$\n1. Run installer as administrator$\r$\n2. Temporarily disable antivirus$\r$\n3. Check disk space and permissions$\r$\n$\r$\nInstallation cannot continue."
    Abort
  ${EndIf}
  
  DetailPrint "✓ All critical components verified successfully"
  
  ; --------------------------------------------------------------------------
  ; Write Application Registry Keys
  ; --------------------------------------------------------------------------
  DetailPrint "Registering application..."
  
  ; Write application-specific registry keys
  WriteRegStr HKLM "${REGKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${REGKEY}" "Version" "${VERSION}"
  WriteRegStr HKLM "${REGKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "${REGKEY}" "Website" "${WEBSITE}"
  
  DetailPrint "Application registered in registry"
  
  ; --------------------------------------------------------------------------
  ; Create Uninstaller
  ; --------------------------------------------------------------------------
  DetailPrint "Creating uninstaller..."
  
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  DetailPrint "Uninstaller created: $INSTDIR\Uninstall.exe"
  
  ; --------------------------------------------------------------------------
  ; Register with Add/Remove Programs
  ; --------------------------------------------------------------------------
  DetailPrint "Registering with Add/Remove Programs..."
  
  ; Write uninstall information for Windows Add/Remove Programs
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "URLInfoAbout" "${WEBSITE}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayIcon" "$INSTDIR\BitcoinSoloMinerMonitor.bat,0"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "NoRepair" 1
  
  ; Calculate and write installation size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "EstimatedSize" "$0"
  
  DetailPrint "Registered with Add/Remove Programs"
  
  ; --------------------------------------------------------------------------
  ; Installation Complete
  ; --------------------------------------------------------------------------
  DetailPrint "Core installation completed successfully"
  
SectionEnd

; ============================================================================
; SECTION 5: OPTIONAL COMPONENTS
; ============================================================================
; These sections provide optional features that users can choose to install.
; All optional components can be selected or deselected during installation.
; ============================================================================

Section "Start Menu Shortcuts" SecStartMenu
  DetailPrint "Creating Start Menu shortcuts..."
  
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  
  ; Create application shortcut with Bitcoin icon
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
      "$INSTDIR\BitcoinSoloMinerMonitor.bat" \
      "" \
      "$INSTDIR\bitcoin-symbol.ico" \
      0 \
      SW_SHOWMINIMIZED \
      "" \
      "Bitcoin Solo Miner Monitor"
  
  ; Create uninstaller shortcut with Bitcoin icon
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
      "$INSTDIR\Uninstall.exe" \
      "" \
      "$INSTDIR\bitcoin-symbol.ico" \
      0 \
      SW_SHOWNORMAL \
      "" \
      "Uninstall Bitcoin Solo Miner Monitor"
  
  DetailPrint "Start Menu shortcuts created with icons"
SectionEnd

Section "Desktop Shortcut" SecDesktop
  DetailPrint "Creating Desktop shortcut..."
  
  ; Create desktop shortcut with Bitcoin icon
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" \
      "$INSTDIR\BitcoinSoloMinerMonitor.bat" \
      "" \
      "$INSTDIR\bitcoin-symbol.ico" \
      0 \
      SW_SHOWMINIMIZED \
      "" \
      "Bitcoin Solo Miner Monitor"
  
  DetailPrint "Desktop shortcut created with icon"
SectionEnd

Section "Start with Windows" SecStartup
  DetailPrint "Configuring auto-start..."
  
  ; Add registry entry to start application automatically when Windows starts
  ; This uses the launcher batch file to ensure proper startup
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}" "$INSTDIR\BitcoinSoloMinerMonitor.bat"
  
  DetailPrint "Auto-start configured"
SectionEnd

; ============================================================================
; SECTION 6: UNINSTALLER
; ============================================================================
; This section handles the complete removal of the application from the system.
; It stops any running processes, removes all files and directories, cleans up
; shortcuts, removes registry entries, and optionally removes user data.
;
; The uninstaller ensures a clean removal with verification steps to confirm
; all components have been properly removed.
;
; Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
; ============================================================================

Section "Uninstall"
  DetailPrint "Starting uninstallation of ${APP_NAME}..."
  
  ; --------------------------------------------------------------------------
  ; Stop Running Application Processes
  ; --------------------------------------------------------------------------
  ; Before removing files, we need to stop any running instances of the
  ; application. This prevents file-in-use errors during uninstallation.
  ;
  ; We check for python.exe processes that may be running the application.
  ; If found, we attempt to terminate them gracefully using Windows taskkill.
  ;
  ; Requirements: 10.1, 10.2
  ; --------------------------------------------------------------------------
  DetailPrint "Checking for running application processes..."
  
  ; Use tasklist to check if python.exe is running
  ; We check the exit code - 0 means process found, 1 means not found
  nsExec::ExecToStack 'tasklist /FI "IMAGENAME eq python.exe" /NH | find /I "python.exe"'
  Pop $R0 ; Return value (0 if found, 1 if not found)
  Pop $R1 ; Output
  
  ; Check if python.exe was found (exit code 0)
  ${If} $R0 == 0
    DetailPrint "Found running Python process, attempting to stop..."
    
    ; Display message to user
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "${APP_NAME} is currently running.$\r$\n$\r$\nClick OK to close the application and continue with uninstallation, or Cancel to abort." IDOK stopProcess
    
    ; User cancelled, abort uninstallation
    DetailPrint "Uninstallation cancelled by user"
    Abort
    
    stopProcess:
      ; Attempt to kill the process using taskkill
      ; /F = Force termination
      ; /IM = Image name (process name)
      DetailPrint "Stopping Python processes..."
      nsExec::ExecToLog 'taskkill /F /IM python.exe'
      Pop $R0
      
      ${If} $R0 = 0
        DetailPrint "✓ Application process stopped successfully"
        ; Wait a moment for process to fully terminate
        Sleep 2000
      ${Else}
        DetailPrint "⚠ Warning: Could not stop application process (error code: $R0)"
        MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "Unable to automatically stop the application.$\r$\n$\r$\nPlease close ${APP_NAME} manually and click OK to continue, or Cancel to abort." IDOK continueUninstall
        Abort
        
        continueUninstall:
          DetailPrint "Continuing with uninstallation..."
      ${EndIf}
  ${Else}
    DetailPrint "✓ No running application processes found"
  ${EndIf}
  
  ; --------------------------------------------------------------------------
  ; Remove Application Files and Directories
  ; --------------------------------------------------------------------------
  ; Remove all application files from the installation directory.
  ; We remove files in a specific order to ensure clean removal:
  ; 1. Launcher batch file
  ; 2. Application entry point
  ; 3. Python runtime directory
  ; 4. Source code directory
  ; 5. Configuration directory
  ; 6. Logs directory
  ; 7. Any remaining files
  ; 8. Uninstaller itself
  ;
  ; Requirements: 10.3
  ; --------------------------------------------------------------------------
  DetailPrint "Removing application files..."
  
  ; Remove launcher batch file
  DetailPrint "Removing launcher..."
  Delete "$INSTDIR\BitcoinSoloMinerMonitor.bat"
  ${If} ${FileExists} "$INSTDIR\BitcoinSoloMinerMonitor.bat"
    DetailPrint "⚠ Warning: Could not remove launcher file"
  ${Else}
    DetailPrint "✓ Launcher removed"
  ${EndIf}
  
  ; Remove application entry point
  DetailPrint "Removing application entry point..."
  Delete "$INSTDIR\run.py"
  ${If} ${FileExists} "$INSTDIR\run.py"
    DetailPrint "⚠ Warning: Could not remove run.py"
  ${Else}
    DetailPrint "✓ Application entry point removed"
  ${EndIf}
  
  ; Remove requirements.txt
  Delete "$INSTDIR\requirements.txt"
  
  ; Remove README
  Delete "$INSTDIR\README.md"
  
  ; Remove application icon
  DetailPrint "Removing application icon..."
  Delete "$INSTDIR\bitcoin-symbol.ico"
  ${If} ${FileExists} "$INSTDIR\bitcoin-symbol.ico"
    DetailPrint "⚠ Warning: Could not remove application icon"
  ${Else}
    DetailPrint "✓ Application icon removed"
  ${EndIf}
  
  ; Remove assets directory
  DetailPrint "Removing assets directory..."
  RMDir /r "$INSTDIR\assets"
  ${If} ${FileExists} "$INSTDIR\assets"
    DetailPrint "⚠ Warning: Could not completely remove assets directory"
  ${Else}
    DetailPrint "✓ Assets directory removed"
  ${EndIf}
  
  ; Remove Python runtime directory
  DetailPrint "Removing Python runtime..."
  RMDir /r "$INSTDIR\python"
  ${If} ${FileExists} "$INSTDIR\python"
    DetailPrint "⚠ Warning: Could not completely remove Python runtime"
  ${Else}
    DetailPrint "✓ Python runtime removed"
  ${EndIf}
  
  ; Remove source code directory
  DetailPrint "Removing application source code..."
  RMDir /r "$INSTDIR\src"
  ${If} ${FileExists} "$INSTDIR\src"
    DetailPrint "⚠ Warning: Could not completely remove source code"
  ${Else}
    DetailPrint "✓ Source code removed"
  ${EndIf}
  
  ; Remove configuration directory
  DetailPrint "Removing configuration files..."
  RMDir /r "$INSTDIR\config"
  ${If} ${FileExists} "$INSTDIR\config"
    DetailPrint "⚠ Warning: Could not completely remove configuration"
  ${Else}
    DetailPrint "✓ Configuration removed"
  ${EndIf}
  
  ; Remove logs directory
  DetailPrint "Removing logs..."
  RMDir /r "$INSTDIR\logs"
  ${If} ${FileExists} "$INSTDIR\logs"
    DetailPrint "⚠ Warning: Could not completely remove logs"
  ${Else}
    DetailPrint "✓ Logs removed"
  ${EndIf}
  
  ; Remove uninstaller
  DetailPrint "Removing uninstaller..."
  Delete "$INSTDIR\Uninstall.exe"
  
  ; --------------------------------------------------------------------------
  ; Remove Desktop and Start Menu Shortcuts
  ; --------------------------------------------------------------------------
  ; Remove all shortcuts that may have been created during installation.
  ; This includes desktop shortcuts and Start Menu folder with all its contents.
  ;
  ; Requirements: 10.4
  ; --------------------------------------------------------------------------
  DetailPrint "Removing shortcuts..."
  
  ; Remove desktop shortcut
  DetailPrint "Removing desktop shortcut..."
  Delete "$DESKTOP\${APP_NAME}.lnk"
  ${If} ${FileExists} "$DESKTOP\${APP_NAME}.lnk"
    DetailPrint "⚠ Warning: Could not remove desktop shortcut"
  ${Else}
    DetailPrint "✓ Desktop shortcut removed"
  ${EndIf}
  
  ; Remove Start Menu shortcuts
  DetailPrint "Removing Start Menu shortcuts..."
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"
  ${If} ${FileExists} "$SMPROGRAMS\${APP_NAME}"
    DetailPrint "⚠ Warning: Could not completely remove Start Menu folder"
  ${Else}
    DetailPrint "✓ Start Menu shortcuts removed"
  ${EndIf}
  
  ; --------------------------------------------------------------------------
  ; Remove Registry Keys
  ; --------------------------------------------------------------------------
  ; Remove all registry entries created during installation:
  ; 1. Application registry keys (installation info)
  ; 2. Uninstall registry keys (Add/Remove Programs entry)
  ; 3. Auto-start registry entry (if present)
  ;
  ; Requirements: 10.5
  ; --------------------------------------------------------------------------
  DetailPrint "Removing registry entries..."
  
  ; Remove application registry keys
  DetailPrint "Removing application registry keys..."
  DeleteRegKey HKLM "${REGKEY}"
  
  ; Verify removal
  ReadRegStr $0 HKLM "${REGKEY}" "InstallDir"
  ${If} $0 != ""
    DetailPrint "⚠ Warning: Could not remove application registry keys"
  ${Else}
    DetailPrint "✓ Application registry keys removed"
  ${EndIf}
  
  ; Remove uninstall registry keys (Add/Remove Programs entry)
  DetailPrint "Removing Add/Remove Programs entry..."
  DeleteRegKey HKLM "${UNINSTALL_REGKEY}"
  
  ; Verify removal
  ReadRegStr $0 HKLM "${UNINSTALL_REGKEY}" "DisplayName"
  ${If} $0 != ""
    DetailPrint "⚠ Warning: Could not remove Add/Remove Programs entry"
  ${Else}
    DetailPrint "✓ Add/Remove Programs entry removed"
  ${EndIf}
  
  ; Remove auto-start registry entry (if present)
  DetailPrint "Removing auto-start entry..."
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"
  
  ; Verify removal
  ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"
  ${If} $0 != ""
    DetailPrint "⚠ Warning: Could not remove auto-start entry"
  ${Else}
    DetailPrint "✓ Auto-start entry removed (if it existed)"
  ${EndIf}
  
  ; --------------------------------------------------------------------------
  ; Prompt User About Removing Application Data
  ; --------------------------------------------------------------------------
  ; Ask the user if they want to remove application data stored in AppData.
  ; This includes user-specific configuration, database files, and other
  ; runtime data. We give the user the choice to preserve this data in case
  ; they plan to reinstall the application later.
  ;
  ; Requirements: 10.6
  ; --------------------------------------------------------------------------
  DetailPrint "Checking for application data..."
  
  ${If} ${FileExists} "$APPDATA\${APP_NAME}"
    DetailPrint "Application data found in user profile"
    
    MessageBox MB_YESNO|MB_ICONQUESTION "Remove application data?$\r$\n$\r$\nThe application has stored data in your user profile:$\r$\n$APPDATA\${APP_NAME}$\r$\n$\r$\nThis includes:$\r$\n- Configuration settings$\r$\n- Database files$\r$\n- User preferences$\r$\n$\r$\nDo you want to remove this data?$\r$\n$\r$\nClick Yes to remove all data, or No to keep it." IDNO SkipDataRemoval
    
    ; User chose to remove data
    DetailPrint "Removing application data..."
    RMDir /r "$APPDATA\${APP_NAME}"
    
    ; Verify removal
    ${If} ${FileExists} "$APPDATA\${APP_NAME}"
      DetailPrint "⚠ Warning: Could not completely remove application data"
      MessageBox MB_OK|MB_ICONEXCLAMATION "Some application data could not be removed.$\r$\n$\r$\nYou may need to manually delete:$\r$\n$APPDATA\${APP_NAME}"
    ${Else}
      DetailPrint "✓ Application data removed"
    ${EndIf}
    
    Goto DataRemovalComplete
    
    SkipDataRemoval:
      DetailPrint "Application data preserved at user's request"
      MessageBox MB_OK|MB_ICONINFORMATION "Application data has been preserved.$\r$\n$\r$\nYour settings and data are still available at:$\r$\n$APPDATA\${APP_NAME}$\r$\n$\r$\nYou can manually delete this folder later if desired."
    
    DataRemovalComplete:
  ${Else}
    DetailPrint "✓ No application data found"
  ${EndIf}
  
  ; --------------------------------------------------------------------------
  ; Verify Complete Removal and Clean Up Installation Directory
  ; --------------------------------------------------------------------------
  ; Verify that all critical components have been removed and attempt to
  ; remove the installation directory if it's empty or only contains
  ; non-critical files.
  ;
  ; Requirements: 10.6
  ; --------------------------------------------------------------------------
  DetailPrint "Verifying complete removal..."
  
  ; Check if critical files still exist
  ${If} ${FileExists} "$INSTDIR\python\python.exe"
    DetailPrint "⚠ Warning: Python runtime still exists"
  ${EndIf}
  
  ${If} ${FileExists} "$INSTDIR\run.py"
    DetailPrint "⚠ Warning: Application entry point still exists"
  ${EndIf}
  
  ${If} ${FileExists} "$INSTDIR\BitcoinSoloMinerMonitor.bat"
    DetailPrint "⚠ Warning: Launcher still exists"
  ${EndIf}
  
  ; Attempt to remove installation directory
  DetailPrint "Removing installation directory..."
  RMDir "$INSTDIR"
  
  ; Check if directory was removed
  ${If} ${FileExists} "$INSTDIR"
    DetailPrint "⚠ Installation directory still exists (may contain leftover files)"
    
    ; Count remaining files to inform user
    ; Note: This is informational only, we don't fail the uninstall
    MessageBox MB_OK|MB_ICONINFORMATION "Uninstallation completed with warnings.$\r$\n$\r$\nSome files or folders could not be removed from:$\r$\n$INSTDIR$\r$\n$\r$\nThis may be due to:$\r$\n- Files in use by another program$\r$\n- Insufficient permissions$\r$\n- User-created files in the directory$\r$\n$\r$\nYou can manually delete this folder if desired."
  ${Else}
    DetailPrint "✓ Installation directory removed successfully"
  ${EndIf}
  
  ; --------------------------------------------------------------------------
  ; Uninstallation Complete
  ; --------------------------------------------------------------------------
  DetailPrint "Uninstallation completed"
  DetailPrint "Thank you for using ${APP_NAME}"
  
SectionEnd

; ============================================================================
; SECTION DESCRIPTIONS
; ============================================================================
; These descriptions are displayed in the component selection page to help
; users understand what each optional component does.
; ============================================================================
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Core application files (required)."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Create shortcuts in the Start Menu."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on the Desktop."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartup} "Start the application automatically when Windows starts."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ============================================================================
; SECTION 7: HELPER FUNCTIONS
; ============================================================================
; These functions handle installer initialization, post-installation tasks,
; error handling, and uninstaller initialization.
;
; Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
; ============================================================================

; ----------------------------------------------------------------------------
; .onInit - Installer Initialization
; ----------------------------------------------------------------------------
; This function is called when the installer starts. It performs the following:
; 1. Checks Windows version (requires Windows 10 or later)
; 2. Detects existing installation and offers to uninstall
; 3. Sets default section selections
; 4. Reads configuration from CONFIG file if provided
;
; Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
; ----------------------------------------------------------------------------
Function .onInit
  ; Check Windows version
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "This application requires Windows 10 or later."
    Abort
  ${EndIf}
  
  ; Check if application is already installed
  ReadRegStr $0 HKLM "${UNINSTALL_REGKEY}" "UninstallString"
  ${If} $0 != ""
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "${APP_NAME} is already installed. $\n$\nClick 'OK' to remove the previous version or 'Cancel' to cancel this installation." IDOK uninst
    Abort
    
    uninst:
      ClearErrors
      ExecWait '$0 _?=$INSTDIR'
      
      ${If} ${Errors}
        MessageBox MB_OK|MB_ICONSTOP "Error removing previous version. Please manually uninstall before continuing."
        Abort
      ${EndIf}
  ${EndIf}
  
  ; Set default section selections
  SectionSetFlags ${SecCore} 17 ; Selected and read-only
  SectionSetFlags ${SecStartMenu} 1 ; Selected
  SectionSetFlags ${SecDesktop} 1 ; Selected
  SectionSetFlags ${SecStartup} 1 ; Selected
FunctionEnd

; ----------------------------------------------------------------------------
; .onInstSuccess - Post-Installation Success Handler
; ----------------------------------------------------------------------------
; This function is called when the installation completes successfully.
; It performs any final cleanup or notification tasks.
;
; Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
; ----------------------------------------------------------------------------
Function .onInstSuccess
  DetailPrint "Installation completed successfully!"
  DetailPrint "You can now launch ${APP_NAME} from:"
  DetailPrint "  - Desktop shortcut (if selected)"
  DetailPrint "  - Start Menu"
  DetailPrint "  - Installation directory: $INSTDIR"
  
  ; Log successful installation
  DetailPrint "Installation log saved to: $INSTDIR\logs\install.log"
FunctionEnd

; ----------------------------------------------------------------------------
; .onInstFailed - Installation Failure Handler
; ----------------------------------------------------------------------------
; This function is called when the installation fails or is aborted.
; It performs cleanup of partial installations and provides helpful
; error information to the user.
;
; Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
; ----------------------------------------------------------------------------
Function .onInstFailed
  DetailPrint "Installation failed or was cancelled"
  
  ; Display helpful message to user
  MessageBox MB_OK|MB_ICONEXCLAMATION "Installation of ${APP_NAME} was not completed.$\r$\n$\r$\nPossible reasons:$\r$\n- Installation was cancelled by user$\r$\n- Insufficient disk space$\r$\n- Insufficient permissions$\r$\n- Missing required components$\r$\n- Antivirus interference$\r$\n$\r$\nPlease check the installation log for details and try again.$\r$\n$\r$\nIf the problem persists, please visit:$\r$\n${WEBSITE}"
  
  ; Attempt to clean up partial installation
  DetailPrint "Attempting to clean up partial installation..."
  
  ; Remove installation directory if it exists and is not empty
  ${If} ${FileExists} "$INSTDIR"
    DetailPrint "Removing partial installation from: $INSTDIR"
    
    ; Remove any files that were copied
    Delete "$INSTDIR\BitcoinSoloMinerMonitor.bat"
    Delete "$INSTDIR\run.py"
    Delete "$INSTDIR\requirements.txt"
    Delete "$INSTDIR\README.md"
    RMDir /r "$INSTDIR\python"
    RMDir /r "$INSTDIR\src"
    RMDir /r "$INSTDIR\config"
    RMDir /r "$INSTDIR\logs"
    
    ; Try to remove the installation directory
    RMDir "$INSTDIR"
    
    ${If} ${FileExists} "$INSTDIR"
      DetailPrint "⚠ Warning: Could not completely remove partial installation"
      DetailPrint "You may need to manually delete: $INSTDIR"
    ${Else}
      DetailPrint "✓ Partial installation cleaned up successfully"
    ${EndIf}
  ${EndIf}
  
  ; Remove any registry keys that were created
  DetailPrint "Cleaning up registry entries..."
  DeleteRegKey HKLM "${REGKEY}"
  DeleteRegKey HKLM "${UNINSTALL_REGKEY}"
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"
  
  ; Remove any shortcuts that were created
  DetailPrint "Removing any shortcuts that were created..."
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"
  
  DetailPrint "Cleanup completed"
FunctionEnd

; ----------------------------------------------------------------------------
; un.onInit - Uninstaller Initialization
; ----------------------------------------------------------------------------
; This function is called when the uninstaller starts. It performs
; initialization tasks and confirms the user wants to uninstall.
;
; Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
; ----------------------------------------------------------------------------
Function un.onInit
  DetailPrint "Initializing uninstaller for ${APP_NAME}..."
  
  ; Confirm uninstallation with user
  MessageBox MB_YESNO|MB_ICONQUESTION "Are you sure you want to uninstall ${APP_NAME}?$\r$\n$\r$\nThis will remove the application from your computer.$\r$\n$\r$\nYou will be asked separately about removing your application data." IDYES continueUninstall
  
  ; User chose not to uninstall
  DetailPrint "Uninstallation cancelled by user"
  Abort
  
  continueUninstall:
    DetailPrint "User confirmed uninstallation"
    DetailPrint "Starting uninstallation process..."
FunctionEnd

; ----------------------------------------------------------------------------
; un.onUninstSuccess - Uninstallation Success Handler
; ----------------------------------------------------------------------------
; This function is called when the uninstallation completes successfully.
; It displays a confirmation message to the user.
;
; Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
; ----------------------------------------------------------------------------
Function un.onUninstSuccess
  DetailPrint "Uninstallation completed successfully!"
  
  ; Display success message to user
  MessageBox MB_OK|MB_ICONINFORMATION "${APP_NAME} has been successfully removed from your computer.$\r$\n$\r$\nThank you for using ${APP_NAME}!$\r$\n$\r$\nIf you have any feedback or suggestions, please visit:$\r$\n${WEBSITE}"
  
  DetailPrint "Thank you for using ${APP_NAME}"
FunctionEnd