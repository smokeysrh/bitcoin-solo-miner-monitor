# Comprehensive Miner Detection Logic Analysis & Implementation Plan

## Executive Summary

The Bitcoin Solo Miner Monitoring App detects and monitors:

- **Bitaxe miners** (HTTP API on port 80) - Official Bitaxe devices
- **NerdQaxe/NerdAxe** (HTTP API on port 80) - Bitaxe forks with 4+ ASICs
- **Magic Miner BG02** (Web interface on port 80) - GPU-style ASIC miner
- **Avalon Nano miners** (cgminer API on port 4028) - Canaan devices
- **Bitcoin Core nodes** (RPC/Web/P2P on multiple ports) - Full nodes

**Critical Issues Identified:**

1. ✗ .156 not detected - Detection timeout (10s) too short for sequential port checks
2. ✗ NerdQaxe misidentified as Bitaxe - Both use same Bitaxe firmware/API
3. ✗ Magic Miners mislabeled - Generic keyword matching
4. ✗ Avalon Nano mislabeled - Any cgminer device = Avalon Nano
5. ✗ Bitcoin nodes mislabeled as "miners" - Generic keyword matching

---

## Research Findings

### 1. Bitaxe vs NerdQaxe/NerdAxe

**Key Discovery:** NerdQaxe/NerdAxe are **Bitaxe forks** that run the **same Bitaxe firmware**!

**Bitaxe Characteristics:**

- Uses ESP32 chip on board
- Single ASIC chip (BM1366, BM1368, or BM1397)
- Hashrate: ~500 GH/s to 1.2 TH/s
- One-color OLED display
- Default hostname: "bitaxe"
- Board versions: 200, 300, 302, 401, 402, 403, 601, 602

**NerdQaxe+ Characteristics:**

