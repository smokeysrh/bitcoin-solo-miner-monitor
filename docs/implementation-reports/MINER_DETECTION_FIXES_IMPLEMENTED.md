# Miner Detection Fixes - Implementation Summary

## Date: October 19, 2025

## Overview
Implemented critical fixes to the miner detection logic based on the comprehensive analysis in `MINER_DETECTION_COMPLETE_ANALYSIS.md`. These fixes address detection timeouts, misidentification issues, and improve overall detection accuracy.

---

## Phase 1: Critical Fixes (COMPLETED)

### Fix 1.1: Increased Detection Timeout ✓
**File:** `src/backend/services/miner_manager.py`

**Change:**
```python
# OLD: detection_timeout = timeout * 2  # 5 * 2 = 10 seconds
# NEW: detection_timeout = timeout * 6  # 5 * 6 = 30 seconds
```

**Impact:** Allows sufficient time for sequential Bitcoin port checks and complex detection scenarios.

---

### Fix 1.2: Enhanced Logging ✓
**File:** `src/backend/models/miner_factory.py`

**Changes:**
- Added INFO-level logging at start of detection: `"Starting detection for {ip_address} with open ports: {ports}"`
- Added INFO-level logging for each detection attempt:
  - `"Trying Avalon Nano detection on {ip_address}:4028"`
  - `"Trying Bitaxe detection on {ip_address}:80"`
  - `"Bitaxe detection failed on {ip_address}, trying Magic Miner"`
  - `"Trying Bitcoin node detection on {ip_address} with ports: {bitcoin_ports_available}"`
- Added final status logging: `"All detection attempts failed for {ip_address}"`

**Impact:** Full visibility into detection process for debugging and monitoring.

---

### Fix 1.3: Bitaxe vs NerdQaxe Differentiation ✓
**File:** `src/backend/models/bitaxe_miner.py`

**Key Changes:**
1. Check for `deviceModel` field in API response (most reliable differentiator)
2. If `deviceModel` exists → NerdQaxe/NerdAxe variant
3. If `deviceModel` does NOT exist → Standard Bitaxe
4. Determine specific Bitaxe model based on ASIC chip (BM1366=Ultra, BM1368=Supra, BM1397=Gamma, BM1370=Hex)

**Code:**
```python
device_model = self.device_info.get("deviceModel", None)

if device_model:
    # This is a NerdQaxe/NerdAxe variant (has deviceModel field)
    device_type = device_model  # Use exact model name from device
    model = device_model
    logger.info(f"Detected {device_model} at {self.ip_address} (asicCount: {asic_count})")
else:
    # This is a standard Bitaxe (NO deviceModel field)
    device_type = "Bitaxe"
    # Determine model based on ASIC chip...
```

**Impact:** Accurate differentiation between Bitaxe and NerdQaxe devices.

---

## Phase 2: High Priority Fixes (COMPLETED)

### Fix 2.1: Optimized Detection Order ✓
**File:** `src/backend/models/miner_factory.py`

**New Detection Order:**
1. **Avalon Nano (port 4028)** - Most specific, cgminer API
2. **Bitaxe (port 80)** - Specific JSON API
3. **Magic Miner (port 80)** - Web scraping
4. **Bitcoin Node (ports 8332, 18332, 8333, 18333)** - Bitcoin-specific ports only

**Impact:** Checks most specific ports first, avoids redundant checks.

---

### Fix 2.2: Fixed Bitcoin Node Detection ✓
**Files:** 
- `src/backend/models/miner_factory.py`
- `src/backend/models/bitcoin_node.py`

**Key Changes:**
1. **Removed port 80 and 8080** from Bitcoin node detection
2. Only check Bitcoin-specific ports: 8332, 18332, 8333, 18333
3. Updated port list in both detection files

**Before:**
```python
bitcoin_ports = [8332, 18332, 8333, 18333, 80, 8080]
```

**After:**
```python
bitcoin_ports = [8332, 18332, 8333, 18333]
```

**Impact:** Prevents misidentification of miners as Bitcoin nodes.

---

### Fix 2.3: Strengthened Magic Miner Detection ✓
**File:** `src/backend/models/magic_miner.py`

