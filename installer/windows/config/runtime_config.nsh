; Runtime Configuration for Bitcoin Solo Miner Monitor
; This file handles embedded Python environment path configuration

; Runtime path configuration
!define RUNTIME_PYTHON_DIR "$INSTDIR\python"
!define RUNTIME_SITE_PACKAGES "$INSTDIR\python\Lib\site-packages"
!define RUNTIME_SCRIPTS_DIR "$INSTDIR\python\Scripts"

; Function to configure runtime environment
Function ConfigureRuntimeEnvironment
  DetailPrint "Configuring runtime environment..."
  
  ; Create Python path configuration file
  FileOpen $R1 "${RUNTIME_PYTHON_DIR}\python311._pth" w
  FileWrite $R1 "python311.zip$\r$\n"
  FileWrite $R1 ".$\r$\n"
  FileWrite $R1 "Lib\site-packages$\r$\n"
  FileWrite $R1 "$\r$\n"
  FileWrite $R1 "# Enable site module for pip functionality$\r$\n"
  FileWrite $R1 "import site$\r$\n"
  FileClose $R1
  
  ; Create environment configuration script
  FileOpen $R1 "$INSTDIR\set_environment.bat" w
  FileWrite $R1 "@echo off$\r$\n"
  FileWrite $R1 "REM Bitcoin Solo Miner Monitor - Environment Configuration$\r$\n"
  FileWrite $R1 "set PYTHONHOME=$INSTDIR\python$\r$\n"
  FileWrite $R1 "set PYTHONPATH=$INSTDIR\python;$INSTDIR\python\Lib\site-packages$\r$\n"
  FileWrite $R1 "set PATH=$INSTDIR\python;$INSTDIR\python\Scripts;%PATH%$\r$\n"
  FileWrite $R1 "cd /d $INSTDIR$\r$\n"
  FileClose $R1
  
  DetailPrint "Runtime environment configured"
FunctionEnd

; Function to create application wrapper
Function CreateApplicationWrapper
  DetailPrint "Creating application wrapper..."
  
  ; Create main application launcher
  FileOpen $R1 "$INSTDIR\BitcoinSoloMinerMonitor.bat" w
  FileWrite $R1 "@echo off$\r$\n"
  FileWrite $R1 "REM Bitcoin Solo Miner Monitor - Application Launcher$\r$\n"
  FileWrite $R1 "cd /d %~dp0$\r$\n"
  FileWrite $R1 "call set_environment.bat$\r$\n"
  FileWrite $R1 "start /min python\python.exe run.py$\r$\n"
  FileClose $R1
  
  ; Create console launcher for debugging
  FileOpen $R1 "$INSTDIR\BitcoinSoloMinerMonitor_Console.bat" w
  FileWrite $R1 "@echo off$\r$\n"
  FileWrite $R1 "REM Bitcoin Solo Miner Monitor - Console Launcher$\r$\n"
  FileWrite $R1 "cd /d %~dp0$\r$\n"
  FileWrite $R1 "call set_environment.bat$\r$\n"
  FileWrite $R1 "echo Starting Bitcoin Solo Miner Monitor...$\r$\n"
  FileWrite $R1 "echo The application will be available at: http://localhost:8000$\r$\n"
  FileWrite $R1 "echo Press Ctrl+C to stop the application$\r$\n"
  FileWrite $R1 "echo.$\r$\n"
  FileWrite $R1 "python\python.exe run.py$\r$\n"
  FileWrite $R1 "pause$\r$\n"
  FileClose $R1
  
  ; Create service installer (for advanced users)
  FileOpen $R1 "$INSTDIR\install_service.bat" w
  FileWrite $R1 "@echo off$\r$\n"
  FileWrite $R1 "REM Bitcoin Solo Miner Monitor - Service Installer$\r$\n"
  FileWrite $R1 "echo Installing Bitcoin Solo Miner Monitor as Windows Service...$\r$\n"
  FileWrite $R1 "cd /d %~dp0$\r$\n"
  FileWrite $R1 "call set_environment.bat$\r$\n"
  FileWrite $R1 "python\python.exe -m pip install pywin32$\r$\n"
  FileWrite $R1 "python\python.exe src\service\install_service.py$\r$\n"
  FileWrite $R1 "pause$\r$\n"
  FileClose $R1
  
  DetailPrint "Application wrapper created"
FunctionEnd

; Function to test runtime configuration
Function TestRuntimeConfiguration
  DetailPrint "Testing runtime configuration..."
  
  ; Test Python execution
  ExecWait '"$INSTDIR\python\python.exe" --version' $R0
  
  ${If} $R0 != 0
    DetailPrint "Warning: Python runtime test failed"
    MessageBox MB_OK|MB_ICONEXCLAMATION "Python runtime test failed. The application may not work correctly."
  ${Else}
    DetailPrint "Python runtime test successful"
  ${EndIf}
  
  ; Test application import
  ExecWait '"$INSTDIR\python\python.exe" -c "import sys; sys.path.insert(0, r\"$INSTDIR\"); import src.main; print(\"Application import successful\")"' $R0
  
  ${If} $R0 != 0
    DetailPrint "Warning: Application import test failed"
    MessageBox MB_OK|MB_ICONEXCLAMATION "Application import test failed. Some dependencies may be missing."
  ${Else}
    DetailPrint "Application import test successful"
  ${EndIf}
  
  DetailPrint "Runtime configuration testing complete"
FunctionEnd

; Function to create runtime shortcuts
Function CreateRuntimeShortcuts
  DetailPrint "Creating runtime shortcuts..."
  
  ; Create Python console shortcut
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Python Console.lnk" \
    "cmd.exe" \
    '/k "cd /d "$INSTDIR" && call set_environment.bat && echo Python Console Ready"' \
    "$INSTDIR\assets\python_icon.ico" \
    0 \
    SW_SHOWNORMAL \
    "" \
    "Python Console for Bitcoin Solo Miner Monitor"
  
  ; Create application console shortcut
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME} (Console).lnk" \
    "$INSTDIR\BitcoinSoloMinerMonitor_Console.bat" \
    "" \
    "$INSTDIR\assets\console_icon.ico" \
    0 \
    SW_SHOWNORMAL \
    "" \
    "Bitcoin Solo Miner Monitor with Console Output"
  
  DetailPrint "Runtime shortcuts created"
FunctionEnd

; Macro to configure complete runtime environment
!macro ConfigureRuntimeEnvironment
  Call ConfigureRuntimeEnvironment
  Call CreateApplicationWrapper
  Call TestRuntimeConfiguration
  Call CreateRuntimeShortcuts
!macroend