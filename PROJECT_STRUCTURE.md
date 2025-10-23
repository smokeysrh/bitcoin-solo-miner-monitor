# Bitcoin Solo Miner Monitor - Project Structure

## Root Directory

```
BTCsoloApp/
├── .gitignore              # Git ignore rules
├── CHANGELOG.md            # Version history and changes
├── CONTRIBUTING.md         # Contribution guidelines
├── CONTRIBUTORS.md         # List of contributors
├── package.json            # Node.js dependencies (v0.9.1)
├── package-lock.json       # Locked dependency versions
├── README.md               # Project overview and quick start
├── requirements.txt        # Python dependencies
├── run.py                  # Application entry point
└── PROJECT_STRUCTURE.md    # This file
```

## Main Directories

### `/src` - Source Code
```
src/
├── backend/           # Python backend (FastAPI)
│   ├── api/          # API endpoints
│   ├── models/       # Data models
│   ├── services/     # Business logic
│   └── version.py    # Version management
├── frontend/         # Vue.js frontend
│   ├── src/
│   │   ├── components/  # Vue components
│   │   ├── views/       # Page views
│   │   ├── stores/      # Pinia stores
│   │   └── App.vue      # Main app component
│   └── package.json
├── common/           # Shared utilities
└── main.py          # Backend entry point
```

### `/docs` - Documentation
```
docs/
├── bug-reports/              # Bug diagnostics (dev only)
├── investigations/           # Issue investigations (dev only)
├── development/              # Dev guides (dev only)
├── implementation-reports/   # Feature reports
├── implementation-summaries/ # Implementation overviews
├── build/                    # Build documentation
├── community/                # Community guides
├── distribution/             # Distribution guides
├── installation/             # Installation guides
├── security/                 # Security documentation
├── README.md                 # Docs structure guide
└── RELEASE_PREPARATION.md    # Release checklist
```

### `/tests` - Test Files
```
tests/
├── api/              # API tests
├── frontend/         # Frontend tests
├── integration/      # Integration tests
├── unit/             # Unit tests
└── *.py             # Test scripts
```

### `/config` - Configuration
```
config/
├── app_config.py           # Application configuration
├── security-config.json    # Security settings
└── security-monitoring.json
```

### `/data` - Application Data
```
data/
└── config.db         # SQLite database
```

### `/scripts` - Utility Scripts
```
scripts/
├── release/          # Release automation
├── security/         # Security tools
└── *.bat/*.sh       # Build and deploy scripts
```

### `/installer` - Installation Packages
```
installer/
├── windows/          # Windows installer
├── macos/            # macOS installer
├── linux/            # Linux installer
└── common/           # Shared installer files
```

### `/distribution` - Release Builds
```
distribution/
├── windows/          # Windows builds
├── macos/            # macOS builds
└── BitcoinSoloMinerMonitor-*.zip
```

## Development-Only Directories

These directories are excluded from releases (via .gitignore):

- `/debug` - Debug scripts and tools
- `/testing` - Test scripts and HTML files
- `/verification` - Verification tools
- `/verification-results` - Verification outputs
- `/bug-reports` - Bug tracking (empty, moved to docs)
- `/community-audit-workspace` - Audit workspace
- `/security-audit` - Security audit files
- `/security-reports` - Security reports
- `/community-feedback` - Feedback data
- `/.kiro` - IDE configuration
- `/.vscode` - VS Code settings

## Key Files

### Configuration
- `.gitignore` - Excludes dev files from releases
- `package.json` - Frontend dependencies and version
- `requirements.txt` - Backend Python dependencies
- `config/app_config.py` - Application settings

### Documentation
- `README.md` - Project overview
- `CHANGELOG.md` - Version history
- `CONTRIBUTING.md` - How to contribute
- `docs/RELEASE_PREPARATION.md` - Release process

### Entry Points
- `run.py` - Start the application
- `src/main.py` - Backend server
- `src/frontend/src/main.js` - Frontend app

### Version Management
- `package.json` - Frontend version (0.9.1)
- `src/backend/version.py` - Backend version (0.9.1)
- `src/frontend/src/App.vue` - Displayed version (v0.9.1)

## Quick Navigation

### For Users
- Installation: `/docs/installation/`
- User Guide: `/docs/user-guide.md`
- Troubleshooting: `/docs/installation/troubleshooting.md`

### For Developers
- Development Guide: `/docs/development/DEVELOPMENT_MODE_GUIDE.md`
- API Documentation: `/docs/API_SECURITY.md`
- Build Guide: `/docs/BUILD.md`
- Testing Guide: `/docs/TESTING_GUIDE.md`

### For Contributors
- Contributing: `/CONTRIBUTING.md`
- Security: `/docs/security/`
- Community: `/docs/community/`

### For Maintainers
- Release Process: `/docs/RELEASE_PREPARATION.md`
- Distribution: `/docs/distribution/`
- Build System: `/docs/build/`

## Version Information

- **Current Version:** 0.9.1
- **Release Date:** October 23, 2025
- **Status:** Ready for Release

## Notes

- Development folders are automatically excluded from releases
- All version numbers are synchronized across files
- Documentation is organized by purpose and audience
- Test files are centralized in `/tests`
- Clean root directory for professional appearance

---

For more information, see `/docs/README.md`
