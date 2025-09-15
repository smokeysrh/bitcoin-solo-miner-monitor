; Version Information for Bitcoin Solo Miner Monitor
; This file handles version metadata injection

; Version information
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "CompanyName" "${PUBLISHER}"
VIAddVersionKey "LegalCopyright" "© 2024 ${PUBLISHER}. Open Source Software."
VIAddVersionKey "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey "FileVersion" "${VERSION}.0"
VIAddVersionKey "InternalName" "BitcoinSoloMinerMonitor"
VIAddVersionKey "OriginalFilename" "BitcoinSoloMinerMonitor-${VERSION}-Setup.exe"
VIAddVersionKey "Comments" "Unified monitoring and management solution for Bitcoin mining hardware"

; Additional metadata
!define PRODUCT_WEB_SITE "${WEBSITE}"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; Build information (to be populated by build system)
!ifndef BUILD_DATE
  !define BUILD_DATE "Unknown"
!endif

!ifndef BUILD_COMMIT
  !define BUILD_COMMIT "Unknown"
!endif

!ifndef BUILD_NUMBER
  !define BUILD_NUMBER "0"
!endif

; Function to write build information
Function WriteBuildInfo
  DetailPrint "Writing build information..."
  
  ; Create build info file
  FileOpen $R1 "$INSTDIR\build_info.txt" w
  FileWrite $R1 "Bitcoin Solo Miner Monitor$\r$\n"
  FileWrite $R1 "Version: ${VERSION}$\r$\n"
  FileWrite $R1 "Build Date: ${BUILD_DATE}$\r$\n"
  FileWrite $R1 "Build Commit: ${BUILD_COMMIT}$\r$\n"
  FileWrite $R1 "Build Number: ${BUILD_NUMBER}$\r$\n"
  FileWrite $R1 "Installer: NSIS$\r$\n"
  FileClose $R1
  
  ; Write version to registry for update checking
  WriteRegStr HKLM "${REGKEY}" "Version" "${VERSION}"
  WriteRegStr HKLM "${REGKEY}" "BuildDate" "${BUILD_DATE}"
  WriteRegStr HKLM "${REGKEY}" "BuildCommit" "${BUILD_COMMIT}"
  WriteRegStr HKLM "${REGKEY}" "BuildNumber" "${BUILD_NUMBER}"
  
  DetailPrint "Build information written"
FunctionEnd