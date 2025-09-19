; Bitcoin Solo Miner Monitor - Windows Installer Script
; Using NSIS (Nullsoft Scriptable Install System)

; Define constants
!define APP_NAME "Bitcoin Solo Miner Monitor"
!define PUBLISHER "Bitcoin Solo Miner Monitor"
; VERSION is passed as a command line parameter via /DVERSION=x.x.x
!ifndef VERSION
  !define VERSION "0.1.0"
!endif
!define WEBSITE "https://github.com/smokeysrh/bitcoin-solo-miner-monitor"
!define REGKEY "Software\${APP_NAME}"
!define UNINSTALL_REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

; Include necessary NSIS libraries
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "nsDialogs.nsh"
!include "WinVer.nsh"
; !include "StrFunc.nsh"

; Set basic information
Name "${APP_NAME}"
; Use OUTPUT_FILE if provided, otherwise use default naming
!ifdef OUTPUT_FILE
  OutFile "${OUTPUT_FILE}"
!else
  OutFile "BitcoinSoloMinerMonitor-${VERSION}-Setup.exe"
!endif
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKLM "${REGKEY}" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

; Define UI settings
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

; Define installer pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\common\assets\LICENSE.txt"
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

; Define sections
Section "!Core Files (required)" SecCore
  SectionIn RO
  
  ; Set output directory
  SetOutPath "$INSTDIR"
  
  ; Add files from the app directory passed as parameter
  !ifdef APP_DIR
    File /r "${APP_DIR}\*.*"
  !else
    File /r "..\build\windows\*.*"
  !endif
  
  ; Create data directory
  CreateDirectory "$APPDATA\${APP_NAME}"
  
  ; Write registry keys
  WriteRegStr HKLM "${REGKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${REGKEY}" "Version" "${VERSION}"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  ; Add uninstall information to Add/Remove Programs
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "URLInfoAbout" "${WEBSITE}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayIcon" "$INSTDIR\BitcoinSoloMinerMonitor.bat,0"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "NoRepair" 1
  
  ; Get installation size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "EstimatedSize" "$0"
SectionEnd

Section "Start Menu Shortcuts" SecStartMenu
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\BitcoinSoloMinerMonitor.bat"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Desktop Shortcut" SecDesktop
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\BitcoinSoloMinerMonitor.bat"
SectionEnd

Section "Start with Windows" SecStartup
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}" "$INSTDIR\BitcoinSoloMinerMonitor.exe --minimized"
SectionEnd

Section "Uninstall"
  ; Remove files and directories
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"
  
  ; Remove shortcuts
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"
  
  ; Remove registry keys
  DeleteRegKey HKLM "${UNINSTALL_REGKEY}"
  DeleteRegKey HKLM "${REGKEY}"
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"
  
  ; Ask if user wants to remove data
  MessageBox MB_YESNO|MB_ICONQUESTION "Would you like to remove all application data as well?" IDNO SkipDataRemoval
    RMDir /r "$APPDATA\${APP_NAME}"
  SkipDataRemoval:
SectionEnd

; Custom page for network discovery
Var Dialog
Var NetworkDiscoveryCheck
Var NetworkRangeText
Var CONFIG_FILE

Function NetworkDiscoveryPage
  !insertmacro MUI_HEADER_TEXT "Network Discovery" "Configure automatic miner discovery on your network."
  
  nsDialogs::Create 1018
  Pop $Dialog
  
  ${If} $Dialog == error
    Abort
  ${EndIf}
  
  ${NSD_CreateLabel} 0 0 100% 20u "The installer can scan your network to automatically discover miners."
  Pop $0
  
  ${NSD_CreateCheckbox} 0 30u 100% 10u "Enable automatic miner discovery on startup"
  Pop $NetworkDiscoveryCheck
  
  ; Set default value or use value from config file
  ${If} $CONFIG_FILE != ""
    ${If} ${FileExists} $CONFIG_FILE
      ReadINIStr $0 $CONFIG_FILE "NetworkDiscovery" "Enabled"
      ${If} $0 == "1"
        ${NSD_Check} $NetworkDiscoveryCheck
      ${Else}
        ${NSD_Uncheck} $NetworkDiscoveryCheck
      ${EndIf}
    ${Else}
      ${NSD_Check} $NetworkDiscoveryCheck
    ${EndIf}
  ${Else}
    ${NSD_Check} $NetworkDiscoveryCheck
  ${EndIf}
  
  ${NSD_CreateLabel} 0 50u 100% 10u "Network range to scan:"
  Pop $0
  
  ${NSD_CreateText} 0 65u 100% 12u "192.168.1.0/24"
  Pop $NetworkRangeText
  
  ; Set default value or use value from config file
  ${If} $CONFIG_FILE != ""
    ${If} ${FileExists} $CONFIG_FILE
      ReadINIStr $0 $CONFIG_FILE "NetworkDiscovery" "Range"
      ${If} $0 != ""
        ${NSD_SetText} $NetworkRangeText $0
      ${EndIf}
    ${EndIf}
  ${EndIf}
  
  ${NSD_CreateLabel} 0 85u 100% 40u "Note: This is your local network address range. The default value works for most home networks. If you have a different network configuration, please adjust accordingly."
  Pop $0
  
  nsDialogs::Show
