# Development Mode Guide

## What is Development Mode?

Development mode is a special mode that enables verbose logging and debugging features throughout the application. It's used to help diagnose issues, understand application behavior, and debug problems during development and testing.

## How Development Mode Works

The application uses a `DEBUG_MODE` flag that is determined by:

```javascript
const DEBUG_MODE =
  import.meta.env.DEV || localStorage.getItem("debug") === "true";
```

This means development mode is **automatically enabled** when:

1. Running the development server (`npm run dev`)
2. OR when you manually enable it via localStorage

## How to Enable/Disable Development Mode

### Method 1: Run Development Server (Automatic)

**To Enable:**

```bash
cd src/frontend
npm run dev
```

This automatically sets `import.meta.env.DEV` to `true`, enabling all debug logging.

**To Disable:**
Stop the dev server and run the production build:

```bash
cd src/frontend
npm run build
npm run preview
```

### Method 2: Manual Toggle via Browser Console

**To Enable (in any mode):**

1. Open your browser's Developer Tools (F12)
2. Go to the Console tab
3. Run:

```javascript
localStorage.setItem("debug", "true");
```

4. Refresh the page

**To Disable:**

```javascript
localStorage.setItem("debug", "false");
// OR
localStorage.removeItem("debug");
```

Then refresh the page.

**To Check Current Status:**

```javascript
console.log("Debug mode:", localStorage.getItem("debug"));
console.log("DEV mode:", import.meta.env.DEV);
```

## What Changes in Development Mode?

### 1. WebSocket Service (`websocket.js`)

When `DEBUG_MODE = true`:

- Logs connection attempts and status
- Shows subscription updates
- Displays message types received
- Logs reconnection attempts
- Shows ping/pong latency warnings

When `DEBUG_MODE = false`:

- Only logs critical events (connection established/closed)
- Minimal console output

### 2. Settings Service (`settingsService.js`)

When `DEBUG_MODE = true`:

- Logs cache usage
- Shows API authentication details
- Displays save attempts and retries
- Shows validation steps

When `DEBUG_MODE = false`:

- Only logs errors and important events
- No routine operation logs

### 3. Miners Store (`miners.js`)

When `DEBUG_MODE = true`:

- Logs WebSocket initialization
- Shows subscription status
- Displays connection state changes

When `DEBUG_MODE = false`:

- Minimal logging

### 4. Other Features

When `process.env.NODE_ENV === 'development'`:

- Easter egg debug utilities available
- Accessibility testing tools loaded
- CSS optimization analysis tools available
- Additional window debugging functions

## Diagnostic Page Access

According to the design document, the diagnostic page will be accessible:

1. **In development mode** - Always accessible
2. **In production** - Only with URL parameter `?diagnostics=true`

Example:

```
http://localhost:5173/diagnostics          # Works in dev mode
http://localhost:5173/diagnostics?diagnostics=true  # Works in production
```

## Use Cases

### During Development

```bash
# Start dev server (debug mode ON automatically)
cd src/frontend
npm run dev
```

- All debug logs visible
- Full visibility into application behavior
- Easier to diagnose issues

### Testing Production Build with Debug

```bash
# Build and preview
cd src/frontend
npm run build
npm run preview
```

Then in browser console:

```javascript
localStorage.setItem("debug", "true");
// Refresh page
```

- Test production build
- Enable debug logs when needed
- Verify production behavior

### Production Deployment

```bash
# Build for production
cd src/frontend
npm run build
```

- Debug mode OFF by default
- Minimal console output
- Better performance
- Can be enabled by users if needed for troubleshooting

## Quick Reference

| Scenario           | Command/Action                          | Debug Mode        |
| ------------------ | --------------------------------------- | ----------------- |
| Development        | `npm run dev`                           | ✅ ON (automatic) |
| Production Build   | `npm run build`                         | ❌ OFF            |
| Production Preview | `npm run preview`                       | ❌ OFF            |
| Manual Enable      | `localStorage.setItem('debug', 'true')` | ✅ ON             |
| Manual Disable     | `localStorage.removeItem('debug')`      | ❌ OFF            |

## Checking Current Mode

To verify which mode you're currently in:

1. Open browser console (F12)
2. Look for log messages:

   - If you see detailed logs like "WebSocket initialization", "Cache usage", etc. → Debug mode is ON
   - If you only see minimal logs → Debug mode is OFF

3. Or run:

```javascript
// Check localStorage setting
console.log("localStorage debug:", localStorage.getItem("debug"));

// Check if running dev server
console.log("DEV mode:", import.meta.env.DEV);

// The actual DEBUG_MODE value used by the app
console.log(
  "Effective debug mode:",
  import.meta.env.DEV || localStorage.getItem("debug") === "true"
);
```

## Tips

1. **For Bug Hunting**: Enable debug mode to see detailed logs
2. **For Performance Testing**: Disable debug mode to reduce console overhead
3. **For Production Issues**: Users can enable debug mode temporarily to help diagnose issues
4. **For Development**: Just use `npm run dev` - debug mode is automatic

## Related Files

- `src/frontend/src/services/websocket.js` - WebSocket debug logging
- `src/frontend/src/services/settingsService.js` - Settings debug logging
- `src/frontend/src/stores/miners.js` - Miners store debug logging
- `CONSOLE_LOGGING_CLEANUP_SUMMARY.md` - Details on logging cleanup
