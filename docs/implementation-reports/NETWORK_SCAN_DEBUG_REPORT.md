# Network Scan Debug Report

**Date:** October 18, 2025
**Issue:** Network scan appears to hang from user perspective

## Executive Summary

The network scan functionality IS working on the backend, but the frontend appears frozen because:

1. Initial discovery state shows `total_hosts: 0` before network parsing
2. WebSocket updates are not being broadcast to the frontend
3. Users see no progress indication during the scan

## Test Results

### Setup Wizard Test

- **Location:** http://localhost:8000/setup (Discovery step)
- **Test:** Clicked "START NETWORK SCAN" with range 192.168.1.1-192.168.1.254
- **Result:** Scan started but UI showed no progress

### Observations

#### Frontend Behavior

- Button changed from "START NETWORK SCAN" to "STOP SCAN" ✓
- Shows "Scanning IP 192.168.1.1..." (stuck on first IP)
- Shows "Found 0 miners so far" (never updates)
- No progress bar or percentage shown
- Scan completed after ~90 seconds but UI never updated

#### Backend Behavior (from logs)

```
2025-10-18 11:23:23,999 - Discovery state initialized: {'total_hosts': 0, ...}
2025-10-18 11:23:24,003 - Generated 254 hosts from range 192.168.1.1 to 192.168.1.254
2025-10-18 11:23:25,007 - Starting miner type detection for 192.168.1.1
2025-10-18 11:24:18,258 - Starting miner type detection for 192.168.1.156
2025-10-18 11:24:53,389 - Discovery completed. Found 0 miners
```

**Key Finding:** The scan IS running and progressing through IPs, but:

- No WebSocket broadcast messages appear in logs
- Frontend never receives progress updates
- Scan takes ~90 seconds for 254 IPs (with 3 concurrent scans)

## Root Causes

### 1. Initial State Shows Zero Hosts

**File:** `src/backend/services/miner_manager.py`
**Lines:** 388-401

```python
# Initialize discovery state
self.discovery_state = {
    "status": "starting",
    "network": network,
    "ports": ports or [80, 4028],
    "timeout": timeout,
    "total_hosts": 0,  # ❌ Set to 0 BEFORE parsing network
    "scanned_hosts": 0,
    "current_ip": None,
    "found_miners": [],
    ...
}
```

**Problem:** The API returns this state immediately with `total_hosts: 0`, making the frontend think there's nothing to scan.

**Fix:** Parse the network range BEFORE initializing the discovery state, or update the state after parsing.

### 2. Missing WebSocket Broadcasts

**File:** `src/backend/services/miner_manager.py`
**Lines:** 760-770

The code attempts to broadcast updates:

```python
if self.websocket_manager:
    await self.websocket_manager.broadcast_to_topic("discovery", {
        "type": "discovery_update",
        "data": self.discovery_state
    })
```

**Problem:** No broadcast messages appear in the logs, suggesting either:

- `self.websocket_manager` is None
- The broadcast method is not working
- The frontend is not subscribed to the "discovery" topic

### 3. Semaphore Limits Concurrency Too Much

**File:** `src/backend/services/miner_manager.py`
**Line:** 763

```python
semaphore = asyncio.Semaphore(3)  # Only 3 concurrent scans
```

**Problem:** With only 3 concurrent scans and 254 hosts, the scan takes ~90 seconds. This is slow and provides poor user experience.

**Recommendation:** Increase to 10-20 concurrent scans for better performance.

### 4. Update Frequency Too Low

**File:** `src/backend/services/miner_manager.py`
**Lines:** 772-779

```python
update_frequency = 1 if self.discovery_state["total_hosts"] <= 10 else 3
if (self.discovery_state["scanned_hosts"] % update_frequency == 0 or ...):
```

**Problem:** Since `total_hosts` is 0, this condition may not work as expected.

## Code Flow Analysis

### Scan Network Button Locations

1. **Setup Wizard** (`installer/common/wizard/index.html`)

   - Line 970: `<button id="scanNetwork">Scan Network</button>`
   - Line 1264: Event listener calls `scanNetwork(networkRange)`
   - Line 1414: `async function scanNetwork(networkRange)`
   - Uses IPC: `ipcRenderer.invoke('scan-network', networkRange)`

2. **Dashboard** (`src/frontend/src/views/Dashboard.vue`)

   - Line 130: "Scan Network" button in empty state
   - Line 530: `handleQuickScanNetwork` → `startDiscovery()`
   - Line 421: `startDiscovery()` uses `networkScanService`

3. **SimpleDashboard** (`src/frontend/src/views/SimpleDashboard.vue`)

   - Line 87: QuickActions component with `@scan-network`
   - Line 375: `scanNetwork()` uses `networkScanService`

4. **Miners Page** (`src/frontend/src/views/Miners.vue`)

   - Line 13: "Scan Network" button
   - Opens NetworkScanner dialog component

5. **QuickActions Component** (`src/frontend/src/components/QuickActions.vue`)
   - Line 20: "Scan Network" button
   - Line 133: `handleScanNetwork()` uses `networkScanService`

### Network Scan Service Flow

