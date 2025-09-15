; Uninstaller Configuration for Bitcoin Solo Miner Monitor
; This file handles clean uninstallation process

; Function to stop running application
Function un.StopApplication
  DetailPrint "Stopping Bitcoin Solo Miner Monitor..."
  
  ; Find and terminate any running instances
  nsProcess::_FindProcess "python.exe"
  Pop $R0
  ${If} $R0 = 0
    DetailPrint "Found running Python processes, attempting to stop..."
    ; Try graceful shutdown first
    nsProcess::_KillProcess "python.exe"
    Pop $R0
    Sleep 2000
  ${EndIf}
  
  ; Check for any remaining processes
  nsProcess::_FindProcess "BitcoinSoloMinerMonitor.bat"
  Pop $R0
  ${If} $R0 = 0
    nsProcess::_KillProcess "BitcoinSoloMinerMonitor.bat"
    Pop $R0
  ${EndIf}
  
  DetailPrint "Application stopped"
FunctionEnd

; Function to remove application files
Function un.RemoveApplicationFiles
  DetailPrint "Removing application files..."
  
  ; Remove main application files
  Delete "$INSTDIR\run.py"
  Delete "$INSTDIR\requirements.txt"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\launch.bat"
  Delete "$INSTDIR\BitcoinSoloMinerMonitor.bat"
  Delete "$INSTDIR\Uninstall.exe"
  
  ; Remove Python runtime
  RMDir /r "$INSTDIR\python"
  
  ; Remove source code
  RMDir /r "$INSTDIR\src"
  
  ; Remove configuration (preserve user data)
  Delete "$INSTDIR\config\first_run.ini"
  
  ; Remove assets
  RMDir /r "$INSTDIR\assets"
  
  ; Remove logs (ask user first)
  ${If} ${FileExists} "$INSTDIR\logs"
    MessageBox MB_YESNO|MB_ICONQUESTION "Remove application logs?" IDNO SkipLogs
      RMDir /r "$INSTDIR\logs"
    SkipLogs:
  ${EndIf}
  
  DetailPrint "Application files removed"
FunctionEnd

; Function to remove user data
Function un.RemoveUserData
  DetailPrint "Checking for user data..."
  
  ; Check if user data exists
  ${If} ${FileExists} "$APPDATA\${APP_NAME}"
    MessageBox MB_YESNO|MB_ICONQUESTION \
      "Would you like to remove all application data including configurations, databases, and logs?$\r$\n$\r$\nThis cannot be undone." \
      IDNO SkipUserData
      
      DetailPrint "Removing user data..."
      RMDir /r "$APPDATA\${APP_NAME}"
      DetailPrint "User data removed"
      Goto EndUserData
      
    SkipUserData:
      DetailPrint "User data preserved"
      
    EndUserData:
  ${EndIf}
FunctionEnd

; Function to remove registry entries
Function un.RemoveRegistryEntries
  DetailPrint "Removing registry entries..."
  
  ; Remove application registry keys
  DeleteRegKey HKLM "${REGKEY}"
  DeleteRegKey HKLM "${UNINSTALL_REGKEY}"
  
  ; Remove startup entry if it exists
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"
  
  ; Remove file associations (if any were created)
  DeleteRegKey HKCR ".bsmm"
  DeleteRegKey HKCR "BitcoinSoloMinerMonitor"
  
  DetailPrint "Registry entries removed"
FunctionEnd

; Function to remove shortcuts
Function un.RemoveShortcuts
  DetailPrint "Removing shortcuts..."
  
  ; Remove desktop shortcut
  Call un.RemoveDesktopShortcut
  
  ; Remove Start menu shortcuts
  Call un.RemoveStartMenuShortcuts
  
  DetailPrint "Shortcuts removed"
FunctionEnd

; Function to clean temporary files
Function un.CleanTemporaryFiles
  DetailPrint "Cleaning temporary files..."
  
  ; Remove any temporary files created during installation
  Delete "$TEMP\BitcoinSoloMinerMonitor_*"
  
  ; Remove installer cache
  RMDir /r "$LOCALAPPDATA\BitcoinSoloMinerMonitor_InstallerCache"
  
  DetailPrint "Temporary files cleaned"
FunctionEnd

; Function to verify complete removal
Function un.VerifyRemoval
  DetailPrint "Verifying complete removal..."
  
  ; Check if installation directory is empty
  ${If} ${FileExists} "$INSTDIR\*.*"
    DetailPrint "Warning: Some files may remain in installation directory"
    MessageBox MB_OK|MB_ICONINFORMATION \
      "Some files remain in the installation directory:$\r$\n$INSTDIR$\r$\n$\r$\nYou may manually delete this folder if it's empty or contains only user-created files."
  ${Else}
    ; Remove installation directory if empty
    RMDir "$INSTDIR"
    DetailPrint "Installation directory removed"
  ${EndIf}
  
  DetailPrint "Uninstallation verification complete"
FunctionEnd

; Main uninstaller function
Function un.CompleteUninstall
  Call un.StopApplication
  Call un.RemoveShortcuts
  Call un.RemoveApplicationFiles
  Call un.RemoveRegistryEntries
  Call un.RemoveUserData
  Call un.CleanTemporaryFiles
  Call un.VerifyRemoval
FunctionEnd