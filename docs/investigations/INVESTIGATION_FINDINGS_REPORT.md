# Investigation Findings Report: Cached Data Issue

## Executive Summary

**ROOT CAUSE IDENTIFIED**: Backend polling is not running. The miner exists in the database but is not loaded into the active miners dictionary, so no polling tasks are started to fetch fresh data.

## Evidence

### 1. Frontend Logs Show Stale Data
```
"dataAge":"2025-10-21T17:54:50.367675"
```
- Data is from **October 21st at 5:54 PM** (2 days old)
- Current time: **October 23rd at 10:46 AM**
- Data timestamp **never changes** across multiple polls

### 2. Refresh Endpoint Returns Empty
```
Refresh response: {
  "status":"success",
  "message":"No miners configured",
  "miners":[],
  "timestamp":"2025-10-23T10:52:12.169203"
}
```
- Backend reports **"No miners configured"**
- Returns **empty miners array**
- This proves the miner is NOT in the active miners dictionary

### 3. Data Flow Analysis

**Current Flow**:
```
Frontend Request → API get_miner() → miner_manager.get_miner() → miner_data_manager.get_miner()
                                   ↓ (not found in memory)
                                   → data_storage.get_miner_config() (database)
                                   → Returns OLD data from database
```

**Expected Flow**:
```
Backend Startup → Load miners from DB → Add to miners dict → Start polling tasks
                                                            ↓
Polling Task → Fetch from device → Update miner_data_manager → Fresh data available
                                                              ↓
Frontend Request → API → miner_manager → miner_data_manager → Returns FRESH data
```

## Root Cause

The backend is **not loading miners from the database on startup** and **not starting polling tasks** for them.

### Code Analysis

**In `src/backend/services/miner_manager.py`**:

The `start()` method only starts polling for miners already in `self.miners`:
```python
async def start(self):
    self.is_running = True
    # Start polling for existing miners
    for miner_id in self.miners:  # ← This dict is EMPTY on startup!
        await self.start_polling(miner_id)
```

**The Problem**:
- `self.miners` dictionary is empty on startup
- Miners are saved to database but never loaded back
- No polling tasks are created
- API falls back to database which has stale data

## Impact

1. **All miner data is stale** - Shows data from last time backend was running
2. **No real-time updates** - Polling is not happening
3. **Refresh doesn't work** - Can't refresh miners that aren't loaded
4. **Charts have no data** - No metrics are being collected

## Solution Required

The backend needs to:

1. **Load miners from database on startup**
   - Query `data_storage` for all saved miner configs
   - Recreate miner instances for each config
   - Add them to `self.miners` dictionary

2. **Start polling for loaded miners**
   - After loading, start polling tasks
   - Begin collecting fresh data immediately

3. **Persist miner instances across restarts**
   - Ensure miners survive backend restarts
   - Maintain continuity of data collection

## Recommended Fix Location

**File**: `src/backend/services/miner_manager.py`
**Method**: `async def start(self)`

**Add before starting polling**:
```python
async def start(self):
    if self.is_running:
        return
    
    self.is_running = True
    logger.info("Starting miner manager service")
    
    # NEW: Load miners from database
    await self._load_miners_from_database()
    
    # Start polling for existing miners
    for miner_id in self.miners:
        await self.start_polling(miner_id)
```

**New method needed**:
```python
async def _load_miners_from_database(self):
    """Load saved miner configurations from database and recreate instances."""
    try:
        # Get all saved configs
        configs = await self.data_storage.get_all_miner_configs()
        
        for config in configs:
            # Recreate miner instance
            miner_id = config['id']
            miner_type = config['type']
            ip_address = config['ip_address']
            port = config.get('port')
            
            # Create miner instance
            miner = MinerFactory.create_miner(miner_type, ip_address, port)
            
            # Add to miners dict
            self.miners[miner_id] = miner
            
            # Initialize miner data in manager
            await self.miner_data_manager.set_miner(miner_id, config)
            
        logger.info(f"Loaded {len(configs)} miners from database")
    except Exception as e:
        logger.error(f"Error loading miners from database: {e}")
```

## Testing Plan

After implementing the fix:

1. **Restart backend** - Miners should be loaded from database
2. **Check logs** - Should see "Loaded X miners from database"
3. **Check logs** - Should see polling tasks starting
4. **Wait 30 seconds** - First poll should complete
5. **Check frontend** - Data timestamp should be current
6. **Wait for next poll** - Timestamp should update

## Additional Findings

### Frontend is Working Correctly ✓
- API calls are being made
- Store is updating properly
- Polling manager is working
- Component reactivity is functioning
- No frontend bugs found

### Backend Debugging Added
- Added comprehensive logging to `_poll_miner()`
- Added logging to `start_polling()`
- Logs will show when polling actually runs
- Can verify fix is working

## Conclusion

**The issue is NOT in the frontend** - it's a backend initialization problem. The miner exists in the database but is never loaded into memory, so no polling happens and only stale database data is returned.

**Fix complexity**: Low - Just need to add database loading on startup
**Fix risk**: Low - Only adds initialization logic
**Testing**: Easy - Just restart backend and verify logs

---

**Status**: Ready for implementation
**Priority**: High - Core functionality broken
**Estimated fix time**: 30 minutes
