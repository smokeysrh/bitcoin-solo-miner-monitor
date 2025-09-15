; Branding Configuration for Bitcoin Solo Miner Monitor
; This file handles professional installer UI and branding

; Branding constants
!define BRAND_NAME "Bitcoin Solo Miner Monitor"
!define BRAND_TAGLINE "Unified Mining Hardware Monitoring"
!define BRAND_DESCRIPTION "Professional monitoring solution for Bitcoin mining operations"
!define BRAND_COPYRIGHT "© 2024 Bitcoin Solo Miner Monitor. Open Source Software."

; UI Customization
!define MUI_CUSTOMFUNCTION_GUIINIT CustomGUIInit
!define MUI_CUSTOMFUNCTION_UNGUIINIT un.CustomGUIInit

; Custom welcome page text
!define MUI_WELCOMEPAGE_TITLE_3LINES
!define MUI_WELCOMEPAGE_TITLE "Welcome to ${BRAND_NAME}"
!define MUI_WELCOMEPAGE_TEXT "This setup wizard will install ${BRAND_NAME} on your computer.$\r$\n$\r$\n${BRAND_DESCRIPTION}$\r$\n$\r$\nKey Features:$\r$\n• Real-time monitoring of Bitcoin mining hardware$\r$\n• Unified dashboard for multiple miner types$\r$\n• Email alerts and notifications$\r$\n• Historical performance tracking$\r$\n• Network discovery and auto-configuration$\r$\n$\r$\nThis installer includes a complete Python runtime environment - no additional software installation required.$\r$\n$\r$\nClick Next to continue."

; Custom finish page
!define MUI_FINISHPAGE_TITLE_3LINES
!define MUI_FINISHPAGE_TITLE "Installation Complete"
!define MUI_FINISHPAGE_TEXT "${BRAND_NAME} has been successfully installed on your computer.$\r$\n$\r$\nTo get started:$\r$\n1. Launch the application using the desktop or Start menu shortcut$\r$\n2. Open your web browser to http://localhost:8000$\r$\n3. Follow the first-run setup wizard$\r$\n4. Add your Bitcoin miners and start monitoring$\r$\n$\r$\nFor support and documentation, visit our website or check the README file.$\r$\n$\r$\nClick Finish to complete the installation."

; Custom license page
!define MUI_LICENSEPAGE_TEXT_TOP "Please review the license agreement before installing ${BRAND_NAME}."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "If you accept the terms of the agreement, check the box below. You must accept the agreement to install ${BRAND_NAME}."

; Custom directory page
!define MUI_DIRECTORYPAGE_TEXT_TOP "Setup will install ${BRAND_NAME} in the following folder.$\r$\n$\r$\nTo install in a different folder, click Browse and select another folder. Click Next to continue."

; Custom components page
!define MUI_COMPONENTSPAGE_TEXT_TOP "Select the components you want to install and clear the components you do not want to install. Click Next to continue."
!define MUI_COMPONENTSPAGE_TEXT_COMPLIST "Select components to install:"

; Function to customize GUI appearance
Function CustomGUIInit
  ; Set window title
  SendMessage $HWNDPARENT ${WM_SETTEXT} 0 "STR:${BRAND_NAME} Setup"
  
  ; Center the window
  System::Call "user32::GetSystemMetrics(i 0) i .r0"  ; SM_CXSCREEN
  System::Call "user32::GetSystemMetrics(i 1) i .r1"  ; SM_CYSCREEN
  System::Call "user32::GetWindowRect(i $HWNDPARENT, i .r2)"
  System::Call "*$2(i .r3, i .r4, i .r5, i .r6)"
  IntOp $7 $5 - $3  ; width
  IntOp $8 $6 - $4  ; height
  IntOp $9 $0 - $7  ; screen width - window width
  IntOp $9 $9 / 2   ; center x
  IntOp $10 $1 - $8 ; screen height - window height
  IntOp $10 $10 / 2 ; center y
  System::Call "user32::SetWindowPos(i $HWNDPARENT, i 0, i $9, i $10, i 0, i 0, i 0x0001)"
FunctionEnd

; Function to customize uninstaller GUI
Function un.CustomGUIInit
  SendMessage $HWNDPARENT ${WM_SETTEXT} 0 "STR:Uninstall ${BRAND_NAME}"
