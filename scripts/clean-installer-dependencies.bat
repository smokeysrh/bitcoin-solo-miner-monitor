@echo off
REM Clean and Reinstall Installer Dependencies
REM This script removes fs-extra from installer wizard and reinstalls clean dependencies

echo === Cleaning Installer Dependencies ===

set "PROJECT_ROOT=%~dp0.."
set "INSTALLER_DIR=%PROJECT_ROOT%\installer\common\wizard"

echo [INFO] Cleaning installer wizard node_modules...
cd /d "%INSTALLER_DIR%"
if exist "node_modules" rmdir /s /q "node_modules"
if exist "package-lock.json" del "package-lock.json"

echo [INFO] Installing clean dependencies (without fs-extra)...
npm install

echo [INFO] Verifying fs-extra is not installed...
if exist "node_modules\fs-extra" (
    echo [ERROR] fs-extra is still present! Check package.json
    pause
    exit /b 1
) else (
    echo [SUCCESS] fs-extra successfully removed from installer wizard
)

echo [INFO] Cleaning main application dependencies...
cd /d "%PROJECT_ROOT%"
if exist "node_modules" rmdir /s /q "node_modules"
if exist "package-lock.json" del "package-lock.json"

echo [INFO] Installing main application dependencies...
npm install

echo [SUCCESS] All dependencies cleaned and reinstalled!
echo.
echo [NEXT STEPS]
echo 1. Test the installer wizard: npm start (from installer/common/wizard directory)
echo 2. Test the main application: python run.py
echo 3. The fs-extra dependency issue should now be resolved

pause