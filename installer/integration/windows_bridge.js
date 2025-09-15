/**
 * Windows-specific bridge for Bitcoin Solo Miner Monitor Installer
 * 
 * This module provides communication between the Electron wizard and the NSIS installer.
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
      fs.writeFileSync(tempConfigPath, JSON.stringify(config, null, 2));
      
      // Get path to NSIS installer
      const installerPath = path.join(__dirname, '..', 'windows', 'BitcoinSoloMinerMonitor-Setup.exe');
      
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
          try {
            fs.unlinkSync(tempConfigPath);
          } catch (err) {
            console.warn('Could not remove temp config file:', err.message);
          }
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

/**
 * Update the NSIS script to use the Electron wizard
 * 
 * @param {string} nsiScriptPath - Path to the NSIS script
 * @returns {Promise} - Promise that resolves when the script is updated
 */
async function updateNSISScript(nsiScriptPath) {
  try {
    // Read the NSIS script
    const nsiScript = await fs.promises.readFile(nsiScriptPath, 'utf8');
    
    // Update the script to use the Electron wizard
    const updatedScript = nsiScript
      // Add CONFIG parameter
      .replace(
        'RequestExecutionLevel admin',
        'RequestExecutionLevel admin\n\n; Configuration file parameter\nVar CONFIG_FILE'
      )
      // Add command line parameter handling
      .replace(
        'Function .onInit',
        `Function .onInit
  ; Get CONFIG parameter
  ${StrCpy} $CONFIG_FILE ""
  ${GetParameters} $R0
  ${GetOptions} $R0 "/CONFIG=" $CONFIG_FILE
  
  ; If CONFIG_FILE is provided, read settings from it
  ${If} $CONFIG_FILE != ""
    ${If} ${FileExists} $CONFIG_FILE
      ReadINIStr $0 $CONFIG_FILE "Installation" "InstallDir"
      ${If} $0 != ""
        StrCpy $INSTDIR $0
      ${EndIf}
      
      ReadINIStr $0 $CONFIG_FILE "Installation" "CreateDesktopShortcut"
      ${If} $0 == "1"
        SectionSetFlags ${SecDesktop} 1
      ${Else}
        SectionSetFlags ${SecDesktop} 0
      ${EndIf}
      
      ReadINIStr $0 $CONFIG_FILE "Installation" "CreateStartMenuShortcut"
      ${If} $0 == "1"
        SectionSetFlags ${SecStartMenu} 1
      ${Else}
        SectionSetFlags ${SecStartMenu} 0
      ${EndIf}
      
      ReadINIStr $0 $CONFIG_FILE "Installation" "StartOnBoot"
      ${If} $0 == "1"
        SectionSetFlags ${SecStartup} 1
      ${Else}
        SectionSetFlags ${SecStartup} 0
      ${EndIf}
      
      ReadINIStr $0 $CONFIG_FILE "NetworkDiscovery" "Enabled"
      ${If} $0 == "1"
        ${NSD_Check} $NetworkDiscoveryCheck
      ${Else}
        ${NSD_Uncheck} $NetworkDiscoveryCheck
      ${EndIf}
      
      ReadINIStr $0 $CONFIG_FILE "NetworkDiscovery" "Range"
      ${If} $0 != ""
        ${NSD_SetText} $NetworkRangeText $0
      ${EndIf}
    ${EndIf}
  ${EndIf}`
      );
    
    // Write the updated script
    await fs.promises.writeFile(nsiScriptPath, updatedScript);
    
    return { success: true };
  } catch (error) {
    console.error(`Error updating NSIS script: ${error.message}`);
    throw error;
  }
}

module.exports = {
  launchNSISInstaller,
  updateNSISScript
};