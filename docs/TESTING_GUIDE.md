# 🧪 Testing Guide for Bitcoin Solo Miner Monitor

## For Non-Developers: Simple Testing Scripts

This guide provides **simple, double-click scripts** to test the complete user experience without any technical knowledge required.

## 📋 Prerequisites

Before testing, make sure you have these installed on your computer:

### 1. Python (Required)
- Go to [python.org](https://python.org)
- Download Python 3.11 or newer
- **IMPORTANT**: During installation, check the box "Add Python to PATH"
- Restart your computer after installation

### 2. Node.js (Required)
- Go to [nodejs.org](https://nodejs.org)
- Download and install the LTS (Long Term Support) version
- Restart your computer after installation

## 🚀 How to Test

### Option 1: Quick Test (Recommended)
**Double-click: `test-complete-flow.bat`**

This opens a simple menu where you can choose what to test:
- Install Wizard only
- Main Application only  
- Complete user flow (both)

### Option 2: Test Individual Components

#### Test Install Wizard Only
**Double-click: `test-install-wizard.bat`**
- Tests the installation experience
- Shows what new users see when installing
- Safe simulation - nothing actually gets installed

#### Test Main Application Only
**Double-click: `test-full-application.bat`**
- Tests the main monitoring application
- Shows the first-run setup wizard
- Lets you test all application features

## 📖 What Each Test Shows You

### Install Wizard Test
When you run the install wizard test, you'll see:

1. **Welcome Screen** - Choose your experience level
2. **System Check** - Verifies your computer meets requirements
3. **Installation Options** - Choose where to install, shortcuts, etc.
4. **Network Discovery** - Scans for Bitcoin miners on your network
5. **Component Selection** - Choose which features to install
6. **Installation Progress** - Shows installation happening (simulated)
7. **Completion** - Installation finished, ready to launch

### Main Application Test
When you run the main application test, you'll see:

1. **Application Starts** - Backend server launches
2. **Open Browser** - Go to http://localhost:8000
3. **First-Run Wizard** - Configure the app for first use:
   - Welcome and experience level
   - Network discovery for miners
   - Miner configuration
   - User preferences
   - Setup completion
4. **Main Dashboard** - Monitor your Bitcoin miners

## 🔧 Troubleshooting

### "Node.js is not installed" Error
- Install Node.js from [nodejs.org](https://nodejs.org)
- Choose the LTS version
- Restart your computer
- Try again

### "Python is not installed" Error
- Install Python from [python.org](https://python.org)
- Make sure to check "Add Python to PATH" during installation
- Restart your computer
- Try again

### "Failed to install dependencies" Error
- Check your internet connection
- Try running the script again
- If it keeps failing, restart your computer and try again

### Application Won't Start
- Make sure both Python and Node.js are installed
- Check that you're running the script from the correct folder
- Try restarting your computer

## 📝 What to Look For During Testing

### Install Wizard Testing
- [ ] Does the wizard open properly?
- [ ] Can you navigate through all steps?
- [ ] Does network discovery find miners (it will show mock miners for testing)?
- [ ] Can you change installation options?
- [ ] Does the installation progress work?
- [ ] Does the wizard complete successfully?

### Main Application Testing
- [ ] Does the application start without errors?
- [ ] Can you access http://localhost:8000 in your browser?
- [ ] Does the first-run wizard appear?
- [ ] Can you complete the setup wizard?
- [ ] Does the main dashboard load?
- [ ] Can you add miners and see monitoring data?

## 🆘 Getting Help

If you encounter issues:

1. **Note exactly what happened**:
   - Which script you ran
   - What step you were on
   - What error message you saw
   - What you expected vs. what happened

2. **Try these first**:
   - Restart your computer
   - Make sure Python and Node.js are installed
   - Check your internet connection
   - Run the script again

3. **Common Solutions**:
   - **Script won't run**: Right-click the .bat file and "Run as administrator"
   - **Dependencies fail**: Check internet connection and try again
   - **Browser won't open**: Manually go to http://localhost:8000
   - **Application crashes**: Check that no other programs are using port 8000

## ✅ Success Criteria

Your testing is successful if:

- [ ] Install wizard opens and you can complete all steps
- [ ] Main application starts and you can access it in your browser
- [ ] First-run setup wizard works properly
- [ ] You can see the main monitoring dashboard
- [ ] No critical errors or crashes occur

## 📞 Reporting Issues

When reporting issues, please include:
- Which test script you used
- Your operating system (Windows version)
- Screenshots of any error messages
- Step-by-step description of what you did
- What you expected to happen vs. what actually happened

This helps developers fix issues quickly and improve the user experience!