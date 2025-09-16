# Contributing to Bitcoin Solo Miner Monitor

Thank you for your interest in contributing to Bitcoin Solo Miner Monitor! This project thrives on community contributions, and we welcome developers, miners, packagers, and users who want to help improve this open-source Bitcoin mining tool.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Types of Contributions](#types-of-contributions)
- [Development Setup](#development-setup)
- [Contribution Workflow](#contribution-workflow)
- [Packaging and Distribution](#packaging-and-distribution)
- [Community Support](#community-support)
- [Recognition](#recognition)

## Code of Conduct

This project follows the principles of the Bitcoin community: openness, transparency, and mutual respect. We are committed to providing a welcoming environment for all contributors regardless of their experience level, background, or mining setup.

### Our Standards

- **Be respectful**: Treat all community members with respect and kindness
- **Be collaborative**: Work together to solve problems and improve the software
- **Be transparent**: Share your reasoning and be open about challenges
- **Be patient**: Remember that everyone has different experience levels
- **Focus on Bitcoin**: Keep discussions relevant to Bitcoin mining and this project

### Unacceptable Behavior

- Harassment, discrimination, or personal attacks
- Spam, promotional content unrelated to the project
- Sharing of private keys, wallet addresses, or sensitive mining data
- Deliberate misinformation about Bitcoin or mining

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Git** installed and configured
- **Python 3.11+** for backend development
- **Node.js 18+** for frontend development
- **Basic understanding** of Bitcoin mining concepts
- **GitHub account** for submitting contributions

### First Steps

1. **Star and fork** the repository
2. **Read the documentation** in the `docs/` directory
3. **Set up your development environment** (see Development Setup below)
4. **Join community discussions** through GitHub Issues and Discussions
5. **Look for "good first issue"** labels for beginner-friendly tasks

## Types of Contributions

We welcome various types of contributions:

### 🐛 Bug Reports and Fixes

- Report bugs using our [Bug Report template](.github/ISSUE_TEMPLATE/bug-report.md)
- Fix existing bugs listed in the Issues section
- Improve error handling and user experience

### ✨ Feature Development

- Propose new features using our [Feature Request template](.github/ISSUE_TEMPLATE/feature-request.md)
- Implement approved features following our development guidelines
- Enhance existing functionality based on community feedback

### 📦 Packaging and Distribution

- Create packages for new Linux distributions
- Improve existing installer scripts (Windows NSIS, macOS DMG, Linux packages)
- Test installers on different platforms and configurations
- Contribute to reproducible build processes

### 📚 Documentation

- Improve installation guides and troubleshooting documentation
- Create tutorials for different mining setups
- Translate documentation to other languages
- Update API documentation and code comments

### 🔒 Security and Verification

- Perform security audits of the codebase
- Contribute to reproducible build verification
- Report security issues through our [Security Issue template](.github/ISSUE_TEMPLATE/security-issue.md)
- Help with community verification processes

### 🧪 Testing

- Write unit tests and integration tests
- Test on different hardware configurations
- Perform user acceptance testing
- Contribute to automated testing infrastructure

### 🎨 User Interface and Experience

- Improve the Vue.js frontend interface
- Enhance user experience for different skill levels
- Create better visualizations for mining data
- Improve accessibility and responsive design

## Development Setup

### Backend Development (Python)

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/bitcoin-solo-miner-monitor.git
cd bitcoin-solo-miner-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend
python run.py
```

### Frontend Development (Vue.js)

```bash
# Navigate to frontend directory
cd src/frontend

# Install dependencies
npm install

# Build frontend
npm run build

# For development with hot reload
npm run dev
```

### Full Application Testing

```bash
# Build frontend first
cd src/frontend
npm run build
cd ../..

# Run full application
python run.py

# Application will be available at http://localhost:8000
```

### Running Tests

```bash
# Run Python tests
python -m pytest tests/

# Run frontend tests
cd src/frontend
npm test

# Run integration tests
python -m pytest tests/integration/
```

## Contribution Workflow

### 1. Planning Your Contribution

- **Check existing issues** to avoid duplicate work
- **Create an issue** for new features or significant changes
- **Discuss your approach** with maintainers and community
- **Get approval** for major changes before starting work

### 2. Development Process

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ... develop and test your changes ...

# Commit with clear messages
git add .
git commit -m "feat: add mining pool connection timeout handling

- Add configurable timeout for mining pool connections
- Improve error messages for connection failures
- Add unit tests for timeout scenarios
- Update documentation with new configuration options

Fixes #123"

# Push to your fork
git push origin feature/your-feature-name
```

### 3. Commit Message Guidelines

We follow conventional commit format:

```
type(scope): brief description

Detailed explanation of changes made and why.
Include any breaking changes or migration notes.

Fixes #issue-number
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `security`

**Examples**:
- `feat(mining): add support for Stratum v2 protocol`
- `fix(ui): resolve dashboard refresh issue on Windows`
- `docs(install): update Linux installation guide`
- `security(api): validate mining pool URLs to prevent SSRF`

### 4. Pull Request Process

1. **Create a pull request** from your feature branch to `main`
2. **Fill out the PR template** completely
3. **Ensure all tests pass** and code follows style guidelines
4. **Request review** from maintainers
5. **Address feedback** promptly and professionally
6. **Squash commits** if requested before merging

### 5. Code Review Guidelines

**For contributors**:
- Be responsive to feedback
- Ask questions if feedback is unclear
- Make requested changes promptly
- Test your changes thoroughly

**For reviewers**:
- Be constructive and specific in feedback
- Focus on code quality, security, and user experience
- Test changes when possible
- Approve when ready or request specific changes

## Packaging and Distribution

### Creating Platform Packages

We welcome contributions to our packaging and distribution system:

#### Windows NSIS Installer

```bash
# Location: installer/windows/
# Key files:
# - installer.nsi (main installer script)
# - config/ (installer configuration)
# - assets/ (branding and graphics)

# Test installer creation
cd installer/windows
makensis installer.nsi
```

#### macOS DMG Package

```bash
# Location: installer/macos/
# Key files:
# - create_dmg.sh (DMG creation script)
# - Info.plist (application metadata)
# - background.png (DMG background)

# Test DMG creation
cd installer/macos
./create_dmg.sh
```

#### Linux Packages

```bash
# Location: installer/linux/
# Supported formats: DEB, RPM, AppImage

# Test DEB package creation
cd installer/linux
./build-deb.sh

# Test RPM package creation
./build-rpm.sh

# Test AppImage creation
./build-appimage.sh
```

### Package Testing

- Test installation on clean systems
- Verify all dependencies are included
- Test uninstallation process
- Check desktop integration (shortcuts, file associations)
- Validate package metadata and descriptions

### Distribution Channels

Help us distribute to more channels:

- **Linux repositories**: AUR, PPA, Flathub, Snap Store
- **Package managers**: Homebrew, Chocolatey, Scoop
- **Community mirrors**: Help maintain download mirrors
- **Documentation**: Create distribution-specific guides

## Community Support

### Helping Other Users

- Answer questions in GitHub Issues and Discussions
- Help troubleshoot installation and configuration problems
- Share your mining setup and experiences
- Create tutorials and guides for common scenarios

### Community Verification

- Verify release checksums and report results
- Perform reproducible builds and compare outputs
- Test installers on different platforms
- Report verification results using our templates

### Feedback Collection

- Participate in user experience surveys
- Provide feedback on new features and changes
- Report usability issues and suggestions
- Help prioritize development efforts

## Recognition

We value all contributions to the project:

### Contributor Recognition

- **Contributors file**: All contributors are listed in CONTRIBUTORS.md
- **Release notes**: Significant contributions are highlighted in releases
- **GitHub insights**: Contribution statistics are publicly visible
- **Community thanks**: Regular appreciation in project communications

### Types of Recognition

- **Code contributors**: Developers who submit code changes
- **Package maintainers**: Community members who maintain distribution packages
- **Documentation contributors**: Writers and translators who improve documentation
- **Community supporters**: Members who help other users and provide feedback
- **Security researchers**: Contributors who help identify and fix security issues
- **Testers**: Community members who test releases and report issues

### Becoming a Maintainer

Active contributors may be invited to become maintainers:

- **Consistent contributions** over several months
- **Deep understanding** of the project and Bitcoin mining
- **Positive community interactions** and helpful attitude
- **Technical expertise** in relevant areas
- **Commitment** to project values and long-term success

## Development Guidelines

### Code Quality Standards

- **Python**: Follow PEP 8, use type hints, write docstrings
- **JavaScript/Vue**: Follow ESLint configuration, use TypeScript when possible
- **Testing**: Maintain >80% code coverage, write meaningful tests
- **Security**: Follow secure coding practices, validate all inputs
- **Performance**: Consider performance impact of changes

### Architecture Principles

- **Modularity**: Keep components loosely coupled and highly cohesive
- **Testability**: Write code that can be easily tested
- **Maintainability**: Use clear naming and document complex logic
- **Scalability**: Consider how changes affect performance at scale
- **Security**: Assume all inputs are untrusted, validate everything

### Documentation Standards

- **Code comments**: Explain why, not what
- **API documentation**: Keep API docs up to date with changes
- **User documentation**: Write for different skill levels
- **Installation guides**: Test on clean systems
- **Troubleshooting**: Include common issues and solutions

## Getting Help

### For Contributors

- **[Discord Server](https://discord.gg/GzNsNnh4yT)** - Real-time community discussions and support
- **GitHub Discussions**: Ask questions about contributing
- **Issue comments**: Get help with specific issues you're working on
- **Documentation**: Check existing docs before asking questions
- **Community**: Connect with other contributors

### For Maintainers

- **Maintainer guidelines**: Internal documentation for project maintainers
- **Release process**: Detailed steps for creating releases
- **Security procedures**: How to handle security issues
- **Community management**: Guidelines for community interaction

## Project Roadmap

Stay informed about project direction:

- **GitHub Projects**: Track current development priorities
- **Milestones**: See planned features for upcoming releases
- **Issues**: Browse open issues for contribution opportunities
- **Discussions**: Participate in planning conversations

## Legal and Licensing

- **License**: This project is licensed under MIT License
- **Contributor License Agreement**: By contributing, you agree that your contributions will be licensed under the same license
- **Copyright**: Contributors retain copyright to their contributions
- **Attribution**: Significant contributions will be attributed in release notes

---

## Quick Start Checklist

Ready to contribute? Here's your quick start checklist:

- [ ] Fork the repository and clone your fork
- [ ] Set up development environment (Python + Node.js)
- [ ] Read the documentation in `docs/`
- [ ] Look for "good first issue" labels
- [ ] Create a feature branch for your work
- [ ] Make your changes and test thoroughly
- [ ] Write or update tests as needed
- [ ] Update documentation if necessary
- [ ] Submit a pull request with clear description
- [ ] Respond to code review feedback
- [ ] Celebrate your contribution to open-source Bitcoin software! 🎉

---

**Thank you for contributing to Bitcoin Solo Miner Monitor!** Your contributions help make Bitcoin mining more accessible and secure for everyone. Together, we're building better tools for the Bitcoin community.

For questions about contributing, please open a [Community Support Request](.github/ISSUE_TEMPLATE/community-support.md) or start a discussion in GitHub Discussions.