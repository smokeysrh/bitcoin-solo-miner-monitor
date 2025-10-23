# Release Preparation Checklist

This document outlines the steps to prepare the codebase for a new release.

## Version 0.9.1 Release Preparation

### ✅ Completed Tasks

#### Code Cleanup
- [x] Moved all bug reports to `docs/bug-reports/`
- [x] Moved all investigations to `docs/investigations/`
- [x] Moved development docs to `docs/development/`
- [x] Moved implementation summaries to `docs/implementation-summaries/`
- [x] Moved test files from root to `tests/` directory
- [x] Cleaned up root directory

#### Version Updates
- [x] Updated `package.json` to version 0.9.1
- [x] Updated `src/frontend/src/App.vue` to display v0.9.1
- [x] Created `src/backend/version.py` for backend version management
- [x] Updated `CHANGELOG.md` with v0.9.1 changes

#### Configuration Updates
- [x] Updated `.gitignore` to exclude development-only folders:
  - `docs/bug-reports/`
  - `docs/investigations/`
  - `docs/development/`
  - `debug/`
  - `testing/`
  - `verification/`
  - `verification-results/`
  - `bug-reports/`
  - `community-audit-workspace/`
  - `security-audit/`
  - `security-reports/`
  - `community-feedback/`
  - `tools/verification/`
  - `.kiro/`

#### Documentation
- [x] Created `docs/README.md` explaining documentation structure
- [x] Created this release preparation checklist

### 🔍 Pre-Release Verification

Before creating the release, verify:

1. **Version Consistency**
   ```bash
   # Check all version references
   grep -r "0.9.1" package.json src/frontend/src/App.vue src/backend/version.py
   ```

2. **Build Test**
   ```bash
   # Test that the application builds successfully
   cd src/frontend
   npm install
   npm run build
   ```

3. **Functionality Test**
   - [ ] Application starts without errors
   - [ ] Dashboard loads correctly
   - [ ] Miner detail page works (including refresh)
   - [ ] Network topology page functions
   - [ ] Settings save correctly
   - [ ] WebSocket connection establishes

4. **Clean Build**
   ```bash
   # Ensure no development files are included
   # Check that .gitignore is working correctly
   git status --ignored
   ```

### 📦 Release Build Process

1. **Create Distribution Package**
   ```bash
   # Run the distribution creation script
   python scripts/create-distribution.py
   ```

2. **Test Installation**
   - Test installer on Windows
   - Test installer on macOS (if available)
   - Test installer on Linux (if available)

3. **Create Git Tag**
   ```bash
   git tag -a v0.9.1 -m "Release v0.9.1 - Bug fixes and code cleanup"
   git push origin v0.9.1
   ```

4. **Create GitHub Release**
   - Go to GitHub Releases
   - Create new release from tag v0.9.1
   - Copy changelog content
   - Upload distribution packages
   - Publish release

### 🚀 Post-Release Tasks

- [ ] Verify release is available on GitHub
- [ ] Test download and installation from release
- [ ] Update any external documentation
- [ ] Announce release (if applicable)
- [ ] Monitor for issues

## Development-Only Folders

The following folders are excluded from releases and are for development use only:

- `docs/bug-reports/` - Internal bug tracking
- `docs/investigations/` - Internal investigations
- `docs/development/` - Development notes
- `debug/` - Debug scripts and tools
- `testing/` - Test scripts and files
- `verification/` - Verification tools
- `tools/verification/` - Verification utilities
- `.kiro/` - IDE configuration

These folders help with development but are not needed by end users.

## Notes

- Always test the release build before publishing
- Keep the CHANGELOG.md updated with all changes
- Ensure version numbers are consistent across all files
- Verify that no sensitive or development-only files are included in the release
