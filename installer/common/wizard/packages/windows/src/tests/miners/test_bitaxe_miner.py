"""
Bitaxe Miner Tests

This module provides tests for the BitaxeMiner implementation.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.tests.miners.base_miner_test import BaseMinerTest
from src.backend.models.bitaxe_miner import BitaxeMiner


class MockResponse:
    """
    Mock aiohttp response class for testing.
    """
    
    def __init__(self, data, status=200):
        self.data = data
        self.status = status
    
    async def json(self):
        return self.data
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestBitaxeMiner(BaseMinerTest):
    """
    Test class for BitaxeMiner implementation.
    """
    
    def _create_miner_instance(self):
        """
        Create a BitaxeMiner instance for testing.
        """
        return BitaxeMiner(self.test_ip, self.test_port)
    
    @patch('aiohttp.ClientSession.get')
    def test_connect_success(self, mock_get):
        """
        Test successful connection to miner.
        """
        # Mock response for system info
        mock_get.return_value = MockResponse({
            "version": "1.0.0",
            "ASICModel": "Bitaxe v2",
            "idfVersion": "4.4.3",
            "boardVersion": "2.0",
            "macAddr": "AA:BB:CC:DD:EE:FF",
            "hostname": "bitaxe",
            "asicCount": 1,
            "smallCoreCount": 4
        })
        
        # Test connect method
        result = self.loop.run_until_complete(self.miner.connect())
        
        # Verify results
        self.assertTrue(result)
        self.assertTrue(self.miner.connected)
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    def test_connect_failure(self, mock_get):
        """
        Test failed connection to miner.
        """
        # Mock response for system info
        mock_get.return_value = MockResponse({}, 500)
        
        # Test connect method
        result = self.loop.run_until_complete(self.miner.connect())
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.miner.connected)
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    def test_get_status_online(self, mock_get):
        """
        Test getting status when miner is online.
        """
        # Mock response for system info
        mock_get.return_value = MockResponse({
            "hashRate": 100.5,
            "temp": 45.2,
            "fanspeed": 80,
            "fanrpm": 3000,
            "power": 120.5,
            "voltage": 12.1,
            "current": 10.0,
            "uptimeSeconds": 3600,
            "sharesAccepted": 10,
            "sharesRejected": 1,
            "version": "1.0.0",
            "asicCount": 1,
            "frequency": 500
        })
        
        # Test get_status method
        status = self.loop.run_until_complete(self.miner.get_status())
        
        # Verify results
        self.assertTrue(status["online"])
        self.assertEqual(status["hashrate"], 100.5)
        self.assertEqual(status["temperature"], 45.2)
        self.assertEqual(status["fan_speed"], 80)
        self.assertEqual(status["power"], 120.5)
        self.assertEqual(status["shares_accepted"], 10)
        self.assertEqual(status["shares_rejected"], 1)
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    def test_get_status_offline(self, mock_get):
        """
        Test getting status when miner is offline.
        """
        # Mock response for system info
        mock_get.return_value = MockResponse({}, 500)
        
        # Test get_status method
        status = self.loop.run_until_complete(self.miner.get_status())
        
        # Verify results
        self.assertFalse(status["online"])
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    def test_get_metrics(self, mock_get):
        """
        Test getting metrics.
        """
        # Mock response for statistics
        mock_get.return_value = MockResponse({
            "hashRate": 100.5,
            "temp": 45.2,
            "power": 120.5,
            "sharesAccepted": 10,
            "sharesRejected": 1,
            "bestDiff": "1234",
            "bestSessionDiff": "5678"
        })
        
        # Test get_metrics method
        metrics = self.loop.run_until_complete(self.miner.get_metrics())
        
        # Verify results
        self.assertEqual(metrics["hashrate"], 100.5)
        self.assertEqual(metrics["temperature"], 45.2)
        self.assertEqual(metrics["power"], 120.5)
        self.assertEqual(metrics["shares"]["accepted"], 10)
        self.assertEqual(metrics["shares"]["rejected"], 1)
        self.assertEqual(metrics["best_share"]["difficulty"], "1234")
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    def test_get_device_info(self, mock_get):
        """
        Test getting device info.
        """
        # Mock response for system info
        mock_get.return_value = MockResponse({
            "version": "1.0.0",
            "ASICModel": "Bitaxe v2",
            "idfVersion": "4.4.3",
            "boardVersion": "2.0",
            "macAddr": "AA:BB:CC:DD:EE:FF",
            "hostname": "bitaxe",
            "asicCount": 1,
            "smallCoreCount": 4
        })
        
        # Test get_device_info method
        device_info = self.loop.run_until_complete(self.miner.get_device_info())
        
        # Verify results
        self.assertEqual(device_info["type"], "Bitaxe")
        self.assertEqual(device_info["model"], "Bitaxe v2")
        self.assertEqual(device_info["firmware_version"], "1.0.0")
        self.assertEqual(device_info["mac_address"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(device_info["asic_count"], 1)
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    def test_get_pool_info(self, mock_get):
        """
        Test getting pool info.
        """
        # Mock response for system info
        mock_get.return_value = MockResponse({
            "stratumURL": "stratum.example.com",
            "stratumPort": 3333,
            "stratumUser": "user.worker",
            "isUsingFallbackStratum": 0,
            "stratumDiff": 8192,
            "fallbackStratumURL": "backup.example.com",
            "fallbackStratumPort": 3333,
            "fallbackStratumUser": "user.backup"
        })
        
        # Test get_pool_info method
        pool_info = self.loop.run_until_complete(self.miner.get_pool_info())
        
        # Verify results
        self.assertEqual(len(pool_info), 2)
        self.assertEqual(pool_info[0]["url"], "stratum.example.com")
        self.assertEqual(pool_info[0]["port"], 3333)
        self.assertEqual(pool_info[0]["user"], "user.worker")
        self.assertTrue(pool_info[0]["is_active"])
        self.assertFalse(pool_info[0]["is_fallback"])
        
        self.assertEqual(pool_info[1]["url"], "backup.example.com")
        self.assertEqual(pool_info[1]["port"], 3333)
        self.assertEqual(pool_info[1]["user"], "user.backup")
        self.assertFalse(pool_info[1]["is_active"])
        self.assertTrue(pool_info[1]["is_fallback"])
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.post')
    def test_restart(self, mock_post):
        """
        Test restarting the miner.
        """
        # Mock response for restart
        mock_post.return_value = MockResponse({})
        
        # Test restart method
        result = self.loop.run_until_complete(self.miner.restart())
        
        # Verify results
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('aiohttp.ClientSession.patch')
    def test_update_settings(self, mock_patch):
        """
        Test updating miner settings.
        """
        # Mock response for update settings
        mock_patch.return_value = MockResponse({})
        
        # Test update_settings method
        settings = {
            "fanSpeed": 90,
            "frequency": 550
        }
        result = self.loop.run_until_complete(self.miner.update_settings(settings))
        
        # Verify results
        self.assertTrue(result)
        mock_patch.assert_called_once()


if __name__ == '__main__':
    unittest.main()