**Key Changes:**
1. **Require BG02-specific indicator** (one of: "bg02", "magic miner", "magicminer")
2. **Plus 2+ generic mining indicators** (mining, hashrate, pool, bitcoin, "7 th/s", "150w")
3. **Exclude JSON APIs** (check for HTML content)

**Logic:**
```python
# Require HTML content
if "<html" not in main_html_lower:
    return {}

# Check for BG02-specific indicators (REQUIRED)
bg02_specific = ["bg02", "magic miner", "magicminer"]
has_bg02_indicator = any(indicator in combined_html for indicator in bg02_specific)

if not has_bg02_indicator:
    return {}

# Check for generic mining indicators (need 2+)
generic_indicators = ["mining", "hashrate", "pool", "bitcoin", "7 th/s", "150w"]
found_generic = sum(1 for indicator in generic_indicators if indicator in combined_html)

if found_generic >= 2:
    # Valid Magic Miner BG02
```

**Impact:** Reduces false positives, requires BG02-specific evidence.

---

### Fix 2.4: Strengthened Avalon Nano Detection ✓
**File:** `src/backend/models/avalon_nano_miner.py`

**Key Changes:**
1. Check cgminer `version` command for device type
2. Verify "avalon" in miner type string
3. Label non-Avalon cgminer devices as "cgminer Device"

**Code:**
```python
version = await self._send_command("version")
if version and "VERSION" in version:
    version_data = version["VERSION"][0]
    miner_type = version_data.get("Miner", "")
    
    if "avalon" in miner_type.lower():
        device_type = "Avalon Nano"
        model = miner_type
    else:
        device_type = "cgminer Device"
        model = miner_type if miner_type else "Unknown"
```

**Impact:** Accurate identification of Avalon vs other cgminer devices.

---

## Summary of Changes

### Files Modified:
1. `src/backend/services/miner_manager.py` - Increased detection timeout
2. `src/backend/models/miner_factory.py` - Enhanced logging, optimized detection order, fixed Bitcoin port list
3. `src/backend/models/bitaxe_miner.py` - Bitaxe/NerdQaxe differentiation
4. `src/backend/models/magic_miner.py` - Strengthened BG02 detection
5. `src/backend/models/avalon_nano_miner.py` - Improved cgminer device identification
6. `src/backend/models/bitcoin_node.py` - Removed port 80/8080 from detection

### Key Improvements:
- ✓ Detection timeout increased from 10s to 30s
- ✓ Comprehensive INFO-level logging added
- ✓ Bitaxe and NerdQaxe properly differentiated
- ✓ Magic Miner requires BG02-specific indicators
- ✓ Avalon Nano checks device type in cgminer response
- ✓ Bitcoin nodes only check Bitcoin-specific ports (not port 80)
- ✓ Detection order optimized (most specific first)

---

## Expected Outcomes

After these fixes:
1. ✓ .156 and other devices will be detected within timeout
2. ✓ Bitaxe and NerdQaxe will be correctly differentiated
3. ✓ Magic Miners will only match actual BG02 devices
4. ✓ Avalon Nano will only match actual Avalon devices
5. ✓ Bitcoin nodes will be correctly labeled (not as miners)
6. ✓ Full visibility into detection process via logs
7. ✓ No false positives or misidentifications

---

## Testing Recommendations

1. **Test .156 Detection:** Scan network including .156 to verify it's detected
2. **Test Bitaxe:** Verify standard Bitaxe detected correctly
3. **Test NerdQaxe:** Verify NerdQaxe detected with correct model name
4. **Test Magic Miner:** Verify BG02 detected correctly
5. **Test Avalon Nano:** Verify Avalon devices detected correctly
6. **Test Bitcoin Node:** Verify nodes detected on correct ports only
7. **Review Logs:** Check INFO-level logs for detection flow visibility

---

## Next Steps

1. Run network scan to test all fixes
2. Monitor logs for detection flow
3. Verify all device types are correctly identified
4. Check that .156 and other previously missed devices are now detected
5. Confirm no false positives or misidentifications

---

## Notes

- All changes maintain backward compatibility
- No breaking changes to API or data structures
- Logging improvements provide better debugging visibility
- Detection logic is now more robust and accurate
- Timeout increase allows for complex detection scenarios
