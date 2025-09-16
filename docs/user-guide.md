# Bitcoin Solo Miner Monitor - User Guide

## Welcome to Bitcoin Solo Miner Monitor! 🚀⚡

This guide will help you get started with monitoring your Bitcoin solo mining operations after successful installation.

## Quick Start

### 1. Launch the Application

**After installation, start the application:**

- **Windows**: Desktop shortcut or Start Menu → "Bitcoin Solo Miner Monitor"
- **macOS**: Applications folder or Launchpad → "Bitcoin Solo Miner Monitor"
- **Linux**: Applications menu → "Bitcoin Solo Miner Monitor" or run `bitcoin-solo-miner-monitor`

### 2. Access the Dashboard

The application will automatically open your web browser to:
```
http://localhost:8000
```

If it doesn't open automatically, manually navigate to this URL in your browser.

### 3. Initial Setup Wizard

On first launch, you'll see the setup wizard:

1. **Welcome Screen** - Introduction and overview
2. **Network Configuration** - Set your network range for miner discovery
3. **Miner Discovery** - Automatically find miners on your network
4. **Manual Configuration** - Add miners that weren't auto-discovered
5. **Dashboard Setup** - Configure your monitoring preferences

## Supported Miners

### Bitaxe Series
- **Connection**: HTTP API
- **Default Port**: 80
- **Auto-discovery**: ✅ Yes
- **Features**: Full monitoring, configuration, performance metrics

### Avalon Nano Series
- **Connection**: CGMiner API
- **Default Port**: 4028
- **Auto-discovery**: ✅ Yes
- **Features**: Mining stats, pool information, hardware monitoring

### Magic Miner
- **Connection**: Web scraping
- **Default Port**: 80
- **Auto-discovery**: ✅ Yes
- **Features**: Basic monitoring, status information

### Generic Miners
- **Connection**: Configurable
- **Ports**: Custom
- **Auto-discovery**: ⚠️ Limited
- **Features**: Basic HTTP/API monitoring

## Dashboard Overview

### Main Dashboard

**Key Metrics Display:**
- Total hashrate across all miners
- Active miners count
- Network difficulty
- Recent block discoveries
- Power consumption estimates
- Temperature monitoring

**Real-time Charts:**
- Hashrate over time
- Temperature trends
- Power usage
- Pool statistics (if applicable)

### Individual Miner Views

**Per-miner information:**
- Current hashrate
- Temperature readings
- Power consumption
- Uptime statistics
- Error rates
- Pool connection status

## Configuration

### Network Settings

**Automatic Discovery:**
1. Go to Settings → Network
2. Set your network range (e.g., 192.168.1.0/24)
3. Click "Scan Network"
4. Select discovered miners to add

**Manual Miner Addition:**
1. Settings → Miners → Add Miner
2. Enter miner details:
   - Name/Label
   - IP Address
   - Port
   - Miner Type
   - Connection Method
3. Test connection
4. Save configuration

### Dashboard Customization

**Layout Options:**
- Grid view vs. list view
- Chart time ranges
- Metric display preferences
- Color themes
- Update intervals

**Alerts and Notifications:**
- Temperature thresholds
- Hashrate drop alerts
- Offline miner notifications
- Email notifications (if configured)

### Data Retention

**Configure how long to keep data:**
- Real-time data: 24 hours
- Hourly summaries: 30 days
- Daily summaries: 1 year
- Custom retention periods

## Monitoring Features

### Real-time Monitoring

**Live Updates:**
- Hashrate monitoring every 30 seconds
- Temperature checks every minute
- Status updates every 5 minutes
- Automatic reconnection on failures

**Performance Metrics:**
- Average hashrate calculations
- Efficiency measurements (hash/watt)
- Uptime tracking
- Error rate monitoring

### Historical Data

**Charts and Graphs:**
- Hashrate trends over time
- Temperature history
- Power consumption patterns
- Comparative miner performance

**Data Export:**
- CSV export for analysis
- JSON API for integration
- Backup/restore functionality

### Alerting System

**Alert Types:**
- Miner offline
- High temperature
- Low hashrate
- Network connectivity issues
- Power consumption anomalies

**Notification Methods:**
- Browser notifications
- Email alerts (if configured)
- System notifications
- Dashboard indicators

## Troubleshooting

### Common Issues

**Miners Not Discovered:**
1. Check network connectivity
2. Verify IP range settings
3. Ensure miners are powered on
4. Check firewall settings
5. Try manual addition

**Dashboard Not Loading:**
1. Verify application is running
2. Check port 8000 availability
3. Try different browser
4. Clear browser cache
5. Check firewall rules

**Inaccurate Data:**
1. Verify miner API settings
2. Check connection stability
3. Update miner firmware
4. Restart monitoring service
5. Clear cached data

### Performance Optimization

**For Better Performance:**
- Reduce update frequency for many miners
- Limit historical data retention
- Close unnecessary browser tabs
- Ensure adequate system resources
- Use wired network connections

