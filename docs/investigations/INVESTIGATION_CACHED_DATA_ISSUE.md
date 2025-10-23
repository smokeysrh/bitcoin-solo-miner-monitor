# Investigation: Cached Miner Data Issue

## Problem Summary
The app is displaying cached/outdated miner data instead of current data. When attempting to refresh or navigate, the app encounters errors and becomes unresponsive.

## Observed Symptoms

### 1. Dashboard & Miner Details Show Cached Data
- Dashboard displays outdated miner information
- Clicking on miner details shows the same cached data
- Data doesn't update even though polling is active

### 2. Page Refresh Causes Errors
When attempting to refresh the miner details page, multiple errors occur:

**Error 1: Vue Component Update Error**
```
[Vue warn]: Unhandled error during execution of component update
TypeError: Cannot read properties of null (reading 'shapeFlag')
TypeError: Cannot read properties of null (reading 'emitsOptions')
```

**Error 2: Metrics Fetch Issues**
```
miners.js:254 [Vue warn]: Unhandled error during execution of component update
[fetchPreviewMetrics] Metrics received: 0 data points
Canvas refs not ready, retry 1/5 ... retry 5/5
Failed to render charts after max retries
```

### 3. Navigation Failure
- Clicking sidebar menu items changes URL but page doesn't update
- App becomes stuck on the current view
- Console shows unmount errors:
```
TypeError: Cannot read properties of null (reading 'type')
at unmountComponent
```

## Key Error Locations

### Frontend Errors
1. **miners.js:254** - fetchMinerMetrics error
2. **miners.js:103** - fetchMiner error  
3. **MinerDetail.vue:919** - fetchPreviewMetrics
4. **MinerDetail.vue:1269** - onMounted lifecycle
5. **chunk-6NWVO5JW.js** - Vue internal rendering errors

### Backend Concerns
- Need to verify refresh_miners endpoint behavior
- Need to check if data is being cached at API level
- Need to verify WebSocket updates are working

## Investigation Plan

### Phase 1: Add Frontend Debugging
1. **Pinia Store (miners.js)**
   - Add detailed logging for all data mutations
   - Track when data is fetched vs when it's returned from cache
   - Log the complete data flow: API → Store → Component
   - Add timestamps to track data freshness

2. **MinerDetail.vue Component**
   - Add lifecycle logging (mount, unmount, updates)
   - Track computed property recalculations
   - Log when miner data changes
   - Add error boundaries around critical operations

3. **Polling Manager**
   - Log every poll attempt with timestamp
   - Track if polls are actually executing
   - Verify interval changes are applied
   - Check for duplicate polling

### Phase 2: Add Backend Debugging
1. **API Endpoints**
   - Log every request with full details
   - Track response data and timestamps
   - Verify data freshness from miners
   - Check for caching middleware

2. **Miner Manager**
   - Log when miners are polled
   - Track data updates
   - Verify WebSocket broadcasts

### Phase 3: Add Vue Reactivity Debugging
1. **Component Lifecycle**
   - Track when components mount/unmount
   - Log reactive dependency changes
   - Monitor computed property updates
   - Check for memory leaks

2. **Router Navigation**
   - Log navigation attempts
   - Track route changes
   - Monitor component transitions
   - Check for navigation guards blocking

## Specific Debugging Enhancements Needed

### 1. Enhanced Store Logging (miners.js)
```javascript
// Add to fetchMiner
console.log('=== FETCH MINER START ===', {
  minerId: id,
  timestamp: new Date().toISOString(),
  currentStoreData: miners.value.find(m => m.id === id),
  storeSize: miners.value.length
});

// After API call
console.log('=== FETCH MINER API RESPONSE ===', {
  minerId: id,
  responseData: response.data,
  timestamp: new Date().toISOString(),
  dataAge: response.data.last_updated
});

// After normalization
console.log('=== FETCH MINER NORMALIZED ===', {
  minerId: id,
  normalizedData: normalizedMiner,
  beforeUpdate: miners.value.find(m => m.id === id),
  timestamp: new Date().toISOString()
});

// After store update
console.log('=== FETCH MINER STORE UPDATED ===', {
  minerId: id,
  afterUpdate: miners.value.find(m => m.id === id),
  timestamp: new Date().toISOString()
});
```

