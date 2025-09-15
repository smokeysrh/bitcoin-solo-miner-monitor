; Bitcoin Solo Miner Monitor - Enhanced Windows Installer Script
; Using NSIS (Nullsoft Scriptable Install System) with Python Runtime Bundling

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

; Set basic information
Name "${APP_NAME}"
OutFile "BitcoinSoloMinerMonitor-${VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKLM "${REGKEY}" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUnInstDetails show

; Define UI settings
!define MUI_ABORTWARNING
!define MUI_ICON "assets\installer_icon.ico"
!define MUI_UNICON "assets\uninstaller_icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "assets\welcome_image.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "assets\header_image.bmp"
!define MUI_HEADERIMAGE_RIGHT

; Define welcome page
!define MUI_WELCOMEPAGE_TITLE "Welcome to the ${APP_NAME} Setup Wizard"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of ${APP_NAME}, a unified monitoring and management solution for Bitcoin mining hardware.$\r$\n$\r$\nThis installer includes a complete Python runtime environment, so no additional software installation is required.$\r$\n$\r$\nBefore continuing, make sure you have administrator privileges on this computer.$\r$\n$\r$\nClick Next to continue."

; Define license page
!define MUI_LICENSEPAGE_CHECKBOX

; Define components page
!define MUI_COMPONENTSPAGE_SMALLDESC

; Define finish page
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_FINISHPAGE_RUN "$INSTDIR\BitcoinSoloMinerMonitor.bat"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_LINK "Visit ${WEBSITE} for more information"
!define MUI_FINISHPAGE_LINK_LOCATION "${WEBSITE}"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.md"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Show README"

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

; Define sections
Section "!Core Application (required)" SecCore
  SectionIn RO
  
  DetailPrint "Installing core application files..."
  
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
  File /r "..\common\assets\*.*"
  
  ; Create data directories
  CreateDirectory "$APPDATA\${APP_NAME}"
  CreateDirectory "$INSTDIR\logs"
  
  ; Install Python runtime and dependencies
  DetailPrint "Installing Python runtime environment..."
  !insertmacro InstallPythonEnvironment
  
  ; Write build information
  Call WriteBuildInfo
  
  ; Write registry keys
  WriteRegStr HKLM "${REGKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${REGKEY}" "Version" "${VERSION}"
  WriteRegStr HKLM "${REGKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "${REGKEY}" "Website" "${WEBSITE}"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  ; Add uninstall information to Add/Remove Programs
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "URLInfoAbout" "${WEBSITE}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayIcon" "$INSTDIR\assets\app_icon.ico,0"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "HelpLink" "${WEBSITE}"
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "NoRepair" 1
  
  ; Calculate and write installation size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "EstimatedSize" "$0"
  
  DetailPrint "Core application installation complete"
SectionEnd

Section "Start Menu Shortcuts" SecStartMenu
  DetailPrint "Creating Start Menu shortcuts..."
  Call CreateStartMenuShortcuts
SectionEnd

Section "Desktop Shortcut" SecDesktop
  DetailPrint "Creating Desktop shortcut..."
  Call CreateDesktopShortcut
SectionEnd

Section "Start with Windows" SecStartup
  DetailPrint "Configuring startup options..."
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}" "$INSTDIR\BitcoinSoloMinerMonitor.bat"
SectionEnd

Section /o "Development Tools" SecDev
  DetailPrint "Installing development tools..."
  
  ; Install additional development dependencies
  ExecWait '"$INSTDIR\python\python.exe" -m pip install pytest pytest-asyncio --target "$INSTDIR\python\Lib\site-packages"' $R0
  
  ; Create development shortcuts
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Development Console.lnk" \
    "cmd.exe" \
    '/k "cd /d "$INSTDIR" && set PYTHONPATH=$INSTDIR\python;$INSTDIR\python\Lib\site-packages"' \
    "$INSTDIR\assets\dev_icon.ico" \
    0 \
    SW_SHOWNORMAL \
    "" \
    "Development Console for Bitcoin Solo Miner Monitor"
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
  
  ${NSD_CreateLabel} 0 0 100% 20u "The installer can configure automatic network scanning to discover Bitcoin miners on your local network."
  Pop $0
  
  ${NSD_CreateCheckbox} 0 30u 100% 10u "Enable automatic miner discovery on startup"
  Pop $NetworkDiscoveryCheck
  
  ; Set default value
  ${NSD_Check} $NetworkDiscoveryCheck
  
  ${NSD_CreateLabel} 0 50u 100% 10u "Network range to scan (CIDR notation):"
  Pop $0
  
  ${NSD_CreateText} 0 65u 100% 12u "192.168.1.0/24"
  Pop $NetworkRangeText
  
  ${NSD_CreateLabel} 0 85u 100% 40u "Note: This is your local network address range. The default value (192.168.1.0/24) works for most home networks. If you have a different network configuration, please adjust accordingly. You can change this setting later in the application."
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
  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Core application files including Python runtime and all dependencies (required)."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Create shortcuts in the Start Menu for easy access."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on the Desktop."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartup} "Start the application automatically when Windows starts."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDev} "Install additional development tools and create development console shortcut."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Installer initialization
Function .onInit
  ; Get command line parameters
  ${GetParameters} $R0
  
  ; Get CONFIG parameter for silent installation
  ${GetOptions} $R0 "/CONFIG=" $CONFIG_FILE
  
  ; Check Windows version
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "This application requires Windows 10 or later."
    Abort
  ${EndIf}
  
  ; Check for existing installation
  ReadRegStr $0 HKLM "${UNINSTALL_REGKEY}" "UninstallString"
  ${If} $0 != ""
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
      "${APP_NAME} is already installed.$\r$\n$\r$\nClick 'OK' to remove the previous version or 'Cancel' to cancel this installation." \
      IDOK uninst
    Abort
    
    uninst:
      ClearErrors
      ExecWait '$0 /S _?=$INSTDIR'
      
      ${If} ${Errors}
        MessageBox MB_OK|MB_ICONSTOP "Error removing previous version. Please manually uninstall before continuing."
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
  DetailPrint "Installation completed successfully!"
  
  ; Create application data structure
  CreateDirectory "$APPDATA\${APP_NAME}\config"
  CreateDirectory "$APPDATA\${APP_NAME}\logs"
  CreateDirectory "$APPDATA\${APP_NAME}\data"
  
  ; Set appropriate permissions for application data
  AccessControl::GrantOnFile "$APPDATA\${APP_NAME}" "(BU)" "FullAccess"
  
  DetailPrint "Bitcoin Solo Miner Monitor has been installed successfully."
  DetailPrint "You can now launch the application from the Start Menu or Desktop shortcut."
FunctionEnd

; Handle installation failure
Function .onInstFailed
  MessageBox MB_OK|MB_ICONSTOP "Installation failed. Please check the installation log for details."
FunctionEnd

; Uninstaller initialization
Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 \
    "Are you sure you want to completely remove ${APP_NAME} and all of its components?" \
    IDYES +2
  Abort
FunctionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK \
    "${APP_NAME} has been successfully removed from your computer."
FunctionEnd