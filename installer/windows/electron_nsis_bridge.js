/**
 * Electron-NSIS Bridge for Bitcoin Solo Miner Monitor Installer
 * 
 * This script provides communication between the Electron wizard and the NSIS installer.
 * It passes user selections from the wizard to the NSIS installer process.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

/**
 * Launch NSIS installer with parameters from Electron wizard
 * 
 * @param {Object} config - Configuration object from the wizard
 * @returns {Promise} - Promise that resolves when installation is complete
 */
async function launchNSISInstaller(config) {
    return new Promise((resolve, reject) => {
        try {
            // Create a temporary file to store the configuration
            const tempConfigPath = path.join(os.tmpdir(), 'bsmm_installer_config.json');
            
            // Write configuration to temp file
            fs.writeJsonSync(tempConfigPath, config);
            
            // Get path to NSIS installer
            const installerPath = path.join(__dirname, 'BitcoinSoloMinerMonitor-Setup.exe');
            
            // Check if installer exists
            if (!fs.existsSync(installerPath)) {
                throw new Error(`NSIS installer not found at ${installerPath}`);
            }
            
            // Build command line arguments
            const args = [
                '/S',                                   // Silent mode
                `/CONFIG=${tempConfigPath}`,            // Path to configuration file
                `/INSTALLDIR=${config.installDir}`,     // Installation directory
                `/DATADIR=${config.dataDir}`,           // Data directory
                `/COMPONENTS=${getComponentsString(config.components)}` // Selected components
            ];
            
            // Add optional arguments
            if (config.createDesktopShortcut) {
                args.push('/DESKTOP=1');
            } else {
                args.push('/DESKTOP=0');
            }
            
            if (config.createStartMenuShortcut) {
                args.push('/STARTMENU=1');
            } else {
                args.push('/STARTMENU=0');
            }
            
            if (config.startOnBoot) {
                args.push('/STARTUP=1');
            } else {
                args.push('/STARTUP=0');
            }
            
            if (config.autoDiscovery) {
                args.push('/AUTODISCOVERY=1');
            } else {
                args.push('/AUTODISCOVERY=0');
            }
            
            args.push(`/NETWORKRANGE=${config.networkRange}`);
            
            // Launch NSIS installer
            const installer = spawn(installerPath, args, { detached: true });
            
            installer.on('error', (err) => {
                reject(new Error(`Failed to start NSIS installer: ${err.message}`));
            });
            
            installer.on('exit', (code) => {
                if (code === 0) {
                    // Clean up temp file
                    fs.removeSync(tempConfigPath);
                    resolve({ success: true });
                } else {
                    reject(new Error(`NSIS installer exited with code ${code}`));
                }
            });
            
            // Detach the process
            installer.unref();
            
        } catch (error) {
            reject(error);
        }
    });
}

/**
 * Convert components object to string for NSIS
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
    launchNSISInstaller
};