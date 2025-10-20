# Design Document

## Overview

This design addresses critical issues with polling interval settings and WebSocket stability in the MinervaOS application. The solution implements reactive settings watchers, coordinated polling management, and optimized WebSocket communication to ensure user-configured intervals are respected and network scans complete successfully.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Application                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │  Dashboard   │      │   Miners     │                    │
│  │  Component   │      │  Component   │                    │
│  └──────┬───────┘      └──────┬───────┘                    │
│         │                     │                              │
│         └─────────┬───────────┘                              │
│                   │                                          │
│         ┌─────────▼──────────┐                              │
│         │  Polling Manager   │◄──── Settings Watcher        │
│         │   (Composable)     │                              │
│         └─────────┬──────────┘                              │
│                   │                                          │
│         ┌─────────▼──────────┐                              │
│         │  Settings Store    │                              │
│         └─────────┬──────────┘                              │
│                   │                                          │
│         ┌─────────▼──────────┐                              │
│         │ WebSocket Service  │                              │
│         └─────────┬──────────┘                              │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    │ WebSocket Connection
                    │
┌───────────────────▼──────────────────────────────────────────┐
│                     Backend Server                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│         ┌──────────────────────┐                            │
│         │  WebSocket Manager   │                            │
│         └─────────┬────────────┘                            │
│                   │                                          │
│         ┌─────────▼──────────┐                              │
│         │  Broadcast Manager │                              │
│         │  (Change Detection)│                              │
│         └────────────────────┘                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Polling Manager Composable (New)

**Purpose:** Centralized polling management with reactive settings support

**Location:** `src/frontend/src/composables/usePollingManager.js`

**Interface:**
```javascript
export function usePollingManager(options) {
  // Options
  const {
    fetchFunction,      // Function to call for polling
    intervalKey,        // Settings key (e.g., 'refresh_interval')
    componentName,      // For logging/debugging
    enabled = true,     // Whether polling is enabled
    minInterval = 5000  // Minimum interval (safety)
  } = options;

  // State
  const isPolling = ref(false);
  const lastPollTime = ref(null);
  const pollCount = ref(0);

  // Methods
  const startPolling = () => { /* ... */ };
  const stopPolling = () => { /* ... */ };
  const pollNow = () => { /* ... */ };

  // Auto-cleanup on unmount
  onUnmounted(() => stopPolling());

  return {
    isPolling,
    lastPollTime,
    pollCount,
    startPolling,
    stopPolling,
    pollNow
  };
}
```

**Key Features:**
- Watches settings store for interval changes
- Automatically recreates intervals when settings change
- Prevents duplicate polling across components
- Provides polling statistics for debugging
- Auto-cleanup on component unmount

### 2. Settings Store Enhancements

**Location:** `src/frontend/src/stores/settings.js`

**Changes:**
- Add reactive event emitter for settings changes
- Emit events when `refresh_interval` or `ui_refresh_interval` change
- Provide method to get current interval values

**New Methods:**
```javascript
// Emit settings change event
const emitSettingsChange = (key, oldValue, newValue) => {
  window.dispatchEvent(new CustomEvent('settings-changed', {
    detail: { key, oldValue, newValue }
  }));
};

// Get current interval with fallback
const getCurrentInterval = (key, defaultValue) => {
  return settings.value[key] || defaultValue;
};
```

### 3. Component Polling Updates

**Affected Components:**
- `src/frontend/src/views/Dashboard.vue`
- `src/frontend/src/views/Miners.vue`
- `src/frontend/src/views/MinerDetail.vue`
- `src/frontend/src/views/Network.vue`

**Changes:**
Replace manual `setInterval` with `usePollingManager`:

**Before:**
```javascript
onMounted(() => {
  const refreshTime = settingsStore.settings.refresh_interval * 1000 || 10000;
  refreshInterval = setInterval(async () => {
    await minersStore.fetchMiners();
  }, refreshTime);
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
```

