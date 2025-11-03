# Pool Configuration Logic Audit

## Overview
This document explains how the "Update Pool Configuration" feature works in the Bitcoin Solo Miner Monitor application.

## Summary
**The pool configuration logic ADDS a new pool to the miner's pool list using the cgminer `addpool` command. It does NOT change the currently active pool or modify existing pools in the "Pool Information" list.**

---

## How It Works

### 1. Frontend (User Interface)
**Location:** `src/frontend/src/views/MinerDetail.vue` (lines 836-862)

When a user fills out the "Update Pool Configuration" form and clicks the button:

```javascript
const updatePoolConfig = async () => {
  if (!miner.value) return;
  
  updatingPool.value = true;
  
  try {
    await minersStore.updateMiner(miner.value.id, {
      settings: {
        pool_url: poolConfig.value.url,
        pool_port: parseInt(poolConfig.value.port),
        pool_user: poolConfig.value.user,
        pool_pass: poolConfig.value.pass,
      },
    });
    
    // Refresh miner data
    await minersStore.fetchMiner(miner.value.id);
  } catch (error) {
    console.error(`Error updating pool config for miner ${miner.value.id}:`, error);
  } finally {
    updatingPool.value = false;
  }
};
```

**What happens:**
- Collects pool URL, port, username, and password from the form
- Sends these as `settings` to the backend API
- Refreshes the miner data to show updated information

---

### 2. Backend API (API Service)
**Location:** `src/backend/api/api_service.py` (lines 1014-1067)

The API endpoint receives the request:

```python
async def update_miner(self, miner_id: str, request: MinerUpdateRequest) -> Dict[str, Any]:
    # Validate miner exists
    miner = await self.miner_manager.get_miner(miner_id)
    if not miner:
        raise HTTPException(status_code=404, detail=f"Miner {miner_id} not found")
    
    # Prepare updates
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.settings is not None:
        updates["settings"] = request.settings
    
    # Update miner
    success = await self.miner_manager.update_miner(miner_id, updates)
    
    # Save configuration to database
    await self.data_storage.save_miner_config(miner_id, miner)
    
    return miner
```

**What happens:**
- Validates the miner exists
- Extracts the `settings` from the request
- Passes to the Miner Manager
- Saves the configuration to the database

---

### 3. Miner Manager (Business Logic)
**Location:** `src/backend/services/miner_manager.py` (lines 401-450)

The miner manager processes the update:

```python
async def update_miner(self, miner_id: str, updates: Dict[str, Any]) -> bool:
    # Filter out protected fields (id, type, ip_address, port, added_at)
    filtered_updates = {}
    for key, value in updates.items():
        if key not in ["id", "type", "ip_address", "port", "added_at"]:
            filtered_updates[key] = value
    
    # Update miner data in memory
    await self.miner_data_manager.update_miner(miner_id, filtered_updates)
    
    # If updating settings, apply to the actual miner hardware
    if "settings" in updates:
        async with self._miners_lock:
            if miner_id in self.miners:
                miner = self.miners[miner_id]
                await miner.update_settings(updates["settings"])
    
    return True
```

**What happens:**
- Filters out protected fields that shouldn't be changed
- Updates the in-memory miner data
- **Calls the miner's `update_settings()` method to apply changes to the hardware**

---

### 4. Avalon Nano Miner (Hardware Communication)
**Location:** `src/backend/models/avalon_nano_miner.py` (lines 275-307)

The actual hardware command is sent:

```python
async def update_settings(self, settings: Dict[str, Any]) -> bool:
    try:
        success = True
        
        # Handle different settings
        if "fan" in settings:
            fan_response = await self._send_command(f"setfan,{settings['fan']}")
            success = success and fan_response is not None
            
        if "frequency" in settings:
            freq_response = await self._send_command(f"setfreq,{settings['frequency']}")
            success = success and freq_response is not None
        
        # Add pool if provided
        if "pool_url" in settings and "pool_user" in settings:
            pool_url = settings["pool_url"]
            pool_user = settings["pool_user"]
            pool_pass = settings.get("pool_pass", "x")
            pool_response = await self._send_command(f"addpool,{pool_url},{pool_user},{pool_pass}")
            success = success and pool_response is not None
        
        return success
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        return False
```

**What happens:**
- Checks if pool settings are provided (`pool_url` and `pool_user`)
- **Sends the cgminer `addpool` command** with the pool URL, username, and password
- The `addpool` command **ADDS a new pool** to the miner's pool list

---

## What the `addpool` Command Does

The cgminer API `addpool` command:
- **Adds a new pool** to the miner's pool configuration
- **Does NOT remove** existing pools
- **Does NOT change** the currently active pool
- The new pool is added to the pool list with a priority

### Example:
If your miner currently has:
1. Pool A (Active)
2. Pool B (Backup)

After running "Update Pool Configuration" with Pool C:
1. Pool A (Active) - **Still active**
2. Pool B (Backup)
3. **Pool C (New)** - Added to the list

---

## What It Does NOT Do

❌ **Does NOT switch** the currently active pool
❌ **Does NOT remove** existing pools from the list
❌ **Does NOT modify** existing pool configurations
❌ **Does NOT change** pool priorities

---

## What Shows in "Pool Information"

The "Pool Information" section displays all pools configured on the miner by calling the cgminer `pools` command:

**Location:** `src/backend/models/avalon_nano_miner.py` (lines 237-268)

```python
async def get_pool_info(self) -> List[Dict[str, Any]]:
    pools = await self._send_command("pools")
    if not pools or "POOLS" not in pools:
        return []
        
    pool_info = []
    for pool in pools["POOLS"]:
        pool_info.append({
            "url": pool.get("URL", ""),
            "user": pool.get("User", ""),
            "status": pool.get("Status", ""),
            "priority": pool.get("Priority", 0),
            "accepted": pool.get("Accepted", 0),
            "rejected": pool.get("Rejected", 0),
            "is_active": pool.get("Stratum Active", False),
        })
    
    return pool_info
```

This retrieves **ALL pools** configured on the miner, including:
- The original pools that came with the miner
- Any pools added via the "Update Pool Configuration" feature

---

## Recommendations

### If You Want to SWITCH Pools:
You would need to implement additional cgminer commands:
- `switchpool` - Switch to a different pool by ID
- `removepool` - Remove a pool from the list
- `enablepool` - Enable a disabled pool
- `disablepool` - Disable a pool

### If You Want to REPLACE Pools:
You would need to:
1. Remove existing pools using `removepool`
2. Add the new pool using `addpool`
3. Switch to the new pool using `switchpool`

### Current Behavior is Safe:
The current implementation is **safe** because:
- It doesn't disrupt mining operations
- It doesn't remove existing pools
- It adds redundancy by adding backup pools
- The miner will automatically failover to new pools if the current one fails

---

## Conclusion

The "Update Pool Configuration" feature **adds a new pool** to the miner's pool list using the cgminer `addpool` command. It does not change which pool is currently active or modify the existing pools shown in the "Pool Information" list.

If you want different behavior (like switching pools or replacing pools), additional cgminer commands would need to be implemented.
