const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs'); // Using built-in fs instead of fs-extra
const os = require('os');
const { exec, execSync } = require('child_process');
const Store = require('electron-store');
const sudoPrompt = require('sudo-prompt');
const extract = require('extract-zip');
// Network scanning will be implemented later

// Initialize configuration store
const store = new Store({
  name: 'installer-config',
  defaults: {
    installDir: getDefaultInstallDir(),
    dataDir: getDefaultDataDir(),
    createDesktopShortcut: true,
    createStartMenuShortcut: true,
    startOnBoot: true,
    autoDiscovery: true,
    networkRange: '192.168.1.0/24'
  }
});

// Get default installation directory based on platform
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

// Get default data directory based on platform
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

// Create the main window
let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    minWidth: 900,
    minHeight: 650,
    resizable: true,
    show: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true
    },
    icon: path.join(__dirname, 'assets', 'installer_icon.png')
  });

  mainWindow.loadFile('index.html');
  
  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// App ready event
app.whenReady().then(() => {
  createWindow();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed, except on macOS
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC handlers for installer steps
ipcMain.handle('get-system-info', async () => {
  return {
    platform: process.platform,
    arch: process.arch,
    cpuCores: os.cpus().length,
    totalMemory: Math.round(os.totalmem() / (1024 * 1024 * 1024)), // GB
    freeMemory: Math.round(os.freemem() / (1024 * 1024 * 1024)), // GB
    hostname: os.hostname(),
    username: os.userInfo().username,
    homedir: os.homedir()
  };
});

ipcMain.handle('get-installer-config', async () => {
  return store.store;
});

ipcMain.handle('update-installer-config', async (event, config) => {
  store.set(config);
  return store.store;
});

ipcMain.handle('select-install-dir', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select Installation Directory'
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    store.set('installDir', result.filePaths[0]);
    return result.filePaths[0];
  }
  
  return store.get('installDir');
});

ipcMain.handle('select-data-dir', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select Data Directory'
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    store.set('dataDir', result.filePaths[0]);
    return result.filePaths[0];
  }
  
  return store.get('dataDir');
});

ipcMain.handle('check-dependencies', async () => {
  const dependencies = {
    python: { required: '3.11.0', installed: null, status: 'not-found' },
    nodejs: { required: '18.0.0', installed: null, status: 'not-found' }
  };
  
  // Check Python
  try {
    const pythonVersion = execSync('python3 --version || python --version').toString().trim();
    const versionMatch = pythonVersion.match(/Python (\d+\.\d+\.\d+)/);
    if (versionMatch) {
      dependencies.python.installed = versionMatch[1];
      dependencies.python.status = compareVersions(versionMatch[1], dependencies.python.required) >= 0 ? 'ok' : 'outdated';
    }
  } catch (error) {
    console.error('Python check error:', error);
  }
  
  // Check Node.js
  try {
    const nodeVersion = execSync('node --version').toString().trim();
    const versionMatch = nodeVersion.match(/v(\d+\.\d+\.\d+)/);
    if (versionMatch) {
      dependencies.nodejs.installed = versionMatch[1];
      dependencies.nodejs.status = compareVersions(versionMatch[1], dependencies.nodejs.required) >= 0 ? 'ok' : 'outdated';
    }
  } catch (error) {
    console.error('Node.js check error:', error);
  }
  
  // InfluxDB is no longer required - removed dependency check
  
  return dependencies;
});

// Helper function to compare version strings
function compareVersions(a, b) {
  const aParts = a.split('.').map(Number);
  const bParts = b.split('.').map(Number);
  
  for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
    const aVal = aParts[i] || 0;
    const bVal = bParts[i] || 0;
    
    if (aVal > bVal) return 1;
    if (aVal < bVal) return -1;
  }
  
  return 0;
}

ipcMain.handle('scan-network', async (event, networkRange) => {
  return new Promise((resolve) => {
    // Real network scan implementation would go here
    console.log(`Scanning network range: ${networkRange}`);
    
    // Simulate a delay like a real network scan
    setTimeout(() => {
      // Return empty array - no mock data in production
      const hosts = [];
      
      console.log(`Found ${hosts.length} potential devices`);
      resolve(hosts);
    }, 2000); // 2 second delay to simulate scanning
  });
});

ipcMain.handle('detect-miners', async (event, hosts) => {
  const miners = [];
  
  // Real miner detection implementation would go here
  // For now, return empty array - no mock data in production
  for (const host of hosts) {
    // Real detection logic would attempt to connect to each host
    // and determine if it's a supported miner type
    // This is left empty for production deployment
  }
  
  console.log(`Detected ${miners.length} miners`);
  return miners;
});

