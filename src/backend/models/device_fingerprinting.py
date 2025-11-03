"""
Device Fingerprinting Module

This module provides advanced device fingerprinting capabilities to differentiate
between similar devices that use the same ports (e.g., Magic Miners vs Bitaxe).
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from src.backend.models.http_client_mixin import HTTPClientMixin
from src.backend.utils.structured_logging import get_logger

logger = get_logger(__name__)


class DeviceType(Enum):
    """Enumeration of supported device types."""
    BITAXE = "bitaxe"
    MAGIC_MINER = "magic_miner"
    NERDQAXE = "nerdqaxe"
    UNKNOWN = "unknown"


@dataclass
class DeviceFingerprint:
    """Container for device fingerprint data."""
    device_type: DeviceType
    confidence: float  # 0.0 to 1.0
    model: str
    characteristics: Dict[str, Any]
    detection_method: str


class DeviceFingerprinter(HTTPClientMixin):
    """
    Advanced device fingerprinting for miners on port 80.
    
    Uses multiple detection methods to differentiate between similar devices:
    1. API Response Analysis
    2. HTTP Header Analysis  
    3. Response Timing Analysis
    4. Content Structure Analysis
    """
    
    def __init__(self, ip_address: str, port: int = 80):
        """Initialize the device fingerprinter."""
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
    
    async def fingerprint_device(self) -> Optional[DeviceFingerprint]:
        """
        Perform comprehensive device fingerprinting.
        
        Returns:
            DeviceFingerprint: Device identification with confidence score
        """
        logger.info(f"Starting device fingerprinting for {self.ip_address}")
        
        # Collect multiple fingerprints
        fingerprints = []
        
        # Method 1: API System Info Analysis
        api_fingerprint = await self._fingerprint_via_api()
        if api_fingerprint:
            fingerprints.append(api_fingerprint)
        
        # Method 2: HTTP Response Analysis
        http_fingerprint = await self._fingerprint_via_http()
        if http_fingerprint:
            fingerprints.append(http_fingerprint)
        
        # Method 3: Web Interface Analysis
        web_fingerprint = await self._fingerprint_via_web()
        if web_fingerprint:
            fingerprints.append(web_fingerprint)
        
        # Method 4: Timing Analysis
        timing_fingerprint = await self._fingerprint_via_timing()
        if timing_fingerprint:
            fingerprints.append(timing_fingerprint)
        
        # Combine fingerprints and determine best match
        return self._combine_fingerprints(fingerprints)
    
    async def _fingerprint_via_api(self) -> Optional[DeviceFingerprint]:
        """Fingerprint device via API system info endpoint."""
        try:
            logger.debug(f"API fingerprinting for {self.ip_address}")
            
            # Try Bitaxe-style API
            response = await self._http_get("/api/system/info")
            if not response or not isinstance(response, dict):
                return None
            
            # Extract key characteristics
            hostname = str(response.get("hostname", "")).lower()
            asic_count = response.get("asicCount", 0)
            asic_model = str(response.get("ASICModel", "")).lower()
            hash_rate = response.get("hashRate", 0)
            version = str(response.get("version", "")).lower()
            device_model = response.get("deviceModel", None)
            
            characteristics = {
                "hostname": hostname,
                "asic_count": asic_count,
                "asic_model": asic_model,
                "hash_rate": hash_rate,
                "version": version,
                "device_model": device_model,
                "api_fields": list(response.keys())
            }
            
            # Magic Miner Detection (High Confidence)
            magic_indicators = [
                "magic" in hostname,
                "magicminer" in hostname,
                asic_count >= 9,
                (asic_count >= 9 and "bm1368" in asic_model),
                hash_rate > 5000,  # Magic Miners typically > 5 TH/s
            ]
            
            magic_score = sum(magic_indicators) / len(magic_indicators)
            
            if magic_score >= 0.6:  # 60% confidence threshold
                return DeviceFingerprint(
                    device_type=DeviceType.MAGIC_MINER,
                    confidence=magic_score,
                    model="BG02",
                    characteristics=characteristics,
                    detection_method="api_analysis"
                )
            
            # NerdQaxe Detection (High Confidence)
            if device_model and "nerd" in str(device_model).lower():
                return DeviceFingerprint(
                    device_type=DeviceType.NERDQAXE,
                    confidence=0.95,
                    model=str(device_model),
                    characteristics=characteristics,
                    detection_method="api_analysis"
                )
            
            # Bitaxe Detection (Medium Confidence)
            bitaxe_indicators = [
                "bitaxe" in hostname,
                asic_count in [1, 2, 4],  # Typical Bitaxe ASIC counts
                "bm13" in asic_model,  # BM1366, BM1368, BM1370, BM1397
                hash_rate < 5000,  # Bitaxe typically < 5 TH/s
                device_model is None,  # Standard Bitaxe doesn't have deviceModel
            ]
            
            bitaxe_score = sum(bitaxe_indicators) / len(bitaxe_indicators)
            
            if bitaxe_score >= 0.6:
                # Determine Bitaxe model
                model = self._determine_bitaxe_model_from_api(characteristics)
                return DeviceFingerprint(
                    device_type=DeviceType.BITAXE,
                    confidence=bitaxe_score,
                    model=model,
                    characteristics=characteristics,
                    detection_method="api_analysis"
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"API fingerprinting failed for {self.ip_address}: {str(e)}")
            return None
    
    async def _fingerprint_via_http(self) -> Optional[DeviceFingerprint]:
        """Fingerprint device via HTTP headers and response characteristics."""
        try:
            logger.debug(f"HTTP fingerprinting for {self.ip_address}")
            
            # Make a simple HTTP request and analyze headers
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    headers = dict(response.headers)
                    content_type = headers.get('content-type', '').lower()
                    server = headers.get('server', '').lower()
                    content_length = headers.get('content-length', '0')
                    
                    # Read a small portion of content
                    content_preview = await response.text()
                    content_preview = content_preview[:1000].lower()  # First 1KB
            
            characteristics = {
                "server_header": server,
                "content_type": content_type,
                "content_length": content_length,
                "content_preview": content_preview[:200],  # First 200 chars for logging
                "headers": headers
            }
            
            # Magic Miner HTTP characteristics
            magic_http_indicators = [
                "magic" in content_preview,
                "bg02" in content_preview,
                "<html" in content_preview and "miner" in content_preview,
                "esp32" in server or "nginx" in server,
            ]
            
            magic_http_score = sum(magic_http_indicators) / len(magic_http_indicators)
            
            if magic_http_score >= 0.5:
                return DeviceFingerprint(
                    device_type=DeviceType.MAGIC_MINER,
                    confidence=magic_http_score * 0.7,  # Lower confidence than API
                    model="BG02",
                    characteristics=characteristics,
                    detection_method="http_analysis"
                )
            
            # Bitaxe HTTP characteristics
            bitaxe_http_indicators = [
                "bitaxe" in content_preview,
                "esp32" in server,
                content_type == "application/json",
                len(content_preview) < 500,  # Bitaxe API responses are typically small
            ]
            
            bitaxe_http_score = sum(bitaxe_http_indicators) / len(bitaxe_http_indicators)
            
            if bitaxe_http_score >= 0.5:
                return DeviceFingerprint(
                    device_type=DeviceType.BITAXE,
                    confidence=bitaxe_http_score * 0.6,  # Lower confidence than API
                    model="Bitaxe",
                    characteristics=characteristics,
                    detection_method="http_analysis"
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"HTTP fingerprinting failed for {self.ip_address}: {str(e)}")
            return None
    
    async def _fingerprint_via_web(self) -> Optional[DeviceFingerprint]:
        """Fingerprint device via web interface analysis."""
        try:
            logger.debug(f"Web fingerprinting for {self.ip_address}")
            
            # Try to get the main web page
            html_content = await self._http_get_text("/")
            if not html_content:
                return None
            
            html_lower = html_content.lower()
            
            characteristics = {
                "has_html": "<html" in html_lower,
                "page_size": len(html_content),
                "title": self._extract_title(html_content),
                "forms_count": html_lower.count("<form"),
                "scripts_count": html_lower.count("<script"),
            }
            
            # Magic Miner web characteristics
            magic_web_indicators = [
                "magic miner" in html_lower,
                "bg02" in html_lower,
                characteristics["forms_count"] > 2,  # Magic Miners have config forms
                characteristics["page_size"] > 5000,  # Larger web interface
                "mining" in html_lower and "pool" in html_lower,
            ]
            
            magic_web_score = sum(magic_web_indicators) / len(magic_web_indicators)
            
            if magic_web_score >= 0.6:
                return DeviceFingerprint(
                    device_type=DeviceType.MAGIC_MINER,
                    confidence=magic_web_score * 0.8,
                    model="BG02",
                    characteristics=characteristics,
                    detection_method="web_analysis"
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Web fingerprinting failed for {self.ip_address}: {str(e)}")
            return None
    
    async def _fingerprint_via_timing(self) -> Optional[DeviceFingerprint]:
        """Fingerprint device via response timing analysis."""
        try:
            logger.debug(f"Timing fingerprinting for {self.ip_address}")
            
            # Measure response times for different endpoints
            timings = {}
            
            endpoints = ["/", "/api/system/info", "/status", "/config"]
            
            for endpoint in endpoints:
                start_time = asyncio.get_event_loop().time()
                try:
                    await asyncio.wait_for(self._http_get(endpoint), timeout=3)
                    response_time = asyncio.get_event_loop().time() - start_time
                    timings[endpoint] = response_time
                except:
                    timings[endpoint] = None
            
            characteristics = {
                "response_times": timings,
                "avg_response_time": sum(t for t in timings.values() if t is not None) / len([t for t in timings.values() if t is not None]) if any(timings.values()) else 0
            }
            
            # Magic Miners tend to be slower due to more complex web interface
            if characteristics["avg_response_time"] > 1.0:  # > 1 second average
                return DeviceFingerprint(
                    device_type=DeviceType.MAGIC_MINER,
                    confidence=0.3,  # Low confidence, just supporting evidence
                    model="BG02",
                    characteristics=characteristics,
                    detection_method="timing_analysis"
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Timing fingerprinting failed for {self.ip_address}: {str(e)}")
            return None
    
    def _combine_fingerprints(self, fingerprints: List[DeviceFingerprint]) -> Optional[DeviceFingerprint]:
        """Combine multiple fingerprints to determine the best match."""
        if not fingerprints:
            return None
        
        # Group by device type and calculate weighted confidence
        type_scores = {}
        
        for fp in fingerprints:
            device_type = fp.device_type
            if device_type not in type_scores:
                type_scores[device_type] = []
            type_scores[device_type].append(fp)
        
        # Calculate weighted scores for each device type
        best_type = None
        best_score = 0
        best_fingerprint = None
        
        for device_type, fps in type_scores.items():
            # Weight by detection method reliability
            method_weights = {
                "api_analysis": 1.0,
                "web_analysis": 0.8,
                "http_analysis": 0.6,
                "timing_analysis": 0.3
            }
            
            weighted_score = 0
            total_weight = 0
            
            for fp in fps:
                weight = method_weights.get(fp.detection_method, 0.5)
                weighted_score += fp.confidence * weight
                total_weight += weight
            
            if total_weight > 0:
                final_score = weighted_score / total_weight
                
                if final_score > best_score:
                    best_score = final_score
                    best_type = device_type
                    # Use the highest confidence fingerprint of this type
                    best_fingerprint = max(fps, key=lambda x: x.confidence)
        
        if best_fingerprint and best_score >= 0.5:  # Minimum 50% confidence
            # Update with combined confidence
            best_fingerprint.confidence = best_score
            logger.info(f"Device fingerprinting result for {self.ip_address}: {best_fingerprint.device_type.value} (confidence: {best_score:.2f})")
            return best_fingerprint
        
        logger.info(f"Device fingerprinting inconclusive for {self.ip_address}")
        return None
    
    def _determine_bitaxe_model_from_api(self, characteristics: Dict[str, Any]) -> str:
        """Determine specific Bitaxe model from API characteristics."""
        asic_model = characteristics.get("asic_model", "").lower()
        asic_count = characteristics.get("asic_count", 0)
        hash_rate = characteristics.get("hash_rate", 0)
        hostname = characteristics.get("hostname", "").lower()
        
        if "bm1366" in asic_model:
            return "Bitaxe Ultra"
        elif "bm1368" in asic_model and asic_count == 1:
            return "Bitaxe Supra"
        elif "bm1397" in asic_model:
            return "Bitaxe Gamma"
        elif "bm1370" in asic_model:
            # Use improved BM1370 differentiation logic
            return self._differentiate_bm1370_models_fingerprint(hash_rate, asic_count, hostname)
        else:
            return "Bitaxe"
    
    def _differentiate_bm1370_models_fingerprint(self, hash_rate: float, asic_count: int, hostname: str) -> str:
        """
        Differentiate between Bitaxe models that use BM1370 chips for fingerprinting.
        
        Args:
            hash_rate (float): Current hashrate in GH/s
            asic_count (int): Number of ASIC chips
            hostname (str): Device hostname
            
        Returns:
            str: Specific Bitaxe model name
        """
        hostname = hostname.lower()
        
        # Check hostname for explicit model hints
        if "gamma" in hostname:
            return "Bitaxe Gamma"
        elif "hex" in hostname:
            return "Bitaxe Hex"
        
        # Use hashrate for differentiation (if available)
        if hash_rate > 0:
            th_rate = hash_rate / 1000
            
            if th_rate >= 0.85:  # 850+ GH/s strongly suggests Hex
                return "Bitaxe Hex"
            elif th_rate >= 0.25:  # 250-849 GH/s suggests Gamma
                return "Bitaxe Gamma"
            else:
                # Very low hashrate - default to Gamma
                return "Bitaxe Gamma"
        
        # Conservative fallback - default to Gamma (more common)
        return "Bitaxe Gamma"
    
    def _extract_title(self, html_content: str) -> str:
        """Extract title from HTML content."""
        try:
            import re
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
            if title_match:
                return title_match.group(1).strip()
        except:
            pass
        return ""