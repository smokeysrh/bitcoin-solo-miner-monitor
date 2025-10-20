# Network Scan Diagnostics Report
**Date:** October 19, 2025  
**Status:** 🔴 CRITICAL ISSUES IDENTIFIED

---

## Executive Summary

The Network Scan feature is failing due to a **cascade of performance issues** that overwhelm the browser and cause WebSocket disconnections. The root cause is **excessive polling** that ignores user settings.

---

## Critical Issues Identified

### Issue #1: Settings Not Being Applied ⚠️ CRITICAL

**Problem:**
- User sets polling interval to 120 seconds
- User sets UI refresh to 60 seconds  
- Settings save successfully to backend
- **BUT the intervals are NOT being used by the components**

**Root Cause:**
Each view (Dashboard, Miners, MinerDetail, Network) creates its own `setInterval` in `onMounted()`:

```javascript
// Dashboard.vue line 507
const refreshTime = settingsStore.settings.refresh_interval * 1000 || 10000;
refreshInterval = setInterval(async () => {
  await minersStore.fetchMiners();
}, refreshTime);
```

**The Problem:**
- The interval is set ONCE when the component mounts
- It reads `settingsStore.settings.refresh_interval` at that moment
- If settings change later, the interval keeps running with the OLD value
- The interval is never updated when settings change

**Evidence:**
- User reports: "even after setting the polling interval to 120 seconds, its still doing it every few seconds"
- Settings save successfully but behavior doesn't change
- Multiple components all polling independently

---

### Issue #2: Multiple Polling Sources � CMODERATE

**Problem:**
Multiple components create their own polling intervals:

1. **Dashboard.vue** - polls every `refresh_interval` seconds
2. **Miners.vue** - polls every `refresh_interval` seconds  
3. **MinerDetail.vue** - polls every `refresh_interval` seconds
4. **Network.vue** - polls every `refresh_interval * 5` seconds

**Actual Behavior Observed:**
```
10:38:17 - Request from Miners page
10:38:25 - Request from Miners page (8 seconds later)
10:38:27 - Request from Dashboard (2 seconds later)
```

**Pattern:**
- One request every ~10 seconds (matching the original setting)
- Requests come from different pages/components
- Pattern: 3 requests over 30 seconds, then "Received pong from server"

**Impact:**
- Not as severe as initially thought
- Main issue is settings not being applied, not excessive simultaneous requests

---

### Issue #3: WebSocket Heartbeat Failure 🟡 MODERATE

**Problem:**
- Backend sends `ping` every 30 seconds
- Frontend responds with `pong` 
- **BUT the browser is too busy to respond in time**
- Backend marks connection as "stale" after 75 seconds (2.5 × 30s)
- WebSocket closes, interrupting the network scan

**Evidence:**
- Console shows "Received pong from server" - so pong IS being sent
- Backend logs show "Client is stale (no ping response for 90s)"
- This means the pong is being sent but arriving too late

**Why Pongs Are Delayed:**
The browser's event loop is overwhelmed:
```
1. Process 3 HTTP requests to /api/miners
2. Parse 3 JSON responses
3. Update 3 component states
4. Trigger 3 re-renders
5. Process WebSocket ping message (DELAYED)
6. Send pong (TOO LATE)
```

---

### Issue #4: Excessive Console Logging 🟡 MODERATE

**Problem:**
Every single `/api/miners` request logs to console:
```javascript
// settingsService.js line 86
console.log(`SettingsService: No auth required for ${config.method} ${config.url}`);
```

**Impact:**
- Console spam makes debugging impossible
- Logging to console is SLOW (blocks main thread)
- Each log statement adds ~5-10ms delay
- With 3 requests every 10 seconds = 18 logs per minute
- This compounds the browser performance issues

---

### Issue #5: Backend Broadcasting Spam 🟡 MODERATE

**Problem:**
Backend broadcasts `miners_update` every 1 second to all clients:

```
2025-10-19 10:14:44,242 - Broadcasting miners_update to 2 clients on topic 'miners'
2025-10-19 10:14:45,235 - Broadcasting miners_update to 2 clients on topic 'miners'
2025-10-19 10:14:46,242 - Broadcasting miners_update to 2 clients on topic 'miners'
```

**Why This Is Wrong:**
- Broadcasting every second even when there are **0 miners**
- Broadcasting even when **nothing has changed**
- This defeats the purpose of WebSocket (should only send when data changes)
- Adds unnecessary load to both backend and frontend

**Configuration:**
```python
# websocket_manager.py line 48
self._broadcast_intervals = {
    "miners": 1.0,  # ← TOO FREQUENT
    "alerts": 5.0,
    "system": 10.0,
    "discovery": 0.5,
}
```

---

## The Cascade Effect

Here's how these issues compound each other:

