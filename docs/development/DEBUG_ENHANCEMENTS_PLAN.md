# Debugging Enhancements Implementation Plan

## Overview

This document outlines the specific debugging code to add to diagnose the cached data and navigation issues.

## Files to Modify

### 1. src/frontend/src/stores/miners.js

**Purpose**: Track data flow through the Pinia store

**Enhancements**:

- Add detailed logging to `fetchMiner()`
- Add detailed logging to `fetchMiners()`
- Add detailed logging to `refreshMiners()`
- Add detailed logging to `fetchMinerMetrics()`
- Track all store mutations with timestamps
- Log before/after state for all updates

### 2. src/frontend/src/views/MinerDetail.vue

**Purpose**: Track component lifecycle and reactivity

**Enhancements**:

- Add logging to `onMounted()` lifecycle hook
- Add logging to `onUnmounted()` lifecycle hook
- Add deep watcher on `miner` computed property
- Add logging to `fetchPreviewMetrics()`
- Track all user interactions (button clicks, tab changes)
- Log component state before navigation

### 3. src/frontend/src/composables/usePollingManager.js

**Purpose**: Verify polling is executing correctly

**Enhancements**:

- Add detailed logging to `pollNow()`
- Add logging to `startPolling()`
- Add logging to `stopPolling()`
- Track timing between polls
- Log interval changes
- Verify fetch function execution

### 4. src/frontend/src/App.vue

**Purpose**: Track navigation and global state

**Enhancements**:

- Add logging to `navigateToPage()`
- Add router navigation guards with logging
- Track route changes
- Log drawer state changes
- Monitor WebSocket connection status changes

### 5. src/backend/api/api_service.py

**Purpose**: Verify backend is returning fresh data

**Enhancements**:

- Add detailed logging to `get_miner()`
- Add detailed logging to `get_miners()`
- Add detailed logging to `refresh_miners()`
- Add detailed logging to `get_miner_metrics()`
- Log data timestamps
- Track API response times

### 6. src/backend/services/miner_manager.py

**Purpose**: Verify miners are being polled

**Enhancements**:

- Add logging to miner polling loop
- Track when each miner is polled
- Log data freshness
- Monitor WebSocket broadcasts

## Implementation Strategy

### Phase 1: Frontend Store Debugging (Priority 1)

Focus on understanding data flow from API to store to component.

**Files**: miners.js

**Key Questions**:

- Is the API returning fresh data?
- Is the store updating with new data?
- Are mutations triggering reactivity?

### Phase 2: Component Lifecycle Debugging (Priority 1)

Focus on understanding component updates and reactivity.

**Files**: MinerDetail.vue

**Key Questions**:

- Is the component receiving updated data?
- Are computed properties recalculating?
- Is the DOM re-rendering?

### Phase 3: Polling Verification (Priority 2)

Focus on verifying polling is working correctly.

**Files**: usePollingManager.js

**Key Questions**:

- Is polling actually running?
- Are intervals correct?
- Is there duplicate polling?

### Phase 4: Navigation Debugging (Priority 2)

Focus on understanding navigation failures.

**Files**: App.vue, MinerDetail.vue

**Key Questions**:

- What happens during navigation?
- Are components unmounting properly?
- Are there memory leaks?

### Phase 5: Backend Verification (Priority 3)

Focus on verifying backend data freshness.

**Files**: api_service.py, miner_manager.py

**Key Questions**:

- Is backend polling miners?
- Is data being cached?
- Are timestamps correct?

## Debugging Output Format

All debugging logs should follow this format for consistency:

```javascript
console.log("=== [CATEGORY] [ACTION] ===", {
  timestamp: new Date().toISOString(),
  component: "ComponentName",
  // ... relevant data
});
```

Categories:

- `STORE` - Pinia store operations
- `COMPONENT` - Component lifecycle
- `POLLING` - Polling operations
- `NAVIGATION` - Router navigation
- `API` - API calls
- `REACTIVITY` - Vue reactivity system

## Testing Procedure

1. **Enable all debugging**
2. **Clear browser cache and localStorage**
3. **Start fresh app instance**
4. **Reproduce issue step by step**:
   - Load dashboard
   - Note data displayed
   - Click on miner
   - Note data displayed
   - Wait for polling cycle
   - Note if data updates
   - Click refresh
   - Note errors
   - Try to navigate
   - Note navigation failure
5. **Collect all console logs**
6. **Analyze log timeline**
7. **Identify failure points**

## Log Analysis Checklist

For each issue, verify:

### Cached Data Issue

- [ ] API response contains fresh timestamp
- [ ] API response data is different from previous
- [ ] Store mutation is called with new data
- [ ] Store state is updated
- [ ] Computed property recalculates
- [ ] Component receives new data
- [ ] DOM updates with new data

### Navigation Issue

- [ ] Navigation is triggered
- [ ] Router processes navigation
- [ ] Old component unmounts cleanly
- [ ] New component mounts
- [ ] Route updates in URL
- [ ] View updates in DOM

### Polling Issue

- [ ] Polling starts on mount
- [ ] Polling interval is correct
- [ ] Poll executes at intervals
- [ ] Fetch function is called
- [ ] Data is returned
- [ ] Store is updated

## Expected Outcomes

After implementing these debugging enhancements, we should be able to:

1. **Pinpoint exact failure location** - Know exactly where in the data flow things break
2. **Understand timing issues** - See if there are race conditions or timing problems
3. **Identify reactivity problems** - Know if Vue reactivity is working correctly
4. **Diagnose navigation issues** - Understand why navigation fails
5. **Verify backend behavior** - Confirm backend is working as expected

## Important Notes

- **Do NOT remove existing logs** - Add new logs alongside existing ones
- **Use consistent formatting** - Follow the format specified above
- **Include timestamps** - Every log should have a timestamp
- **Log before and after** - Log state before and after operations
- **Be specific** - Include relevant IDs, values, and context
- **Avoid assumptions** - Only log facts, not interpretations

## Cleanup Plan

Once issues are identified and fixed:

1. Keep critical error logging
2. Remove verbose debugging logs
3. Convert some logs to debug level
4. Add comments explaining the fix
5. Document the root cause
