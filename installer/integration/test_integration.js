#!/usr/bin/env node

/**
 * Test script for the integration between the Electron wizard and platform-specific installers
 * 
 * This script simulates the Electron wizard and tests the integration with the platform-specific installers.
 */

const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const installerBridge = require('./installer_bridge');

// Test configuration
const testConfig = {
  installDir: installerBridge.getDefaultInstallDir(),
  dataDir: installerBridge.getDefaultDataDir(),
  createDesktopShortcut: true,
  createStartMenuShortcut: true,
  startOnBoot: true,
  autoDiscovery: true,
  networkRange: '192.168.1.0/24',
  components: {
    core: true,
    database: true,
    dashboard: true,
    alert: true,
    api: true,
    docs: true
  }
};

// Function to test Windows integration
async function testWindowsIntegration() {
  console.log('Testing Windows integration...');
  
  try {
    // Get the path to the NSIS script
    const nsiScriptPath = path.join(__dirname, '..', 'windows', 'installer.nsi');
    
    // Check if the NSIS script exists
    if (!fs.existsSync(nsiScriptPath)) {
      console.error(`NSIS script not found at ${nsiScriptPath}`);
      return false;
    }
    
    // Update the NSIS script to use the Electron wizard configuration
    const windowsBridge = require('./windows_bridge');
    await windowsBridge.updateNSISScript(nsiScriptPath);
    
    console.log('Windows integration test passed!');
    return true;
  } catch (error) {
    console.error(`Windows integration test failed: ${error.message}`);
    return false;
  }
}

// Function to test macOS integration
async function testMacOSIntegration() {
  console.log('Testing macOS integration...');
  
  try {
    // Get the path to the DMG creation script
    const dmgScriptPath = path.join(__dirname, '..', 'macos', 'create_installer.sh');
    
    // Check if the DMG script exists
    if (!fs.existsSync(dmgScriptPath)) {
      console.error(`DMG script not found at ${dmgScriptPath}`);
      return false;
    }
    
    // Update the DMG script to use the Electron wizard configuration
    const macosBridge = require('./macos_bridge');
    await macosBridge.updateDMGScript(dmgScriptPath);
    
    console.log('macOS integration test passed!');
    return true;
  } catch (error) {
    console.error(`macOS integration test failed: ${error.message}`);
    return false;
  }
}

// Function to test Linux integration
async function testLinuxIntegration() {
  console.log('Testing Linux integration...');
  
  try {
    // Get the path to the Linux package creation script
    const linuxScriptPath = path.join(__dirname, '..', 'linux', 'create_packages.sh');
    
    // Check if the Linux script exists
    if (!fs.existsSync(linuxScriptPath)) {
      console.error(`Linux script not found at ${linuxScriptPath}`);
      return false;
    }
    
    // Update the Linux script to use the Electron wizard configuration
    const linuxBridge = require('./linux_bridge');
    await linuxBridge.updateLinuxScript(linuxScriptPath);
    
    console.log('Linux integration test passed!');
    return true;
  } catch (error) {
    console.error(`Linux integration test failed: ${error.message}`);
    return false;
  }
}

// Main function to run all tests
async function runTests() {
  console.log('Starting integration tests...');
  console.log('Test configuration:', JSON.stringify(testConfig, null, 2));
  
  // Determine the platform
  const platform = process.platform;
  
  // Run the appropriate test based on the platform
  let success = false;
  
  switch (platform) {
    case 'win32':
      success = await testWindowsIntegration();
      break;
    case 'darwin':
      success = await testMacOSIntegration();
      break;
    case 'linux':
      success = await testLinuxIntegration();
      break;
    default:
      console.error(`Unsupported platform: ${platform}`);
      process.exit(1);
  }
  
  if (success) {
    console.log('All integration tests passed!');
    process.exit(0);
  } else {
    console.error('Integration tests failed!');
    process.exit(1);
  }
}

// Run the tests
runTests().catch(error => {
  console.error(`Error running tests: ${error.message}`);
  process.exit(1);
});