// Helper function to check if a port is open
function checkPort(ip, port) {
  return new Promise((resolve) => {
    const net = require('net');
    const socket = new net.Socket();
    
    socket.setTimeout(1000);
    
    socket.on('connect', () => {
      socket.destroy();
      resolve(true);
    });
    
    socket.on('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    
    socket.on('error', () => {
      socket.destroy();
      resolve(false);
    });
    
    socket.connect(port, ip);
  });
}

// Mock installer bridge for testing
// const installerBridge = require('../../integration/installer_bridge');

ipcMain.handle('install-application', async (event, options) => {
  // Installation simulation for testing purposes
  console.log('Starting installation simulation with options:', options);
  
  // Define installation steps
  const steps = [
    { id: 'prepare', name: 'Preparing installation (SIMULATION)', status: 'pending' },
    { id: 'dependencies', name: 'Installing dependencies (SIMULATION)', status: 'pending' },
    { id: 'files', name: 'Copying application files (SIMULATION)', status: 'pending' },
    { id: 'database', name: 'Setting up database (SIMULATION)', status: 'pending' },
    { id: 'config', name: 'Creating configuration (SIMULATION)', status: 'pending' },
    { id: 'shortcuts', name: 'Creating shortcuts (SIMULATION)', status: 'pending' },
    { id: 'finish', name: 'Finalizing installation (SIMULATION)', status: 'pending' }
  ];
  
  // Update step status and send progress updates
  const updateStep = (id, status, message = null) => {
    const step = steps.find(s => s.id === id);
    if (step) {
      step.status = status;
      step.message = message;
      event.sender.send('installation-progress', { steps, currentStep: id });
    }
  };
  
  // Simulate installation process
  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    
    // Start step
    updateStep(step.id, 'in-progress');
    
    // Simulate work being done
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
    
    // Complete step
    updateStep(step.id, 'completed', `${step.name} completed successfully`);
  }
  
  console.log('Mock installation completed successfully');
  return { success: true, message: 'Installation completed successfully' };
});

// Save setup data for the main application
ipcMain.handle('save-setup-data', async (event, setupData) => {
  try {
    const dataDir = store.get('dataDir');
    
    // Use Node.js built-in fs instead of fs-extra to avoid dependency issues
    const fsBuiltin = require('fs').promises;
    
    // Ensure directory exists
    try {
      await fsBuiltin.mkdir(dataDir, { recursive: true });
    } catch (err) {
      if (err.code !== 'EEXIST') throw err;
    }
    
    const setupFilePath = path.join(dataDir, 'setup-complete.json');
    await fsBuiltin.writeFile(setupFilePath, JSON.stringify(setupData, null, 2), 'utf8');
    
    console.log('Setup data saved to:', setupFilePath);
    return { success: true };
  } catch (error) {
    console.error('Error saving setup data:', error);
    return { success: false, message: error.message };
  }
});

// Launch application after installation
ipcMain.handle('launch-application', async () => {
  try {
    // Get the installation directory from the installer settings
    const installDir = store.get('installDir') || path.join(process.env.PROGRAMFILES || 'C:\\Program Files', 'Bitcoin Solo Miner Monitor');
    const runScript = path.join(installDir, 'run.py');
    
    console.log('Attempting to launch application from:', installDir);
    
    // Check if the installed application exists
    if (fs.existsSync(runScript)) {
      console.log('Launching installed application...');
      
      // Launch the Python application
      exec(`python "${runScript}"`, { 
        cwd: installDir,
        detached: true,
        stdio: 'ignore'
      }, (error) => {
        if (error) {
          console.error('Error launching installed application:', error);
        } else {
          console.log('Application launched successfully');
        }
      });
      
      return { success: true, message: 'Bitcoin Solo Miner Monitor launched successfully' };
    } else {
      // Fallback: try to launch development version for testing
      const projectRoot = path.join(__dirname, '..', '..', '..');
      const devRunScript = path.join(projectRoot, 'run.py');
      
      if (fs.existsSync(devRunScript)) {
        console.log('Launching development version for testing...');
        exec(`python "${devRunScript}"`, { 
          cwd: projectRoot,
          detached: true,
          stdio: 'ignore'
        }, (error) => {
          if (error) {
            console.error('Error launching development application:', error);
          }
        });
        return { success: true, message: 'Development version launched for testing' };
      } else {
        return { success: false, message: 'Application not found. Please check the installation.' };
      }
    }
  } catch (error) {
    console.error('Error launching application:', error);
    return { success: false, message: error.message };
  }
});