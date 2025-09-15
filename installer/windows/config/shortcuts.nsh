; Shortcuts Configuration for Bitcoin Solo Miner Monitor
; This file handles desktop and Start menu integration

; Function to create desktop shortcut
Function CreateDesktopShortcut
  DetailPrint "Creating desktop shortcut..."
  
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" \
    "$INSTDIR\BitcoinSoloMinerMonitor.bat" \
    "" \
    "$INSTDIR\assets\app_icon.ico" \
    0 \
    SW_SHOWMINIMIZED \
    "" \
    "Bitcoin Solo Miner Monitor - Unified mining hardware monitoring"
    
  DetailPrint "Desktop shortcut created"
FunctionEnd

; Function to create Start menu shortcuts
Function CreateStartMenuShortcuts
  DetailPrint "Creating Start menu shortcuts..."
  
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  
  ; Main application shortcut
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
    "$INSTDIR\BitcoinSoloMinerMonitor.bat" \
    "" \
    "$INSTDIR\assets\app_icon.ico" \
    0 \
    SW_SHOWMINIMIZED \
    "" \
    "Bitcoin Solo Miner Monitor - Unified mining hardware monitoring"
  
  ; Configuration shortcut
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Configuration.lnk" \
    "http://localhost:8000" \
    "" \
    "$INSTDIR\assets\config_icon.ico" \
    0 \
    SW_SHOWNORMAL \
    "" \
    "Open Bitcoin Solo Miner Monitor Configuration"
  
  ; Documentation shortcut
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Documentation.lnk" \
    "$INSTDIR\README.md" \
    "" \
    "$INSTDIR\assets\doc_icon.ico" \
    0 \
    SW_SHOWNORMAL \
    "" \
    "Bitcoin Solo Miner Monitor Documentation"
  
  ; Uninstaller shortcut
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
    "$INSTDIR\Uninstall.exe" \
    "" \
    "$INSTDIR\Uninstall.exe" \
    0 \
    SW_SHOWNORMAL \
    "" \
    "Uninstall Bitcoin Solo Miner Monitor"
    
  DetailPrint "Start menu shortcuts created"
FunctionEnd

; Function to remove desktop shortcut
Function RemoveDesktopShortcut
  Delete "$DESKTOP\${APP_NAME}.lnk"
FunctionEnd

; Function to remove Start menu shortcuts
Function RemoveStartMenuShortcuts
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Configuration.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Documentation.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"
FunctionEnd