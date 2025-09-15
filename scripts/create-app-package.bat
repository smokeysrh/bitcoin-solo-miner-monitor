@echo off
REM Create Application Package for Installer
REM This script packages the application for distribution

echo === Creating Application Package ===

set "PROJECT_ROOT=%~dp0.."
set "PACKAGE_DIR=%PROJECT_ROOT%\installer\common\wizard\packages\windows"

echo [INFO] Cleaning package directory...
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%"

echo [INFO] Copying application files...

REM Copy Python backend
xcopy "%PROJECT_ROOT%\src" "%PACKAGE_DIR%\src" /E /I /Y

REM Copy configuration
xcopy "%PROJECT_ROOT%\config" "%PACKAGE_DIR%\config" /E /I /Y

REM Copy requirements and run script
copy "%PROJECT_ROOT%\requirements.txt" "%PACKAGE_DIR%\"
copy "%PROJECT_ROOT%\run.py" "%PACKAGE_DIR%\"

REM Copy README and LICENSE
copy "%PROJECT_ROOT%\README.md" "%PACKAGE_DIR%\"
if exist "%PROJECT_ROOT%\LICENSE" copy "%PROJECT_ROOT%\LICENSE" "%PACKAGE_DIR%\"

REM Ensure no Node.js files are copied
echo [INFO] Cleaning up any Node.js files...
if exist "%PACKAGE_DIR%\*.js" del "%PACKAGE_DIR%\*.js"
if exist "%PACKAGE_DIR%\package.json" del "%PACKAGE_DIR%\package.json"
if exist "%PACKAGE_DIR%\package-lock.json" del "%PACKAGE_DIR%\package-lock.json"
if exist "%PACKAGE_DIR%\node_modules" rmdir /s /q "%PACKAGE_DIR%\node_modules"

echo [INFO] Creating version info...
echo 1.0.0 > "%PACKAGE_DIR%\VERSION"

echo [INFO] Package created successfully at: %PACKAGE_DIR%
echo [SUCCESS] Application package ready for installer build

pause