FunctionEnd

Function NetworkDiscoveryPageLeave
  ${NSD_GetState} $NetworkDiscoveryCheck $0
  ${NSD_GetText} $NetworkRangeText $1
  
  ; Create config directory if it doesn't exist
  CreateDirectory "$INSTDIR\config"
  
  ; Save settings to be used during first run
  WriteINIStr "$INSTDIR\config\first_run.ini" "NetworkDiscovery" "Enabled" "$0"
  WriteINIStr "$INSTDIR\config\first_run.ini" "NetworkDiscovery" "Range" "$1"
  
  ; If config file was provided, also save component selections
  ${If} $CONFIG_FILE != ""
    ${If} ${FileExists} $CONFIG_FILE
      ReadINIStr $0 $CONFIG_FILE "Components" "Database"
      WriteINIStr "$INSTDIR\config\first_run.ini" "Components" "Database" "$0"
      
      ReadINIStr $0 $CONFIG_FILE "Components" "Dashboard"
      WriteINIStr "$INSTDIR\config\first_run.ini" "Components" "Dashboard" "$0"
      
      ReadINIStr $0 $CONFIG_FILE "Components" "Alert"
      WriteINIStr "$INSTDIR\config\first_run.ini" "Components" "Alert" "$0"
      
      ReadINIStr $0 $CONFIG_FILE "Components" "API"
      WriteINIStr "$INSTDIR\config\first_run.ini" "Components" "API" "$0"
      
      ReadINIStr $0 $CONFIG_FILE "Components" "Documentation"
      WriteINIStr "$INSTDIR\config\first_run.ini" "Components" "Documentation" "$0"
    ${EndIf}
  ${EndIf}
FunctionEnd

; Descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Core application files (required)."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Create shortcuts in the Start Menu."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on the Desktop."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartup} "Start the application automatically when Windows starts."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Initialize string functions (commented out for now)
; ${StrLoc}
; ${StrTok}

; Check system requirements
Function .onInit
  ; Initialize CONFIG_FILE variable
  StrCpy $CONFIG_FILE ""
  
  ; Get command line parameters
  ${GetParameters} $R0
  
  ; Get CONFIG parameter
  ${GetOptions} $R0 "/CONFIG=" $CONFIG_FILE
  
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
  
  ; If CONFIG_FILE is provided, read settings from it
  ${If} $CONFIG_FILE != ""
    ${If} ${FileExists} $CONFIG_FILE
      ; Read installation directory
      ReadINIStr $0 $CONFIG_FILE "Installation" "InstallDir"
      ${If} $0 != ""
        StrCpy $INSTDIR $0
      ${EndIf}
      
      ; Read desktop shortcut preference
      ReadINIStr $0 $CONFIG_FILE "Installation" "CreateDesktopShortcut"
      ${If} $0 == "0"
        SectionSetFlags ${SecDesktop} 0
      ${Else}
        SectionSetFlags ${SecDesktop} 1
      ${EndIf}
      
      ; Read start menu shortcut preference
      ReadINIStr $0 $CONFIG_FILE "Installation" "CreateStartMenuShortcut"
      ${If} $0 == "0"
        SectionSetFlags ${SecStartMenu} 0
      ${Else}
        SectionSetFlags ${SecStartMenu} 1
      ${EndIf}
      
      ; Read startup preference
      ReadINIStr $0 $CONFIG_FILE "Installation" "StartOnBoot"
      ${If} $0 == "0"
        SectionSetFlags ${SecStartup} 0
      ${Else}
        SectionSetFlags ${SecStartup} 1
      ${EndIf}
    ${EndIf}
  ${EndIf}
FunctionEnd