**After:**
```javascript
const { startPolling, stopPolling } = usePollingManager({
  fetchFunction: () => minersStore.fetchMiners(),
  intervalKey: 'refresh_interval',
  componentName: 'Dashboard',
  enabled: true
});

onMounted(() => {
  startPolling();
});
```

### 4. WebSocket Service Enhancements

**Location:** `src/frontend/src/services/websocket.js`

**Changes:**
- Prioritize heartbeat responses over other operations
- Add connection health monitoring
- Reduce polling frequency when WebSocket is active

**New Features:**
```javascript
// Priority queue for WebSocket messages
const messagePriorityQueue = {
  high: [],    // Heartbeat responses
  normal: [],  // Regular messages
  low: []      // Broadcast updates
};

// Process high-priority messages first
const processMessageQueue = () => {
  if (messagePriorityQueue.high.length > 0) {
    const message = messagePriorityQueue.high.shift();
    sendMessage(message);
  } else if (messagePriorityQueue.normal.length > 0) {
    const message = messagePriorityQueue.normal.shift();
    sendMessage(message);
  } else if (messagePriorityQueue.low.length > 0) {
    const message = messagePriorityQueue.low.shift();
    sendMessage(message);
  }
};

// Handle ping with high priority
function handleMessage(event) {
  const message = JSON.parse(event.data);
  
  if (message.type === "ping") {
    // Respond immediately with high priority
    messagePriorityQueue.high.push({
      type: "pong",
      timestamp: new Date().toISOString()
    });
    processMessageQueue();
  }
  // ... other message handling
}
```

### 5. Backend Broadcast Optimization

**Location:** `src/backend/services/websocket_manager.py`

**Changes:**
- Implement change detection before broadcasting
- Increase broadcast intervals
- Skip broadcasts when no data changes

**Implementation:**
```python
class WebSocketManager:
    def __init__(self):
        # ... existing code ...
        
        # Cache last broadcast data for change detection
        self._last_broadcast_data = {}
        
        # Updated broadcast intervals
        self._broadcast_intervals = {
            "miners": 5.0,      # Changed from 1.0
            "alerts": 10.0,     # Changed from 5.0
            "system": 30.0,     # Changed from 10.0
            "discovery": 0.5,   # Keep frequent for scans
        }
    
    async def broadcast(self, topic: str, message: Dict[str, Any]):
        """Broadcast with change detection"""
        
        # Check if data has changed
        data_hash = self._hash_data(message.get("data"))
        last_hash = self._last_broadcast_data.get(topic)
        
        if last_hash == data_hash:
            logger.debug(f"Skipping broadcast for {topic} - no changes")
            return
        
        # Update cache
        self._last_broadcast_data[topic] = data_hash
        
        # Proceed with broadcast
        # ... existing broadcast code ...
    
    def _hash_data(self, data: Any) -> str:
        """Generate hash of data for change detection"""
        import hashlib
        import json
        
        try:
            data_str = json.dumps(data, sort_keys=True)
            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception:
            return str(hash(str(data)))
```

### 6. Console Logging Cleanup

**Location:** `src/frontend/src/services/settingsService.js`

**Changes:**
- Remove verbose "No auth required" logging
- Add debug mode flag
- Use proper log levels

**Implementation:**
```javascript
// Add debug mode flag
const DEBUG_MODE = import.meta.env.DEV || localStorage.getItem('debug') === 'true';

// Update axios interceptor
axiosInstance.interceptors.request.use((config) => {
  // Only log in debug mode
  if (DEBUG_MODE && config.url !== '/api/miners') {
    console.log(`API Request: ${config.method} ${config.url}`);
  }
  
  return config;
});

// Log errors always
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error(`API Error: ${error.config?.method} ${error.config?.url}`, {
      status: error.response?.status,
      message: error.message
    });
    return Promise.reject(error);
  }
);
```

## Data Models

### Polling State Model

```javascript
{
  componentName: string,      // Component identifier
  intervalKey: string,        // Settings key being used
  currentInterval: number,    // Current interval in ms
  isActive: boolean,          // Whether polling is active
  lastPollTime: Date,         // Last poll timestamp
  pollCount: number,          // Total polls executed
  nextPollTime: Date          // Scheduled next poll
}
```

