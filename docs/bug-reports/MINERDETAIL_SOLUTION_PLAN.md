# MinerDetail Refresh Bug - Solution Implementation Plan

**Date:** 2025-10-23 12:41:22
**Priority:** Critical
**Estimated Fix Time:** 30 minutes

---

## Problem Summary

The MinerDetail page fails to render on refresh because:
1. The Pinia store starts empty (miners array = [])
2. The computed `miner` property returns `null`
3. The template tries to render before data is available
4. Vue encounters multiple null/undefined property access errors
5. The component enters a broken state and cannot recover

## Verified Issues

### Issue #1: Template Structure Flaw
The current template structure has a critical flaw:

\\\ue
<template>
  <div>
    <v-skeleton-loader v-if="loading && !miner" ... />
    <v-alert v-else-if="error" ... />
    <v-alert v-else-if="!miner" ... />
    
    <!-- Miner Details -->
    <template v-else>
      <!-- This section renders when miner exists -->
    </template>
  </div>
</template>
\\\

**The Problem:** The `<template v-else>` block assumes `miner` exists, but on refresh:
- `loading` is `true` initially
- `miner` is `null`
- Condition: `loading && !miner` = `true && true` = `true`
- **Should show skeleton loader** ✓

However, the VSkeletonLoader itself is causing an error with its `type` prop!

### Issue #2: VSkeletonLoader Type Prop Error

\\\ue
<v-skeleton-loader
  v-if="loading && !miner"
  type="card, list-item-three-line, card-heading, card-heading"
  class="mx-auto"
></v-skeleton-loader>
\\\

The `type` prop is being processed by Vuetify, which internally calls `.includes()` on something that's undefined during the broken render cycle.

### Issue #3: Race Condition in Computed Property

\\\javascript
const miner = computed(() => {
  const minerGetter = minersStore.getMinerById;
  return minerGetter ? minerGetter(props.id) : null;
});
\\\

This checks if `getMinerById` exists (it always does), but doesn't handle the case where it returns `null`.

## Root Cause Identified

**The actual root cause is a Vue reactivity timing issue:**

1. Component mounts with empty store
2. Template starts rendering
3. `v-if="loading && !miner"` evaluates to `true`
4. VSkeletonLoader tries to render
5. **During VSkeletonLoader's internal processing, Vue's reactivity system is in an inconsistent state**
6. The `type` prop processing fails because Vue internals are accessing undefined properties
7. This cascades into multiple Vue internal errors
8. Component state becomes corrupted

## Solution Strategy

### Immediate Fix (Recommended)

**Option A: Simplify Loading State**
Replace the VSkeletonLoader with a simpler loading indicator that doesn't have complex prop processing:

\\\ue
<v-progress-circular
  v-if="loading && !miner"
  indeterminate
  color="primary"
  size="64"
  class="mx-auto my-16"
></v-progress-circular>
\\\

**Option B: Fix VSkeletonLoader Type Prop**
Change the type prop to a single value or array:

\\\ue
<v-skeleton-loader
  v-if="loading && !miner"
  type="article"
  class="mx-auto"
></v-skeleton-loader>
\\\

**Option C: Add Key to Force Re-render**
Add a key to the skeleton loader to force Vue to treat it as a new component:

\\\ue
<v-skeleton-loader
  v-if="loading && !miner"
  :key="'loading-' + props.id"
  type="article"
  class="mx-auto"
></v-skeleton-loader>
\\\

### Comprehensive Fix (Best Practice)

Restructure the template to be more defensive:

\\\ue
<template>
  <div class="miner-detail">
    <!-- Loading State -->
    <div v-if="loading && !miner" class="loading-container">
      <v-progress-circular
        indeterminate
        color="primary"
        size="64"
      ></v-progress-circular>
      <p class="mt-4">Loading miner details...</p>
    </div>

    <!-- Error State -->
    <v-alert v-else-if="error" type="error" class="mb-4">
      {{ error }}
    </v-alert>

    <!-- Not Found State -->
    <v-alert v-else-if="!loading && !miner" type="warning" class="mb-4">
      Miner not found
    </v-alert>

    <!-- Miner Details - Only render when miner exists -->
    <div v-else-if="miner">
      <!-- All miner content here -->
    </div>
  </div>
</template>
\\\

## Implementation Steps

### Step 1: Backup Current File
\\\ash
cp src/frontend/src/views/MinerDetail.vue src/frontend/src/views/MinerDetail.vue.backup
\\\

### Step 2: Apply Immediate Fix
Replace the VSkeletonLoader with a simpler loading indicator.

### Step 3: Test Refresh Behavior
1. Navigate to MinerDetail page
2. Refresh the page
3. Verify loading indicator appears
4. Verify page loads successfully after data arrives

### Step 4: Test Navigation
1. After successful refresh, click Dashboard
2. Verify navigation works
3. Navigate back to MinerDetail
4. Verify page still works

### Step 5: Verify Error States
1. Navigate to non-existent miner ID
2. Verify "Miner not found" message appears
3. Verify no console errors

## Additional Improvements

### 1. Add Loading State CSS
\\\ue
<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
</style>
\\\

### 2. Improve Computed Property
\\\javascript
const miner = computed(() => {
  if (!minersStore.getMinerById) {
    console.warn('getMinerById not available in store');
    return null;
  }
  const result = minersStore.getMinerById(props.id);
  console.log('[MinerDetail] Computed miner:', result ? result.name : 'null');
  return result;
});
\\\

### 3. Add Error Boundary
Consider wrapping the component in an error boundary to catch and handle rendering errors gracefully.

## Testing Checklist

- [ ] Page loads on initial navigation
- [ ] Page loads on refresh
- [ ] Loading indicator displays correctly
- [ ] No console errors on refresh
- [ ] Navigation works after refresh
- [ ] Error state displays for invalid miner ID
- [ ] All miner data displays correctly after load
- [ ] Tabs work correctly
- [ ] Forms work correctly
- [ ] Charts render correctly

## Rollback Plan

If the fix causes issues:
\\\ash
cp src/frontend/src/views/MinerDetail.vue.backup src/frontend/src/views/MinerDetail.vue
\\\

## Success Criteria

1. ✓ Page loads successfully on refresh
2. ✓ No Vue rendering errors in console
3. ✓ Loading state displays properly
4. ✓ Navigation works after refresh
5. ✓ All functionality remains intact

---

**Next Action:** Implement the immediate fix and test thoroughly.