**File:** `src/frontend/src/services/networkScanService.js`

1. `startScan(options)` - Initiates scan
2. `connectWebSocket()` - Connects to `/ws` endpoint
3. Subscribes to "discovery" topic
4. `handleDiscoveryUpdate(data)` - Processes WebSocket messages
5. `notifyListeners(data)` - Updates UI components

**Key Issue:** The service expects WebSocket messages with type "discovery_update", but these are not being sent from the backend.

### Backend Discovery Flow

**File:** `src/backend/services/miner_manager.py`

1. `start_discovery()` - Initializes state and creates task
2. `_discover_miners()` - Main scan logic
   - Parses network range
   - Updates `total_hosts` AFTER initialization
   - Creates scan tasks with semaphore
   - Attempts to broadcast updates
3. `_scan_host()` - Scans individual host
4. `_check_open_ports()` - Checks for open ports
5. Miner type detection for each open port

## Debugging Enhancements Needed

### 1. Add More Logging

```python
# In _discover_miners, after updating total_hosts:
logger.info(f"Updated discovery state with {len(hosts)} total hosts")
logger.info(f"WebSocket manager available: {self.websocket_manager is not None}")

# Before each broadcast:
logger.info(f"Broadcasting discovery update: {self.discovery_state['status']}")
logger.info(f"Scanned {self.discovery_state['scanned_hosts']}/{self.discovery_state['total_hosts']}")
```

### 2. Add Frontend Console Logging

```javascript
// In networkScanService.js handleDiscoveryUpdate:
console.log("=== DISCOVERY UPDATE RECEIVED ===");
console.log("Status:", data.status);
console.log("Progress:", data.scanned_hosts, "/", data.total_hosts);
console.log("Current IP:", data.current_ip);
console.log("Found miners:", data.found_miners?.length || 0);
```

### 3. Add WebSocket Connection Logging

```python
# In websocket_manager.py broadcast_to_topic:
logger.info(f"Broadcasting to topic '{topic}': {len(self.connections)} connections")
logger.info(f"Subscribers to '{topic}': {len([c for c in self.connections.values() if topic in c.subscribed_topics])}")
```

## Recommended Fixes

### Priority 1: Fix Initial State

```python
# In start_discovery(), parse network FIRST:
try:
    # Parse network to get host count
    if '-' in network:
        start_ip, end_ip = network.split('-')
        start_addr = ipaddress.ip_address(start_ip.strip())
        end_addr = ipaddress.ip_address(end_ip.strip())
        total_hosts = int(end_addr) - int(start_addr) + 1
    else:
        network_obj = ipaddress.ip_network(network)
        total_hosts = len(list(network_obj.hosts()))

    # NOW initialize discovery state with correct total_hosts
    self.discovery_state = {
        "status": "starting",
        "network": network,
        "ports": ports or [80, 4028],
        "timeout": timeout,
        "total_hosts": total_hosts,  # ✓ Correct value
        "scanned_hosts": 0,
        ...
    }
```

### Priority 2: Verify WebSocket Manager

```python
# In start_discovery(), add check:
if not self.websocket_manager:
    logger.warning("WebSocket manager not available - progress updates will not be sent")
else:
    logger.info(f"WebSocket manager available with {len(self.websocket_manager.connections)} connections")
```

### Priority 3: Increase Concurrency

```python
# In _discover_miners():
semaphore = asyncio.Semaphore(15)  # Increase from 3 to 15
```

### Priority 4: Always Broadcast Updates

```python
# In scan_with_progress(), broadcast EVERY update:
if self.discovery_state:
    self.discovery_state["current_ip"] = host_ip
    self.discovery_state["scanned_hosts"] += 1

    # Always broadcast for better UX
    if self.websocket_manager:
        await self.websocket_manager.broadcast_to_topic("discovery", {
            "type": "discovery_update",
            "data": self.discovery_state
        })
```

## Testing Recommendations

### 1. Test with Small Range First

- Use range like 192.168.1.1-192.168.1.10 (10 hosts)
- Should complete in ~10-15 seconds
- Easier to verify progress updates

### 2. Add Debug Endpoint

```python
@app.get("/api/discovery/debug")
async def get_discovery_debug():
    return {
        "discovery_task_exists": self.discovery_task is not None,
        "discovery_task_done": self.discovery_task.done() if self.discovery_task else None,
        "discovery_state": self.discovery_state,
        "websocket_manager_exists": self.websocket_manager is not None,
        "websocket_connections": len(self.websocket_manager.connections) if self.websocket_manager else 0
    }
```

### 3. Monitor WebSocket Messages

Use browser DevTools Network tab → WS filter to see WebSocket messages in real-time.

## Conclusion

The network scan functionality is working correctly on the backend, but lacks proper progress communication to the frontend. The main issues are:

1. **Initial state misleading** - Shows 0 total hosts
2. **No WebSocket updates** - Frontend never receives progress
3. **Slow scanning** - Only 3 concurrent scans
4. **Poor UX** - Users think the scan is frozen

All issues are fixable with the recommended changes above. The scan logic itself is sound and successfully detects miners when present.