### 2. Enhanced Component Logging (MinerDetail.vue)
```javascript
// Add to computed miner
const miner = computed(() => {
  const minerGetter = minersStore.getMinerById;
  const result = minerGetter ? minerGetter(props.id) : null;
  console.log('=== MINER COMPUTED RECALCULATED ===', {
    minerId: props.id,
    result: result,
    timestamp: new Date().toISOString(),
    hasData: !!result,
    dataAge: result?.last_updated
  });
  return result;
});

// Add to onMounted
console.log('=== MINER DETAIL MOUNTED ===', {
  minerId: props.id,
  timestamp: new Date().toISOString(),
  storeHasMiner: !!minersStore.getMinerById(props.id),
  storeSize: minersStore.miners.length
});

// Add to onUnmounted
console.log('=== MINER DETAIL UNMOUNTING ===', {
  minerId: props.id,
  timestamp: new Date().toISOString(),
  pollingActive: isPolling.value
});
```

### 3. Enhanced Polling Logging (usePollingManager.js)
```javascript
// Add to pollNow
console.log('=== POLL EXECUTING ===', {
  component: componentName,
  timestamp: new Date().toISOString(),
  pollCount: pollCount.value,
  interval: currentInterval.value,
  enabled: enabled
});

// After fetch
console.log('=== POLL COMPLETED ===', {
  component: componentName,
  timestamp: new Date().toISOString(),
  success: true,
  duration: Date.now() - startTime
});
```

### 4. Enhanced API Logging (api_service.py)
```python
# Add to refresh_miners
logger.info(f"=== REFRESH MINERS START ===")
logger.info(f"Timestamp: {datetime.now().isoformat()}")
logger.info(f"Current miners count: {len(miners)}")

# After fetching each miner
logger.info(f"=== MINER REFRESHED ===")
logger.info(f"Miner ID: {miner_id}")
logger.info(f"Status: {status}")
logger.info(f"Metrics: {metrics}")
logger.info(f"Data age: {update_data.get('last_updated')}")

# After all refreshes
logger.info(f"=== REFRESH MINERS COMPLETE ===")
logger.info(f"Refreshed: {len(refreshed_miners)}")
logger.info(f"Errors: {len(errors)}")
logger.info(f"Timestamp: {datetime.now().isoformat()}")
```

### 5. Vue Reactivity Debugging
```javascript
// Add to watch miner in MinerDetail.vue
watch(
  () => miner.value,
  (newMiner, oldMiner) => {
    console.log('=== MINER WATCH TRIGGERED ===', {
      timestamp: new Date().toISOString(),
      oldData: oldMiner,
      newData: newMiner,
      changed: JSON.stringify(oldMiner) !== JSON.stringify(newMiner),
      keys: {
        old: oldMiner ? Object.keys(oldMiner) : [],
        new: newMiner ? Object.keys(newMiner) : []
      }
    });
  },
  { deep: true, immediate: true }
);
```

## Questions to Answer Through Debugging

1. **Is the API actually returning fresh data?**
   - Check timestamps in API responses
   - Verify data is different on each call
   - Confirm backend is polling miners

2. **Is the Pinia store updating correctly?**
   - Verify mutations are triggering
   - Check if reactive updates propagate
   - Confirm computed properties recalculate

3. **Is the component receiving updates?**
   - Check if computed properties update
   - Verify watchers are triggering
   - Confirm DOM is re-rendering

4. **Is polling actually running?**
   - Verify intervals are set
   - Check if fetch functions execute
   - Confirm no duplicate polling

5. **What causes the navigation failure?**
   - Check component lifecycle during navigation
   - Verify router guards aren't blocking
   - Confirm cleanup is happening properly

6. **What causes the Vue rendering errors?**
   - Check for null references in templates
   - Verify v-if conditions are correct
   - Confirm refs are properly initialized

## Next Steps

1. **Add all debugging enhancements** to the codebase
2. **Reproduce the issue** with full logging enabled
3. **Analyze the logs** to identify the exact failure point
4. **Determine root cause** based on evidence, not assumptions
5. **Design targeted fix** based on findings
6. **Test fix** with debugging still enabled
7. **Remove excessive logging** once issue is resolved

## Success Criteria

- Identify exact point where data becomes stale
- Understand why Vue components aren't updating
- Determine root cause of navigation failure
- Have evidence-based understanding of all issues
- No assumptions - only facts from logs
