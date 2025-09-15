# Email Notifications Setup Guide

This guide explains how to configure and use email notifications in the Bitcoin Solo Miner Monitoring App.

## Overview

The email notification system allows users to receive alerts via email when important events occur with their miners, such as:

- Miner goes offline
- Temperature exceeds threshold  
- Hashrate drops significantly
- New miner discovered

## Setup Process

### 1. Initial Configuration During Setup Wizard

During the setup wizard (Step 4 - User Preferences), users can:

1. Enable "Email Notifications" toggle
2. Enter their email address when the toggle is enabled
3. The email address field includes validation to ensure proper format

### 2. Backend Email Service Configuration

The email service requires SMTP configuration to actually send emails. This can be configured via the API endpoints:

#### Get Current Configuration
```
GET /api/email/config
```

#### Update Configuration
```
PUT /api/email/config
Content-Type: application/json

{
  "enabled": true,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "your-email@gmail.com", 
  "password": "your-app-password",
  "use_tls": true,
  "from_address": "your-email@gmail.com",
  "from_name": "Bitcoin Miner Monitor"
}
```

#### Test Email Configuration
```
POST /api/email/test
Content-Type: application/json

{
  "to_email": "test@example.com"
}
```

## Security Features

### Rate Limiting
- Maximum 10 emails per hour per recipient
- Maximum 50 emails per day per recipient
- Prevents spam and abuse

### Email Validation
- Frontend validation for proper email format
- Backend validation using `email-validator` library
- DNS validation to ensure domain accepts email

### Configuration Security
- Passwords are not returned in configuration responses
- API endpoints require authentication
- Input sanitization and validation

## Email Templates

The system uses a single, professional unified email template that meets industry standards with proper Bitcoin Miner Monitor branding. The template features:

### Design Features
- **Professional Layout**: Clean, responsive design that works on all devices
- **Bitcoin Branding**: Orange gradient header with Bitcoin symbol (₿) and app branding
- **Priority-Based Styling**: Color-coded alerts based on severity (Critical, Warning, Info)
- **Structured Information**: Organized details section with clear labels and values
- **Call-to-Action**: Prominent button linking back to the dashboard
- **Mobile Responsive**: Optimized for both desktop and mobile email clients

### Notification Types

#### 🚨 Miner Offline Alert (Critical Priority)
- **Color**: Red (#dc3545)
- **Details**: Miner name, IP address, status, last seen timestamp
- **Action**: Check power and network connection

#### 🌡️ Temperature Alert (Warning Priority)  
- **Color**: Orange (#fd7e14)
- **Details**: Current temperature, threshold, severity level
- **Action**: Check ventilation and cooling systems

#### 📉 Hashrate Drop Alert (Warning Priority)
- **Color**: Yellow (#ffc107) 
- **Details**: Current vs expected hashrate, drop percentage
- **Action**: Check for hardware or network issues

#### 🔍 New Miner Discovered (Info Priority)
- **Color**: Blue (#17a2b8)
- **Details**: Miner type, model, status
- **Action**: Review settings and configure alerts

#### ✅ Test Email (Info Priority)
- **Color**: Green (#28a745)
- **Details**: Test type, status, recipient, service info
- **Action**: Configuration confirmation message

### Template Features
- **HTML5 Compliant**: Modern HTML structure with proper DOCTYPE
- **CSS Inline Styles**: Maximum email client compatibility
- **Accessibility**: Proper contrast ratios and semantic HTML
- **Professional Typography**: System font stack for consistent rendering
- **Gradient Backgrounds**: Subtle gradients for visual appeal
- **Box Shadows**: Modern depth and elevation effects
- **Responsive Grid**: Flexible layout that adapts to screen size

## Configuration Examples

### Gmail Configuration
```json
{
  "enabled": true,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "your-email@gmail.com",
  "password": "your-app-password",
  "use_tls": true,
  "from_address": "your-email@gmail.com",
  "from_name": "Bitcoin Miner Monitor"
}
```

**Note**: For Gmail, you need to use an "App Password" instead of your regular password.

### Outlook/Hotmail Configuration
```json
{
  "enabled": true,
  "smtp_server": "smtp-mail.outlook.com",
  "smtp_port": 587,
  "username": "your-email@outlook.com",
  "password": "your-password",
  "use_tls": true,
  "from_address": "your-email@outlook.com", 
  "from_name": "Bitcoin Miner Monitor"
}
```

## Troubleshooting

### Common Issues

1. **"Email service is not configured"**
   - Ensure all required fields are set: smtp_server, username, password, from_address
   - Set `enabled: true` in the configuration

2. **"Invalid email address"**
   - Check email format includes @ symbol and valid domain
   - Ensure domain accepts email (some test domains like example.com don't)

3. **"Rate limit exceeded"**
   - Wait for the rate limit window to reset
   - Check if too many emails were sent recently

4. **SMTP connection errors**
   - Verify SMTP server and port are correct
   - Check if TLS is required (most modern servers require it)
   - Ensure username/password are correct
   - For Gmail, use App Passwords instead of regular password

### Testing Email Configuration

Use the test endpoint to verify your configuration:

```bash
curl -X POST "http://localhost:8000/api/email/test" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"to_email": "your-email@example.com"}'
```

## Data Storage

Email preferences are stored in:
- **Frontend**: localStorage as part of `userPreferences`
- **Setup Wizard**: Collected during step 4 and saved via `firstRunService`
- **Backend**: Email configuration stored in email service (in-memory, consider persisting to database for production)

## Technical Specifications

### Email Template Architecture
- **Template Engine**: Jinja2 for dynamic content rendering
- **HTML Structure**: Single unified template with conditional content
- **CSS Framework**: Custom inline styles for maximum compatibility
- **Font Stack**: System fonts (-apple-system, BlinkMacSystemFont, Segoe UI, Roboto)
- **Color Palette**: Bitcoin-themed orange (#f7931a) with semantic colors for alerts
- **Responsive Breakpoint**: 600px width for mobile optimization

### Email Client Compatibility
The template is designed to work across major email clients:
- **Desktop**: Outlook 2016+, Apple Mail, Thunderbird, Gmail web
- **Mobile**: iOS Mail, Android Gmail, Outlook mobile
- **Webmail**: Gmail, Yahoo Mail, Outlook.com, iCloud Mail

### Performance Optimizations
- **Inline CSS**: All styles inlined for maximum compatibility
- **Minimal Images**: Uses Unicode emojis instead of image assets
- **Lightweight HTML**: Optimized structure under 50KB
- **Fast Rendering**: Table-based layout for older email clients

## Future Enhancements

Potential improvements for the email system:
- Database persistence for email configuration
- Custom template themes and color schemes
- Unsubscribe mechanism with preference center
- Email delivery status tracking and analytics
- Multiple recipient support with distribution lists
- Email scheduling and batching for digest notifications
- Dark mode template variant
- Multi-language template support