#!/usr/bin/env python3
"""
Improved Bitaxe Detection Logic

Based on research and real device data analysis, this implements more accurate
detection logic for differentiating between Bitaxe models, especially 
Gamma vs Hex with BM1370 chips.
"""

import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ImprovedBitaxeDetection:
    """Improved Bitaxe model detection with multiple factors."""
    
    @staticmethod
    def determine_bitaxe_model(device_info: Dict[str, Any]) -> Tuple[str, float, str]:
        """
        Determine Bitaxe model using multiple detection factors.
        
        Args:
            device_info: Dictionary containing device information from API
            
        Returns:
            Tuple of (model_name, confidence, detection_method)
        """
        asic_model = str(device_info.get("ASICModel", "")).lower()
        asic_count = device_info.get("asicCount", 0)
        hash_rate = device_info.get("hashRate", 0)
        hostname = str(device_info.get("hostname", "")).lower()
        board_version = str(device_info.get("boardVersion", ""))
        firmware_version = str(device_info.get("version", ""))
        power = device_info.get("power", 0)
        core_count = device_info.get("smallCoreCount", 0)
        frequency = device_info.get("frequency", 0)
        
        # Check for NerdQaxe/NerdAxe variants first
        device_model = device_info.get("deviceModel")
        if device_model:
            return str(device_model), 0.95, "deviceModel field"
        
        # Handle different ASIC models
        if "bm1366" in asic_model:
            return "Bitaxe Ultra", 0.9, "ASIC model BM1366"
        
        elif "bm1368" in asic_model:
            if asic_count == 1:
                return "Bitaxe Supra", 0.9, "ASIC model BM1368 (single chip)"
            else:
                logger.warning(f"Unusual BM1368 configuration: {asic_count} ASICs")
                return "Bitaxe Supra", 0.7, f"ASIC model BM1368 ({asic_count} chips)"
        
        elif "bm1397" in asic_model:
            return "Bitaxe Gamma", 0.9, "ASIC model BM1397"
        
        elif "bm1370" in asic_model:
            # This is the complex case - need sophisticated detection
            return ImprovedBitaxeDetection._differentiate_bm1370_models(
                hash_rate, asic_count, hostname, board_version, 
                firmware_version, power, core_count, frequency
            )
        
        else:
            logger.warning(f"Unknown ASIC model: {asic_model}")
            return "Bitaxe (Unknown ASIC)", 0.5, f"Unknown ASIC: {asic_model}"
    
    @staticmethod
    def _differentiate_bm1370_models(hash_rate: float, asic_count: int, hostname: str,
                                   board_version: str, firmware_version: str, 
                                   power: float, core_count: int, frequency: int) -> Tuple[str, float, str]:
        """
        Differentiate between BM1370-based Bitaxe models (Gamma vs Hex).
        
        Uses multiple factors in priority order:
        1. Board version (most reliable)
        2. Hardware characteristics (core count, frequency)
        3. Performance characteristics (efficiency, hashrate)
        4. Firmware version patterns
        5. Hostname hints
        """
        
        detection_factors = []
        confidence_score = 0.0
        
        # Convert board version to integer for comparison
        try:
            board_ver_int = int(board_version) if board_version else 0
        except (ValueError, TypeError):
            board_ver_int = 0
        
        # Calculate efficiency if power data available
        hashrate_th = hash_rate / 1000 if hash_rate > 0 else 0
        efficiency = power / hashrate_th if hashrate_th > 0 and power > 0 else 0
        
        # FACTOR 1: Board Version Analysis (Primary - Most Reliable)
        model_from_board = None
        if board_ver_int >= 600:
            model_from_board = "Bitaxe Hex"
            confidence_score += 0.8
            detection_factors.append(f"Board v{board_version} (600+ series → Hex)")
            logger.info(f"BM1370 strongly identified as Hex via board version: {board_version}")
        
        elif 200 <= board_ver_int < 600:
            model_from_board = "Bitaxe Gamma"
            confidence_score += 0.8
            detection_factors.append(f"Board v{board_version} (200-599 series → Gamma)")
            logger.info(f"BM1370 strongly identified as Gamma via board version: {board_version}")
        
        elif board_ver_int > 0:
            # Unknown board version range
            detection_factors.append(f"Board v{board_version} (unknown range)")
            logger.warning(f"Unknown board version range for BM1370: {board_version}")
        
        # FACTOR 2: Hardware Characteristics Analysis
        if core_count > 0:
            # Based on real device data: 2040 cores observed on 602 board (likely Hex)
            if core_count >= 2000:
                if model_from_board == "Bitaxe Gamma":
                    confidence_score -= 0.1  # Conflict
                    detection_factors.append(f"High core count {core_count} conflicts with board → uncertainty")
                else:
                    confidence_score += 0.1
                    detection_factors.append(f"High core count {core_count} → suggests Hex")
                    if not model_from_board:
                        model_from_board = "Bitaxe Hex"
            
            elif core_count < 2000:
                if model_from_board == "Bitaxe Hex":
                    confidence_score -= 0.1  # Conflict
                    detection_factors.append(f"Lower core count {core_count} conflicts with board → uncertainty")
                else:
                    confidence_score += 0.1
                    detection_factors.append(f"Lower core count {core_count} → suggests Gamma")
                    if not model_from_board:
                        model_from_board = "Bitaxe Gamma"
        
        # FACTOR 3: Frequency Analysis
        if frequency > 0:
            if frequency >= 500:  # High frequency suggests newer/higher-performance model
                if model_from_board == "Bitaxe Gamma":
                    detection_factors.append(f"High frequency {frequency}MHz (unusual for Gamma)")
                else:
                    confidence_score += 0.05
                    detection_factors.append(f"High frequency {frequency}MHz → supports Hex")
                    if not model_from_board:
                        model_from_board = "Bitaxe Hex"
        
        # FACTOR 4: Performance Characteristics
        if efficiency > 0:
            if efficiency <= 22:  # More efficient suggests Hex
                if model_from_board == "Bitaxe Gamma":
                    confidence_score -= 0.1
                    detection_factors.append(f"Efficient {efficiency:.1f}W/TH conflicts with Gamma identification")
                else:
                    confidence_score += 0.1
                    detection_factors.append(f"Efficient {efficiency:.1f}W/TH → supports Hex")
                    if not model_from_board:
                        model_from_board = "Bitaxe Hex"
            
            elif efficiency > 25:  # Less efficient suggests Gamma
                if model_from_board == "Bitaxe Hex":
                    confidence_score -= 0.1
                    detection_factors.append(f"Less efficient {efficiency:.1f}W/TH conflicts with Hex identification")
                else:
                    confidence_score += 0.1
                    detection_factors.append(f"Less efficient {efficiency:.1f}W/TH → supports Gamma")
                    if not model_from_board:
                        model_from_board = "Bitaxe Gamma"
        
        # FACTOR 5: Hashrate Analysis (Lower Priority)
        if hashrate_th > 0:
            if hashrate_th >= 1.3:  # Very high hashrate
                detection_factors.append(f"Very high hashrate {hashrate_th:.2f}TH/s")
                if model_from_board == "Bitaxe Gamma":
                    confidence_score -= 0.05
                    detection_factors.append("Very high hashrate unusual for Gamma")
                else:
                    confidence_score += 0.02
            
            elif hashrate_th <= 0.6:  # Lower hashrate
                detection_factors.append(f"Moderate hashrate {hashrate_th:.2f}TH/s")
                if model_from_board == "Bitaxe Hex":
                    detection_factors.append("Moderate hashrate acceptable for both models")
        
        # FACTOR 6: Firmware Version Patterns
        if firmware_version:
            # Look for version patterns (this would need more research)
            detection_factors.append(f"Firmware {firmware_version}")
        
        # FACTOR 7: Hostname Hints (Fallback)
        if not model_from_board:
            if "gamma" in hostname:
                model_from_board = "Bitaxe Gamma"
                confidence_score += 0.6
                detection_factors.append("Hostname contains 'gamma'")
            elif "hex" in hostname:
                model_from_board = "Bitaxe Hex"
                confidence_score += 0.6
                detection_factors.append("Hostname contains 'hex'")
        
        # FINAL DECISION
        if not model_from_board:
            # Conservative fallback - Gamma is more common
            model_from_board = "Bitaxe Gamma"
            confidence_score = 0.3
            detection_factors.append("Conservative default (insufficient data)")
            logger.warning("BM1370 device lacks clear identification markers, defaulting to Gamma")
        
        # Ensure confidence is within bounds
        confidence_score = max(0.0, min(1.0, confidence_score))
        
        # Create detection method summary
        method_summary = "; ".join(detection_factors[:3])  # Top 3 factors
        if len(detection_factors) > 3:
            method_summary += f" (+{len(detection_factors)-3} more)"
        
        logger.info(f"BM1370 model determination: {model_from_board} (confidence: {confidence_score:.2f})")
        logger.debug(f"Detection factors: {detection_factors}")
        
        return model_from_board, confidence_score, method_summary


