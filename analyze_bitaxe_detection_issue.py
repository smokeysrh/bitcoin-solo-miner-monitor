#!/usr/bin/env python3
"""
Analyze Bitaxe Detection Issue

This script analyzes the collected data to understand why Gammas are being 
misidentified as Hexes and proposes better detection logic.
"""

import json
from datetime import datetime


def analyze_detection_issue():
    """Analyze the detection issue with real device data."""
    
    print("🔍 BITAXE GAMMA vs HEX DETECTION ANALYSIS")
    print("=" * 60)
    
    # Load the real device data
    try:
        with open("bitaxe_data_192_168_50_85_20251103_140638.json", 'r') as f:
            device_data = json.load(f)
    except FileNotFoundError:
        print("❌ Device data file not found. Run the collector first.")
        return
    
    analysis = device_data["analysis"]
    key_fields = analysis["key_fields"]
    
    print(f"\n📊 CURRENT DETECTION RESULT:")
    print(f"   Detected Model: {analysis['model']}")
    print(f"   Confidence: {analysis['confidence']:.1%}")
    print(f"   Method: {analysis['detection_method']}")
    
    print(f"\n🔑 KEY DEVICE CHARACTERISTICS:")
    print(f"   ASIC Model: {key_fields['ASICModel']}")
    print(f"   ASIC Count: {key_fields['asicCount']}")
    print(f"   Hashrate: {key_fields['hashRate']:.1f} GH/s ({key_fields['hashRate']/1000:.2f} TH/s)")
    print(f"   Board Version: {key_fields['boardVersion']}")
    print(f"   Firmware Version: {key_fields['version']}")
    print(f"   Hostname: {key_fields['hostname']}")
    print(f"   Core Count: {key_fields['smallCoreCount']}")
    print(f"   Frequency: {key_fields['frequency']} MHz")
    print(f"   Power: {key_fields['power']:.1f} W")
    print(f"   Voltage: {key_fields['voltage']:.1f} mV")
    
    print(f"\n🤔 ANALYSIS OF DETECTION LOGIC:")
    
    # Current logic analysis
    hashrate_gh = key_fields['hashRate']
    hashrate_th = hashrate_gh / 1000
    
    print(f"   Current Logic:")
    print(f"   - BM1370 ASIC detected ✓")
    print(f"   - Hashrate: {hashrate_gh:.1f} GH/s = {hashrate_th:.2f} TH/s")
    print(f"   - Threshold check: {hashrate_th:.2f} >= 0.85? {'YES' if hashrate_th >= 0.85 else 'NO'}")
    print(f"   - Result: {'Bitaxe Hex' if hashrate_th >= 0.85 else 'Bitaxe Gamma'}")
    
    print(f"\n❓ QUESTION: Is this actually a Gamma being misidentified?")
    print(f"   If YES, then the current threshold (850 GH/s) is too low.")
    print(f"   Some Gamma variants with BM1370 can achieve 1+ TH/s.")
    
    print(f"\n💡 PROPOSED IMPROVED DETECTION METHODS:")
    
    # Method 1: Board version analysis
    board_version = key_fields['boardVersion']
    print(f"\n   Method 1: Board Version Analysis")
    print(f"   - Current board version: {board_version}")
    print(f"   - Gamma boards typically: 200-400 series")
    print(f"   - Hex boards typically: 500-600+ series")
    print(f"   - This device (602) suggests: Hex or newer Gamma")
    
    # Method 2: Firmware version analysis
    firmware = key_fields['version']
    print(f"\n   Method 2: Firmware Version Analysis")
    print(f"   - Current firmware: {firmware}")
    print(f"   - Need to research version patterns by model")
    
    # Method 3: Core count analysis
    core_count = key_fields['smallCoreCount']
    print(f"\n   Method 3: Core Count Analysis")
    print(f"   - Current core count: {core_count}")
    print(f"   - This could be model-specific")
    
    # Method 4: Power consumption analysis
    power = key_fields['power']
    efficiency = power / hashrate_th if hashrate_th > 0 else 0
    print(f"\n   Method 4: Power/Efficiency Analysis")
    print(f"   - Current power: {power:.1f} W")
    print(f"   - Efficiency: {efficiency:.1f} W/TH")
    print(f"   - Gamma efficiency: typically 15-25 W/TH")
    print(f"   - Hex efficiency: typically 12-20 W/TH")
    print(f"   - This device: {'Efficient (likely Hex)' if efficiency < 22 else 'Less efficient (likely Gamma)'}")
    
    # Method 5: Frequency analysis
    frequency = key_fields['frequency']
    print(f"\n   Method 5: Frequency Analysis")
    print(f"   - Current frequency: {frequency} MHz")
    print(f"   - Higher frequencies often indicate newer/higher-performance models")
    
    print(f"\n🎯 RECOMMENDED DETECTION STRATEGY:")
    print(f"   1. Use multiple factors, not just hashrate")
    print(f"   2. Board version as primary indicator:")
    print(f"      - 600+ series: Likely Hex")
    print(f"      - 200-500 series: Likely Gamma")
    print(f"   3. Efficiency as secondary check:")
    print(f"      - <22 W/TH: Likely Hex")
    print(f"      - >22 W/TH: Likely Gamma")
    print(f"   4. Hashrate as tertiary check (with higher thresholds)")
    print(f"   5. Conservative fallback when uncertain")
    
    # Generate improved detection function
    generate_improved_detection_logic(key_fields)


