# Changelog

All notable changes to Bitcoin Solo Miner Monitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/0.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.1] - 2025-10-23

### 🐛 Bug Fixes
- **Critical**: Fixed MinerDetail page refresh bug that caused blank screen on page reload
  - Replaced problematic VSkeletonLoader with simple loading indicator
  - Improved template structure for better null safety
  - Added proper loading state handling when store is empty
- Resolved Vue rendering errors on component initialization

### 🧹 Code Cleanup
- Organized project documentation into proper folder structure
  - Moved bug reports to `docs/bug-reports/`
  - Moved investigations to `docs/investigations/`
  - Moved development docs to `docs/development/`
  - Moved implementation summaries to `docs/implementation-summaries/`
- Moved all test files to `tests/` directory
- Updated `.gitignore` to exclude development-only folders from releases
- Cleaned up root directory for better project organization

### 📦 Release Preparation
- Updated version to 0.9.1 across all files
- Added backend version management system
- Prepared codebase for production release

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