### WebSocket Connection State Model

```javascript
{
  status: 'connected' | 'disconnected' | 'reconnecting',
  lastPing: Date,             // Last ping sent
  lastPong: Date,             // Last pong received
  latency: number,            // Round-trip time in ms
  messageQueue: {
    high: Array,              // Priority messages
    normal: Array,            // Regular messages
    low: Array                // Low priority messages
  },
  subscriptions: Array<string> // Active topic subscriptions
}
```

## Error Handling

### Polling Errors

1. **Fetch Failure:**
   - Log error with component name and timestamp
   - Continue polling (don't stop on single failure)
   - Show user notification after 3 consecutive failures

2. **Settings Load Failure:**
   - Use cached localStorage settings
   - Fall back to default intervals
   - Retry settings fetch in background

3. **Interval Too Low:**
   - Enforce minimum interval (5 seconds)
   - Log warning
   - Use minimum instead of requested value

### WebSocket Errors

1. **Connection Loss:**
   - Attempt reconnection with exponential backoff
   - Show reconnection indicator to user
   - Queue messages during disconnection

2. **Heartbeat Timeout:**
   - Increase timeout to 180 seconds (from 75)
   - Log warning before disconnecting
   - Attempt immediate reconnection

3. **Message Send Failure:**
   - Retry high-priority messages (heartbeat)
   - Drop low-priority messages after 3 attempts
   - Clean up failed connections

## Testing Strategy

### Unit Tests

1. **Polling Manager Tests:**
   - Test interval creation and cleanup
   - Test settings change reactivity
   - Test minimum interval enforcement
   - Test component unmount cleanup

2. **Settings Store Tests:**
   - Test settings update propagation
   - Test localStorage persistence
   - Test event emission

3. **WebSocket Service Tests:**
   - Test message priority queue
   - Test heartbeat response timing
   - Test reconnection logic

### Integration Tests

1. **Settings Application Test:**
   - Change refresh_interval to 120 seconds
   - Verify polling occurs every 120 seconds
   - Verify across multiple components

2. **WebSocket Stability Test:**
   - Start network scan
   - Monitor WebSocket connection
   - Verify connection stays active for 5+ minutes
   - Verify scan completes successfully

3. **Broadcast Optimization Test:**
   - Monitor backend broadcasts
   - Verify no broadcasts when data unchanged
   - Verify broadcasts only on data changes

### Manual Testing

1. **Settings UI Test:**
   - Open Settings page
   - Change refresh_interval to 120 seconds
   - Open browser DevTools Network tab
   - Verify requests occur every 120 seconds
   - Navigate between pages
   - Verify interval persists

2. **Network Scan Test:**
   - Start scan of 192.168.1.0/28 (16 hosts)
   - Monitor WebSocket in DevTools
   - Verify connection stays open
   - Verify progress updates in real-time
   - Verify scan completes and shows results

3. **Console Logging Test:**
   - Open browser console
   - Navigate through application
   - Verify minimal logging (no spam)
   - Trigger an error
   - Verify error is logged with details

## Performance Considerations

### Frontend Optimizations

1. **Reduced HTTP Requests:**
   - Before: 3+ requests every 10 seconds = 18 requests/minute
   - After: 1 request every 120 seconds = 0.5 requests/minute
   - **Reduction: 97%**

2. **Reduced Console Logging:**
   - Before: 18 log statements/minute
   - After: 0 log statements/minute (in production)
   - **Improvement: Main thread freed up**

3. **WebSocket Priority Queue:**
   - Heartbeat responses sent within 100ms
   - Prevents timeout disconnections
   - Maintains stable connections during scans

### Backend Optimizations

1. **Reduced Broadcasts:**
   - Before: 60 broadcasts/minute (1 per second)
   - After: ~5 broadcasts/minute (only on changes)
   - **Reduction: 92%**

2. **Change Detection:**
   - Hash-based comparison
   - O(1) lookup time
   - Minimal CPU overhead

3. **Increased Heartbeat Timeout:**
   - Before: 75 seconds
   - After: 180 seconds
   - **Improvement: More tolerance for busy event loops**

## Migration Strategy

### Phase 1: Frontend Polling (Priority 1)

1. Create `usePollingManager` composable
2. Update Dashboard.vue to use new composable
3. Test settings reactivity
4. Update remaining components (Miners, MinerDetail, Network)
5. Remove old polling code

### Phase 2: Console Logging (Priority 2)

1. Add debug mode flag
2. Update settingsService.js interceptors
3. Test in development and production modes
4. Remove verbose logging

### Phase 3: Backend Optimization (Priority 3)

1. Implement change detection in WebSocketManager
2. Update broadcast intervals
3. Test with multiple clients
4. Monitor performance improvements

### Phase 4: WebSocket Enhancements (Priority 4)

1. Implement message priority queue
2. Update heartbeat timeout
3. Test during network scans
4. Verify stability improvements

### Phase 5: Testing & Validation (Priority 5)

1. Run all unit tests
2. Run integration tests
3. Perform manual testing
4. Document results
5. Create diagnostic page for monitoring

## Rollback Plan

If issues are discovered:

1. **Polling Issues:**
   - Revert to manual `setInterval` in components
   - Keep settings watcher for future fix

2. **WebSocket Issues:**
   - Revert heartbeat timeout to 75 seconds
   - Disable message priority queue
   - Keep change detection (safe optimization)

3. **Broadcast Issues:**
   - Revert broadcast intervals to original values
   - Disable change detection
   - Monitor for improvements

## Success Metrics

1. **Settings Application:**
   - ✅ Settings change reflected within 1 second
   - ✅ Polling interval matches configured value ±2 seconds
   - ✅ Settings persist across page refreshes

2. **WebSocket Stability:**
   - ✅ Connection stays active for 300+ seconds during scans
   - ✅ Heartbeat responses within 5 seconds
   - ✅ Zero unexpected disconnections

3. **Performance:**
   - ✅ HTTP requests reduced by 90%+
   - ✅ Backend broadcasts reduced by 90%+
   - ✅ Console logging reduced by 100% (production)

4. **User Experience:**
   - ✅ Network scans complete successfully
   - ✅ Real-time updates work smoothly
   - ✅ No page flickering or freezing
   - ✅ Settings changes take effect immediately

## Monitoring and Diagnostics

### Diagnostic Page (New)

**Location:** `src/frontend/src/views/Diagnostics.vue`

**Features:**
- Display current polling intervals for all components
- Show WebSocket connection status and latency
- Display last 10 API requests with timestamps
- Show settings values and last update time
- Export diagnostic data as JSON

**Access:** Available in development mode or via URL parameter `?diagnostics=true`

## Dependencies

### Frontend
- Vue 3 (existing)
- Pinia (existing)
- Axios (existing)

### Backend
- FastAPI (existing)
- Python asyncio (existing)
- hashlib (standard library)

### No New Dependencies Required

## Security Considerations

1. **Settings Validation:**
   - Enforce minimum interval (5 seconds)
   - Enforce maximum interval (3600 seconds)
   - Validate interval is a positive number

2. **WebSocket Security:**
   - Maintain existing authentication (none required for local network)
   - Rate limit message sending
   - Validate message structure

3. **Diagnostic Page:**
   - Only accessible in development mode
   - No sensitive data exposed
   - Can be disabled via environment variable

## Future Enhancements

1. **Adaptive Polling:**
   - Reduce polling when WebSocket is active and healthy
   - Increase polling when WebSocket is disconnected
   - Smart interval adjustment based on data change frequency

2. **Polling Coordination:**
   - Single shared polling service across all components
   - Deduplicate requests from multiple components
   - Batch multiple API calls into single request

3. **Advanced Change Detection:**
   - Field-level change detection
   - Partial updates instead of full broadcasts
   - Compression for large payloads

4. **Enhanced Diagnostics:**
   - Real-time performance graphs
   - Historical polling statistics
   - WebSocket message inspector
   - Network scan timeline visualization
