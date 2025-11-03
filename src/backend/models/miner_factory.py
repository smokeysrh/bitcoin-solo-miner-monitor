"""
Miner Factory

This module provides a factory for creating miner instances based on miner type.
"""

import logging
from typing import Optional, Dict, Any

from src.backend.models.miner_interface import MinerInterface
from src.backend.models.bitaxe_miner import BitaxeMiner
from src.backend.models.avalon_nano_miner import AvalonNanoMiner
from src.backend.models.magic_miner import MagicMiner
from src.backend.models.bitcoin_node import BitcoinNode
from src.backend.exceptions import (
    MinerError, MinerConnectionError, MinerConfigurationError,
    HTTPSessionError, ValidationError
)
from src.backend.utils.structured_logging import get_logger

logger = get_logger(__name__)


class MinerFactory:
    """
    Factory class for creating miner instances.
    """
    
    @staticmethod
    async def create_miner(miner_type: str, ip_address: str, port: Optional[int] = None, **kwargs) -> Optional[MinerInterface]:
        """
        Create a miner instance based on the miner type.
        
        Args:
            miner_type (str): Type of miner to create
            ip_address (str): IP address of the miner
            port (Optional[int]): Port number (if None, default port for the miner type will be used)
            **kwargs: Additional parameters for the miner constructor
            
        Returns:
            Optional[MinerInterface]: Miner instance or None if miner type is not supported
        """
        miner_type = miner_type.lower()
        
        try:
            if miner_type == "bitaxe":
                # Default port for Bitaxe is 80
                miner_port = port if port is not None else 80
                miner = BitaxeMiner(ip_address, miner_port)
            elif miner_type in ["avalon", "avalon_nano", "avalonnano"]:
                # Default port for Avalon Nano (cgminer API) is 4028
                miner_port = port if port is not None else 4028
                miner = AvalonNanoMiner(ip_address, miner_port)
            elif miner_type in ["magic", "magic_miner", "magicminer", "bg02"]:
                # Default port for Magic Miner is 80
                miner_port = port if port is not None else 80
                miner = MagicMiner(ip_address, miner_port)
            elif miner_type in ["bitcoin_node", "bitcoinnode", "node", "btc_node"]:
                # Default port for Bitcoin node RPC is 8332, but detection will try multiple ports
                miner_port = port if port is not None else 8332
                miner = BitcoinNode(ip_address, miner_port)
            else:
                raise MinerConfigurationError(f"Unsupported miner type: {miner_type}", 
                                            context={'miner_type': miner_type, 'ip_address': ip_address})
            
            # Try to connect to the miner
            connected = await miner.connect()
            if not connected:
                # Ensure cleanup if connection failed
                try:
                    await miner.disconnect()
                    # For HTTP-based miners, also cleanup any active sessions
                    if hasattr(miner, 'is_http_session_active') and miner.is_http_session_active():
                        from src.backend.services.http_session_manager import get_session_manager
                        session_manager = await get_session_manager()
                        await session_manager.close_session(ip_address, miner_port)
                except HTTPSessionError as cleanup_error:
                    logger.debug(f"HTTP session cleanup error after failed connection", {
                        'miner_type': miner_type,
                        'ip_address': ip_address,
                        'port': miner_port,
                        'cleanup_error': str(cleanup_error)
                    })
                except MinerError as cleanup_error:
                    logger.debug(f"Miner cleanup error after failed connection", {
                        'miner_type': miner_type,
                        'ip_address': ip_address,
                        'port': miner_port,
                        'cleanup_error': str(cleanup_error)
                    })
                
                raise MinerConnectionError(f"Failed to connect to {miner_type} miner", 
                                         ip_address=ip_address, 
                                         context={'port': miner_port, 'miner_type': miner_type})
            
            return miner
        except MinerError:
            # Re-raise specific miner errors
            raise
        except ValidationError:
            # Re-raise validation errors
            raise
        except (OSError, ConnectionError) as e:
            # Network-related errors
            raise MinerConnectionError(f"Network error creating miner instance for {miner_type}", 
                                     ip_address=ip_address, 
                                     context={'original_error': str(e), 'miner_type': miner_type})
        except (ValueError, TypeError) as e:
            # Data validation errors
            raise ValidationError(f"Invalid data creating miner instance for {miner_type}", 
                                context={'original_error': str(e), 'miner_type': miner_type, 'ip_address': ip_address})
        except (RuntimeError, MemoryError, SystemError) as e:
            # Handle system-level runtime errors
            try:
                if 'miner' in locals() and hasattr(miner, 'is_http_session_active'):
                    from src.backend.services.http_session_manager import get_session_manager
                    session_manager = await get_session_manager()
                    miner_port = port if port is not None else (80 if miner_type in ["bitaxe", "magic", "magic_miner", "magicminer", "bg02"] else 4028)
                    await session_manager.close_session(ip_address, miner_port)
            except HTTPSessionError as cleanup_error:
                logger.debug(f"HTTP session cleanup error after system error", {
                    'miner_type': miner_type,
                    'ip_address': ip_address,
                    'original_error': str(e),
                    'cleanup_error': str(cleanup_error)
                })
            except MinerError as cleanup_error:
                logger.debug(f"Miner cleanup error after system error", {
                    'miner_type': miner_type,
                    'ip_address': ip_address,
                    'original_error': str(e),
                    'cleanup_error': str(cleanup_error)
                })
            except (OSError, IOError) as cleanup_error:
                logger.debug(f"IO cleanup error after system error", {
                    'miner_type': miner_type,
                    'ip_address': ip_address,
                    'original_error': str(e),
                    'cleanup_error': str(cleanup_error)
                })
            
            raise MinerError(f"System error creating miner instance for {miner_type}", 
                           ip_address=ip_address, 
                           context={'original_error': str(e), 'miner_type': miner_type})
    
    @staticmethod
    async def detect_miner_type(ip_address: str, ports: Optional[list] = None) -> Dict[str, Any]:
        """
        Attempt to detect the miner type at the given IP address.
        
        Args:
            ip_address (str): IP address to check
            ports (Optional[list]): List of ports to check (if None, default ports will be checked)
            
        Returns:
            Dict[str, Any]: Dictionary containing detected miner information or empty dict if no miner detected
        """
        if ports is None:
            # Default ports to check
            ports = [80, 4028]
        
        logger.info(f"Starting detection for {ip_address} with open ports: {ports}")
        result = {}
        
        # Try Avalon Nano FIRST (port 4028 - most specific)
        if 4028 in ports:
            logger.info(f"Trying Avalon Nano detection on {ip_address}:4028")
            avalon = None
            try:
                avalon = AvalonNanoMiner(ip_address, 4028)
                connected = await avalon.connect()
                if connected:
                    device_info = await avalon.get_device_info()
                    if device_info:
                        logger.info(f"Avalon Nano detected at {ip_address}:4028")
                        await avalon.disconnect()
                        return {
                            "type": "avalon_nano",
                            "ip_address": ip_address,
                            "port": 4028,
                            "device_info": device_info
                        }
                    else:
                        logger.debug(f"Device at {ip_address}:4028 responded but is not a valid Avalon Nano")
                else:
                    logger.debug(f"Avalon Nano connection failed at {ip_address}:4028")
            except MinerConnectionError as e:
                logger.debug(f"Avalon Nano connection failed at {ip_address}:4028", {
                    'ip_address': ip_address,
                    'port': 4028,
                    'error_type': 'connection_error'
                })
            except MinerError as e:
                logger.debug(f"Avalon Nano detection failed at {ip_address}:4028", {
                    'ip_address': ip_address,
                    'port': 4028,
                    'error_type': 'miner_error'
                })
            except (RuntimeError, MemoryError) as e:
                logger.debug(f"System error during Avalon Nano detection at {ip_address}:4028", {
                    'ip_address': ip_address,
                    'port': 4028,
                    'error_type': 'system_error',
                    'error': str(e)
                })
            finally:
                # Ensure cleanup (Avalon Nano uses TCP sockets, not HTTP sessions)
                if avalon:
                    try:
                        await avalon.disconnect()
                    except MinerError as cleanup_error:
                        logger.debug(f"Miner error during Avalon Nano detection cleanup", {
                            'ip_address': ip_address,
                            'port': 4028,
                            'cleanup_error': str(cleanup_error)
                        })
                    except Exception as cleanup_error:
                        logger.debug(f"Unexpected error during Avalon Nano detection cleanup", {
                            'ip_address': ip_address,
                            'port': 4028,
                            'cleanup_error': str(cleanup_error)
                        })
        
        # Try to detect miners on port 80 (both Bitaxe and Magic Miner use this port)
        if 80 in ports:
            logger.info(f"Trying advanced detection on {ip_address}:80 (Bitaxe/Magic Miner)")
            
            # ENHANCED: Use device fingerprinting for accurate identification
            try:
                from src.backend.models.device_fingerprinting import DeviceFingerprinter, DeviceType
                
                fingerprinter = DeviceFingerprinter(ip_address, 80)
                fingerprint = await fingerprinter.fingerprint_device()
                
                if fingerprint and fingerprint.confidence >= 0.5:
                    logger.info(f"Device fingerprinting successful: {fingerprint.device_type.value} "
                               f"(confidence: {fingerprint.confidence:.2f}) at {ip_address}:80")
                    
                    # Create appropriate miner instance based on fingerprint
                    if fingerprint.device_type == DeviceType.MAGIC_MINER:
                        magic = MagicMiner(ip_address, 80)
                        try:
                            connected = await magic.connect()
                            if connected:
                                device_info = await magic.get_device_info()
                                await magic.disconnect()
                                
                                if device_info:
                                    # Enhance device_info with fingerprint data
                                    device_info.update({
                                        "fingerprint_confidence": fingerprint.confidence,
                                        "detection_method": fingerprint.detection_method
                                    })
                                    
                                    logger.info(f"Magic Miner confirmed at {ip_address}:80")
                                    return {
                                        "type": "magic_miner",
                                        "ip_address": ip_address,
                                        "port": 80,
                                        "device_info": device_info
                                    }
                        except Exception as e:
                            logger.debug(f"Magic Miner connection failed after fingerprinting: {str(e)}")
                        finally:
                            try:
                                await magic.disconnect()
                                from src.backend.services.http_session_manager import get_session_manager
                                session_manager = await get_session_manager()
                                await session_manager.close_session(ip_address, 80)
                            except:
                                pass
                    
                    elif fingerprint.device_type in [DeviceType.BITAXE, DeviceType.NERDQAXE]:
                        bitaxe = BitaxeMiner(ip_address, 80)
                        try:
                            connected = await bitaxe.connect()
                            if connected:
                                device_info = await bitaxe.get_device_info()
                                await bitaxe.disconnect()
                                
                                if device_info:
                                    # Enhance device_info with fingerprint data
                                    device_info.update({
                                        "fingerprint_confidence": fingerprint.confidence,
                                        "detection_method": fingerprint.detection_method
                                    })
                                    
                                    device_type = device_info.get("type", "Bitaxe")
                                    logger.info(f"{device_type} confirmed at {ip_address}:80")
                                    return {
                                        "type": "bitaxe",
                                        "ip_address": ip_address,
                                        "port": 80,
                                        "device_info": device_info
                                    }
                        except Exception as e:
                            logger.debug(f"Bitaxe connection failed after fingerprinting: {str(e)}")
                        finally:
                            try:
                                await bitaxe.disconnect()
                                from src.backend.services.http_session_manager import get_session_manager
                                session_manager = await get_session_manager()
                                await session_manager.close_session(ip_address, 80)
                            except:
                                pass
                
                # Fallback: If fingerprinting fails or is inconclusive, try traditional detection
                logger.debug(f"Fingerprinting inconclusive for {ip_address}:80, trying traditional detection")
                
            except Exception as e:
                logger.debug(f"Device fingerprinting failed for {ip_address}:80: {str(e)}")
            
            # FALLBACK: Traditional detection method
            bitaxe = None
            magic = None
            bitaxe_device_info = None
            magic_device_info = None
            
            # Try Bitaxe detection
            try:
                logger.debug(f"Attempting traditional Bitaxe detection on {ip_address}:80")
                bitaxe = BitaxeMiner(ip_address, 80)
                connected = await bitaxe.connect()
                if connected:
                    bitaxe_device_info = await bitaxe.get_device_info()
                    logger.debug(f"Traditional Bitaxe detection result: {bool(bitaxe_device_info)}")
            except Exception as e:
                logger.debug(f"Traditional Bitaxe detection error at {ip_address}:80: {str(e)}")
            finally:
                if bitaxe:
                    try:
                        await bitaxe.disconnect()
                        from src.backend.services.http_session_manager import get_session_manager
                        session_manager = await get_session_manager()
                        await session_manager.close_session(ip_address, 80)
                    except:
                        pass
            
            # Try Magic Miner detection
            try:
                logger.debug(f"Attempting traditional Magic Miner detection on {ip_address}:80")
                magic = MagicMiner(ip_address, 80)
                connected = await magic.connect()
                if connected:
                    magic_device_info = await magic.get_device_info()
                    logger.debug(f"Traditional Magic Miner detection result: {bool(magic_device_info)}")
            except Exception as e:
                logger.debug(f"Traditional Magic Miner detection error at {ip_address}:80: {str(e)}")
            finally:
                if magic:
                    try:
                        await magic.disconnect()
                        from src.backend.services.http_session_manager import get_session_manager
                        session_manager = await get_session_manager()
                        await session_manager.close_session(ip_address, 80)
                    except:
                        pass
            
            # Determine which traditional detection succeeded
            if magic_device_info and magic_device_info.get("type") == "Magic Miner":
                logger.info(f"Magic Miner detected via traditional method at {ip_address}:80")
                return {
                    "type": "magic_miner",
                    "ip_address": ip_address,
                    "port": 80,
                    "device_info": magic_device_info
                }
            elif bitaxe_device_info and bitaxe_device_info.get("type"):
                device_type = bitaxe_device_info.get("type")
                logger.info(f"{device_type} detected via traditional method at {ip_address}:80")
                return {
                    "type": "bitaxe",
                    "ip_address": ip_address,
                    "port": 80,
                    "device_info": bitaxe_device_info
                }
            else:
                logger.debug(f"No valid miner detected at {ip_address}:80")
        
        # Try Bitcoin Node detection (check ONLY Bitcoin-specific ports, NOT port 80)
        bitcoin_ports = [8332, 18332, 8333, 18333]
        # Check if any Bitcoin-specific ports are available
        bitcoin_ports_available = [p for p in bitcoin_ports if p in ports]
        
        if bitcoin_ports_available:
            logger.info(f"Trying Bitcoin node detection on {ip_address} with ports: {bitcoin_ports_available}")
            
            for bitcoin_port in bitcoin_ports_available:
                node = None
                try:
                    node = BitcoinNode(ip_address, bitcoin_port)
                    connected = await node.connect()
                    if connected:
                        logger.info(f"Bitcoin node connection successful on {ip_address}:{bitcoin_port}")
                        device_info = await node.get_device_info()
                        # Only return if we got valid Bitcoin node device info
                        if device_info and device_info.get("type") == "Bitcoin Node":
                            logger.info(f"Valid Bitcoin node detected on {ip_address}:{bitcoin_port}")
                            await node.disconnect()
                            return {
                                "type": "bitcoin_node",
                                "ip_address": ip_address,
                                "port": bitcoin_port,
                                "device_info": device_info
                            }
                        else:
                            logger.debug(f"Invalid device info from {ip_address}:{bitcoin_port}")
                    else:
                        logger.debug(f"Bitcoin node connection failed on {ip_address}:{bitcoin_port}")
                except MinerConnectionError as e:
                    logger.debug(f"Bitcoin node connection failed at {ip_address}:{bitcoin_port}", {
                        'ip_address': ip_address,
                        'port': bitcoin_port,
                        'error_type': 'connection_error'
                    })
                except MinerError as e:
                    logger.debug(f"Bitcoin node detection failed at {ip_address}:{bitcoin_port}", {
                        'ip_address': ip_address,
                        'port': bitcoin_port,
                        'error_type': 'miner_error'
                    })
                except (RuntimeError, MemoryError) as e:
                    logger.debug(f"System error during Bitcoin node detection at {ip_address}:{bitcoin_port}", {
                        'ip_address': ip_address,
                        'port': bitcoin_port,
                        'error_type': 'system_error',
                        'error': str(e)
                    })
                finally:
                    # Ensure cleanup
                    if node:
                        try:
                            await node.disconnect()
                            # Cleanup any active sessions
                            from src.backend.services.http_session_manager import get_session_manager
                            session_manager = await get_session_manager()
                            await session_manager.close_session(ip_address, bitcoin_port)
                        except HTTPSessionError as cleanup_error:
                            logger.debug(f"HTTP session error during Bitcoin node detection cleanup", {
                                'ip_address': ip_address,
                                'port': bitcoin_port,
                                'cleanup_error': str(cleanup_error)
                            })
                        except MinerError as cleanup_error:
                            logger.debug(f"Miner error during Bitcoin node detection cleanup", {
                                'ip_address': ip_address,
                                'port': bitcoin_port,
                                'cleanup_error': str(cleanup_error)
                            })
                        except Exception as cleanup_error:
                            logger.debug(f"Unexpected error during Bitcoin node detection cleanup", {
                                'ip_address': ip_address,
                                'port': bitcoin_port,
                                'cleanup_error': str(cleanup_error)
                            })
        else:
            logger.debug(f"No Bitcoin-specific ports available for {ip_address}")
        
        logger.info(f"All detection attempts failed for {ip_address}")
        return result