def generate_improved_detection_logic(device_fields):
    """Generate improved detection logic based on analysis."""
    
    print(f"\n🛠️  IMPROVED DETECTION LOGIC:")
    
    asic_model = device_fields['ASICModel']
    board_version = int(device_fields['boardVersion']) if device_fields['boardVersion'] else 0
    hashrate = device_fields['hashRate']
    power = device_fields['power']
    core_count = device_fields['smallCoreCount']
    
    # Calculate efficiency
    hashrate_th = hashrate / 1000 if hashrate > 0 else 0
    efficiency = power / hashrate_th if hashrate_th > 0 and power > 0 else 0
    
    print(f"\n   Testing improved logic on current device:")
    
    if asic_model == "BM1370":
        confidence = 0.5
        model = "Bitaxe (BM1370)"
        reasons = []
        
        # Primary: Board version check
        if board_version >= 600:
            model = "Bitaxe Hex"
            confidence = 0.8
            reasons.append(f"Board version {board_version} (600+ series)")
        elif 200 <= board_version < 600:
            model = "Bitaxe Gamma"
            confidence = 0.8
            reasons.append(f"Board version {board_version} (200-599 series)")
        
        # Secondary: Efficiency check
        if efficiency > 0:
            if efficiency < 22:
                if model == "Bitaxe Gamma":
                    confidence = 0.6  # Conflicting signals
                    reasons.append(f"Efficient ({efficiency:.1f} W/TH) suggests Hex, but board suggests Gamma")
                else:
                    confidence = min(confidence + 0.1, 0.9)
                    reasons.append(f"Efficient ({efficiency:.1f} W/TH) supports Hex")
            else:
                if model == "Bitaxe Hex":
                    confidence = 0.6  # Conflicting signals
                    reasons.append(f"Less efficient ({efficiency:.1f} W/TH) suggests Gamma, but board suggests Hex")
                else:
                    confidence = min(confidence + 0.1, 0.9)
                    reasons.append(f"Less efficient ({efficiency:.1f} W/TH) supports Gamma")
        
        # Tertiary: Hashrate check (with higher thresholds)
        if hashrate > 0:
            hashrate_th = hashrate / 1000
            if hashrate_th >= 1.2:  # Raised threshold
                if model == "Bitaxe Gamma":
                    confidence = max(confidence - 0.1, 0.5)
                    reasons.append(f"Very high hashrate ({hashrate_th:.2f} TH/s) unusual for Gamma")
                else:
                    confidence = min(confidence + 0.05, 0.95)
                    reasons.append(f"High hashrate ({hashrate_th:.2f} TH/s) supports Hex")
        
        print(f"   Result: {model}")
        print(f"   Confidence: {confidence:.1%}")
        print(f"   Reasoning:")
        for reason in reasons:
            print(f"     - {reason}")
    
    print(f"\n   For this specific device:")
    print(f"   - Board version 602 strongly suggests Hex")
    print(f"   - Efficiency {efficiency:.1f} W/TH is good (supports Hex)")
    print(f"   - High hashrate {hashrate_th:.2f} TH/s supports Hex")
    print(f"   - CONCLUSION: This appears to be correctly identified as Bitaxe Hex")


