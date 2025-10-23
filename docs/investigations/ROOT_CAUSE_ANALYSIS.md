# Root Cause Analysis: Why Polling Stopped Working

## The Bug

Between v0.5.0 and v0.9.0, the system lost the ability to automatically load miners from the database on startup and start polling them.

## What Changed

### The Problem Code

**Current `reload_miners()` in api_service.py**:
```python
async def reload_miners(self) -> Dict[str, Any]:
    # Get saved configurations from database
    saved_configs = await self.data_storage.get_all_miner_configs()
    
    # Add them to the miner data manager
    for config in saved_configs:
        miner_id = config.get('id')
        if miner_id:
            await miner_data_manager.set_miner(miner_id, config)  # ← WRONG!
```

**The Issue**: This only loads data into the cache (`miner_data_manager`), but doesn't:
1. Create actual miner instances in `self.miners` dictionary
2. Start polling tasks for those miners

### What Should Happen

```python
async def reload_miners(self) -> Dict[str, Any]:
    saved_configs = await self.data_storage.get_all_miner_configs()
    
    for config in saved_configs:
        # Need to:
        # 1. Create miner instance using MinerFactory
        # 2. Add to self.miner_manager.miners dictionary
        # 3. Start polling task
        # 4. Update miner_data_manager with initial data
```

## Why It Worked in v0.5.0

Looking at the git history, in v0.5.0:
- Miners were likely added during the session and stayed in memory
- Backend wasn't restarted often during development
- When backend restarted, miners had to be re-added manually

## Why It Broke

The `reload_miners` endpoint was added as a development tool but:
1. It's incomplete - doesn't recreate miner instances
2. It's not called automatically on startup
3. It's secured behind dev_endpoint_auth so can't be easily called

## The Fix Needed

### Option 1: Fix `reload_miners` and call it on startup

**In `api_service.py` - Fix the method**:
```python
async def reload_miners(self) -> Dict[str, Any]:
    """Reload miners from database and start polling."""
    try:
        saved_configs = await self.data_storage.get_all_miner_configs()
        
        reloaded_count = 0
        for config in saved_configs:
            try:
                miner_id = config.get('id')
                miner_type = config.get('type')
                ip_address = config.get('ip_address')
                port = config.get('port')
                name = config.get('name')
                
                # Check if already loaded
                if miner_id in self.miner_manager.miners:
                    logger.info(f"Miner {miner_id} already loaded, skipping")
                    continue
                
                # Create miner instance
                from src.backend.models.miner_factory import MinerFactory
                miner = await MinerFactory.create_miner(miner_type, ip_address, port)
                
                if miner:
                    # Add to miners dictionary
                    async with self.miner_manager._miners_lock:
                        self.miner_manager.miners[miner_id] = miner
                    
                    # Set initial data in manager
                    await self.miner_manager.miner_data_manager.set_miner(miner_id, config)
                    
                    # Start polling if manager is running
                    if self.miner_manager.is_running:
                        await self.miner_manager.start_polling(miner_id)
                    
                    reloaded_count += 1
                    logger.info(f"Reloaded and started polling for miner {miner_id}")
                    
            except Exception as e:
                logger.error(f"Failed to reload miner {config.get('id')}: {e}")
                continue
        
        return {
            "success": True,
            "message": f"Successfully reloaded {reloaded_count} miners",
            "miners_count": reloaded_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to reload miners: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reload miners: {str(e)}")
```

**In `api_service.py` - Call it on startup**:
```python
async def start(self):
    """Start the API service."""
    # Initialize services
    await self.data_storage.initialize()
    
    # Wire TimeSeriesStorage to MinerManager
    if self.data_storage.timeseries_storage:
        self.miner_manager.set_timeseries_storage(self.data_storage.timeseries_storage)
        logger.info("TimeSeriesStorage wired to MinerManager")
    
    # Connect WebSocket manager
    self.miner_manager.set_websocket_manager(self.websocket_manager)
    
    # Start miner manager
    await self.miner_manager.start()
    
    # NEW: Load miners from database and start polling
    try:
        logger.info("Loading miners from database...")
        result = await self.reload_miners()
        logger.info(f"Loaded {result.get('miners_count', 0)} miners from database")
    except Exception as e:
        logger.error(f"Failed to load miners from database: {e}")
        # Don't fail startup if this fails
    
    await self.system_monitor.start()
    await self._broadcast_updates()
    
    logger.info(f"API service started on {HOST}:{PORT}")
```

### Option 2: Add method to MinerManager

**In `miner_manager.py`**:
```python
async def load_miners_from_storage(self, data_storage):
    """Load saved miners from storage and start polling."""
    try:
        saved_configs = await data_storage.get_all_miner_configs()
        
        for config in saved_configs:
            try:
                miner_id = config.get('id')
                miner_type = config.get('type')
                ip_address = config.get('ip_address')
                port = config.get('port')
                
                # Skip if already loaded
                if miner_id in self.miners:
                    continue
                
                # Create miner instance
                miner = await MinerFactory.create_miner(miner_type, ip_address, port)
                
                if miner:
                    async with self._miners_lock:
                        self.miners[miner_id] = miner
                    
                    await self.miner_data_manager.set_miner(miner_id, config)
                    
                    if self.is_running:
                        await self.start_polling(miner_id)
                    
                    logger.info(f"Loaded miner {miner_id} from storage")
                    
            except Exception as e:
                logger.error(f"Failed to load miner {config.get('id')}: {e}")
                continue
        
        logger.info(f"Loaded {len(saved_configs)} miners from storage")
        
    except Exception as e:
        logger.error(f"Failed to load miners from storage: {e}")
```

**Call it in `api_service.start()`**:
```python
async def start(self):
    # ... existing code ...
    
    await self.miner_manager.start()
    
    # Load miners from database
    await self.miner_manager.load_miners_from_storage(self.data_storage)
    
    # ... rest of startup ...
```

## Recommendation

**Use Option 2** - It's cleaner because:
1. Keeps miner loading logic in MinerManager where it belongs
2. Separates concerns properly
3. Easier to test
4. `reload_miners` endpoint can call the same method

## Testing the Fix

1. Add a miner through the UI
2. Restart the backend
3. Check logs for "Loaded X miners from storage"
4. Check logs for "=== [BACKEND] POLL CYCLE START ===" 
5. Verify data timestamp updates in frontend
6. Confirm polling continues every 30 seconds

## Summary

The bug was introduced when `reload_miners` was added as a development tool but:
- It was incomplete (didn't create miner instances or start polling)
- It was never called automatically on startup
- The system relied on miners being added during runtime

The fix is to properly load miners from the database on startup and recreate their instances with polling tasks.