**System Requirements:**
- Minimum: 2GB RAM, 500MB disk space
- Recommended: 4GB RAM, 1GB disk space
- Network: Stable local network connection

## Advanced Features

### API Access

**REST API Endpoints:**
```
GET /api/miners          # List all miners
GET /api/miners/{id}     # Get specific miner
GET /api/stats           # System statistics
GET /api/history         # Historical data
```

**WebSocket Updates:**
```javascript
// Connect to real-time updates
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle real-time updates
};
```

### Integration Options

**Third-party Integration:**
- Prometheus metrics export
- InfluxDB data storage
- Grafana dashboard templates
- Home Assistant integration

**Custom Scripts:**
- Python API client examples
- Bash monitoring scripts
- PowerShell automation
- Custom alert handlers

### Command Line Interface

**Available Commands:**
```bash
# Start with custom port
bitcoin-solo-miner-monitor --port 8001

# Enable debug logging
bitcoin-solo-miner-monitor --debug

# Run as service
bitcoin-solo-miner-monitor --service

# Export configuration
bitcoin-solo-miner-monitor --export-config config.json

# Import configuration
bitcoin-solo-miner-monitor --import-config config.json
```

## Security Considerations

### Network Security

**Best Practices:**
- Use dedicated mining network/VLAN
- Implement firewall rules
- Regular security updates
- Monitor network traffic
- Secure miner web interfaces

**Access Control:**
- Change default passwords on miners
- Use strong authentication
- Limit network access
- Regular security audits

### Data Privacy

**Local Data Only:**
- All data stored locally
- No external data transmission
- User controls all information
- Optional cloud backup

## Maintenance

### Regular Maintenance

**Weekly Tasks:**
- Check miner status
- Review performance trends
- Update miner firmware
- Verify network connectivity

**Monthly Tasks:**
- Clean historical data
- Backup configuration
- Review alert settings
- Check for software updates

**Quarterly Tasks:**
- Full system review
- Security audit
- Performance optimization
- Hardware inspection

### Updates

**Application Updates:**
- Automatic update notifications
- Manual update process
- Backup before updating
- Rollback procedures

**Miner Firmware:**
- Regular firmware checks
- Coordinated update scheduling
- Backup configurations
- Test after updates

## Getting Help

### Documentation

- **[Installation Guide](installation/README.md)** - Complete installation instructions
- **[Troubleshooting Guide](installation/troubleshooting.md)** - Common issues and solutions
- **[Security Guide](installation/security-guide.md)** - Security best practices
- **[Build Guide](BUILD.md)** - Building from source

### Community Support

- **[GitHub Issues](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions)** - Community support and questions
- **[Project Wiki](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/wiki)** - Community documentation

### Contributing

**Ways to Contribute:**
- Report bugs and issues
- Suggest new features
- Test on different platforms
- Improve documentation
- Submit code contributions
- Help other users

**Development:**
- Fork the repository
- Create feature branches
- Submit pull requests
- Follow coding standards
- Add tests for new features

## Frequently Asked Questions

### General Questions

**Q: Does this software mine Bitcoin?**
A: No, this is a monitoring application. It watches your miners but doesn't mine itself.

**Q: Does it work with mining pools?**
A: Yes, it monitors miners regardless of whether they're solo mining or pool mining.

**Q: Can I monitor remote miners?**
A: Yes, as long as they're network accessible and you configure the correct IP addresses.

**Q: Is my data sent anywhere?**
A: No, all data stays on your local system. The only external connection is for optional update checks.

### Technical Questions

**Q: What ports does it use?**
A: The dashboard runs on port 8000 by default. It connects to miners on their respective ports (80, 4028, etc.).

**Q: Can I run multiple instances?**
A: Yes, but they need different ports. Use `--port` parameter to specify alternative ports.

**Q: Does it support HTTPS?**
A: Currently HTTP only for local access. HTTPS support is planned for remote access scenarios.

**Q: Can I customize the dashboard?**
A: Yes, the dashboard supports themes, layout options, and metric customization.

### Troubleshooting Questions

**Q: Why can't I see my miners?**
A: Check network connectivity, firewall settings, and ensure miners are on the same network segment.

**Q: Why is the dashboard slow?**
A: Try reducing update frequency, limiting historical data, or checking system resources.

**Q: How do I backup my configuration?**
A: Use the export function in settings or manually backup the configuration files.

## Conclusion

Bitcoin Solo Miner Monitor is designed to make monitoring your mining operations simple and effective. Whether you're running a single Bitaxe or a farm of various miners, this tool provides the insights you need to optimize your setup.

**Remember**: This tool is built by solo miners, for solo miners. Your feedback and contributions help make it better for the entire community!

**Happy Mining!** 🚀⚡

---

**Need more help?** Check out our [community resources](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/discussions) or [report an issue](https://github.com/smokeysrh/bitcoin-solo-miner-monitor/issues/new/choose).