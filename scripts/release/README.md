# Bitcoin Solo Miner Monitor - Release Scripts

This directory contains automated release management scripts for Bitcoin Solo Miner Monitor. These scripts handle the complete release process including GitHub release creation, release notes generation, and documentation updates.

## 📋 Overview

The release system provides:
- **Automated release note generation** from commit history and changelog
- **Documentation synchronization** with new version information
- **GitHub release creation** with all platform installers
- **Comprehensive verification** and validation

## 🚀 Quick Start

### Create a Release

**Windows:**
```cmd
scripts\create-release.bat 1.0.0
```

**Linux/macOS:**
```bash
python scripts/release/create-release.py 1.0.0
```

### Dry Run (Test Without Changes)

**Windows:**
```cmd
scripts\create-release.bat 1.0.0 --dry-run
```

**Linux/macOS:**
```bash
python scripts/release/create-release.py 1.0.0 --dry-run
```

## 📁 Script Components

### 1. `create-release.py` - Main Release Orchestrator

The primary script that coordinates the entire release process.

**Usage:**
```bash
python scripts/release/create-release.py <version> [options]
```

**Options:**
- `--tag-name TAG` - Custom git tag name (default: v{version})
- `--skip-build-wait` - Skip waiting for GitHub Actions build completion
- `--dry-run` - Perform a dry run without making changes
- `--project-root PATH` - Specify project root directory

**Process:**
1. ✅ Check git working directory is clean
2. 📝 Generate comprehensive release notes
3. 📚 Update all documentation with new version
4. 💾 Commit documentation changes
5. 🏷️ Create and push git tag
6. ⏳ Wait for GitHub Actions build completion
7. 🎉 GitHub release created automatically

### 2. `generate-release-notes.py` - Release Notes Generator

Generates comprehensive release notes from commit history and changelog.

**Usage:**
```bash
python scripts/release/generate-release-notes.py <version> [options]
```

**Options:**
- `--tag-name TAG` - Git tag name for the release
- `--output FILE` - Output file (default: stdout)
- `--update-changelog` - Update CHANGELOG.md with new release
- `--project-root PATH` - Project root directory

**Features:**
- 📝 Categorizes commits by type (features, fixes, improvements, etc.)
- 📋 Generates download links for all platforms
- 🔐 Includes verification instructions and checksums
- 📚 Adds installation instructions for each platform
- 🔒 Includes security information and warnings explanation
- 📖 Updates CHANGELOG.md automatically

### 3. `update-documentation.py` - Documentation Updater

Updates all documentation files with new version information.

**Usage:**
```bash
python scripts/release/update-documentation.py <version> [options]
```

**Options:**
- `--tag-name TAG` - Git tag name for download links
- `--project-root PATH` - Project root directory

**Updates:**
- 📄 Main project README.md
- 📋 Installation guide (docs/installation/README.md)
- 🪟 Windows installation guide
- 🍎 macOS installation guide
- 🐧 Linux installation guide
- 👤 User guide
- 📥 Creates/updates download page (docs/DOWNLOADS.md)

## 🔄 Release Process Workflow

### 1. Pre-Release Preparation

Before creating a release:

```bash
# Ensure working directory is clean
git status

# Pull latest changes
git pull origin main

# Run tests (if applicable)
npm test  # or your test command
```

### 2. Create Release

```bash
# Standard release
python scripts/release/create-release.py 1.0.0

# Or with Windows batch script
scripts\create-release.bat 1.0.0
```

### 3. Monitor Build

The script will create a git tag which triggers GitHub Actions:
- 🪟 Windows installer (.exe)
- 🍎 macOS installer (.dmg)
- 🐧 Linux packages (.deb, .rpm, .AppImage)
- 🔐 SHA256 checksums for all files

### 4. Post-Release

After the GitHub Actions build completes:
- ✅ GitHub release is created automatically
- 📦 All installers are attached to the release
- 📝 Comprehensive release notes are published
- 📚 Documentation is updated with new download links

## 📝 Manual Usage Examples

### Generate Release Notes Only

```bash
# Generate and display release notes
python scripts/release/generate-release-notes.py 1.0.0

# Save to file and update changelog
python scripts/release/generate-release-notes.py 1.0.0 \
  --output release-notes.md \
  --update-changelog
```

### Update Documentation Only

```bash
# Update all documentation for version 1.0.0
python scripts/release/update-documentation.py 1.0.0 --tag-name v1.0.0
```

### Test Release Process

```bash
# Dry run - see what would happen without making changes
python scripts/release/create-release.py 1.0.0 --dry-run
```

## 🔧 Configuration

### Commit Message Categorization

The release notes generator categorizes commits based on patterns:

- **🚀 Features**: `feat:`, `add:`, `implement:`, `new:`
- **🐛 Bug Fixes**: `fix:`, `bug:`, `hotfix:`, `patch:`
- **⚡ Improvements**: `improve:`, `enhance:`, `update:`, `refactor:`
- **🔒 Security**: `security:`, `sec:`, vulnerability-related keywords
- **📚 Documentation**: `docs:`, `doc:`, documentation-related keywords
- **🔧 Build**: `build:`, `ci:`, `chore:`, build-related keywords

### Changelog Format

The system uses [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [1.0.0] - 2024-01-15

### 🚀 New Features
- Feature description ([commit-hash](link))

### 🐛 Bug Fixes
- Bug fix description ([commit-hash](link))
```

## 🚨 Troubleshooting

### Common Issues

**"Git working directory is not clean"**
```bash
# Check what files are modified
git status

# Commit or stash changes
git add .
git commit -m "Prepare for release"
```

**"Python script not found"**
```bash
# Ensure you're in the project root
cd /path/to/bitcoin-solo-miner-monitor

# Check if scripts exist
ls scripts/release/
```

**"GitHub Actions build failed"**
- Check the [Actions tab](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/actions)
- Review build logs for specific errors
- Common issues: missing dependencies, test failures, build environment problems

### Manual Recovery

If the automated process fails partway through:

1. **Tag already created but release failed:**
   ```bash
   # Delete the tag locally and remotely
   git tag -d v1.0.0
   git push origin :refs/tags/v1.0.0
   
   # Start over
   python scripts/release/create-release.py 1.0.0
   ```

2. **Documentation committed but tag creation failed:**
   ```bash
   # Reset the documentation commit
   git reset --hard HEAD~1
   
   # Start over
   python scripts/release/create-release.py 1.0.0
   ```

## 🔐 Security Considerations

- All scripts validate input and check git status
- No sensitive information is logged or exposed
- GitHub token is handled securely by GitHub Actions
- All operations are logged for transparency

## 🤝 Contributing

To improve the release system:

1. Test changes with `--dry-run` first
2. Update this documentation for any new features
3. Ensure cross-platform compatibility (Windows/macOS/Linux)
4. Follow the existing code style and error handling patterns

## 📚 Related Documentation

- [GitHub Actions Workflow](../../.github/workflows/build-installers.yml)
- [Installation Guide](../../docs/installation/README.md)
- [Build Guide](../../docs/BUILD.md)
- [Contributing Guide](../../CONTRIBUTING.md)

---

**Built by solo miners, for solo miners** 🚀⚡