- Uses Lilygo T-Display-S3 LCD (ESP32 built-in)
- **4 ASIC chips** (BM1368 or BM1370)
- Hashrate: ~2.4 TH/s (4x Bitaxe)
- Full-color LCD display (NerdMiner/Nerdaxe style)
- Runs **Bitaxe firmware** as core
- Default hostname: likely "nerdqaxe" or "nerdaxe"
- asicCount: 4 (vs Bitaxe's 1)

**API Response Differences:**

```json
// Bitaxe (NO deviceModel field)
{
  "asicCount": 1,
  "hostname": "bitaxe",
  "ASICModel": "BM1366",
  "boardVersion": "302",
  "version": "v2.6.0",
  "hashRate": 2372.758  // varies by model
}

// NerdQaxe++ (HAS deviceModel field)
{
  "deviceModel": "NerdQAxe++",  // ← KEY DIFFERENTIATOR
  "asicCount": 4,
  "hostname": "nerdqaxe",
  "ASICModel": "BM1370",
  "version": "v1.0.30",
  "hashRate": 4822.423
}
```

**CONCRETE Differentiation Strategy:**

1. **Check for `deviceModel` field** (MOST RELIABLE):
   - If `deviceModel` exists → NerdQaxe/NerdAxe variant
   - If `deviceModel` does NOT exist → Standard Bitaxe
2. Use `deviceModel` value to identify specific variant:
   - "NerdQAxe++" → NerdQaxe++ (BM1370 chips)
   - "NerdQAxe+" → NerdQaxe+ (BM1368 chips)
   - "NerdAxe" → NerdAxe
3. Fallback: Check `hostname` if deviceModel is ambiguous

---

### 2. Magic Miner BG02

**Characteristics:**

- GPU-style form factor (285 x 134 x 50mm)
- Web-based control interface
- Hashrate: 7 TH/s
- Power: 150W
- Network: RJ45 Ethernet + WiFi
- Control Mode: Web-based (no documented API)

**Detection Challenge:**

- No documented API endpoints
- Must rely on web scraping
- Generic HTML content

**Unique Identifiers:**

- Model name: "BG02" (should appear in HTML)
- Brand: "Magic Miner" or "magicminer"
- Specific hashrate: 7 TH/s
- Power consumption: 150W
- May have unique HTML element IDs or classes

**Differentiation Strategy:**

1. Require "BG02" OR "Magic Miner" in HTML (case-insensitive)
2. Plus 2+ generic mining indicators
3. Check for 7 TH/s hashrate if displayed
4. Exclude if JSON API detected (not a web-only interface)

---

### 3. Avalon Nano & cgminer Devices

**Characteristics:**

- Uses cgminer API on port 4028
- Canaan Avalon series
- Various models: Nano 3, Nano 3s, etc.

**cgminer API Commands:**

- `version` - Returns cgminer version and device info
- `stats` - Returns device statistics
- `devs` - Returns device list
- `summary` - Returns summary statistics

**Detection Challenge:**

- Many miners use cgminer (Antminer, Whatsminer, etc.)
- Need to check device type in response

**cgminer Response Example:**

```json
{
  "STATUS": [
    {
      "STATUS": "S",
      "When": 1234567890,
      "Code": 22,
      "Msg": "CGMiner versions",
      "Description": "cgminer 4.11.1"
    }
  ],
  "VERSION": [
    {
      "CGMiner": "4.11.1",
      "API": "3.7",
      "Miner": "Avalon Nano 3", // <-- KEY FIELD
      "CompileTime": "..."
    }
  ]
}
```

**Differentiation Strategy:**

1. Send `version` command
2. Check `Miner` field for "Avalon"
3. If not present, check `stats` for device type
4. Label as "Avalon Nano" only if confirmed
5. Otherwise label as "Unknown cgminer device"

---

### 4. Bitcoin Core Nodes

**Characteristics:**

- Bitcoin Core software
- RPC API on ports 8332 (mainnet) or 18332 (testnet)
- P2P network on ports 8333 (mainnet) or 18333 (testnet)
- Optional web interface on port 80/8080

**RPC API:**

- Requires authentication (username/password)
- Returns JSON-RPC responses
- `getnetworkinfo` returns version and subversion

**Response Example:**

```json
{
  "version": 220000,
  "subversion": "/Satoshi:22.0.0/",  // <-- KEY FIELD
  "protocolversion": 70016,
  "localservices": "0000000000000409",
  ...
}
```

**Detection Challenge:**

- RPC requires auth (will get 401 Unauthorized)
- Web interfaces vary widely
- Generic keywords match mining UIs

**Differentiation Strategy:**

1. **Only check Bitcoin-specific ports** (8332, 18332, 8333, 18333)
2. **Do NOT check port 80** for Bitcoin nodes
3. Look for RPC error responses (401 with "authorization" header)
4. Check for "Satoshi" in user agent
5. Require Bitcoin Core-specific indicators:
   - "bitcoin core" (exact match)
   - "bitcoind" (exact match)
   - "/Satoshi:" (version string)
   - "getblockchaininfo" (RPC method)
6. Label as "Bitcoin Core Node" (not "Bitcoin Miner")

---

## Root Cause Analysis: .156 Detection Failure

### The Timeout Problem

**Current Flow:**

```
1. Port scan finds port 80 open on .156
2. Bitaxe detection (port 80):
   - GET /api/system/info
   - Timeout: 10s, Retries: 3
   - Result: Fails (not Bitaxe API)

3. Magic Miner detection (port 80):
   - GET /
   - Timeout: 10s, Retries: 3
   - Result: Fails (not Magic Miner)

4. Avalon Nano detection (port 4028):
   - Skipped (port not open)

5. Bitcoin Node detection (ALL ports):
   - Tries ports: 8332, 18332, 8333, 18333, 80, 8080
   - SEQUENTIALLY checks each port
   - Each port: 10s timeout + 3 retries = up to 14s
   - Total: 14s × 6 ports = 84 seconds worst case

6. Detection timeout: 10 seconds
   - Times out before Bitcoin checks complete
   - No miner detected
   - No log entry (exception caught at DEBUG level)
```

**Why .156 Isn't in Logs:**

- Concurrent scanning (15 hosts at once)
- Timeout exception caught silently
- No INFO-level log for timeout
- Lost in the noise of other scans

---

## Complete Implementation Plan

### Phase 1: Immediate Fixes (Critical)

#### Fix 1.1: Increase Detection Timeout

**File:** `src/backend/services/miner_manager.py`

**Change:**

```python
# OLD
detection_timeout = timeout * 2  # 5 * 2 = 10 seconds

# NEW
detection_timeout = timeout * 6  # 5 * 6 = 30 seconds
```

**Rationale:** Allows time for sequential Bitcoin port checks

---

#### Fix 1.2: Make Bitcoin Port Checks Concurrent

**File:** `src/backend/models/miner_factory.py`

**Change:** Instead of sequential loop, check all Bitcoin ports concurrently:

```python
# OLD (Sequential)
for bitcoin_port in bitcoin_ports:
    result = await check_port(bitcoin_port)
    if result:
        return result

# NEW (Concurrent)
async def check_bitcoin_ports_concurrent(ip, ports):
    tasks = [check_bitcoin_port(ip, port) for port in ports]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Return first successful result
    for result in results:
        if result and not isinstance(result, Exception):
            return result
    return None
```

**Rationale:** Reduces total time from 84s to ~14s worst case

---

#### Fix 1.3: Add Comprehensive Logging

**File:** `src/backend/models/miner_factory.py`

**Add INFO-level logs:**

```python
logger.info(f"Starting detection for {ip_address} with open ports: {ports}")
logger.info(f"Trying Bitaxe detection on {ip_address}:80")
logger.info(f"Bitaxe detection failed on {ip_address}, trying Magic Miner")
logger.info(f"Magic Miner detection failed on {ip_address}, trying Avalon Nano")
logger.info(f"Avalon Nano detection failed on {ip_address}, trying Bitcoin Node")
logger.info(f"All detection attempts failed for {ip_address}")
logger.warning(f"Detection timed out for {ip_address} after {timeout}s")
```

**Rationale:** Visibility into what's happening with each IP

---

### Phase 2: Strengthen Validations (High Priority)

#### Fix 2.1: Differentiate Bitaxe from NerdQaxe

**File:** `src/backend/models/bitaxe_miner.py`

**Update `get_device_info()` method:**

```python
async def get_device_info(self) -> Dict[str, Any]:
    if not self.device_info:
        response = await self._http_get("/api/system/info")
        if not isinstance(response, dict):
            return {}
        self.device_info = response

    if not self.device_info or not isinstance(self.device_info, dict):
        return {}

    # Check for required Bitaxe fields
    required_fields = ["ASICModel", "version", "boardVersion", "asicCount"]
    present_fields = sum(1 for field in required_fields if field in self.device_info)

    if present_fields < 3:
        return {}

    # Get key identifiers
    asic_count = self.device_info.get("asicCount", 0)
    hostname = str(self.device_info.get("hostname", "")).lower()
    asic_model = self.device_info.get("ASICModel", "").lower()
    hash_rate = self.device_info.get("hashRate", 0)

    # Validate ASIC model
    valid_asic_models = ["bm1366", "bm1368", "bm1397", "bitaxe"]
    if not any(model in asic_model for model in valid_asic_models):
        return {}

    # CONCRETE DIFFERENTIATION: Check for deviceModel field
    device_model = self.device_info.get("deviceModel", None)

    if device_model:
        # This is a NerdQaxe/NerdAxe variant (has deviceModel field)
        device_type = device_model  # Use exact model name from device
        model = device_model
        logger.info(f"Detected {device_model} at {self.ip_address}")
    else:
        # This is a standard Bitaxe (NO deviceModel field)
        device_type = "Bitaxe"

        # Determine Bitaxe model based on ASIC chip
        if "bm1366" in asic_model:
            model = "Bitaxe Ultra"
        elif "bm1368" in asic_model:
            model = "Bitaxe Supra"
        elif "bm1397" in asic_model:
            model = "Bitaxe Gamma"
        elif "bm1370" in asic_model:
            model = "Bitaxe Hex"
        else:
            model = "Bitaxe"

        logger.info(f"Detected {model} at {self.ip_address}")

    return {
        "type": device_type,
        "model": model,
        "asic_model": self.device_info.get("ASICModel", "Unknown"),
        "asic_count": asic_count,
        "firmware_version": self.device_info.get("version", "Unknown"),
        "board_version": self.device_info.get("boardVersion", "Unknown"),
        "hostname": self.device_info.get("hostname", "Unknown"),
        "mac_address": self.device_info.get("macAddr", "Unknown"),
        "hash_rate": hash_rate,
    }
```

**Rationale:** Accurately identifies Bitaxe vs NerdQaxe based on asicCount

---

#### Fix 2.2: Strengthen Magic Miner Detection

**File:** `src/backend/models/magic_miner.py`

**Update `get_device_info()` method:**

```python
async def get_device_info(self) -> Dict[str, Any]:
    if not self.device_info:
        try:
            # Get main page
            main_html = await self._http_get_text("/")
            if not main_html:
                return {}

            main_html_lower = main_html.lower()

            # Exclude JSON APIs (not Magic Miner)
            if main_html_lower.strip().startswith('{') or main_html_lower.strip().startswith('['):
                return {}

            # Require HTML content
            if "<html" not in main_html_lower:
                return {}

            # Check for BG02-specific indicators (REQUIRED)
            bg02_specific = [
                "bg02",
                "magic miner",
                "magicminer"
            ]

            has_bg02_indicator = any(indicator in main_html_lower for indicator in bg02_specific)

            if not has_bg02_indicator:
                logger.debug(f"No BG02-specific indicators found at {self.ip_address}")
                return {}

            # Check for generic mining indicators (need 2+)
            generic_indicators = [
                "mining",
                "hashrate",
                "pool",
                "bitcoin",
                "7 th/s",  # BG02-specific hashrate
                "150w"     # BG02-specific power
            ]

            found_generic = sum(1 for indicator in generic_indicators if indicator in main_html_lower)

            if found_generic >= 2:
                logger.info(f"Magic Miner BG02 detected at {self.ip_address}")
                self.device_info = {
                    "validated": True,
                    "found_bg02_indicator": True,
                    "found_generic_count": found_generic
                }
            else:
                logger.debug(f"Insufficient indicators for Magic Miner at {self.ip_address}")
                return {}

        except Exception as e:
            logger.debug(f"Error detecting Magic Miner at {self.ip_address}: {e}")
            return {}

    # Return device info only if validated
    if self.device_info and self.device_info.get("validated"):
        return {
            "type": "Magic Miner",
            "model": "BG02",
            "hashrate": "7 TH/s",
            "power": "150W"
        }

    return {}
```

**Rationale:** Requires BG02-specific indicator, not just generic keywords

---

#### Fix 2.3: Strengthen Avalon Nano Detection

**File:** `src/backend/models/avalon_nano_miner.py`

**Update `get_device_info()` method:**

```python
async def get_device_info(self) -> Dict[str, Any]:
    if not self.device_info:
        self.device_info = await self._get_device_details()

    # Get version info to identify device type
    try:
        version = await self._send_command("version")
        if version and "VERSION" in version:
            version_data = version["VERSION"][0]
            miner_type = version_data.get("Miner", "")

            # Check if this is actually an Avalon device
            if "avalon" in miner_type.lower():
                device_type = "Avalon Nano"
                model = miner_type
            else:
                # It's a cgminer device, but not Avalon
                device_type = "cgminer Device"
                model = miner_type if miner_type else "Unknown"
                logger.info(f"Detected cgminer device (not Avalon): {miner_type} at {self.ip_address}")
        else:
            device_type = "cgminer Device"
            model = "Unknown"
    except Exception as e:
        logger.debug(f"Error getting version info: {e}")
        device_type = "cgminer Device"
        model = "Unknown"

    # Build device info
    device_info = {
        "type": device_type,
        "model": model,
        "api": "cgminer",
        "cgminer_version": self.device_info.get("cgminer_version", "Unknown"),
        "api_version": self.device_info.get("api_version", "Unknown"),
    }

    # Add additional details
    device_info.update(self.device_info)

    return device_info
```

**Rationale:** Checks device type in cgminer response, doesn't assume all cgminer = Avalon

---

#### Fix 2.4: Fix Bitcoin Node Detection

**File:** `src/backend/models/bitcoin_node.py`

**Update `_detect_bitcoin_node()` method:**

```python
async def _detect_bitcoin_node(self) -> Dict[str, Any]:
    logger.info(f"Starting Bitcoin node detection for {self.ip_address}")

    # ONLY check Bitcoin-specific ports (NOT port 80)
    bitcoin_rpc_ports = [8332, 18332]  # RPC ports
    bitcoin_p2p_ports = [8333, 18333]  # P2P ports

    detected_info = {}

    # Check RPC ports concurrently
    rpc_tasks = [self._check_rpc_interface(port) for port in bitcoin_rpc_ports]
    rpc_results = await asyncio.gather(*rpc_tasks, return_exceptions=True)

    for port, result in zip(bitcoin_rpc_ports, rpc_results):
        if result and not isinstance(result, Exception):
            logger.info(f"Bitcoin RPC interface detected on {self.ip_address}:{port}")
            self.detected_ports.append(port)
            self.port = port
            return {
                "type": "rpc_interface",
                "interface": "RPC",
                "port": port,
                **result
            }

    # Check P2P ports concurrently
    p2p_tasks = [self._check_p2p_port(port) for port in bitcoin_p2p_ports]
    p2p_results = await asyncio.gather(*p2p_tasks, return_exceptions=True)

    for port, result in zip(bitcoin_p2p_ports, p2p_results):
        if result and not isinstance(result, Exception):
            logger.info(f"Bitcoin P2P port detected on {self.ip_address}:{port}")
            self.detected_ports.append(port)
            self.port = port
            return {
                "type": "p2p_interface",
                "interface": "P2P",
                "port": port,
                **result
            }

    logger.info(f"No Bitcoin node detected on {self.ip_address}")
    return {}
```

**Update `_check_rpc_interface()` to look for Bitcoin Core-specific indicators:**

```python
async def _check_rpc_interface(self, port: int) -> Dict[str, Any]:
    try:
        # Try RPC call (will fail with auth error, but we can detect the interface)
        rpc_data = {
            "jsonrpc": "1.0",
            "id": "test",
            "method": "getnetworkinfo",
            "params": []
        }

        try:
            response = await self._http_post("/", rpc_data)
            # If we get a response, check for Bitcoin Core indicators
            if response:
                response_str = str(response).lower()
                if "satoshi" in response_str or "bitcoin core" in response_str:
                    return {
                        "interface_type": "RPC",
                        "network": "mainnet" if port == 8332 else "testnet",
                        "software": "Bitcoin Core"
                    }
        except Exception as e:
            error_str = str(e).lower()
            # Check for Bitcoin Core-specific error messages
            bitcoin_core_indicators = [
                "unauthorized",
                "authorization required",
                "rpc",
                "bitcoin",
                "satoshi"
            ]

            found_indicators = sum(1 for indicator in bitcoin_core_indicators if indicator in error_str)

            if found_indicators >= 2:
                return {
                    "interface_type": "RPC",
                    "network": "mainnet" if port == 8332 else "testnet",
                    "auth_required": True,
                    "software": "Bitcoin Core"
                }

    except Exception as e:
        logger.debug(f"RPC check failed on {self.ip_address}:{port}: {e}")

    return {}
```

**Rationale:** Only checks Bitcoin-specific ports, requires Bitcoin Core indicators

---

### Phase 3: Optimize Detection Order (Medium Priority)

#### Fix 3.1: Reorder Detection Logic

**File:** `src/backend/models/miner_factory.py`

**New detection order:**

```python
@staticmethod
async def detect_miner_type(ip_address: str, ports: Optional[list] = None) -> Dict[str, Any]:
    if ports is None:
        ports = [80, 4028]

    result = {}

    # 1. Check port 4028 FIRST (Avalon Nano - most specific)
    if 4028 in ports:
        avalon_result = await _try_avalon_detection(ip_address)
        if avalon_result:
            return avalon_result

    # 2. Check port 80 for Bitaxe (specific API)
    if 80 in ports:
        bitaxe_result = await _try_bitaxe_detection(ip_address)
        if bitaxe_result:
            return bitaxe_result

    # 3. Check port 80 for Magic Miner (web scraping)
    if 80 in ports:
        magic_result = await _try_magic_miner_detection(ip_address)
        if magic_result:
            return magic_result

    # 4. Check Bitcoin-specific ports (NOT port 80)
    bitcoin_ports = [8332, 18332, 8333, 18333]
    bitcoin_ports_available = [p for p in bitcoin_ports if p in ports]

    if bitcoin_ports_available:
        bitcoin_result = await _try_bitcoin_node_detection(ip_address, bitcoin_ports_available)
        if bitcoin_result:
            return bitcoin_result

    logger.info(f"No miner detected on {ip_address}")
    return {}
```

**Rationale:** Checks most specific ports first, avoids redundant checks

---

### Phase 4: Testing & Validation

#### Test Case 1: Bitaxe Detection

- Scan actual Bitaxe device
- Verify detected as "Bitaxe" (not NerdQaxe)
- Verify asicCount = 1
- Verify correct model (Ultra/Supra/Gamma)

#### Test Case 2: NerdQaxe Detection

- Scan NerdQaxe device
- Verify detected as "NerdQaxe" (not Bitaxe)
- Verify asicCount = 4
- Verify hashrate > 1.5 TH/s

#### Test Case 3: Magic Miner Detection

- Scan Magic Miner BG02
- Verify detected as "Magic Miner BG02"
- Verify NOT detected as Bitaxe or Bitcoin Node

#### Test Case 4: Avalon Nano Detection

- Scan Avalon Nano device
- Verify detected as "Avalon Nano"
- Verify cgminer version info correct

#### Test Case 5: Bitcoin Node Detection

- Scan Bitcoin Core node
- Verify detected as "Bitcoin Core Node" (not "Bitcoin Miner")
- Verify only RPC/P2P ports checked (not port 80)

#### Test Case 6: .156 Detection

- Scan 192.168.1.0/24 network
- Verify .156 appears in logs
- Verify .156 is correctly identified
- Verify detection completes within timeout

---

## Implementation Priority

### Critical (Implement Immediately)

1. **Fix 1.1** - Increase detection timeout to 30 seconds
2. **Fix 1.3** - Add comprehensive logging
3. **Fix 2.1** - Differentiate Bitaxe from NerdQaxe

### High Priority (Implement This Week)

4. **Fix 1.2** - Make Bitcoin port checks concurrent
5. **Fix 2.4** - Fix Bitcoin Node detection (don't check port 80)
6. **Fix 3.1** - Optimize detection order

### Medium Priority (Implement Next Week)

7. **Fix 2.2** - Strengthen Magic Miner detection
8. **Fix 2.3** - Strengthen Avalon Nano detection

### Testing (After Implementation)

9. **Phase 4** - Comprehensive testing with all device types

---

## Expected Outcomes

After implementing all fixes:

1. ✓ .156 will be detected correctly
2. ✓ Bitaxe and NerdQaxe will be differentiated
3. ✓ Magic Miners will be accurately identified
4. ✓ Avalon Nano will only match actual Avalon devices
5. ✓ Bitcoin nodes will be correctly labeled (not as miners)
6. ✓ Detection will complete within 30 seconds
7. ✓ Full visibility into detection process via logs
8. ✓ No false positives or misidentifications

---

## Conclusion

The detection system requires a **multi-phase refactor**:

**Phase 1 (Critical):** Fix the timeout issue so .156 can be detected
**Phase 2 (High):** Strengthen validations to prevent misidentification
**Phase 3 (Medium):** Optimize detection order for efficiency
**Phase 4 (Testing):** Validate all fixes with real devices

The root cause is **weak validation logic** combined with **inefficient sequential checking**. By implementing stronger device-specific validation and concurrent port checking, we can achieve accurate, fast detection of all miner types.

**Estimated Implementation Time:**

- Phase 1: 2-4 hours
- Phase 2: 4-6 hours
- Phase 3: 2-3 hours
- Phase 4: 4-6 hours (testing)
- **Total: 12-19 hours**

**Recommended Approach:**

1. Start with Phase 1 (critical fixes) to get .156 working
2. Then implement Phase 2 (validations) to fix misidentifications
3. Finally Phase 3 (optimization) for long-term maintainability
4. Test thoroughly with all device types