def test_improved_detection():
    """Test the improved detection with real device data."""
    
    print("🧪 TESTING IMPROVED BITAXE DETECTION")
    print("=" * 50)
    
    # Real device data from 192.168.50.85
    real_device = {
        "ASICModel": "BM1370",
        "asicCount": 1,
        "hashRate": 1008.69,
        "hostname": "bitaxe",
        "version": "v2.7.1",
        "boardVersion": "602",
        "deviceModel": None,
        "power": 20.16,
        "smallCoreCount": 2040,
        "frequency": 525
    }
    
    print(f"\n📊 Testing with real device data:")
    for key, value in real_device.items():
        print(f"   {key}: {value}")
    
    model, confidence, method = ImprovedBitaxeDetection.determine_bitaxe_model(real_device)
    
    print(f"\n🎯 DETECTION RESULT:")
    print(f"   Model: {model}")
    print(f"   Confidence: {confidence:.1%}")
    print(f"   Method: {method}")
    
    # Test with various scenarios
    test_scenarios = [
        {
            "name": "Gamma with BM1397",
            "data": {"ASICModel": "BM1397", "asicCount": 1, "hashRate": 450, "boardVersion": "300"}
        },
        {
            "name": "Supra with BM1368", 
            "data": {"ASICModel": "BM1368", "asicCount": 1, "hashRate": 15000, "boardVersion": "400"}
        },
        {
            "name": "Gamma with BM1370 (low board version)",
            "data": {"ASICModel": "BM1370", "asicCount": 1, "hashRate": 600, "boardVersion": "300", "smallCoreCount": 1500}
        },
        {
            "name": "Hex with BM1370 (high board version)",
            "data": {"ASICModel": "BM1370", "asicCount": 1, "hashRate": 1100, "boardVersion": "650", "smallCoreCount": 2100}
        }
    ]
    
    print(f"\n🔬 TESTING VARIOUS SCENARIOS:")
    
    for scenario in test_scenarios:
        print(f"\n   Scenario: {scenario['name']}")
        model, confidence, method = ImprovedBitaxeDetection.determine_bitaxe_model(scenario['data'])
        print(f"   Result: {model} ({confidence:.1%}) - {method}")


if __name__ == "__main__":
    test_improved_detection()