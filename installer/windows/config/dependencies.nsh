; Dependencies Configuration for Bitcoin Solo Miner Monitor
; This file handles Python runtime bundling and dependency management

; Python runtime configuration
!define PYTHON_VERSION "3.11.7"
!define PYTHON_ARCH "amd64"
!define PYTHON_EMBED_URL "https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-${PYTHON_ARCH}.zip"
!define PYTHON_EMBED_FILE "python-${PYTHON_VERSION}-embed-${PYTHON_ARCH}.zip"

; Dependency paths
!define DEPS_DIR "$PLUGINSDIR\deps"
!define PYTHON_DIR "$INSTDIR\python"
!define VENV_DIR "$INSTDIR\venv"

; Function to download Python embeddable package
Function DownloadPythonRuntime
  DetailPrint "Downloading Python ${PYTHON_VERSION} runtime..."
  
  ; Create temporary directory
  CreateDirectory "${DEPS_DIR}"
  
  ; Download Python embeddable package
  NSISdl::download "${PYTHON_EMBED_URL}" "${DEPS_DIR}\${PYTHON_EMBED_FILE}"
  Pop $R0
  
  ${If} $R0 != "success"
    DetailPrint "Failed to download Python runtime: $R0"
    MessageBox MB_OK|MB_ICONSTOP "Failed to download Python runtime. Please check your internet connection and try again."
    Abort
  ${EndIf}
  
  DetailPrint "Python runtime downloaded successfully"
FunctionEnd

; Function to extract and configure Python runtime
Function InstallPythonRuntime
  DetailPrint "Installing Python runtime..."
  
  ; Create Python directory
  CreateDirectory "${PYTHON_DIR}"
  
  ; Extract Python embeddable package
  nsisunz::UnzipToLog "${DEPS_DIR}\${PYTHON_EMBED_FILE}" "${PYTHON_DIR}"
  Pop $R0
  
  ${If} $R0 != "success"
    DetailPrint "Failed to extract Python runtime: $R0"
    MessageBox MB_OK|MB_ICONSTOP "Failed to extract Python runtime."
    Abort
  ${EndIf}
  
  ; Configure Python path
  FileOpen $R1 "${PYTHON_DIR}\python311._pth" w
  FileWrite $R1 "python311.zip$\r$\n"
  FileWrite $R1 ".$\r$\n"
  FileWrite $R1 "..\\Lib\\site-packages$\r$\n"
  FileWrite $R1 "import site$\r$\n"
  FileClose $R1
  
  DetailPrint "Python runtime installed successfully"
FunctionEnd

; Function to install pip
Function InstallPip
  DetailPrint "Installing pip..."
  
  ; Download get-pip.py
  NSISdl::download "https://bootstrap.pypa.io/get-pip.py" "${DEPS_DIR}\get-pip.py"
  Pop $R0
  
  ${If} $R0 != "success"
    DetailPrint "Failed to download pip installer: $R0"
    MessageBox MB_OK|MB_ICONSTOP "Failed to download pip installer."
    Abort
  ${EndIf}
  
  ; Install pip
  ExecWait '"${PYTHON_DIR}\python.exe" "${DEPS_DIR}\get-pip.py" --target "${PYTHON_DIR}\Lib\site-packages"' $R0
  
  ${If} $R0 != 0
    DetailPrint "Failed to install pip (exit code: $R0)"
    MessageBox MB_OK|MB_ICONSTOP "Failed to install pip."
    Abort
  ${EndIf}
  
  DetailPrint "Pip installed successfully"
FunctionEnd

; Function to install Python dependencies
Function InstallDependencies
  DetailPrint "Installing Python dependencies..."
  
  ; Copy requirements.txt to temp directory
  CopyFiles "$INSTDIR\requirements.txt" "${DEPS_DIR}\requirements.txt"
  
  ; Install dependencies
  ExecWait '"${PYTHON_DIR}\python.exe" -m pip install -r "${DEPS_DIR}\requirements.txt" --target "${PYTHON_DIR}\Lib\site-packages" --no-warn-script-location' $R0
  
  ${If} $R0 != 0
    DetailPrint "Failed to install dependencies (exit code: $R0)"
    MessageBox MB_OK|MB_ICONSTOP "Failed to install Python dependencies."
    Abort
  ${EndIf}
  
  DetailPrint "Dependencies installed successfully"
FunctionEnd

; Function to create basic launcher (used by runtime_config.nsh for full launcher)
Function CreateBasicLauncher
  DetailPrint "Creating basic application launcher..."
  
  ; Create simple launcher script for testing
  FileOpen $R1 "$INSTDIR\launch_basic.bat" w
  FileWrite $R1 "@echo off$\r$\n"
  FileWrite $R1 "cd /d %~dp0$\r$\n"
  FileWrite $R1 "set PYTHONPATH=%~dp0python;%~dp0python\Lib\site-packages$\r$\n"
  FileWrite $R1 "python\python.exe run.py$\r$\n"
  FileClose $R1
  
  DetailPrint "Basic application launcher created"
FunctionEnd

; Function to verify installation
Function VerifyInstallation
  DetailPrint "Verifying installation..."
  
  ; Test Python installation
  ExecWait '"${PYTHON_DIR}\python.exe" --version' $R0
  
  ${If} $R0 != 0
    DetailPrint "Python installation verification failed"
    MessageBox MB_OK|MB_ICONEXCLAMATION "Python installation verification failed. The application may not work correctly."
  ${Else}
    DetailPrint "Python installation verified"
  ${EndIf}
  
  ; Test application import
  ExecWait '"${PYTHON_DIR}\python.exe" -c "import sys; sys.path.insert(0, r\"$INSTDIR\"); import src.main"' $R0
  
  ${If} $R0 != 0
    DetailPrint "Application verification failed"
    MessageBox MB_OK|MB_ICONEXCLAMATION "Application verification failed. Some dependencies may be missing."
  ${Else}
    DetailPrint "Application verified successfully"
  ${EndIf}
FunctionEnd

; Macro to install complete Python environment
!macro InstallPythonEnvironment
  Call DownloadPythonRuntime
  Call InstallPythonRuntime
  Call InstallPip
  Call InstallDependencies
  Call CreateBasicLauncher
  Call VerifyInstallation
!macroend