```
1. Multiple components poll /api/miners every 10s
   ↓
2. Browser processes 3+ HTTP requests simultaneously
   ↓
3. Each request logs to console (slows down main thread)
   ↓
4. Backend broadcasts miners_update every 1s via WebSocket
   ↓
5. Frontend processes WebSocket messages (more work)
   ↓
6. Components re-render with new data (even if unchanged)
   ↓
7. Browser event loop is overwhelmed
   ↓
8. WebSocket ping arrives but pong is delayed
   ↓
9. Backend doesn't receive pong within 75s
   ↓
10. Backend closes WebSocket as "stale"
    ↓
11. Network scan loses real-time updates
    ↓
12. Scan appears stuck at "28/254 hosts"
```

---

## Why Settings Don't Work

### The Lifecycle Problem

```javascript
// Component mounts
onMounted(() => {
  // Reads settings ONCE
  const refreshTime = settingsStore.settings.refresh_interval * 1000;
  
  // Creates interval with that value
  refreshInterval = setInterval(() => {
    fetchMiners();
  }, refreshTime);  // ← This value NEVER changes
});

// User changes settings
// Settings save successfully
// BUT the interval keeps running with the old value!

// Component unmounts
onUnmounted(() => {
  clearInterval(refreshInterval);  // Only cleared on unmount
});
```

### What Should Happen

```javascript
// Watch for settings changes
watch(() => settingsStore.settings.refresh_interval, (newInterval) => {
  // Clear old interval
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  
  // Create new interval with updated value
  const refreshTime = newInterval * 1000;
  refreshInterval = setInterval(() => {
    fetchMiners();
  }, refreshTime);
});
```

---

## Why WebSocket Closes During Scans

### The Timing

```
00:00 - Scan starts, WebSocket connected
00:05 - 3 HTTP requests to /api/miners
00:10 - 3 more HTTP requests
00:15 - 3 more HTTP requests
00:20 - 3 more HTTP requests
00:25 - 3 more HTTP requests
00:30 - Backend sends ping
00:30 - Frontend receives ping (delayed by 2-3 seconds due to busy event loop)
00:33 - Frontend sends pong (3 seconds late)
00:35 - 3 more HTTP requests
...
01:15 - Backend hasn't received pong within 75 seconds
01:15 - Backend closes WebSocket as "stale"
01:15 - Scan loses real-time updates
```

---

## Recommended Fixes (Priority Order)

### Priority 1: Fix Settings Not Being Applied
**Impact:** HIGH - This is why user settings are ignored
**Effort:** MEDIUM

**Solution:**
Add watchers to all components that create intervals:
- Dashboard.vue
- Miners.vue  
- MinerDetail.vue
- Network.vue

### Priority 2: Eliminate Redundant Polling
**Impact:** HIGH - Reduces load by 75%
**Effort:** LOW

**Solution:**
Remove polling from all components. Let WebSocket handle updates.
Only poll on initial load or manual refresh.

### Priority 3: Remove Console Logging
**Impact:** MEDIUM - Improves performance
**Effort:** LOW

**Solution:**
Remove or comment out the "No auth required" log statement.
Use proper logging levels (debug/info/error).

### Priority 4: Reduce Backend Broadcast Frequency
**Impact:** MEDIUM - Reduces WebSocket traffic
**Effort:** LOW

**Solution:**
Change miners broadcast from 1s to 5s or 10s.
Only broadcast when data actually changes.

### Priority 5: Increase Heartbeat Timeout
**Impact:** LOW - Temporary workaround
**Effort:** LOW

**Solution:**
Increase backend heartbeat timeout from 75s to 180s.
This gives browser more time to respond during heavy load.

---

## Testing Plan

1. **Verify settings are applied:**
   - Set refresh_interval to 120 seconds
   - Monitor network tab - should see requests every 120s
   - Check console - should see interval updated

2. **Verify single polling source:**
   - Open Dashboard
   - Monitor network tab
   - Should see only 1 request per interval, not 3+

3. **Verify WebSocket stability:**
   - Start a network scan
   - Monitor WebSocket connection
   - Should stay connected for entire scan duration

4. **Verify scan completion:**
   - Start scan of 192.168.1.0/28 (16 hosts)
   - Watch progress update in real-time
   - Verify scan completes and shows final results

---

## Current State vs. Desired State

### Current State ❌
- Settings saved but not applied
- 3+ components polling simultaneously
- Console spam every few seconds
- WebSocket closes after ~60 seconds
- Scans appear stuck
- Page flickers/blinks

### Desired State ✅
- Settings applied immediately
- Single source of truth (WebSocket)
- Minimal console logging
- WebSocket stays connected
- Scans complete successfully
- Smooth UI performance

---

## Next Steps

1. Review this diagnostic with the team
2. Prioritize which fixes to implement first
3. Create a fix plan with estimated effort
4. Test each fix independently
5. Verify the cascade effect is resolved

---

**End of Diagnostic Report**
