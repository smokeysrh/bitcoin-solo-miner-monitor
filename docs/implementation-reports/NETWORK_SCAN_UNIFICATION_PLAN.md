# Network Scan Unification Implementation Plan

**Date:** October 18, 2025  
**Goal:** Unify all "Scan Network" buttons to use NetworkScanner dialog with consistent behavior

## Strategy Overview

### Phase 1: Fix Core Issues (30 min) ⚡ CRITICAL

Fix the NetworkScanner dialog to work perfectly

### Phase 2: Unify Main App (15 min) 🎯 QUICK WIN

Make all main app buttons open the NetworkScanner dialog

### Phase 3: Adapt Setup Wizard (45 min) 🎨 CUSTOM UI

Keep inline display but use same logic

---

## Phase 1: Fix Core Issues

### Issue 1: WebSocket Subscription Format ⚡ CRITICAL

**Problem Found:**

```javascript
// networkScanService sends (WRONG):
{
  "type": "subscribe",
  "topic": "discovery"  // ❌ Wrong key!
}

// Backend expects:
{
  "type": "subscribe",
  "topics": ["discovery"]  // ✅ Correct - array with 's'
}
```

**Fix Location:** `src/frontend/src/services/networkScanService.js`  
**Line:** ~360 in `connectWebSocket()` method

**Change:**

```javascript
// OLD (line ~360):
this.websocket.send(
  JSON.stringify({
    type: "subscribe",
    topic: "discovery", // ❌ Wrong
  })
);

// NEW:
this.websocket.send(
  JSON.stringify({
    type: "subscribe",
    topics: ["discovery"], // ✅ Correct
  })
);
```

**Expected Result:**

- Backend will receive subscription
- Backend logs will show: "Client subscribed to topics: ['discovery']"
- Progress updates will be received by frontend

---

### Issue 2: formatPortList Function Missing

**Problem:** `TypeError: D.formatPortList is not a function`

**Investigation Needed:**

1. Check if `formatPortList` exists in NetworkScanner.vue
2. Check if it's imported correctly
3. Check if it's being called with correct parameters

**Fix Location:** `src/frontend/src/components/NetworkScanner.vue`

**Likely Fix:**

```javascript
// Add missing function or fix import
const formatPortList = (ports) => {
  if (!ports || !Array.isArray(ports)) return "";
  return ports.join(", ");
};
```

---

### Issue 3: Display Shows "0/0" Instead of "0/254"

**Problem:** Total hosts not displaying correctly in NetworkScanner

**Investigation:** Check how NetworkScanner receives and displays scan status

**Fix Location:** `src/frontend/src/components/NetworkScanner.vue`

**Likely Issue:** Not reading `total_hosts` from scan status correctly

---

## Phase 2: Unify Main App (Quick Win)

### Goal

All main app "Scan Network" buttons open the NetworkScanner dialog

### Changes Required

#### 1. Dashboard Quick Actions

**File:** `src/frontend/src/components/QuickActions.vue`

**Current:**

```javascript
const handleScanNetwork = async () => {
  scanning.value = true;
  try {
    emit("scan-network", props.defaultNetwork);
    const { networkScanService } = await import(
      "../services/networkScanService"
    );
    await networkScanService.startScan({
      network: props.defaultNetwork,
    });
  } finally {
    scanning.value = false;
  }
};
```

**New:**

```javascript
const networkScannerDialog = ref(false);

const handleScanNetwork = () => {
  networkScannerDialog.value = true;
  emit("scan-network", props.defaultNetwork);
};
```

**Template Addition:**

```vue
<NetworkScanner
  v-model="networkScannerDialog"
  @close="networkScannerDialog = false"
/>
```

---

#### 2. SimpleDashboard

**File:** `src/frontend/src/views/SimpleDashboard.vue`

**Current:**

