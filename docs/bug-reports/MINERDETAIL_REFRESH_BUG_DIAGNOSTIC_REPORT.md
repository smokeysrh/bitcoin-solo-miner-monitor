# MinerDetail Page Refresh Bug - Comprehensive Diagnostic Report

**Date:** October 23, 2025
**Bug ID:** MinerDetail-Refresh-001
**Severity:** Critical - Page fails to load on refresh

---

## Executive Summary

The MinerDetail page fails to render after a browser refresh, displaying a blank/black screen with multiple Vue rendering errors. The page works correctly on initial navigation but breaks when refreshed directly. This is a critical Vue reactivity/lifecycle timing issue.

## Reproduction Steps

1. Navigate to Dashboard (http://localhost:3000/)
2. Click "View Details" on any miner
3. MinerDetail page loads successfully ✓
4. Refresh the page (F5 or Ctrl+R)
5. Page fails to load - blank/black screen ✗

## Observed Errors

### Console Errors (in order of occurrence):
1. **Cannot read properties of undefined (reading 'includes')**
   - Occurs during VSkeletonLoader render
   - Happens 3 times during initial render attempt

2. **Cannot read properties of null (reading 'shapeFlag')**
   - Vue internal error during component update
   - Indicates Vue is trying to process a null VNode

3. **Cannot read properties of null (reading 'emitsOptions')**
   - Vue internal error during component update
   - Occurs multiple times as Vue tries to recover

## Root Cause Analysis

### Primary Issue: Store State Initialization Timing

**On Initial Navigation (Works):**
- Store already has miners loaded: `storeSize: 1`
- `getMinerById` computed returns miner immediately
- Component renders with data available

**On Page Refresh (Fails):**
- Store starts empty: `storeSize: 0`
- `getMinerById` computed returns `null` initially
- Component tries to render before data arrives
- Template directives access undefined/null properties

### Evidence from Console Logs:

\\\
[STORE] FETCH MINER START === {"storeSize":0}  // ← Store is empty on refresh
\\\

vs.

\\\
[STORE] FETCH MINER START === {"storeSize":1}  // ← Store has data on navigation
\\\

### Secondary Issue: VSkeletonLoader Type Prop

The skeleton loader in MinerDetail.vue uses:
\\\ue
<v-skeleton-loader
  v-if="loading && !miner"
  type="card, list-item-three-line, card-heading, card-heading"
  class="mx-auto"
></v-skeleton-loader>
\\\

The `type` prop with comma-separated values may be causing the 'includes' error when Vue tries to process it during the broken render cycle.

### Tertiary Issue: Computed Property Race Condition

\\\javascript
const miner = computed(() => {
  const minerGetter = minersStore.getMinerById;
  return minerGetter ? minerGetter(props.id) : null;
});
\\\

This computed property checks if `getMinerById` exists, but on refresh:
1. Store is empty (miners array = [])
2. `getMinerById` returns `null`
3. Template tries to access `miner.status`, `miner.pool_info`, etc.
4. Vue throws errors trying to render with null/undefined values

## Affected Template Sections

Multiple template sections access miner properties without proper null checks:

1. **Line 30:** `{{ miner.name }}` - Direct property access
2. **Line 31:** `getStatusColor(miner.status)` - Function call with undefined
3. **Line 44:** `miner.status === 'offline'` - Comparison with undefined
4. **Line 67:** `formatHashrate(miner.hashrate)` - Function with undefined
5. **Line 82:** `getTemperatureColor(miner.temperature)` - Function with undefined
6. **Line 147:** `{{ miner.type }}` - Direct property access
7. **Line 195:** `miner.pool_info && miner.pool_info.length` - Chained access
8. **Line 350+:** Multiple pool_info iterations

## Why Initial Navigation Works

When navigating from Dashboard → MinerDetail:
1. Dashboard already fetched all miners
2. Store is populated with miner data
3. `getMinerById` immediately returns the miner object
4. Component renders successfully with data

## Why Refresh Fails

When refreshing the MinerDetail page directly:
1. Vue Router mounts MinerDetail component
2. Store is empty (no miners loaded yet)
3. Component's `onMounted` starts fetching miner data
4. **BUT** Vue tries to render immediately
5. Template accesses `miner.property` where `miner` is `null`
6. Vue's internal rendering fails with multiple errors
7. Component enters broken state

## Technical Deep Dive

### Vue Rendering Lifecycle Issue

\\\
1. Component Setup Phase
   ↓
2. Computed Properties Evaluated (miner = null)
   ↓
3. Template Render Attempted
   ↓
4. VSkeletonLoader processes type prop → ERROR: 'includes' undefined
   ↓
5. Template tries to render miner sections → ERROR: null properties
   ↓
6. Vue internal state corrupted
   ↓
7. onMounted fires, fetches data
   ↓
8. Data arrives, but Vue can't recover from broken state
\\\

### Store Behavior Difference

**Initial Navigation:**
\\\javascript
miners.value = [existingMiner]  // Already populated
getMinerById(id) → returns existingMiner
\\\

**On Refresh:**
\\\javascript
miners.value = []  // Empty array
getMinerById(id) → returns null
// Later...
miners.value.push(fetchedMiner)  // Data arrives too late
\\\

## Impact Assessment

- **User Experience:** Critical - Page completely unusable after refresh
- **Navigation:** Broken - Users cannot navigate to other pages after failed load
- **Data Loss:** None - Data is fetched but cannot be displayed
- **Workaround:** Navigate from Dashboard instead of refreshing

## Recommended Solutions

### Solution 1: Add Proper Loading Guards (Immediate Fix)
Add null checks throughout the template:

\\\ue
<template v-else-if="miner">
  <!-- All miner content here -->
</template>
\\\

### Solution 2: Fix VSkeletonLoader Type Prop
Change the type prop format or add proper guards.

### Solution 3: Ensure Store Hydration Before Render
Modify the component to wait for data before attempting render.

### Solution 4: Add Suspense Boundary
Wrap the component in Vue's Suspense to handle async data loading.

## Next Steps

1. Implement immediate template guards
2. Test refresh behavior
3. Verify navigation works after failed refresh
4. Add proper error boundaries
5. Consider store persistence for better UX

---

**Report Generated:** 2025-10-23 12:39:54
**Diagnostic Method:** Chrome DevTools MCP + Console Analysis
**Test Environment:** Windows, localhost:3000
