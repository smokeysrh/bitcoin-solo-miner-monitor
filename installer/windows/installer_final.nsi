; Bitcoin Solo Miner Monitor - Final Enhanced Windows Installer Script
; Professional installer with Python runtime bundling and branding

; Define constants
!define APP_NAME "Bitcoin Solo Miner Monitor"
!define PUBLISHER "Bitcoin Solo Miner Monitor"
!define VERSION "1.0.0"
!define WEBSITE "https://github.com/bitcoin-solo-miner-monitor"
!define REGKEY "Software\${APP_NAME}"
!define UNINSTALL_REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

; Include necessary NSIS libraries
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "nsDialogs.nsh"
!include "WinVer.nsh"
!include "nsProcess.nsh"
!include "nsisunz.nsh"

; Include custom configuration files
!include "config\dependencies.nsh"
!include "config\shortcuts.nsh"
!include "config\uninstaller.nsh"
!include "config\version.nsh"
!include "config\runtime_config.nsh"
!include "config\branding.nsh"

; Set basic information
Name "${APP_NAME}"
OutFile "BitcoinSoloMinerMonitor-${VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKLM "${REGKEY}" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUnInstDetails show

; Define UI settings with branding
!define MUI_ABORTWARNING
!define MUI_ICON "assets\installer_icon.ico"
!define MUI_UNICON "assets\uninstaller_icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "assets\welcome_image.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "assets\header_image.bmp"
!define MUI_HEADERIMAGE_RIGHT

; Apply branding customizations (defined in branding.nsh)
; Welcome, license, finish page customizations are in branding.nsh

; Define installer pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "assets\LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
Page custom NetworkDiscoveryPage NetworkDiscoveryPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Define uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Set language
!insertmacro MUI_LANGUAGE "English"

; Reserve files for solid compression
ReserveFile "network_discovery.ini"
ReserveFile "${NSISDIR}\Plugins\x86-unicode\nsDialogs.dll"
ReserveFile "${NSISDIR}\Plugins\x86-unicode\nsProcess.dll"
ReserveFile "${NSISDIR}\Plugins\x86-unicode\nsisunz.dll"

; Variables
Var CONFIG_FILE
Var Dialog
Var NetworkDiscoveryCheck
Var NetworkRangeText
Var INSTDATE

; Define sections
Section "!Core Application (required)" SecCore
  SectionIn RO
  
  DetailPrint "Installing ${APP_NAME} core files..."
  
  ; Set output directory
  SetOutPath "$INSTDIR"
  
  ; Copy application files
  File /r "..\..\src"
  File "..\..\run.py"
  File "..\..\requirements.txt"
  File "..\..\README.md"
  
  ; Copy configuration files
  SetOutPath "$INSTDIR\config"
  File /r "..\..\config\*.*"
  
  ; Copy assets
  SetOutPath "$INSTDIR\assets"
  File /r "assets\*.*"
  
  ; Create data directories
  CreateDirectory "$APPDATA\${APP_NAME}"
  CreateDirectory "$APPDATA\${APP_NAME}\config"
  CreateDirectory "$APPDATA\${APP_NAME}\logs"
  CreateDirectory "$APPDATA\${APP_NAME}\data"
  CreateDirectory "$INSTDIR\logs"
  
  ; Install Python runtime and dependencies
  DetailPrint "Installing Python runtime environment..."
  !insertmacro InstallPythonEnvironment
  
  ; Configure runtime environment
  DetailPrint "Configuring runtime environment..."
  !insertmacro ConfigureRuntimeEnvironment
  
  ; Write build information
  Call WriteBuildInfo
  
  ; Write registry keys
  WriteRegStr HKLM "${REGKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${REGKEY}" "Version" "${VERSION}"
  WriteRegStr HKLM "${REGKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "${REGKEY}" "Website" "${WEBSITE}"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  DetailPrint "Core application installation complete"
SectionEnd

Section "Start Menu Shortcuts" SecStartMenu
  DetailPrint "Creating Start Menu shortcuts..."
  ; Create Start Menu shortcuts using functions from branding.nsh
  ; This will be handled by ApplyBrandingEnhancements macro
SectionEnd