```javascript
const scanNetwork = async () => {
  scanning.value = true;
  try {
    const { networkScanService } = await import(
      "../services/networkScanService"
    );
    await networkScanService.startScan({
      network: defaultNetwork,
    });
  } finally {
    scanning.value = false;
  }
};
```

**New:**

```javascript
const networkScannerDialog = ref(false);

const scanNetwork = () => {
  networkScannerDialog.value = true;
};
```

**Template Addition:**

```vue
<NetworkScanner
  v-model="networkScannerDialog"
  @close="networkScannerDialog = false"
/>
```

---

#### 3. Dashboard (Advanced)

**File:** `src/frontend/src/views/Dashboard.vue`

**Current:** Has inline discovery section (keep it)

**Addition:** Add NetworkScanner dialog option for Quick Actions

**Change:** Same as SimpleDashboard above

---

## Phase 3: Adapt Setup Wizard

### Goal

Setup wizard uses same logic but displays inline (no dialog popup)

### Approach

**Keep:** Inline display in setup wizard  
**Change:** Use networkScanService for logic  
**Add:** WebSocket subscription to 'discovery' topic

### Implementation Options

#### Option A: Create Inline NetworkScan Component (RECOMMENDED)

**New Component:** `src/frontend/src/components/NetworkScanInline.vue`

**Features:**

- Uses same `networkScanService`
- Displays progress inline (no dialog)
- Shows same data as NetworkScanner dialog
- Reusable for other inline contexts

**Usage in Setup Wizard:**

```vue
<NetworkScanInline
  :network-range="networkRange"
  :ports="selectedPorts"
  :timeout="scanTimeout"
  @scan-complete="handleScanComplete"
  @miners-found="handleMinersFound"
/>
```

---

#### Option B: Modify Setup Wizard to Use networkScanService Directly

**File:** `installer/common/wizard/index.html`

**Changes:**

1. Remove IPC call: `ipcRenderer.invoke('scan-network')`
2. Import networkScanService
3. Subscribe to WebSocket updates
4. Display progress inline

**Pros:** No new component needed  
**Cons:** Mixing Vue logic in HTML file, harder to maintain

---

### Recommended: Option A

Create `NetworkScanInline.vue` component that:

- Shares logic with NetworkScanner dialog
- Displays inline without dialog wrapper
- Can be used in setup wizard and anywhere else

---

## Implementation Order

### Step 1: Fix WebSocket Subscription (5 min) ⚡

```
src/frontend/src/services/networkScanService.js
Line ~360: Change "topic" to "topics" array
```

### Step 2: Fix formatPortList Error (10 min)

```
src/frontend/src/components/NetworkScanner.vue
Add or fix formatPortList function
```

### Step 3: Fix Display "0/0" Issue (15 min)

```
src/frontend/src/components/NetworkScanner.vue
Ensure total_hosts displays correctly
```

### Step 4: Test NetworkScanner Works (10 min)

```
Navigate to /miners
Click "SCAN NETWORK"
Verify:
- Dialog opens ✓
- Shows correct total hosts ✓
- Progress updates in real-time ✓
- Found miners display ✓
```

### Step 5: Update QuickActions Component (5 min)

```
src/frontend/src/components/QuickActions.vue
Add NetworkScanner dialog
Update handleScanNetwork to open dialog
```

### Step 6: Update SimpleDashboard (5 min)

```
src/frontend/src/views/SimpleDashboard.vue
Add NetworkScanner dialog
Update scanNetwork to open dialog
```

### Step 7: Update Dashboard (5 min)

```
src/frontend/src/views/Dashboard.vue
Add NetworkScanner dialog for Quick Actions
Keep inline discovery section
```

### Step 8: Create NetworkScanInline Component (30 min)

```
src/frontend/src/components/NetworkScanInline.vue
Extract logic from NetworkScanner
Create inline display version
```

### Step 9: Update Setup Wizard (15 min)

```
installer/common/wizard/index.html
Import and use NetworkScanInline component
Remove IPC implementation
```