FunctionEnd

; Function to create branded shortcuts with descriptions
Function CreateBrandedShortcuts
  DetailPrint "Creating branded shortcuts..."
  
  ; Check if desktop shortcut section is selected
  SectionGetFlags ${SecDesktop} $R0
  IntOp $R0 $R0 & ${SF_SELECTED}
  ${If} $R0 != 0
    ; Main application shortcut with detailed description
    CreateShortcut "$DESKTOP\${BRAND_NAME}.lnk" \
      "$INSTDIR\BitcoinSoloMinerMonitor.bat" \
      "" \
      "$INSTDIR\assets\app_icon.ico" \
      0 \
      SW_SHOWMINIMIZED \
      "" \
      "${BRAND_TAGLINE} - Monitor your Bitcoin mining hardware with real-time statistics, alerts, and performance tracking"
  ${EndIf}
  
  ; Check if Start Menu shortcuts section is selected
  SectionGetFlags ${SecStartMenu} $R0
  IntOp $R0 $R0 & ${SF_SELECTED}
  ${If} $R0 != 0
    ; Start menu folder with comprehensive shortcuts
    CreateDirectory "$SMPROGRAMS\${BRAND_NAME}"
    
    ; Main application
    CreateShortcut "$SMPROGRAMS\${BRAND_NAME}\${BRAND_NAME}.lnk" \
      "$INSTDIR\BitcoinSoloMinerMonitor.bat" \
      "" \
      "$INSTDIR\assets\app_icon.ico" \
      0 \
      SW_SHOWMINIMIZED \
      "" \
      "${BRAND_TAGLINE}"
    
    ; Web interface shortcut
    CreateShortcut "$SMPROGRAMS\${BRAND_NAME}\Open Web Interface.lnk" \
      "http://localhost:8000" \
      "" \
      "$INSTDIR\assets\web_icon.ico" \
      0 \
      SW_SHOWNORMAL \
      "" \
      "Open ${BRAND_NAME} web interface in your default browser"
    
    ; Console version for troubleshooting
    CreateShortcut "$SMPROGRAMS\${BRAND_NAME}\${BRAND_NAME} (Console).lnk" \
      "$INSTDIR\BitcoinSoloMinerMonitor_Console.bat" \
      "" \
      "$INSTDIR\assets\console_icon.ico" \
      0 \
      SW_SHOWNORMAL \
      "" \
      "Launch ${BRAND_NAME} with console output for troubleshooting"
    
    ; Documentation
    CreateShortcut "$SMPROGRAMS\${BRAND_NAME}\Documentation.lnk" \
      "$INSTDIR\README.md" \
      "" \
      "$INSTDIR\assets\doc_icon.ico" \
      0 \
      SW_SHOWNORMAL \
      "" \
      "View ${BRAND_NAME} documentation and user guide"
    
    ; Configuration folder
    CreateShortcut "$SMPROGRAMS\${BRAND_NAME}\Configuration Folder.lnk" \
      "$APPDATA\${BRAND_NAME}" \
      "" \
      "$INSTDIR\assets\folder_icon.ico" \
      0 \
      SW_SHOWNORMAL \
      "" \
      "Open ${BRAND_NAME} configuration and data folder"
    
    ; Uninstaller
    CreateShortcut "$SMPROGRAMS\${BRAND_NAME}\Uninstall ${BRAND_NAME}.lnk" \
      "$INSTDIR\Uninstall.exe" \
      "" \
      "$INSTDIR\Uninstall.exe" \
      0 \
      SW_SHOWNORMAL \
      "" \
      "Uninstall ${BRAND_NAME} from your computer"
  ${EndIf}
  
  DetailPrint "Branded shortcuts created"
FunctionEnd

