# Bitcoin Solo Miner Monitor - Installer Integration

This directory contains the integration code that connects the Electron-based installation wizard UI with the platform-specific installers (NSIS for Windows, DMG for macOS, and DEB/RPM for Linux).

## Overview

The installer integration provides a unified interface for the Electron wizard to communicate with platform-specific installers. This allows users to configure their installation through a consistent, modern UI while still leveraging native installers for each platform.

## Components

### `installer_bridge.js`

The main bridge module that provides a unified interface for the Electron wizard to communicate with platform-specific installers. It determines the platform and calls the appropriate platform-specific bridge.

### `windows_bridge.js`

Handles communication between the Electron wizard and the NSIS installer for Windows. It updates the NSIS script to use the configuration from the Electron wizard and launches the NSIS installer with the appropriate parameters.

### `macos_bridge.js`

Handles communication between the Electron wizard and the macOS DMG installer. It updates the DMG creation script to use the configuration from the Electron wizard and launches the DMG installer with the appropriate parameters.

### `linux_bridge.js`

Handles communication between the Electron wizard and the Linux DEB/RPM installers. It updates the package creation scripts to use the configuration from the Electron wizard and launches the appropriate installer based on the Linux distribution.

### `test_integration.js`

A test script that simulates the Electron wizard and tests the integration with the platform-specific installers.

## How It Works

1. The Electron wizard collects user preferences through a series of screens.
2. When the user clicks "Install", the wizard calls the `launchInstaller` function in `installer_bridge.js`.
3. The bridge determines the platform and calls the appropriate platform-specific bridge.
4. The platform-specific bridge updates the installer script to use the configuration from the Electron wizard.
5. The platform-specific bridge launches the installer with the appropriate parameters.
6. The installer reads the configuration and performs the installation accordingly.

## Configuration Options

The configuration object passed from the Electron wizard to the installers includes:

- `installDir`: The directory where the application should be installed
- `dataDir`: The directory where application data should be stored
- `createDesktopShortcut`: Whether to create a desktop shortcut
- `createStartMenuShortcut`: Whether to create a start menu shortcut (Windows only)
- `startOnBoot`: Whether to start the application automatically at system startup
- `autoDiscovery`: Whether to enable automatic miner discovery
- `networkRange`: The network range to scan for miners
- `components`: An object specifying which components to install:
  - `core`: Always true (required)
  - `database`: Whether to install the database component
  - `dashboard`: Whether to install the dashboard component
  - `alert`: Whether to install the alert system component
  - `api`: Whether to install the API server component
  - `docs`: Whether to install the documentation component

## Testing

To test the integration, run the `test_integration.js` script:

```bash
node test_integration.js
```

This will test the integration with the platform-specific installer for the current platform.

## Platform-Specific Notes

### Windows

The Windows integration updates the NSIS script to read configuration from a JSON file passed as a command-line parameter. It adds command-line parameters to the NSIS installer to control installation options.

### macOS

The macOS integration updates the DMG creation script to read configuration from a JSON file passed as a command-line parameter. It modifies the post-installation script to configure the application based on user preferences.

### Linux

The Linux integration updates the package creation scripts to read configuration from a JSON file passed as a command-line parameter. It modifies the post-installation scripts in both DEB and RPM packages to configure the application based on user preferences.