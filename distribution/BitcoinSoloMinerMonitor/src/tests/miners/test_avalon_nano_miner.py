"""
Avalon Nano Miner Tests

This module provides tests for the AvalonNanoMiner implementation.
"""

import unittest
import asyncio
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.tests.miners.base_miner_test import BaseMinerTest
from src.backend.models.avalon_nano_miner import AvalonNanoMiner


class MockSocketResponse:
    """
    Mock socket response for testing.
    """
    def __init__(self, data):
        self.data = data
        
    def encode(self):
        return json.dumps(self.data).encode()


class TestAvalonNanoMiner(BaseMinerTest):
    """
    Test class for AvalonNanoMiner implementation.
    """
    
    def setUp(self):
        """
        Set up test environment.
        """
        super().setUp()
        self.test_port = 4028  # Default port for cgminer API
    
    def _create_miner_instance(self):
        """
        Create an AvalonNanoMiner instance for testing.
        """
        return AvalonNanoMiner(self.test_ip, self.test_port)
    
    @patch('socket.socket')
    def test_connect_success(self, mock_socket):
        """
        Test successful connection to miner.
        """
        # Mock socket instance
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # Mock socket response for version command
        mock_socket_instance.recv.return_value = json.dumps({
            "STATUS": [
                {
                    "STATUS": "S",
                    "When": 1629123456,
                    "Code": 22,
                    "Msg": "CGMiner version",
                    "Description": "cgminer 4.10.0"
                }
            ],
            "VERSION": [
                {
                    "CGMiner": "4.10.0",
                    "API": "3.1",
                    "Miner": "Avalon Nano",
                    "CompileTime": "2021-08-01 12:00:00",
                    "Type": "CGMiner"
                }
            ],
            "id": 1
        }).encode()
        
        # Test connect method
        result = self.loop.run_until_complete(self.miner.connect())
        
        # Verify results
        self.assertTrue(result)
        mock_socket_instance.connect.assert_called_once()
        mock_socket_instance.send.assert_called_once()
        mock_socket_instance.recv.assert_called_once()
    
    @patch('socket.socket')
    def test_connect_failure(self, mock_socket):
        """
        Test failed connection to miner.
        """
        # Mock socket instance
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # Mock socket connection error
        mock_socket_instance.connect.side_effect = ConnectionRefusedError()
        
        # Test connect method
        result = self.loop.run_until_complete(self.miner.connect())
        
        # Verify results
        self.assertFalse(result)
        mock_socket_instance.connect.assert_called_once()
    
    @patch('src.backend.models.avalon_nano_miner.AvalonNanoMiner._send_command')
    def test_get_status_online(self, mock_send_command):
        """
        Test getting status when miner is online.
        """
        # Mock response for summary command
        mock_send_command.return_value = {
            "STATUS": [
                {
                    "STATUS": "S",
                    "When": 1629123456,
                    "Code": 11,
                    "Msg": "Summary",
                    "Description": "cgminer 4.10.0"
                }
            ],
            "SUMMARY": [
                {
                    "Elapsed": 3600,
                    "GHS 5s": 100.5,
                    "GHS av": 98.7,
                    "Found Blocks": 0,
                    "Getworks": 100,
                    "Accepted": 10,
                    "Rejected": 1,
                    "Hardware Errors": 0,
                    "Utility": 0.1,
                    "Discarded": 0,
                    "Stale": 0,
                    "Get Failures": 0,
                    "Local Work": 100,
                    "Remote Failures": 0,
                    "Network Blocks": 5,
                    "Total MH": 360000,
                    "Work Utility": 0.1,
                    "Difficulty Accepted": 10240,
                    "Difficulty Rejected": 1024,
                    "Difficulty Stale": 0,
                    "Best Share": 12345,
                    "Device Hardware%": 0.0,
                    "Device Rejected%": 9.09,
                    "Pool Rejected%": 9.09,
                    "Pool Stale%": 0.0,
                    "Last getwork": 1629123456
                }
            ],
            "id": 1
        }
        
        # Test get_status method
        status = self.loop.run_until_complete(self.miner.get_status())
        
        # Verify results
        self.assertTrue(status["online"])
        self.assertEqual(status["hashrate"], 100.5)
        self.assertEqual(status["uptime"], 3600)
        self.assertEqual(status["accepted"], 10)
        self.assertEqual(status["rejected"], 1)
        self.assertEqual(status["hardware_errors"], 0)
        mock_send_command.assert_called_once_with("summary")
    
    @patch('src.backend.models.avalon_nano_miner.AvalonNanoMiner._send_command')
    def test_get_status_offline(self, mock_send_command):
        """
        Test getting status when miner is offline.
        """
        # Mock response for summary command
        mock_send_command.side_effect = Exception("Connection error")
        
        # Test get_status method
        status = self.loop.run_until_complete(self.miner.get_status())
        
        # Verify results
        self.assertFalse(status["online"])
        mock_send_command.assert_called_once_with("summary")
    
    @patch('src.backend.models.avalon_nano_miner.AvalonNanoMiner._send_command')
    def test_get_metrics(self, mock_send_command):
        """
        Test getting metrics.
        """
        # Mock responses for commands
        def mock_response(command):
            if command == "summary":
                return {
                    "SUMMARY": [
                        {
                            "GHS 5s": 100.5,
                            "GHS av": 98.7,
                            "Accepted": 10,
                            "Rejected": 1,
                            "Hardware Errors": 0,
                            "Utility": 0.1,
                            "Best Share": 12345
                        }
                    ]
                }
            elif command == "stats":
                return {
                    "STATS": [
                        {
                            "temp1": 45.2,
                            "temp_avg": 44.8,
                            "temp_max": 46.5,
                            "power": 120.5,
                            "voltage": 12.1,
                            "frequency": 500
                        }
                    ]
                }
            return {}
        
        mock_send_command.side_effect = mock_response
        
        # Test get_metrics method
        metrics = self.loop.run_until_complete(self.miner.get_metrics())
        
        # Verify results
        self.assertEqual(metrics["hashrate"], 100.5)
        self.assertEqual(metrics["hashrate_average"], 98.7)
        self.assertEqual(metrics["temperature"], 45.2)
        self.assertEqual(metrics["temperature_average"], 44.8)
        self.assertEqual(metrics["temperature_max"], 46.5)
        self.assertEqual(metrics["power"], 120.5)
        self.assertEqual(metrics["shares"]["accepted"], 10)
        self.assertEqual(metrics["shares"]["rejected"], 1)
        self.assertEqual(metrics["shares"]["hardware_errors"], 0)
        self.assertEqual(metrics["best_share"], 12345)
        self.assertEqual(mock_send_command.call_count, 2)
    
    @patch('src.backend.models.avalon_nano_miner.AvalonNanoMiner._send_command')
    def test_get_device_info(self, mock_send_command):
        """
        Test getting device info.
        """
        # Mock response for version command
        mock_send_command.return_value = {
            "VERSION": [
                {
                    "CGMiner": "4.10.0",
                    "API": "3.1",
                    "Miner": "Avalon Nano",
                    "CompileTime": "2021-08-01 12:00:00",
                    "Type": "CGMiner"
                }
            ]
        }
        
        # Test get_device_info method
        device_info = self.loop.run_until_complete(self.miner.get_device_info())
        
        # Verify results
        self.assertEqual(device_info["type"], "Avalon Nano")
        self.assertEqual(device_info["model"], "Avalon Nano")
        self.assertEqual(device_info["firmware_version"], "4.10.0")
        self.assertEqual(device_info["api_version"], "3.1")
        mock_send_command.assert_called_once_with("version")
    
    @patch('src.backend.models.avalon_nano_miner.AvalonNanoMiner._send_command')
    def test_get_pool_info(self, mock_send_command):
        """
        Test getting pool info.
        """
        # Mock response for pools command
        mock_send_command.return_value = {
            "POOLS": [
                {
                    "POOL": 0,
                    "URL": "stratum+tcp://stratum.example.com:3333",
                    "Status": "Alive",
                    "Priority": 0,
                    "Quota": 1,
                    "Long Poll": "N",
                    "Getworks": 100,
                    "Accepted": 10,
                    "Rejected": 1,
                    "Works": 100,
                    "Discarded": 0,
                    "Stale": 0,
                    "Get Failures": 0,
                    "Remote Failures": 0,
                    "User": "user.worker",
                    "Last Share Time": 1629123456,
                    "Diff1 Shares": 0,
                    "Proxy Type": "",
                    "Proxy": "",
                    "Difficulty Accepted": 10240,
                    "Difficulty Rejected": 1024,
                    "Difficulty Stale": 0,
                    "Last Share Difficulty": 1024,
                    "Work Difficulty": 1024,
                    "Has Stratum": True,
                    "Stratum Active": True,
                    "Stratum URL": "stratum.example.com",
                    "Stratum Difficulty": 1024,
                    "Has GBT": False,
                    "Best Share": 12345,
                    "Pool Rejected%": 9.09,
                    "Pool Stale%": 0.0
                },
                {
                    "POOL": 1,
                    "URL": "stratum+tcp://backup.example.com:3333",
                    "Status": "Alive",
                    "Priority": 1,
                    "Quota": 1,
                    "Long Poll": "N",
                    "Getworks": 0,
                    "Accepted": 0,
                    "Rejected": 0,
                    "Works": 0,
                    "Discarded": 0,
                    "Stale": 0,
                    "Get Failures": 0,
                    "Remote Failures": 0,
                    "User": "user.backup",
                    "Last Share Time": 0,
                    "Diff1 Shares": 0,
                    "Proxy Type": "",
                    "Proxy": "",
                    "Difficulty Accepted": 0,
                    "Difficulty Rejected": 0,
                    "Difficulty Stale": 0,
                    "Last Share Difficulty": 0,
                    "Work Difficulty": 1024,
                    "Has Stratum": True,
                    "Stratum Active": False,
                    "Stratum URL": "backup.example.com",
                    "Stratum Difficulty": 1024,
                    "Has GBT": False,
                    "Best Share": 0,
                    "Pool Rejected%": 0.0,
                    "Pool Stale%": 0.0
                }
            ]
        }
        
        # Test get_pool_info method
        pool_info = self.loop.run_until_complete(self.miner.get_pool_info())
        
        # Verify results
        self.assertEqual(len(pool_info), 2)
        self.assertEqual(pool_info[0]["url"], "stratum+tcp://stratum.example.com:3333")
        self.assertEqual(pool_info[0]["status"], "Alive")
        self.assertEqual(pool_info[0]["user"], "user.worker")
        self.assertTrue(pool_info[0]["active"])
        self.assertEqual(pool_info[0]["priority"], 0)
        
        self.assertEqual(pool_info[1]["url"], "stratum+tcp://backup.example.com:3333")
        self.assertEqual(pool_info[1]["status"], "Alive")
        self.assertEqual(pool_info[1]["user"], "user.backup")
        self.assertFalse(pool_info[1]["active"])
        self.assertEqual(pool_info[1]["priority"], 1)
        mock_send_command.assert_called_once_with("pools")
    
    @patch('src.backend.models.avalon_nano_miner.AvalonNanoMiner._send_command')
    def test_restart(self, mock_send_command):
        """
        Test restarting the miner.
        """
        # Mock response for restart command
        mock_send_command.return_value = {
            "STATUS": [
                {
                    "STATUS": "S",
                    "When": 1629123456,
                    "Code": 42,
                    "Msg": "Restart",
                    "Description": "cgminer restart"
                }
            ],
            "id": 1
        }
        
        # Test restart method
        result = self.loop.run_until_complete(self.miner.restart())
        
        # Verify results
        self.assertTrue(result)
        mock_send_command.assert_called_once_with("restart")
    
    @patch('src.backend.models.avalon_nano_miner.AvalonNanoMiner._send_command')
    def test_update_settings(self, mock_send_command):
        """
        Test updating miner settings.
        """
        # Mock responses for commands
        def mock_response(command):
            if command.startswith("setfan"):
                return {
                    "STATUS": [
                        {
                            "STATUS": "S",
                            "When": 1629123456,
                            "Code": 69,
                            "Msg": "Set fan succeeded",
                            "Description": "cgminer set fan"
                        }
                    ]
                }
            elif command.startswith("setfreq"):
                return {
                    "STATUS": [
                        {
                            "STATUS": "S",
                            "When": 1629123456,
                            "Code": 70,
                            "Msg": "Set frequency succeeded",
                            "Description": "cgminer set frequency"
                        }
                    ]
                }
            return {}
        
        mock_send_command.side_effect = mock_response
        
        # Test update_settings method
        settings = {
            "fan_speed": 90,
            "frequency": 550
        }
        result = self.loop.run_until_complete(self.miner.update_settings(settings))
        
        # Verify results
        self.assertTrue(result)
        self.assertEqual(mock_send_command.call_count, 2)


if __name__ == '__main__':
    unittest.main()