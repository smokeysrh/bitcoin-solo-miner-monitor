# Development Tools

This directory contains various development and utility tools for the Bitcoin Solo Miner Monitor project.

## Build Tools (`build/`)

- **build-from-source.py** - Comprehensive build tool for creating installers from source
- **build-reproducible.sh** - Script for reproducible builds
- **verify-reproducible-build.sh** - Verification script for reproducible builds

## Verification Tools (`verification/`)

- **verify-checksums.py** - Tool for verifying SHA256 checksums of release files

## Utility Scripts

- **reload_miners.py** - Script to call the reload-miners endpoint for development

## Usage

Most tools include help information when run with `--help` or `-h` flags.

For build tools:
```bash
python3 tools/build/build-from-source.py --help
```

For verification:
```bash
python3 tools/verification/verify-checksums.py --help
```