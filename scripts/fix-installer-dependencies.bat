@echo off
REM Fix Installer Dependencies Issue
REM This script ensures fs-extra and other installer dependencies are properly isolated

echo === Fixing Installer Dependencies Issue ===

set "PROJECT_ROOT=%~dp0.."

echo [INFO] Installing fs-extra for main application (temporary fix)...
cd /d "%PROJECT_ROOT%"
npm install

echo [INFO] Checking for any installer files in main application...
if exist "%PROJECT_ROOT%\src\main.js" (
    echo [WARNING] Found main.js in src directory - this might be causing the issue
    echo [INFO] Renaming to avoid conflicts...
    ren "%PROJECT_ROOT%\src\main.js" "main.js.backup"
)

echo [INFO] Ensuring installer wizard dependencies are isolated...
cd /d "%PROJECT_ROOT%\installer\common\wizard"
if exist "package.json" (
    echo [INFO] Installing installer wizard dependencies...
    npm install
) else (
    echo [ERROR] Installer wizard package.json not found!
)

echo [INFO] Cleaning up any stray Node.js files in main application...
cd /d "%PROJECT_ROOT%"
if exist "main.js" del "main.js"

echo [SUCCESS] Dependencies fixed!
echo.
echo [NEXT STEPS]
echo 1. Try running the application again
echo 2. If the error persists, check for any remaining Node.js references
echo 3. The fs-extra dependency has been added to the main package.json as a temporary fix

pause