"""
Magic Miner Tests

This module provides tests for the MagicMiner implementation.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
import re

from src.tests.miners.base_miner_test import BaseMinerTest
from src.backend.models.magic_miner import MagicMiner


class MockResponse:
    """
    Mock aiohttp response class for testing.
    """
    
    def __init__(self, text, status=200):
        self.text = text
        self.status = status
    
    async def text(self):
        return self.text
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestMagicMiner(BaseMinerTest):
    """
    Test class for MagicMiner implementation.
    """
    
    def _create_miner_instance(self):
        """
        Create a MagicMiner instance for testing.
        """
        return MagicMiner(self.test_ip, self.test_port)
    
    @patch('aiohttp.ClientSession.get')
    def test_connect_success(self, mock_get):
        """
        Test successful connection to miner.
        """
        # Mock response for index page
        mock_get.return_value = MockResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>BG02 Miner</title>
        </head>
        <body>
            <div class="header">
                <h1>BG02 Bitcoin Miner</h1>
                <p>Firmware Version: 0.1.0</p>
            </div>
        </body>
        </html>
        """)
        
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
        # Mock response for index page
        mock_get.return_value = MockResponse("", 500)
        
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
        # Mock response for status page
        mock_get.return_value = MockResponse("""
        <!DOCTYPE html>
        <html>
        <body>
            <div class="status-container">
                <div class="status-item">
                    <span class="label">Status:</span>
                    <span class="value">Mining</span>
                </div>
                <div class="status-item">
                    <span class="label">Hashrate:</span>
                    <span class="value">100.5 GH/s</span>
                </div>
                <div class="status-item">
                    <span class="label">Temperature:</span>
                    <span class="value">45.2°C</span>
                </div>
                <div class="status-item">
                    <span class="label">Fan Speed:</span>
                    <span class="value">80%</span>
                </div>
                <div class="status-item">
                    <span class="label">Power:</span>
                    <span class="value">120.5W</span>
                </div>
                <div class="status-item">
                    <span class="label">Uptime:</span>
                    <span class="value">1d 0h 0m</span>
                </div>
                <div class="status-item">
                    <span class="label">Accepted Shares:</span>
                    <span class="value">10</span>
                </div>
                <div class="status-item">
                    <span class="label">Rejected Shares:</span>
                    <span class="value">1</span>
                </div>
            </div>
        </body>
        </html>
        """)
        
        # Test get_status method
        status = self.loop.run_until_complete(self.miner.get_status())
        
        # Verify results
        self.assertTrue(status["online"])
        self.assertEqual(status["status"], "Mining")
        self.assertEqual(status["hashrate"], 100.5)
        self.assertEqual(status["temperature"], 45.2)
        self.assertEqual(status["fan_speed"], 80)
        self.assertEqual(status["power"], 120.5)
        self.assertEqual(status["uptime"], 86400)  # 1 day in seconds
        self.assertEqual(status["shares_accepted"], 10)
        self.assertEqual(status["shares_rejected"], 1)
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    def test_get_status_offline(self, mock_get):
        """
        Test getting status when miner is offline.
        """
        # Mock response for status page
        mock_get.return_value = MockResponse("", 500)
        
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
        # Mock response for metrics page
        mock_get.return_value = MockResponse("""
        <!DOCTYPE html>
        <html>
        <body>
            <div class="metrics-container">
                <div class="metric-item">
                    <span class="label">Hashrate (5s):</span>
                    <span class="value">100.5 GH/s</span>
                </div>
                <div class="metric-item">
                    <span class="label">Hashrate (avg):</span>
                    <span class="value">98.7 GH/s</span>
                </div>
                <div class="metric-item">
                    <span class="label">Temperature:</span>
                    <span class="value">45.2°C</span>
                </div>
                <div class="metric-item">
                    <span class="label">Power:</span>
                    <span class="value">120.5W</span>
                </div>
                <div class="metric-item">
                    <span class="label">Efficiency:</span>
                    <span class="value">0.82 J/GH</span>
                </div>
                <div class="metric-item">
                    <span class="label">Accepted:</span>
                    <span class="value">10</span>
                </div>
                <div class="metric-item">
                    <span class="label">Rejected:</span>
                    <span class="value">1</span>
                </div>
                <div class="metric-item">
                    <span class="label">Best Share:</span>
                    <span class="value">1234</span>
                </div>
            </div>
        </body>
        </html>
        """)
        
        # Test get_metrics method
        metrics = self.loop.run_until_complete(self.miner.get_metrics())
        
        # Verify results
        self.assertEqual(metrics["hashrate"], 100.5)
        self.assertEqual(metrics["hashrate_average"], 98.7)
        self.assertEqual(metrics["temperature"], 45.2)
        self.assertEqual(metrics["power"], 120.5)
        self.assertEqual(metrics["efficiency"], 0.82)
        self.assertEqual(metrics["shares"]["accepted"], 10)
        self.assertEqual(metrics["shares"]["rejected"], 1)
        self.assertEqual(metrics["best_share"], 1234)
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    def test_get_device_info(self, mock_get):
        """
        Test getting device info.
        """
        # Mock response for info page
        mock_get.return_value = MockResponse("""
        <!DOCTYPE html>
        <html>
        <body>
            <div class="info-container">
                <div class="info-item">
                    <span class="label">Model:</span>
                    <span class="value">BG02</span>
                </div>
                <div class="info-item">
                    <span class="label">Firmware Version:</span>
                    <span class="value">0.1.0</span>
                </div>
                <div class="info-item">
                    <span class="label">Serial Number:</span>
                    <span class="value">BG02123456</span>
                </div>
                <div class="info-item">
                    <span class="label">MAC Address:</span>
                    <span class="value">AA:BB:CC:DD:EE:FF</span>
                </div>
                <div class="info-item">
                    <span class="label">Hostname:</span>
                    <span class="value">magic-miner</span>
                </div>
            </div>
        </body>
        </html>
        """)
        
        # Test get_device_info method
        device_info = self.loop.run_until_complete(self.miner.get_device_info())
        
        # Verify results
        self.assertEqual(device_info["type"], "Magic Miner")
        self.assertEqual(device_info["model"], "BG02")
        self.assertEqual(device_info["firmware_version"], "0.1.0")
        self.assertEqual(device_info["serial_number"], "BG02123456")
        self.assertEqual(device_info["mac_address"], "AA:BB:CC:DD:EE:FF")
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.get')
    def test_get_pool_info(self, mock_get):
        """
        Test getting pool info.
        """
        # Mock response for pool page
        mock_get.return_value = MockResponse("""
        <!DOCTYPE html>
        <html>
        <body>
            <div class="pool-container">
                <div class="pool-item active">
                    <div class="pool-header">Primary Pool (Active)</div>
                    <div class="pool-content">
                        <div class="pool-row">
                            <span class="label">URL:</span>
                            <span class="value">stratum.example.com</span>
                        </div>
                        <div class="pool-row">
                            <span class="label">Port:</span>
                            <span class="value">3333</span>
                        </div>
                        <div class="pool-row">
                            <span class="label">User:</span>
                            <span class="value">user.worker</span>
                        </div>
                        <div class="pool-row">
                            <span class="label">Status:</span>
                            <span class="value">Connected</span>
                        </div>
                    </div>
                </div>
                <div class="pool-item">
                    <div class="pool-header">Backup Pool</div>
                    <div class="pool-content">
                        <div class="pool-row">
                            <span class="label">URL:</span>
                            <span class="value">backup.example.com</span>
                        </div>
                        <div class="pool-row">
                            <span class="label">Port:</span>
                            <span class="value">3333</span>
                        </div>
                        <div class="pool-row">
                            <span class="label">User:</span>
                            <span class="value">user.backup</span>
                        </div>
                        <div class="pool-row">
                            <span class="label">Status:</span>
                            <span class="value">Standby</span>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)
        
        # Test get_pool_info method
        pool_info = self.loop.run_until_complete(self.miner.get_pool_info())
        
        # Verify results
        self.assertEqual(len(pool_info), 2)
        self.assertEqual(pool_info[0]["url"], "stratum.example.com")
        self.assertEqual(pool_info[0]["port"], 3333)
        self.assertEqual(pool_info[0]["user"], "user.worker")
        self.assertEqual(pool_info[0]["status"], "Connected")
        self.assertTrue(pool_info[0]["active"])
        
        self.assertEqual(pool_info[1]["url"], "backup.example.com")
        self.assertEqual(pool_info[1]["port"], 3333)
        self.assertEqual(pool_info[1]["user"], "user.backup")
        self.assertEqual(pool_info[1]["status"], "Standby")
        self.assertFalse(pool_info[1]["active"])
        mock_get.assert_called_once()
    
    @patch('aiohttp.ClientSession.post')
    def test_restart(self, mock_post):
        """
        Test restarting the miner.
        """
        # Mock response for restart
        mock_post.return_value = MockResponse("Restart initiated")
        
        # Test restart method
        result = self.loop.run_until_complete(self.miner.restart())
        
        # Verify results
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('aiohttp.ClientSession.post')
    def test_update_settings(self, mock_post):
        """
        Test updating miner settings.
        """
        # Mock response for update settings
        mock_post.return_value = MockResponse("Settings updated")
        
        # Test update_settings method
        settings = {
            "fan_speed": 90,
            "frequency": 550
        }
        result = self.loop.run_until_complete(self.miner.update_settings(settings))
        
        # Verify results
        self.assertTrue(result)
        mock_post.assert_called_once()


if __name__ == '__main__':
    unittest.main()