Section "Desktop Shortcut" SecDesktop
  DetailPrint "Creating Desktop shortcut..."
  ; Create Desktop shortcut using functions from branding.nsh
  ; This will be handled by ApplyBrandingEnhancements macro
SectionEnd

Section "Start with Windows" SecStartup
  DetailPrint "Configuring startup options..."
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}" "$INSTDIR\BitcoinSoloMinerMonitor.bat"
SectionEnd

Section /o "Development Tools" SecDev
  DetailPrint "Installing development tools..."
  
  ; Install additional development dependencies
  ExecWait '"$INSTDIR\python\python.exe" -m pip install pytest pytest-asyncio --target "$INSTDIR\python\Lib\site-packages"' $R0
  
  ${If} $R0 != 0
    DetailPrint "Warning: Failed to install development tools (exit code: $R0)"
  ${Else}
    DetailPrint "Development tools installed successfully"
  ${EndIf}
SectionEnd

; Uninstaller section
Section "Uninstall"
  ; Call complete uninstall function
  Call un.CompleteUninstall
SectionEnd

; Custom page for network discovery configuration
Function NetworkDiscoveryPage
  !insertmacro MUI_HEADER_TEXT "Network Discovery" "Configure automatic miner discovery on your network."
  
  nsDialogs::Create 1018
  Pop $Dialog
  
  ${If} $Dialog == error
    Abort
  ${EndIf}
  
  ${NSD_CreateLabel} 0 0 100% 30u "Bitcoin Solo Miner Monitor can automatically scan your network to discover Bitcoin miners.$\r$\n$\r$\nThis feature helps you quickly add miners to your monitoring dashboard without manual configuration."
  Pop $0
  
  ${NSD_CreateCheckbox} 0 40u 100% 10u "Enable automatic miner discovery on startup"
  Pop $NetworkDiscoveryCheck
  
  ; Set default value
  ${NSD_Check} $NetworkDiscoveryCheck
  
  ${NSD_CreateLabel} 0 60u 100% 10u "Network range to scan (CIDR notation):"
  Pop $0
  
  ${NSD_CreateText} 0 75u 100% 12u "192.168.1.0/24"
  Pop $NetworkRangeText
  
  ${NSD_CreateLabel} 0 95u 100% 50u "The network range specifies which IP addresses to scan for miners. The default value (192.168.1.0/24) covers most home networks (192.168.1.1 to 192.168.1.254).$\r$\n$\r$\nCommon alternatives:$\r$\n• 192.168.0.0/24 (192.168.0.1 to 192.168.0.254)$\r$\n• 10.0.0.0/24 (10.0.0.1 to 10.0.0.254)$\r$\n$\r$\nYou can change this setting later in the application."
  Pop $0
  
  nsDialogs::Show
FunctionEnd

Function NetworkDiscoveryPageLeave
  ${NSD_GetState} $NetworkDiscoveryCheck $0
  ${NSD_GetText} $NetworkRangeText $1
  
  ; Create config directory if it doesn't exist
  CreateDirectory "$INSTDIR\config"
  
  ; Save settings for first run
  WriteINIStr "$INSTDIR\config\first_run.ini" "NetworkDiscovery" "Enabled" "$0"
  WriteINIStr "$INSTDIR\config\first_run.ini" "NetworkDiscovery" "Range" "$1"
  WriteINIStr "$INSTDIR\config\first_run.ini" "Installation" "FirstRun" "true"
  WriteINIStr "$INSTDIR\config\first_run.ini" "Installation" "InstallDate" "$INSTDATE"
  WriteINIStr "$INSTDIR\config\first_run.ini" "Installation" "Version" "${VERSION}"
FunctionEnd

