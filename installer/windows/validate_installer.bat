@echo off
REM Installer Validation Script for Bitcoin Solo Miner Monitor
REM This script validates all installer components before building

echo === Bitcoin Solo Miner Monitor - Installer Validation ===
echo.

set "INSTALLER_DIR=%~dp0"
set "PROJECT_ROOT=%~dp0..\.."
set "ERRORS=0"

echo [INFO] Validating installer configuration...

REM Check NSIS configuration files
echo [INFO] Checking NSIS configuration files...

if exist "%INSTALLER_DIR%config\dependencies.nsh" (
    echo [OK] dependencies.nsh found
) else (
    echo [ERROR] dependencies.nsh missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%config\shortcuts.nsh" (
    echo [OK] shortcuts.nsh found
) else (
    echo [ERROR] shortcuts.nsh missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%config\uninstaller.nsh" (
    echo [OK] uninstaller.nsh found
) else (
    echo [ERROR] uninstaller.nsh missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%config\version.nsh" (
    echo [OK] version.nsh found
) else (
    echo [ERROR] version.nsh missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%config\runtime_config.nsh" (
    echo [OK] runtime_config.nsh found
) else (
    echo [ERROR] runtime_config.nsh missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%config\branding.nsh" (
    echo [OK] branding.nsh found
) else (
    echo [ERROR] branding.nsh missing
    set /a ERRORS+=1
)

REM Check main installer script
echo [INFO] Checking main installer script...

if exist "%INSTALLER_DIR%installer_final.nsi" (
    echo [OK] installer_final.nsi found
) else (
    echo [ERROR] installer_final.nsi missing
    set /a ERRORS+=1
)

REM Check assets
echo [INFO] Checking installer assets...

if exist "%INSTALLER_DIR%assets\installer_icon.ico" (
    echo [OK] installer_icon.ico found
) else (
    echo [ERROR] installer_icon.ico missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%assets\app_icon.ico" (
    echo [OK] app_icon.ico found
) else (
    echo [ERROR] app_icon.ico missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%assets\LICENSE.txt" (
    echo [OK] LICENSE.txt found
) else (
    echo [ERROR] LICENSE.txt missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%assets\welcome_image.bmp" (
    echo [OK] welcome_image.bmp found
) else (
    echo [ERROR] welcome_image.bmp missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%assets\header_image.bmp" (
    echo [OK] header_image.bmp found
) else (
    echo [ERROR] header_image.bmp missing
    set /a ERRORS+=1
)

REM Check Python runtime preparation scripts
echo [INFO] Checking Python runtime scripts...

if exist "%INSTALLER_DIR%scripts\prepare_python_runtime.py" (
    echo [OK] prepare_python_runtime.py found
) else (
    echo [ERROR] prepare_python_runtime.py missing
    set /a ERRORS+=1
)

if exist "%INSTALLER_DIR%scripts\prepare_runtime.bat" (
    echo [OK] prepare_runtime.bat found
) else (
    echo [ERROR] prepare_runtime.bat missing
    set /a ERRORS+=1
)

REM Check build scripts
echo [INFO] Checking build scripts...

if exist "%INSTALLER_DIR%build_final_installer.bat" (
    echo [OK] build_final_installer.bat found
) else (
    echo [ERROR] build_final_installer.bat missing
    set /a ERRORS+=1
)

REM Check project files
echo [INFO] Checking project files...

if exist "%PROJECT_ROOT%\requirements.txt" (
    echo [OK] requirements.txt found
) else (
    echo [ERROR] requirements.txt missing
    set /a ERRORS+=1
)

if exist "%PROJECT_ROOT%\run.py" (
    echo [OK] run.py found
) else (
    echo [ERROR] run.py missing
    set /a ERRORS+=1
)

if exist "%PROJECT_ROOT%\README.md" (
    echo [OK] README.md found
) else (
    echo [ERROR] README.md missing
    set /a ERRORS+=1
)

if exist "%PROJECT_ROOT%\src" (
    echo [OK] src directory found
) else (
    echo [ERROR] src directory missing
    set /a ERRORS+=1
)

REM Check NSIS installation
echo [INFO] Checking NSIS installation...

where makensis >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] NSIS found in PATH
    makensis /VERSION
) else (
    echo [WARNING] NSIS not found in PATH
    echo Please install NSIS from https://nsis.sourceforge.io/
)

REM Check required NSIS plugins
echo [INFO] Checking NSIS plugins...

set "NSIS_PLUGINS=%PROGRAMFILES(x86)%\NSIS\Plugins\x86-unicode"

if exist "%NSIS_PLUGINS%\nsProcess.dll" (
    echo [OK] nsProcess plugin found
) else (
    echo [WARNING] nsProcess plugin missing
    echo Download from: https://nsis.sourceforge.io/NsProcess_plugin
)

if exist "%NSIS_PLUGINS%\nsisunz.dll" (
    echo [OK] nsisunz plugin found
) else (
    echo [WARNING] nsisunz plugin missing
    echo Download from: https://nsis.sourceforge.io/Nsisunz_plug-in
)

if exist "%NSIS_PLUGINS%\AccessControl.dll" (
    echo [OK] AccessControl plugin found
) else (
    echo [WARNING] AccessControl plugin missing
    echo Download from: https://nsis.sourceforge.io/AccessControl_plug-in
)

REM Summary
echo.
echo === Validation Summary ===

if %ERRORS% equ 0 (
    echo [SUCCESS] All critical components found - installer ready to build!
    echo.
    echo To build the installer:
    echo 1. Run build_final_installer.bat
    echo 2. Check the distribution directory for the final installer
) else (
    echo [ERROR] Found %ERRORS% critical errors - please fix before building
    echo.
    echo Common fixes:
    echo - Ensure all configuration files are present
    echo - Verify asset files exist
    echo - Check project structure is complete
)

echo.
pause