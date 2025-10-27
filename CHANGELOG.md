# Changelog

All notable changes to Bitcoin Solo Miner Monitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/0.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.2] - 2025-10-27

### 🚀 Major Improvements

#### Windows Installer Refactoring
- **Complete installer system overhaul** for simplicity, speed, and reliability
  - Consolidated 3 installer scripts into 1 unified `installer.nsi`
  - Eliminated 6 configuration files and complex macro dependencies
  - Reduced installation time from 5-10 minutes to under 60 seconds
  - Pre-bundled Python runtime for offline installation (no internet required)
  - Single source of truth for version management (`src/backend/version.py`)
  - Automated build process with `build.ps1` script
  - One-time bundle preparation with `prepare-bundle.ps1`
  - Inline launcher creation (prevents bugs from forgotten macro calls)
  - Comprehensive error handling and verification
  - Improved uninstaller with user data preservation options

### 🐛 Bug Fixes
- **Critical**: Fixed Windows installer not launching app after installation
  - Resolved through complete installer refactoring
  - Improved launcher batch file with instance checking and browser auto-launch
  - Added 3-second startup delay for proper server initialization
  - Added helper scripts and documentation for installer fix
  - Updated .gitignore to exclude installer build staging directories

### 🧹 Code Cleanup
- **Installer System Cleanup**
  - Removed old installer scripts (`installer_enhanced.nsi`, `installer_final.nsi`)
  - Removed old build scripts (`build_installer.bat`, `build_final_installer.bat`)
  - Removed entire `config/` directory with legacy .nsh files
  - Removed entire `scripts/` directory with unused Python scripts
  - Removed test installer executables from repository
  - Cleaned up redundant and unused code
- **Project Organization**
  - Organized project documentation into proper folder structure
  - Moved bug reports to `docs/bug-reports/`
  - Moved investigations to `docs/investigations/`
  - Moved development docs to `docs/development/`
  - Moved implementation summaries to `docs/implementation-summaries/`
  - Moved all test files to `tests/` directory
  - Updated `.gitignore` to exclude development-only folders from releases
  - Cleaned up root directory for better project organization

### 📚 Documentation
- Created comprehensive installer documentation (`installer/windows/README.md`)
  - Architecture overview and component descriptions
  - Detailed build and preparation instructions
  - Testing procedures and troubleshooting guide
  - Version management documentation
  - Advanced topics (code signing, silent install, portable version)
- Updated `BUILD_INSTALLER_FOR_RELEASE.md` with new build process
- Created `INSTALLER_MIGRATION_GUIDE.md` explaining changes from old system
- Added cleanup summary documentation

### 📦 Release Preparation
- Updated version to 0.9.2 across all files
- Added backend version management system
- Prepared codebase for production release
- Streamlined build and release process

## [0.9.1] - 2025-10-25

### 🐛 Bug Fixes
- **Critical**: Fixed MinerDetail page refresh bug that caused blank screen on page reload
  - Replaced problematic VSkeletonLoader with simple loading indicator
  - Improved template structure for better null safety
  - Added proper loading state handling when store is empty
- Resolved Vue rendering errors on component initialization

## [Unreleased]

### 🚀 New Features
- Enhanced automated release publishing system with comprehensive release notes
- Automated documentation synchronization with releases
- Community verification and transparency features

### ⚡ Improvements
- Professional installer distribution for Windows, macOS, and Linux
- Comprehensive GitHub Actions CI/CD pipeline
- Enhanced security scanning and validation
- Reproducible build system for community verification

### 🔧 Build & Infrastructure
- Automated release note generation from commit history
- Documentation update automation
- Cross-platform installer testing and validation
- Community trust and transparency systems

---

*This changelog is automatically updated during the release process.*