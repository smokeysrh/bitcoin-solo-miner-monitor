# Investigation Summary: Cached Data & Navigation Issues

## Executive Summary

I've investigated the reported issues with cached miner data and navigation failures. Rather than making assumptions, I've created a comprehensive debugging plan to gather evidence about what's actually happening.

## Issues Identified

### Issue 1: Cached/Outdated Data Display
**Symptoms**:
- Dashboard shows outdated miner data
- Miner details page shows same outdated data
- Data doesn't update despite polling being active

**Potential Causes** (need evidence):
- API returning cached data
- Pinia store not updating
- Vue reactivity not triggering
- Computed properties not recalculating
- Polling not executing

### Issue 2: Page Refresh Causes Errors
**Symptoms**:
```
TypeError: Cannot read properties of null (reading 'shapeFlag')
TypeError: Cannot read properties of null (reading 'emitsOptions')
```

**Potential Causes** (need evidence):
- Component unmounting during update
- Null references in template
- Chart rendering timing issues
- Async data loading race conditions

### Issue 3: Navigation Failure
**Symptoms**:
- URL changes but view doesn't update
- Sidebar clicks don't navigate
- App becomes stuck on current view
- Unmount errors in console

**Potential Causes** (need evidence):
- Component not unmounting properly
- Router navigation blocked
- Memory leaks preventing cleanup
- Event listeners not removed

## Current Code Analysis

### Data Flow Path
```
Miner Device → Backend API → Pinia Store → Vue Component → DOM
```

### Key Components Involved

1. **Backend (src/backend/api/api_service.py)**
   - `get_miner()` - Fetches single miner
   - `get_miners()` - Fetches all miners
   - `refresh_miners()` - Forces fresh data fetch
   - `get_miner_metrics()` - Fetches metrics

2. **Frontend Store (src/frontend/src/stores/miners.js)**
   - `fetchMiner()` - Fetches and stores miner data
   - `fetchMiners()` - Fetches all miners
   - `refreshMiners()` - Calls refresh endpoint
   - `fetchMinerMetrics()` - Fetches metrics
   - `normalizeMinerData()` - Normalizes data structure

3. **Component (src/frontend/src/views/MinerDetail.vue)**
   - `onMounted()` - Initializes component
   - `miner` computed - Gets miner from store
   - `fetchPreviewMetrics()` - Loads chart data
   - Polling via `usePollingManager`

4. **Polling (src/frontend/src/composables/usePollingManager.js)**
   - `startPolling()` - Starts interval
   - `pollNow()` - Executes fetch
   - `stopPolling()` - Cleans up

### Observations from Code Review

1. **Store has extensive logging already**
   - Debug mode logs raw API responses
   - Logs normalized data
   - Logs temperature extraction
   - BUT: May not be enabled or visible

2. **Component has lifecycle logging**
   - Logs mount/unmount
   - Logs metrics fetch
   - Logs chart rendering attempts
   - BUT: May not show full picture

3. **Polling manager has logging**
   - Logs start/stop
   - Logs each poll
   - Tracks duplicate polling
   - BUT: May not show timing issues

4. **Backend has request logging**
   - Logs all incoming requests
   - Logs discovery requests
   - BUT: May not log response data

## What We DON'T Know Yet

These are the critical unknowns that debugging will reveal:

1. **Is the API actually returning fresh data?**
   - Need to see actual API response timestamps
   - Need to compare consecutive responses
   - Need to verify backend is polling miners

2. **Is the store updating correctly?**
   - Need to see before/after store state
   - Need to verify mutations trigger
   - Need to confirm reactivity works

3. **Is the component receiving updates?**
   - Need to see computed property recalculations
   - Need to verify watchers trigger
   - Need to confirm DOM updates

4. **Is polling actually running?**
   - Need to see actual poll executions
   - Need to verify timing
   - Need to confirm no interference

5. **What causes the null reference errors?**
   - Need to see component state during error
   - Need to identify which template reference is null
   - Need to understand timing of the error

6. **What blocks navigation?**
   - Need to see navigation attempt
   - Need to see component lifecycle during nav
   - Need to identify what's preventing unmount

## Debugging Strategy

### Phase 1: Enhanced Logging (Immediate)
Add comprehensive logging to track:
- Every API call with request/response
- Every store mutation with before/after state
- Every component update with data changes
- Every poll execution with timing
- Every navigation attempt with outcome

### Phase 2: Reproduce with Logging (Next)
1. Start app with debugging enabled
2. Load dashboard - capture logs
3. Click miner - capture logs
4. Wait for poll - capture logs
5. Click refresh - capture logs
6. Try to navigate - capture logs

### Phase 3: Analyze Evidence (Then)
1. Review complete log timeline
2. Identify exact failure points
3. Understand data flow breaks
4. Determine root causes
5. Design targeted fixes

## Files Created

1. **INVESTIGATION_CACHED_DATA_ISSUE.md**
   - Detailed problem breakdown
   - Specific debugging enhancements needed
   - Questions to answer through debugging

2. **DEBUG_ENHANCEMENTS_PLAN.md**
   - Implementation plan for debugging
   - Files to modify
   - Testing procedure
   - Log analysis checklist

3. **INVESTIGATION_SUMMARY.md** (this file)
   - Executive summary
   - Current understanding
   - Next steps

## Recommended Next Steps

1. **Review the investigation documents**
   - INVESTIGATION_CACHED_DATA_ISSUE.md
   - DEBUG_ENHANCEMENTS_PLAN.md

2. **Decide on debugging approach**
   - Add all enhancements at once, OR
   - Add incrementally by phase

3. **Implement debugging enhancements**
   - Start with Phase 1 (Store debugging)
   - Then Phase 2 (Component debugging)
   - Then remaining phases

4. **Reproduce and capture logs**
   - Follow exact steps from your report
   - Capture complete console output
   - Save logs for analysis

5. **Analyze findings**
   - Review logs together
   - Identify root causes
   - Design evidence-based fixes

## Key Principle

**NO ASSUMPTIONS - ONLY EVIDENCE**

We will not make changes based on "might be" or "could be". Every fix will be based on concrete evidence from the debugging logs showing exactly what's failing and why.

## Questions for You

1. Would you like me to implement all debugging enhancements now?
2. Should I start with a specific phase (e.g., just store debugging)?
3. Do you want to review the debug plan before implementation?
4. Are there specific areas you want me to focus on first?

## Notes

- All existing functionality will remain unchanged
- Debugging code is additive only
- Can be easily removed after diagnosis
- Will not impact performance significantly
- Follows existing code patterns
