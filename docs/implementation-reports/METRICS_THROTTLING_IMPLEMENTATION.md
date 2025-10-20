# Metrics Saving Throttling Implementation

## Overview

Implemented a decoupled metrics saving mechanism that saves metrics at a fixed 60-second interval, independent of the user-configurable polling interval.

## Changes Made

### File: `src/backend/services/miner_manager.py`

#### 1. Added Metrics Throttling Configuration (Line ~48)

```python
# Metrics saving configuration - decoupled from polling interval
# Fixed at 60 seconds to align with Analytics minimum timeframe (1 minute)
self.metrics_save_interval = 60  # seconds
self.last_metrics_save: Dict[str, datetime] = {}  # Track last save time per miner
```

#### 2. Modified `_poll_miner` Method (Line ~780)

**Before:**
- Metrics saved on every polling cycle
- No throttling mechanism

**After:**
- Check elapsed time since last save
- Only save if >= 60 seconds have passed
- Track last save time per miner
- Log when metrics are saved vs skipped

```python
# Save metrics to timeseries storage (throttled to metrics_save_interval)
if self.timeseries_storage and status:
    current_time = datetime.now()
    last_save = self.last_metrics_save.get(miner_id)
    
    # Check if enough time has passed since last save
    should_save = (
        last_save is None or 
        (current_time - last_save).total_seconds() >= self.metrics_save_interval
    )
    
    if should_save:
        # Save metrics and update last_save time
        ...
```

#### 3. Updated `remove_miner` Method (Line ~240)

Added cleanup of metrics save tracking when a miner is removed:

```python
# Clean up metrics save tracking
if miner_id in self.last_metrics_save:
    del self.last_metrics_save[miner_id]
```

## Benefits

### 1. Storage Efficiency

**Example with 30-second polling (default):**
- Before: 2 saves/minute = 604,800 records/month per miner
- After: 1 save/minute = 302,400 records/month per miner
- **Savings: 50%**

**Example with 5-second polling (worst case):**
- Before: 12 saves/minute = 3,628,800 records/month per miner
- After: 1 save/minute = 302,400 records/month per miner
- **Savings: 92%**

### 2. Alignment with Analytics

- Analytics minimum timeframe: 1 minute
- Metrics save interval: 60 seconds
- Perfect alignment - no wasted data

### 3. User Experience

- Users can still set polling to 5-10 seconds for responsive UI
- Real-time updates in dashboard
- Storage efficiency maintained

### 4. Backward Compatibility

- No API changes
- No database schema changes
- No UI changes required
- Transparent to users

## Testing

### Test Script: `test_metrics_throttling.py`

Monitors the database for 3 minutes to verify:
- Metrics are saved at 60-second intervals
- Intervals are consistent (55-65 second range)
- Independent of polling frequency

### Manual Testing

1. Set polling interval to 10 seconds in Settings
2. Monitor logs for "Saved metrics" vs "Skipping metrics save" messages
3. Query database to verify save frequency:

```sql
SELECT 
    miner_id,
    timestamp,
    metric_type
FROM miner_metrics
WHERE miner_id = 'bitaxe_192_168_1_156'
ORDER BY timestamp DESC
LIMIT 20;
```

Expected: Timestamps should be ~60 seconds apart

## Configuration

### Current Settings

- `metrics_save_interval`: 60 seconds (hardcoded)
- `polling_interval`: User-configurable (5-300 seconds)

### Future Enhancements (Optional)

If needed, `metrics_save_interval` could be made configurable:

1. Add to `config/app_config.py`:
   ```python
   METRICS_SAVE_INTERVAL = 60  # seconds
   ```

2. Add to Settings UI:
   ```vue
   <v-select
     v-model="settings.metrics_save_interval"
     :items="[30, 60, 120, 300]"
     label="Metrics Save Interval"
     hint="How often to save metrics to database (in seconds)"
   />
   ```

However, this is **not recommended** as it adds complexity without clear benefit.

## Logging

### Debug Logs

When metrics are saved:
```
DEBUG: Saved metrics for miner bitaxe_192_168_1_156 to timeseries storage (interval: 60s)
```

When metrics are skipped:
```
DEBUG: Skipping metrics save for bitaxe_192_168_1_156 (elapsed: 25.3s, interval: 60s)
```

### Error Logs

If metrics saving fails:
```
ERROR: Failed to save metrics for bitaxe_192_168_1_156: [error details]
```

Note: Errors don't stop the polling cycle - they're logged and the next save is attempted.

## Impact on Existing Data

- No migration needed
- Existing metrics remain unchanged
- New throttling applies immediately after restart
- Database will grow more slowly going forward

## Rollback Plan

If issues arise, revert by:

1. Remove throttling logic from `_poll_miner`
2. Remove `metrics_save_interval` and `last_metrics_save` from `__init__`
3. Restore original save-on-every-poll behavior

The changes are isolated and easy to revert.