### Step 10: Test All Locations (15 min)

```
Test each "Scan Network" button:
1. Setup Wizard ✓
2. Dashboard Quick Actions ✓
3. SimpleDashboard Quick Actions ✓
4. Miners Page ✓
```

---

## File Changes Summary

### Files to Modify:

1. ✅ `src/frontend/src/services/networkScanService.js` - Fix subscription
2. ✅ `src/frontend/src/components/NetworkScanner.vue` - Fix display bugs
3. ✅ `src/frontend/src/components/QuickActions.vue` - Add dialog
4. ✅ `src/frontend/src/views/SimpleDashboard.vue` - Add dialog
5. ✅ `src/frontend/src/views/Dashboard.vue` - Add dialog
6. ✅ `installer/common/wizard/index.html` - Use new component

### Files to Create:

1. ✅ `src/frontend/src/components/NetworkScanInline.vue` - New inline component

### Files to Remove (Later):

1. ❌ IPC handler for 'scan-network' in Electron main process (if exists)

---

## Testing Checklist

### After Phase 1 (Core Fixes):

- [ ] NetworkScanner dialog opens
- [ ] WebSocket subscription succeeds
- [ ] Backend logs show: "Client subscribed to topics: ['discovery']"
- [ ] Progress updates received
- [ ] Total hosts displays correctly (e.g., "0/254")
- [ ] Current IP updates
- [ ] Found miners display
- [ ] No JavaScript errors

### After Phase 2 (Main App):

- [ ] Dashboard Quick Actions opens NetworkScanner dialog
- [ ] SimpleDashboard opens NetworkScanner dialog
- [ ] Miners page still works (already uses dialog)
- [ ] All show same consistent UI
- [ ] All receive real-time updates

### After Phase 3 (Setup Wizard):

- [ ] Setup wizard displays scan inline
- [ ] Uses same networkScanService
- [ ] Receives real-time updates
- [ ] Shows same data as dialog
- [ ] No IPC calls
- [ ] Consistent behavior with main app

---

## Success Criteria

### User Experience:

✅ All "Scan Network" buttons work consistently  
✅ Real-time progress updates visible  
✅ Clear indication of scan progress  
✅ Found miners display immediately  
✅ No frozen or hanging UI  
✅ Professional, polished experience

### Technical:

✅ Single source of truth (networkScanService)  
✅ Proper WebSocket subscription  
✅ No duplicate code  
✅ Maintainable architecture  
✅ No JavaScript errors  
✅ Comprehensive logging

---

## Rollback Plan

If issues occur:

### Phase 1 Rollback:

```
git checkout src/frontend/src/services/networkScanService.js
git checkout src/frontend/src/components/NetworkScanner.vue
```

### Phase 2 Rollback:

```
git checkout src/frontend/src/components/QuickActions.vue
git checkout src/frontend/src/views/SimpleDashboard.vue
git checkout src/frontend/src/views/Dashboard.vue
```

### Phase 3 Rollback:

```
git checkout installer/common/wizard/index.html
rm src/frontend/src/components/NetworkScanInline.vue
```

---

## Estimated Time

- **Phase 1 (Core Fixes):** 30 minutes
- **Phase 2 (Main App):** 15 minutes
- **Phase 3 (Setup Wizard):** 45 minutes
- **Testing:** 30 minutes

**Total:** ~2 hours

---

## Next Steps

1. ✅ Review this plan
2. ✅ Approve approach
3. ⚡ Start with Phase 1 (critical fixes)
4. 🎯 Move to Phase 2 (quick wins)
5. 🎨 Complete Phase 3 (custom UI)
6. ✅ Test thoroughly
7. 🚀 Deploy

---

## Notes

- NetworkScanner dialog is the best implementation - use it as the standard
- Setup wizard needs inline display but same logic
- All implementations must use networkScanService for consistency
- WebSocket subscription is the key to real-time updates
- Fix the subscription format first - everything else depends on it
