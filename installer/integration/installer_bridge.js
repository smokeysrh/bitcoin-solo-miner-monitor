/**
 * Installer Bridge for Bitcoin Solo Miner Monitor
 * 
 * This module provides a unified interface for the Electron wizard to communicate
 * with platform-specific installers (NSIS for Windows, DMG for macOS, and DEB/RPM for Linux).
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { exec } = require('child_process');

// Import platform-specific bridges
const windowsBridge = require('./windows_bridge');
const macosBridge = require('./macos_bridge');
const linuxBridge = require('./linux_bridge');

/**
 * Launch the appropriate installer based on the platform
 * 
 * @param {Object} config - Configuration object from the wizard
 * @returns {Promise} - Promise that resolves when installation is complete
 */
async function launchInstaller(config) {
  // Determine the platform
  const platform = process.platform;
  
  try {
    // Call the appropriate platform-specific bridge
    switch (platform) {
      case 'win32':
        return await windowsBridge.launchNSISInstaller(config);
      case 'darwin':
        return await macosBridge.launchDMGInstaller(config);
      case 'linux':
        return await linuxBridge.launchLinuxInstaller(config);
      default:
        throw new Error(`Unsupported platform: ${platform}`);
    }
  } catch (error) {
    console.error(`Error launching installer: ${error.message}`);
    throw error;
  }
}

/**
 * Get the default installation directory based on the platform
 * 
 * @returns {string} - Default installation directory
 */
function getDefaultInstallDir() {
  switch (process.platform) {
    case 'win32':
      return path.join(process.env.PROGRAMFILES || 'C:\\Program Files', 'Bitcoin Solo Miner Monitor');
    case 'darwin':
      return '/Applications/Bitcoin Solo Miner Monitor.app';
    case 'linux':
      return '/opt/bitcoin-solo-miner-monitor';
    default:
      return path.join(os.homedir(), 'Bitcoin Solo Miner Monitor');
  }
}

/**
 * Get the default data directory based on the platform
 * 
 * @returns {string} - Default data directory
 */
function getDefaultDataDir() {
  switch (process.platform) {
    case 'win32':
      return path.join(process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming'), 'Bitcoin Solo Miner Monitor');
    case 'darwin':
      return path.join(os.homedir(), 'Library', 'Application Support', 'Bitcoin Solo Miner Monitor');
    case 'linux':
      return path.join(os.homedir(), '.bitcoin-solo-miner-monitor');
    default:
      return path.join(os.homedir(), '.bitcoin-solo-miner-monitor');
  }
}

/**
 * Check if the application is already installed
 * 
 * @returns {Promise<boolean>} - True if the application is already installed
 */
async function isApplicationInstalled() {
  return new Promise((resolve) => {
    switch (process.platform) {
      case 'win32':
        // Check Windows registry
        exec('reg query "HKLM\\Software\\Bitcoin Solo Miner Monitor" /v InstallDir', (error) => {
          resolve(!error);
        });
        break;
      case 'darwin':
        // Check if the application exists in the Applications folder
        fs.access('/Applications/Bitcoin Solo Miner Monitor.app', fs.constants.F_OK, (error) => {
          resolve(!error);
        });
        break;
      case 'linux':
        // Check if the application is installed via package manager
        exec('which bitcoin-solo-miner-monitor', (error) => {
          if (!error) {
            resolve(true);
          } else {
            // Check common installation directories
            fs.access('/opt/bitcoin-solo-miner-monitor', fs.constants.F_OK, (error) => {
              resolve(!error);
            });
          }
        });
        break;
      default:
        resolve(false);
    }
  });
}

/**
 * Convert components object to string for installers
 * 
 * @param {Object} components - Components selection object
 * @returns {string} - Comma-separated string of selected components
 */
function getComponentsString(components) {
  const selectedComponents = [];
  
  // Core is always included
  selectedComponents.push('core');
  
  if (components.database) {
    selectedComponents.push('database');
  }
  
  if (components.dashboard) {
    selectedComponents.push('dashboard');
  }
  
  if (components.alert) {
    selectedComponents.push('alert');
  }
  
  if (components.api) {
    selectedComponents.push('api');
  }
  
  if (components.docs) {
    selectedComponents.push('docs');
  }
  
  return selectedComponents.join(',');
}

module.exports = {
  launchInstaller,
  getDefaultInstallDir,
  getDefaultDataDir,
  isApplicationInstalled,
  getComponentsString
};