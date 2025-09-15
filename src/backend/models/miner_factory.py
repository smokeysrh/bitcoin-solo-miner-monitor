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
        
        result = {}
        
        # Try Bitaxe first (HTTP API on port 80)
        if 80 in ports:
            bitaxe = None
            try:
                bitaxe = BitaxeMiner(ip_address, 80)
                connected = await bitaxe.connect()
                if connected:
                    device_info = await bitaxe.get_device_info()
                    if device_info:
                        await bitaxe.disconnect()
                        return {
                            "type": "bitaxe",
                            "ip_address": ip_address,
                            "port": 80,
                            "device_info": device_info
                        }
            except MinerConnectionError as e:
                logger.debug(f"Bitaxe connection failed at {ip_address}:80", {
                    'ip_address': ip_address,
                    'port': 80,
                    'error_type': 'connection_error'
                })
            except MinerError as e:
                logger.debug(f"Bitaxe detection failed at {ip_address}:80", {
                    'ip_address': ip_address,
                    'port': 80,
                    'error_type': 'miner_error'
                })
            except (RuntimeError, MemoryError) as e:
                logger.debug(f"System error during Bitaxe detection at {ip_address}:80", {
                    'ip_address': ip_address,
                    'port': 80,
                    'error_type': 'system_error',
                    'error': str(e)
                })
            finally:
                # Ensure cleanup
                if bitaxe:
                    try:
                        await bitaxe.disconnect()
                        # Cleanup any active sessions
                        from src.backend.services.http_session_manager import get_session_manager
                        session_manager = await get_session_manager()
                        await session_manager.close_session(ip_address, 80)
                    except HTTPSessionError as cleanup_error:
                        logger.debug(f"HTTP session error during Bitaxe detection cleanup", {
                            'ip_address': ip_address,
                            'port': 80,
                            'cleanup_error': str(cleanup_error)
                        })
                    except MinerError as cleanup_error:
                        logger.debug(f"Miner error during Bitaxe detection cleanup", {
                            'ip_address': ip_address,
                            'port': 80,
                            'cleanup_error': str(cleanup_error)
                        })
                    except Exception as cleanup_error:
                        logger.debug(f"Unexpected error during Bitaxe detection cleanup", {
                            'ip_address': ip_address,
                            'port': 80,
                            'cleanup_error': str(cleanup_error)
                        })
        
        # Try Avalon Nano (cgminer API on port 4028)
        if 4028 in ports:
            avalon = None
            try:
                avalon = AvalonNanoMiner(ip_address, 4028)
                connected = await avalon.connect()
                if connected:
                    device_info = await avalon.get_device_info()
                    if device_info:
                        await avalon.disconnect()
                        return {
                            "type": "avalon_nano",
                            "ip_address": ip_address,
                            "port": 4028,
                            "device_info": device_info
                        }
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
        
        # Try Magic Miner (Web interface on port 80)
        if 80 in ports:
            magic = None
            try:
                magic = MagicMiner(ip_address, 80)
                connected = await magic.connect()
                if connected:
                    device_info = await magic.get_device_info()
                    if device_info and device_info.get("model") == "BG02":
                        await magic.disconnect()
                        return {
                            "type": "magic_miner",
                            "ip_address": ip_address,
                            "port": 80,
                            "device_info": device_info
                        }
            except MinerConnectionError as e:
                logger.debug(f"Magic Miner connection failed at {ip_address}:80", {
                    'ip_address': ip_address,
                    'port': 80,
                    'error_type': 'connection_error'
                })
            except MinerError as e:
                logger.debug(f"Magic Miner detection failed at {ip_address}:80", {
                    'ip_address': ip_address,
                    'port': 80,
                    'error_type': 'miner_error'
                })
            except (RuntimeError, MemoryError) as e:
                logger.debug(f"System error during Magic Miner detection at {ip_address}:80", {
                    'ip_address': ip_address,
                    'port': 80,
                    'error_type': 'system_error',
                    'error': str(e)
                })
            finally:
                # Ensure cleanup
                if magic:
                    try:
                        await magic.disconnect()
                        # Cleanup any active sessions
                        from src.backend.services.http_session_manager import get_session_manager
                        session_manager = await get_session_manager()
                        await session_manager.close_session(ip_address, 80)
                    except HTTPSessionError as cleanup_error:
                        logger.debug(f"HTTP session error during Magic Miner detection cleanup", {
                            'ip_address': ip_address,
                            'port': 80,
                            'cleanup_error': str(cleanup_error)
                        })
                    except MinerError as cleanup_error:
                        logger.debug(f"Miner error during Magic Miner detection cleanup", {
                            'ip_address': ip_address,
                            'port': 80,
                            'cleanup_error': str(cleanup_error)
                        })
                    except Exception as cleanup_error:
                        logger.debug(f"Unexpected error during Magic Miner detection cleanup", {
                            'ip_address': ip_address,
                            'port': 80,
                            'cleanup_error': str(cleanup_error)
                        })
        
        return result