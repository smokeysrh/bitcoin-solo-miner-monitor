# Quick Start Guide - Running from Source Code

**Version:** 0.9.1  
**For:** Testing and development purposes

## What You Downloaded

You downloaded the **source code** (not a pre-built installer). This requires Python and Node.js to be installed on your system.

## Prerequisites

Before you can run the application, you need:

1. **Python 3.11 or higher**
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

2. **Node.js 18.x or higher**
   - Download from: https://nodejs.org/
   - Choose the LTS (Long Term Support) version

## Installation Steps

### Step 1: Verify Prerequisites

Open Command Prompt (cmd) or PowerShell and verify installations:

```bash
python --version
# Should show: Python 3.11.x or higher

node --version
# Should show: v18.x.x or higher

npm --version
# Should show: 9.x.x or higher
```

### Step 2: Navigate to the Application Folder

```bash
cd path\to\BTCsoloApp
# Replace with the actual path where you unzipped the files
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install all required Python packages (FastAPI, aiohttp, etc.)

### Step 4: Install Frontend Dependencies

```bash
cd src\frontend
npm install
cd ..\..
```

This will install all required Node.js packages (Vue.js, Vuetify, etc.)

## Running the Application

### Option 1: Using the Run Script (Easiest)

From the root directory (BTCsoloApp):

```bash
python run.py
```

This will:
- Start the backend server on http://localhost:8000
- Start the frontend dev server on http://localhost:3000
- Open your browser automatically

### Option 2: Manual Start (Two Terminals)

**Terminal 1 - Backend:**
```bash
python src\main.py
```

**Terminal 2 - Frontend:**
```bash
cd src\frontend
npm run dev
```

Then open your browser to: http://localhost:3000

## First Time Setup

1. **Allow Firewall Access**
   - Windows may prompt you to allow network access
   - Click "Allow" for both Private and Public networks
   - This is needed for miner discovery on your network

2. **Access the Application**
   - The app should open automatically in your browser
   - If not, navigate to: http://localhost:3000

3. **Add Your Miners**
   - Click "Add Miner" or use "Scan Network" to discover miners
   - The app will find miners on your local network (192.168.1.156, etc.)

## Stopping the Application

- Press `Ctrl+C` in the terminal(s) where the app is running
- Or close the terminal windows

## Troubleshooting

### "Python is not recognized"
- Python is not installed or not in PATH
- Reinstall Python and check "Add Python to PATH"

### "npm is not recognized"
- Node.js is not installed or not in PATH
- Reinstall Node.js

### Port Already in Use
If you see "Port 8000 already in use" or "Port 3000 already in use":
```bash
# Find and kill the process using the port
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

### Dependencies Installation Fails
Try upgrading pip first:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend Build Errors
Clear npm cache and reinstall:
```bash
cd src\frontend
rmdir /s /q node_modules
npm cache clean --force
npm install
```

## For Production Use

**Note:** Running from source is for testing/development. For production use, you should:

1. Build a proper installer using the build scripts in `/scripts`
2. Or wait for official pre-built installers to be released
3. Or use the Docker deployment option

## Need Help?

- Check the full documentation in `/docs`
- Review the README.md for more details
- Check GitHub Issues for known problems
- The miner at 192.168.1.156 should be automatically detected once the app is running

## What's Next?

Once the app is running:
1. Go to Dashboard
2. Click "Scan Network" to find your miners
3. Your NerdQAxe at 192.168.1.156 should appear
4. Click "View Details" to see detailed miner information
5. Explore the Analytics and Network Topology pages

---

**Remember:** This is running in development mode. For a production installation, use the official installer when available.
