# Task 9: Analytics Page Testing - Fixes Applied

## Issues Found and Fixed

### 1. Invalid Interval Values (CRITICAL)
**Problem:** The `getInterval()` method was returning invalid interval values (`1s`, `10s`) that the backend API doesn't support.

**Error:** `Invalid interval: 1s. Valid intervals: 1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d`

**Fix:** Updated `src/frontend/src/views/Analytics.vue` line 466-476:
- Changed `1s` → `1m` for time ranges <= 1 minute
- Changed `10s` → `1m` for time ranges <= 15 minutes
- Kept other intervals as they were already valid

### 2. Data Format Mismatch (CRITICAL)
**Problem:** The API returns aggregated metrics grouped by `metric_type` and `time_bucket`, but the frontend expected a time-series format with all metrics at each timestamp.

**API Response Format:**
```json
[
  {"time_bucket": "2025-10-19 19:45", "metric_type": "hashrate", "avg_value": 4776504666666.667, ...},
  {"time_bucket": "2025-10-19 19:45", "metric_type": "temperature", "avg_value": 53.36, ...},
  ...
]
```

**Expected Frontend Format:**
```json
[
  {"timestamp": "2025-10-19 19:45", "hashrate": 4776504666666.667, "temperature": 53.36, ...},
  ...
]
```

**Fix:** Added `transformMetricsData()` function in `src/frontend/src/views/Analytics.vue` to transform the API response into the expected format.

### 3. Miner Dropdown Display Issue
**Problem:** The miner selection dropdown was showing "[object Object]" instead of miner names.

**Root Cause:** Vuetify 3 changed the property name from `item-text` to `item-title`.

**Fix:** Updated `src/frontend/src/views/Analytics.vue` line 108:
- Changed `item-text="name"` → `item-title="name"`

### 5. Canvas Refs Null Check and Double-Call Prevention (CRITICAL)
**Problem:** Debug logs revealed that `updateCharts()` was being called twice:
1. First call: All canvas refs were `null` because `hasData.value` was still false, so the canvas elements hadn't rendered yet
2. Second call: Canvas refs existed but already had failed Chart.js instances attached

**Root Cause:** 
- `fetchMetricsData()` was being called twice in `onMounted`:
  1. Once by the watcher when `selectedMiners` was set
  2. Once directly after setting `selectedMiners`
- The `nextTick()` wasn't sufficient because the first call happened before `hasData` was set to true

**Fix:**
- Added null check in `updateCharts()` to return early if canvas refs aren't available
- Removed the direct `fetchMetricsData()` call in `onMounted` to prevent double-calling
- Now only the watcher triggers `fetchMetricsData()` when miners are selected
- Added double `nextTick()` to ensure DOM is fully updated
- Added retry mechanism with 100ms delay if refs still aren't available after nextTick

## Testing Status

**Requires:** Frontend rebuild and server restart to test the fixes and view debug output.

**Next Steps:**
1. Rebuild frontend: `npm run build` in `src/frontend/`
2. Restart backend server
3. Navigate to Analytics page
4. Select miner from dropdown
5. Verify all 4 charts display data:
   - Hashrate chart
   - Temperature chart
   - Shares chart
   - Power Consumption chart
6. Test all time range options (1M, 15M, 1H, 24H, 7D, 30D)
7. Test custom date range selection
8. Verify statistics summary displays correct values
9. Test data export functionality for each chart

### 4. Chart Rendering Timing Issue (CRITICAL)
**Problem:** Charts were failing to render with error "Failed to create chart: can't acquire context from the given item"

**Root Cause:** The canvas elements are inside `v-else` blocks that only render when `hasData.value` is true. The code was trying to create charts immediately after setting `hasData.value = true`, but the DOM hadn't updated yet, so the canvas refs were still null.

**Fix:** 
- Added `nextTick` to imports from Vue
- Added `await nextTick()` before calling `updateCharts()` to wait for DOM update

### 6. Chart.js Date Adapter Issue (CRITICAL)
**Problem:** Charts were failing with error "This method is not implemented: Check that a complete date adapter is provided"

**Root Cause:** Chart.js requires a date adapter (like `chartjs-adapter-date-fns`) when using `type: "time"` for x-axis scales. The package wasn't installed and npm had dependency resolution issues.

**Fix:**
- Instead of installing the adapter, switched to using formatted string labels
- Imported `format` from `date-fns` (already installed)
- Changed timestamp processing to format dates as strings (e.g., "Oct 20, 14:30")
- Removed `type: "time"` and `time: { unit: ... }` from all chart x-axis configurations
- Charts now use default category scale with formatted time labels

## Files Modified

1. `src/frontend/src/views/Analytics.vue`
   - Fixed `getInterval()` method (lines 466-476)
   - Added `transformMetricsData()` function (lines 478-510)
   - Updated miner selection dropdown (line 108)
   - Added `nextTick` import (line 351)
   - Added `await nextTick()` before updateCharts() (line 547)
   - Added canvas ref null check with retry mechanism
   - Removed duplicate fetchMetricsData() call in onMounted
   - Imported `format` from date-fns
   - Changed timestamp formatting to strings
   - Removed time scale configuration from all charts
