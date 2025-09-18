# Bitcoin Solo Miner Monitor - Remote Access Guide

## Overview
Your Bitcoin Solo Miner Monitor is designed as a web application that can be accessed remotely. This guide shows you how to access the monitoring dashboard from anywhere.

## Quick Start - Same Network Access

### Step 1: Find the Mining Computer's IP Address
On the computer running the Bitcoin Solo Miner Monitor:

**Windows:**
```cmd
ipconfig
```

**Look for the "IPv4 Address" under your active network adapter:**
```
Ethernet adapter Ethernet:
   IPv4 Address. . . . . . . . . . . : 192.168.1.100
```

### Step 2: Access from Other Devices
From any device on the same network (WiFi/Ethernet):
- Open web browser
- Go to: `http://192.168.1.100:8000` (replace with actual IP)
- The monitoring dashboard will load

**Works on:**
- ✅ Phones (iPhone, Android)
- ✅ Tablets (iPad, Android tablets)  
- ✅ Laptops (Windows, Mac, Linux)
- ✅ Other computers on the network

## Remote Access - Different Locations

### Option 1: Router Port Forwarding (Simple)

**Setup (Mining Partner does this once):**
1. Log into router admin panel (usually `192.168.1.1` or `192.168.0.1`)
2. Find "Port Forwarding" or "Virtual Server" settings
3. Add rule: External Port `8000` → Internal IP `192.168.1.100` Port `8000`
4. Find public IP address at [whatismyip.com](https://whatismyip.com)

**Access (You can do this from anywhere):**
- Go to: `http://[public-ip]:8000`
- Example: `http://203.0.113.45:8000`

**Security Note:** This exposes the service to the internet. Consider adding router firewall rules to limit access to specific IP addresses.

### Option 2: VPN Access (More Secure)

**Setup:**
1. Set up VPN server at mining location (router VPN, or service like Tailscale)
2. Connect to VPN from your device

**Access:**
- Connect to VPN first
- Then access: `http://192.168.1.100:8000` (internal IP)

### Option 3: Secure Tunnel (Most Secure)

**Using ngrok (free tier available):**
1. Install ngrok on mining computer
2. Run: `ngrok http 8000`
3. Get secure URL like: `https://abc123.ngrok.io`
4. Access from anywhere using that URL

## Troubleshooting

### Can't Access from Same Network
1. **Check Windows Firewall:**
   - Windows may block port 8000
   - Add exception for port 8000 or the application

2. **Verify Service is Running:**
   - Mining computer should show: "Server running on 0.0.0.0:8000"
   - Try accessing `http://localhost:8000` on mining computer first

3. **Check Network Settings:**
   - Ensure all devices are on same network
   - Some guest networks block device-to-device communication

### Can't Access Remotely
1. **Router Configuration:**
   - Verify port forwarding is set up correctly
   - Check if ISP blocks incoming connections on port 8000

2. **Dynamic IP Issues:**
   - Public IP addresses can change
   - Consider dynamic DNS service (like No-IP, DuckDNS)

3. **Firewall Issues:**
   - Router firewall may block external access
   - ISP may block certain ports

## Security Best Practices

### For Local Network Access
- ✅ Generally safe on trusted home/office networks
- ✅ No additional security needed for same-network access

### For Remote Access
- 🔒 **Use VPN when possible** (most secure)
- 🔒 **Change default port** from 8000 to something random (e.g., 18472)
- 🔒 **Limit access by IP** if you have static IP addresses
- 🔒 **Use HTTPS tunnel services** (like ngrok) instead of direct port forwarding
- 🔒 **Monitor access logs** for suspicious activity

## Mobile Access Tips

### Phone/Tablet Optimization
- The web interface is responsive and works well on mobile
- Add bookmark to home screen for app-like experience
- Consider using browser in "Desktop Mode" for full feature access

### Bookmark Setup
1. Open the monitoring URL in your mobile browser
2. Add to bookmarks or home screen
3. Name it "Mining Monitor" for easy access

## Example Network Scenarios

### Scenario 1: Home Mining Setup
- Mining rig in basement: `192.168.1.100:8000`
- Check from living room TV: Same URL
- Check from work: VPN → Same URL
- Partner checks from their house: Port forwarding or VPN

### Scenario 2: Remote Mining Facility  
- Mining facility with business internet
- VPN server at facility
- All partners connect via VPN
- Access internal monitoring dashboard

### Scenario 3: Multiple Locations
- Multiple mining locations
- Each runs monitoring on different ports
- Central VPN or tunnel service
- Dashboard shows: Location A, Location B, etc.

## Need Help?

If you're having trouble with remote access:
1. Test local access first (`http://localhost:8000`)
2. Test same-network access (`http://[internal-ip]:8000`)
3. Check firewall and router settings
4. Consider using VPN or tunnel service for security

The Bitcoin Solo Miner Monitor is designed to be accessible from anywhere - you just need to set up the network access method that works best for your situation!