; Function to create Windows integration
Function CreateWindowsIntegration
  DetailPrint "Setting up Windows integration..."
  
  ; Register application with Windows
  WriteRegStr HKLM "Software\Classes\Applications\BitcoinSoloMinerMonitor.exe\shell\open\command" "" '"$INSTDIR\BitcoinSoloMinerMonitor.bat"'
  WriteRegStr HKLM "Software\Classes\Applications\BitcoinSoloMinerMonitor.exe" "FriendlyAppName" "${BRAND_NAME}"
  
  ; Add to Windows "Open With" menu for configuration files
  WriteRegStr HKLM "Software\Classes\.json\OpenWithList\BitcoinSoloMinerMonitor.exe" "" ""
  WriteRegStr HKLM "Software\Classes\.conf\OpenWithList\BitcoinSoloMinerMonitor.exe" "" ""
  
  ; Register URL protocol for web interface (optional)
  WriteRegStr HKLM "Software\Classes\bsmm" "" "URL:Bitcoin Solo Miner Monitor Protocol"
  WriteRegStr HKLM "Software\Classes\bsmm" "URL Protocol" ""
  WriteRegStr HKLM "Software\Classes\bsmm\DefaultIcon" "" "$INSTDIR\assets\app_icon.ico,0"
  WriteRegStr HKLM "Software\Classes\bsmm\shell\open\command" "" '"$INSTDIR\BitcoinSoloMinerMonitor.bat" "%1"'
  
  ; Add to Windows Firewall exceptions (if needed)
  ; This is commented out as it requires additional permissions
  ; ExecWait 'netsh advfirewall firewall add rule name="${BRAND_NAME}" dir=in action=allow program="$INSTDIR\python\python.exe" enable=yes'
  
  DetailPrint "Windows integration configured"
FunctionEnd

; Function to create professional Add/Remove Programs entry
Function CreateProfessionalUninstallEntry
  DetailPrint "Creating Add/Remove Programs entry..."
  
  ; Enhanced uninstall registry entries
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayName" "${BRAND_NAME}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "URLInfoAbout" "${WEBSITE}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "HelpLink" "${WEBSITE}/docs"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "URLUpdateInfo" "${WEBSITE}/releases"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayIcon" "$INSTDIR\assets\app_icon.ico,0"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "QuietUninstallString" "$INSTDIR\Uninstall.exe /S"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "InstallDate" "$INSTDATE"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "Comments" "${BRAND_DESCRIPTION}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "Readme" "$INSTDIR\README.md"
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "NoRepair" 1
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "VersionMajor" 1
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "VersionMinor" 0
  
  ; Calculate and write installation size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "EstimatedSize" "$0"
  
  DetailPrint "Add/Remove Programs entry created"
FunctionEnd

; Function to show post-installation information
Function ShowPostInstallInfo
  ; Create information file
  FileOpen $R1 "$INSTDIR\GETTING_STARTED.txt" w
  FileWrite $R1 "${BRAND_NAME} - Getting Started$\r$\n"
  FileWrite $R1 "================================$\r$\n"
  FileWrite $R1 "$\r$\n"
  FileWrite $R1 "Thank you for installing ${BRAND_NAME}!$\r$\n"
  FileWrite $R1 "$\r$\n"
  FileWrite $R1 "Quick Start:$\r$\n"
  FileWrite $R1 "1. Launch the application from your desktop or Start menu$\r$\n"
  FileWrite $R1 "2. Open your web browser to http://localhost:8000$\r$\n"
  FileWrite $R1 "3. Follow the first-run setup wizard$\r$\n"
  FileWrite $R1 "4. Add your Bitcoin miners and start monitoring$\r$\n"
  FileWrite $R1 "$\r$\n"
  FileWrite $R1 "Support:$\r$\n"
  FileWrite $R1 "- Documentation: README.md in installation folder$\r$\n"
  FileWrite $R1 "- Website: ${WEBSITE}$\r$\n"
  FileWrite $R1 "- Configuration: $APPDATA\${BRAND_NAME}$\r$\n"
  FileWrite $R1 "$\r$\n"
  FileWrite $R1 "Installation Details:$\r$\n"
  FileWrite $R1 "- Version: ${VERSION}$\r$\n"
  FileWrite $R1 "- Install Date: $INSTDATE$\r$\n"
  FileWrite $R1 "- Install Location: $INSTDIR$\r$\n"
  FileWrite $R1 "- Data Location: $APPDATA\${BRAND_NAME}$\r$\n"
  FileClose $R1
FunctionEnd

; Macro to apply all branding enhancements
!macro ApplyBrandingEnhancements
  Call CreateBrandedShortcuts
  Call CreateWindowsIntegration
  Call CreateProfessionalUninstallEntry
  Call ShowPostInstallInfo
!macroend