; Section descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Core application files including Python runtime and all dependencies. This component is required and cannot be deselected."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Create shortcuts in the Start Menu for easy access to the application, documentation, and configuration."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on the Desktop for quick access to Bitcoin Solo Miner Monitor."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartup} "Automatically start Bitcoin Solo Miner Monitor when Windows starts. Recommended for continuous monitoring."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDev} "Install additional development tools including pytest for testing. Only needed for developers."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Installer initialization
Function .onInit
  ; Get command line parameters
  ${GetParameters} $R0
  
  ; Get CONFIG parameter for silent installation
  ${GetOptions} $R0 "/CONFIG=" $CONFIG_FILE
  
  ; Check Windows version
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "Bitcoin Solo Miner Monitor requires Windows 10 or later.$\r$\n$\r$\nYour system: $(^Name)$\r$\nRequired: Windows 10 or newer"
    Abort
  ${EndIf}
  
  ; Check for existing installation
  ReadRegStr $0 HKLM "${UNINSTALL_REGKEY}" "UninstallString"
  ${If} $0 != ""
    ReadRegStr $1 HKLM "${UNINSTALL_REGKEY}" "DisplayVersion"
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
      "Bitcoin Solo Miner Monitor version $1 is already installed.$\r$\n$\r$\nClick 'OK' to remove the previous version and continue with the installation, or 'Cancel' to exit the installer." \
      IDOK uninst
    Abort
    
    uninst:
      ClearErrors
      ExecWait '$0 /S _?=$INSTDIR'
      
      ${If} ${Errors}
        MessageBox MB_OK|MB_ICONSTOP "Error removing the previous version. Please manually uninstall Bitcoin Solo Miner Monitor from Add/Remove Programs before continuing."
        Abort
      ${EndIf}
  ${EndIf}
  
  ; Set default section selections
  SectionSetFlags ${SecCore} 17        ; Selected and read-only
  SectionSetFlags ${SecStartMenu} 1    ; Selected
  SectionSetFlags ${SecDesktop} 1      ; Selected
  SectionSetFlags ${SecStartup} 0      ; Not selected by default
  SectionSetFlags ${SecDev} 0          ; Not selected by default
  
  ; Process configuration file if provided
  ${If} $CONFIG_FILE != ""
    ${If} ${FileExists} $CONFIG_FILE
      ; Read installation preferences from config file
      ReadINIStr $0 $CONFIG_FILE "Installation" "InstallDir"
      ${If} $0 != ""
        StrCpy $INSTDIR $0
      ${EndIf}
      
      ReadINIStr $0 $CONFIG_FILE "Installation" "CreateDesktopShortcut"
      ${If} $0 == "0"
        SectionSetFlags ${SecDesktop} 0
      ${EndIf}
      
      ReadINIStr $0 $CONFIG_FILE "Installation" "CreateStartMenuShortcut"
      ${If} $0 == "0"
        SectionSetFlags ${SecStartMenu} 0
      ${EndIf}
      
      ReadINIStr $0 $CONFIG_FILE "Installation" "StartOnBoot"
      ${If} $0 == "1"
        SectionSetFlags ${SecStartup} 1
      ${EndIf}
      
      ReadINIStr $0 $CONFIG_FILE "Installation" "InstallDevTools"
      ${If} $0 == "1"
        SectionSetFlags ${SecDev} 1
      ${EndIf}
    ${EndIf}
  ${EndIf}
  
  ; Set installation date
  ${GetTime} "" "L" $0 $1 $2 $3 $4 $5 $6
  StrCpy $INSTDATE "$2-$1-$0"
FunctionEnd

; Post-installation function
Function .onInstSuccess
  DetailPrint "Finalizing installation..."
  
  ; Apply branding enhancements
  !insertmacro ApplyBrandingEnhancements
  
  ; Set appropriate permissions for application data
  AccessControl::GrantOnFile "$APPDATA\${APP_NAME}" "(BU)" "FullAccess"
  
  DetailPrint "Bitcoin Solo Miner Monitor has been installed successfully!"
  DetailPrint "You can now launch the application from the Start Menu or Desktop shortcut."
FunctionEnd

; Handle installation failure
Function .onInstFailed
  MessageBox MB_OK|MB_ICONSTOP "Installation failed. Please check the installation log for details and try again.$\r$\n$\r$\nIf the problem persists, please visit our website for support."
FunctionEnd

; Uninstaller initialization
Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 \
    "Are you sure you want to completely remove Bitcoin Solo Miner Monitor and all of its components?$\r$\n$\r$\nThis will remove the application, Python runtime, and optionally your configuration data." \
    IDYES +2
  Abort
FunctionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK \
    "Bitcoin Solo Miner Monitor has been successfully removed from your computer.$\r$\n$\r$\nThank you for using Bitcoin Solo Miner Monitor!"
FunctionEnd