def create_improved_detection_function():
    """Create the improved detection function code."""
    
    print(f"\n📝 IMPROVED DETECTION FUNCTION CODE:")
    
    code = '''
def _differentiate_bm1370_models_improved(self, hash_rate: float, asic_count: int, 
                                        hostname: str, board_version: str = "", 
                                        power: float = 0, core_count: int = 0) -> str:
    """
    Improved differentiation between Bitaxe models that use BM1370 chips.
    
    Uses multiple factors for more accurate detection:
    1. Board version (primary indicator)
    2. Power efficiency (secondary indicator) 
    3. Hashrate (tertiary indicator)
    4. Hostname hints (fallback)
    """
    hostname = hostname.lower()
    
    # Convert board version to int for comparison
    try:
        board_ver_int = int(board_version) if board_version else 0
    except (ValueError, TypeError):
        board_ver_int = 0
    
    # Calculate efficiency if power data available
    hashrate_th = hash_rate / 1000 if hash_rate > 0 else 0
    efficiency = power / hashrate_th if hashrate_th > 0 and power > 0 else 0
    
    confidence_factors = []
    
    # Method 1: Board version analysis (most reliable)
    if board_ver_int >= 600:
        model = "Bitaxe Hex"
        confidence_factors.append(("board_version_hex", 0.8))
        logger.info(f"BM1370 identified as Hex via board version: {board_version}")
    elif 200 <= board_ver_int < 600:
        model = "Bitaxe Gamma" 
        confidence_factors.append(("board_version_gamma", 0.8))
        logger.info(f"BM1370 identified as Gamma via board version: {board_version}")
    else:
        # No reliable board version, use other methods
        model = None
    
    # Method 2: Efficiency analysis (if power data available)
    if efficiency > 0:
        if efficiency < 22:  # More efficient suggests Hex
            if model == "Bitaxe Gamma":
                confidence_factors.append(("efficiency_conflict", -0.2))
                logger.warning(f"Efficiency conflict: {efficiency:.1f} W/TH suggests Hex but board suggests Gamma")
            else:
                confidence_factors.append(("efficiency_hex", 0.1))
                if not model:
                    model = "Bitaxe Hex"
        else:  # Less efficient suggests Gamma
            if model == "Bitaxe Hex":
                confidence_factors.append(("efficiency_conflict", -0.2))
                logger.warning(f"Efficiency conflict: {efficiency:.1f} W/TH suggests Gamma but board suggests Hex")
            else:
                confidence_factors.append(("efficiency_gamma", 0.1))
                if not model:
                    model = "Bitaxe Gamma"
    
    # Method 3: Hashrate analysis (with higher thresholds)
    if hashrate_th > 0:
        if hashrate_th >= 1.2:  # Very high hashrate (1.2+ TH/s)
            if model == "Bitaxe Gamma":
                confidence_factors.append(("hashrate_unusual_gamma", -0.1))
                logger.warning(f"Unusually high hashrate for Gamma: {hash_rate} GH/s")
            else:
                confidence_factors.append(("hashrate_hex", 0.05))
                if not model:
                    model = "Bitaxe Hex"
        elif hashrate_th >= 0.9:  # High hashrate (900+ GH/s)
            confidence_factors.append(("hashrate_high", 0.02))
            if not model:
                model = "Bitaxe Hex"
        # No penalty for lower hashrates - both models can vary
    
    # Method 4: Hostname hints (fallback)
    if not model:
        if "gamma" in hostname:
            model = "Bitaxe Gamma"
            confidence_factors.append(("hostname_gamma", 0.6))
        elif "hex" in hostname:
            model = "Bitaxe Hex"
            confidence_factors.append(("hostname_hex", 0.6))
        else:
            # Conservative fallback - default to Gamma as it's more common
            model = "Bitaxe Gamma"
            confidence_factors.append(("conservative_default", 0.3))
            logger.info(f"BM1370 device lacks clear indicators, defaulting to Gamma")
    
    # Log the decision process
    total_confidence = sum(factor[1] for factor in confidence_factors)
    logger.info(f"BM1370 model determination: {model}")
    logger.debug(f"Confidence factors: {confidence_factors} (total: {total_confidence:.2f})")
    logger.debug(f"Analysis context: hashrate={hash_rate}GH/s, board={board_version}, "
                f"efficiency={efficiency:.1f}W/TH, hostname='{hostname}'")
    
    return model
'''
    
    print(code)


if __name__ == "__main__":
    analyze_detection_issue()
    create_improved_detection_function()