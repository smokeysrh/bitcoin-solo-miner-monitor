# Metrics Saving Analysis & Recommendations

## Current Implementation

### How Metrics Are Currently Saved

**Location:** `src/backend/services/miner_manager.py` (line ~780 in `_poll_miner` method)

```python
async def _poll_miner(self, miner_id: str):
    while self.is_running:
        # ... poll miner for status ...
        
        # Save metrics to timeseries storage after successful poll
        if self.timeseries_storage and status:
            extracted_metrics = self._extract_metrics(status)
            await self.timeseries_storage.save_metrics(miner_id, extracted_metrics, datetime.now())
        
        # Wait for next polling interval
        await asyncio.sleep(self.polling_interval)
```

### Key Findings

1. **Metrics are saved on EVERY polling cycle** - no separate throttling
2. **Polling interval is user-configurable** via Settings UI (`settings.polling_interval`)
3. **Default polling interval:** 30 seconds (`config/app_config.py`)
4. **User can set polling interval** from 5 seconds to 300 seconds (5 minutes)

### Current Behavior

- If user sets polling to 5 seconds → metrics saved every 5 seconds
- If user sets polling to 30 seconds → metrics saved every 30 seconds  
- If user sets polling to 60 seconds → metrics saved every 60 seconds
- If user sets polling to 300 seconds → metrics saved every 300 seconds

## Problem

1. **Storage inefficiency:** Saving metrics every 5-30 seconds creates excessive data
2. **Lowest analytics timeframe is 1 minute:** The Analytics page's lowest interval is "1M" (1 minute)
3. **Mismatch:** Polling interval affects both UI refresh rate AND metrics storage rate

## Recommended Solution

### Option 1: Decouple Metrics Saving from Polling (RECOMMENDED)

Add a separate `metrics_save_interval` that's independent of the polling interval:

**Benefits:**
- Users can poll frequently for real-time UI updates (e.g., 5-10 seconds)
- Metrics saved less frequently for storage efficiency (e.g., 60 seconds)
- Aligns with Analytics minimum timeframe of 1 minute

**Implementation:**


```python
class MinerManager:
    def __init__(self):
        self.polling_interval = DEFAULT_POLLING_INTERVAL  # For UI updates
        self.metrics_save_interval = 60  # Fixed at 60 seconds for storage
        self.last_metrics_save = {}  # Track last save time per miner
    
    async def _poll_miner(self, miner_id: str):
        while self.is_running:
            # ... poll miner for status ...
            
            # Save metrics only if enough time has passed
            current_time = datetime.now()
            last_save = self.last_metrics_save.get(miner_id)
            
            should_save = (
                last_save is None or 
                (current_time - last_save).total_seconds() >= self.metrics_save_interval
            )
            
            if should_save and self.timeseries_storage and status:
                extracted_metrics = self._extract_metrics(status)
                await self.timeseries_storage.save_metrics(miner_id, extracted_metrics, current_time)
                self.last_metrics_save[miner_id] = current_time
            
            # Wait for next polling interval (for UI updates)
            await asyncio.sleep(self.polling_interval)
```

### Option 2: Force Polling Interval to Minimum 60 Seconds

**Benefits:**
- Simpler implementation
- Reduces both UI refresh and metrics storage

**Drawbacks:**
- Less responsive UI (users can't see real-time updates)
- Removes user flexibility

### Option 3: Make Metrics Save Interval Configurable

Add a new setting in the Settings UI for `metrics_save_interval`:

**Benefits:**
- Maximum user control
- Can optimize for their specific needs

**Drawbacks:**
- More complex UI
- Users might not understand the difference

## Recommendation

**Implement Option 1** with these specifics:

1. **Fixed metrics save interval:** 60 seconds (hardcoded)
2. **Keep polling interval configurable:** 5-300 seconds (user choice)
3. **Rationale:**
   - Aligns with Analytics minimum timeframe (1 minute)
   - Reduces storage by 50-92% depending on polling interval
   - Maintains responsive UI for users who want frequent updates
   - Simple implementation without adding UI complexity

## Storage Impact

### Current Storage (30-second polling):
- 2 saves/minute × 7 metrics = 14 records/minute
- 14 × 60 minutes = 840 records/hour
- 840 × 24 hours = 20,160 records/day
- 20,160 × 30 days = **604,800 records/month per miner**

### Proposed Storage (60-second metrics saving):
- 1 save/minute × 7 metrics = 7 records/minute
- 7 × 60 minutes = 420 records/hour
- 420 × 24 hours = 10,080 records/day
- 10,080 × 30 days = **302,400 records/month per miner**

**Savings: 50% reduction in storage**

### If user has 5-second polling (current worst case):
- Current: 12 saves/minute = 3,628,800 records/month
- Proposed: 1 save/minute = 302,400 records/month
- **Savings: 92% reduction in storage**

## Implementation Steps

1. Add `metrics_save_interval` constant (60 seconds)
2. Add `last_metrics_save` dictionary to track last save time per miner
3. Modify `_poll_miner` to check elapsed time before saving
4. Update documentation to explain the difference between polling and metrics saving
5. Consider adding a log message when metrics are saved (at DEBUG level)
