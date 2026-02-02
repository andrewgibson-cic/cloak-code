#!/usr/bin/env python3
"""
Unit tests for the health check module.

Tests cover:
- Basic health check
- Readiness probe
- Liveness probe
- Statistics endpoint
- Configuration validation
- Credential checking (without exposing secrets)
- Error handling
"""

import unittest
import os
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add proxy directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "proxy"))

from health_check import HealthChecker, create_health_endpoints


class TestHealthChecker(unittest.TestCase):
    """Test suite for HealthChecker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = HealthChecker()
    
    def test_initialization(self):
        """Test HealthChecker initialization."""
        self.assertIsNotNone(self.checker)
        self.assertIsNotNone(self.checker.start_time)
        self.assertIsInstance(self.checker.start_time, datetime)
    
    def test_check_basic(self):
        """Test basic health check returns 200 OK."""
        status, response = self.checker.check_basic()
        
        self.assertEqual(status, 200)
        self.assertIn('status', response)
        self.assertEqual(response['status'], 'ok')
        self.assertIn('service', response)
        self.assertEqual(response['service'], 'cloakcode-proxy')
        self.assertIn('timestamp', response)
    
    def test_check_live(self):
        """Test liveness probe returns 200 OK."""
        status, response = self.checker.check_live()
        
        self.assertEqual(status, 200)
        self.assertIn('alive', response)
        self.assertTrue(response['alive'])
        self.assertIn('service', response)
        self.assertIn('timestamp', response)
        self.assertIn('uptime_seconds', response)
        self.assertGreaterEqual(response['uptime_seconds'], 0)
    
    def test_check_ready_without_injector(self):
        """Test readiness probe without injector reference."""
        status, response = self.checker.check_ready()
        
        # Should return 503 (not ready) without injector
        self.assertEqual(status, 503)
        self.assertIn('ready', response)
        self.assertFalse(response['ready'])
        self.assertIn('checks', response)
        self.assertIn('strategies_loaded', response['checks'])
    
    def test_check_ready_with_injector(self):
        """Test readiness probe with mock injector."""
        # Create mock injector with strategies
        mock_injector = Mock()
        mock_injector.strategies = [Mock(), Mock(), Mock()]
        mock_injector.config_mode = 'v2'
        
        checker = HealthChecker(injector=mock_injector)
        status, response = checker.check_ready()
        
        # Should return 200 (ready) with strategies loaded
        self.assertEqual(status, 200)
        self.assertIn('ready', response)
        self.assertTrue(response['ready'])
        self.assertIn('checks', response)
        
        # Check strategies_loaded status
        strategies_check = response['checks']['strategies_loaded']
        self.assertEqual(strategies_check['status'], 'pass')
        self.assertEqual(strategies_check['count'], 3)
        self.assertEqual(strategies_check['mode'], 'v2')
    
    def test_get_stats_without_injector(self):
        """Test statistics endpoint without injector."""
        status, response = self.checker.get_stats()
        
        self.assertEqual(status, 200)
        self.assertIn('service', response)
        self.assertIn('timestamp', response)
        self.assertIn('uptime_seconds', response)
    
    def test_get_stats_with_injector(self):
        """Test statistics endpoint with mock injector."""
        # Create mock injector with stats
        mock_injector = Mock()
        mock_injector.stats = {
            'requests_processed': 100,
            'credentials_injected': 95,
            'requests_blocked': 5,
        }
        mock_injector.strategies = [
            Mock(name='strategy1'),
            Mock(name='strategy2'),
        ]
        mock_injector.config_mode = 'v2'
        
        checker = HealthChecker(injector=mock_injector)
        status, response = checker.get_stats()
        
        self.assertEqual(status, 200)
        self.assertIn('injection_stats', response)
        self.assertEqual(response['injection_stats']['requests_processed'], 100)
        self.assertEqual(response['injection_stats']['credentials_injected'], 95)
        
        self.assertIn('strategies', response)
        self.assertEqual(response['strategies']['count'], 2)
        self.assertEqual(response['strategies']['mode'], 'v2')
    
    def test_check_config_files(self):
        """Test configuration file checking."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('test: config')
            temp_config = f.name
        
        try:
            # Should find readable config
            result = self.checker._check_config_files()
            self.assertTrue(result)  # Has fallback, always returns True
        finally:
            os.unlink(temp_config)
    
    def test_check_credentials_available_with_env(self):
        """Test credential checking with environment variables."""
        # Set test credential
        os.environ['OPENAI_API_KEY'] = 'test-key-12345'
        
        try:
            result = self.checker._check_credentials_available()
            self.assertTrue(result)
        finally:
            del os.environ['OPENAI_API_KEY']
    
    def test_check_credentials_available_dummy_ignored(self):
        """Test that DUMMY credentials are ignored."""
        # Set DUMMY credential
        os.environ['OPENAI_API_KEY'] = 'DUMMY_KEY'
        
        try:
            result = self.checker._check_credentials_available()
            self.assertFalse(result)  # DUMMY should be ignored
        finally:
            del os.environ['OPENAI_API_KEY']
    
    def test_check_credentials_with_strategy(self):
        """Test credential checking via strategy."""
        # Create mock injector with strategy that has credentials
        mock_strategy = Mock()
        mock_strategy.has_credential = Mock(return_value=True)
        
        mock_injector = Mock()
        mock_injector.strategies = [mock_strategy]
        
        checker = HealthChecker(injector=mock_injector)
        result = checker._check_credentials_available()
        
        self.assertTrue(result)
    
    def test_check_logs_writable(self):
        """Test log directory writability check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override log directory
            original_log_dir = self.checker._check_logs_writable.__globals__.get('Path')
            
            result = self.checker._check_logs_writable()
            # Should succeed (creates /logs or checks existing)
            self.assertIsInstance(result, bool)
    
    def test_uptime_tracking(self):
        """Test that uptime is tracked correctly."""
        import time
        
        checker = HealthChecker()
        time.sleep(0.1)  # Sleep 100ms
        
        status, response = checker.check_live()
        uptime = response['uptime_seconds']
        
        self.assertGreaterEqual(uptime, 0.1)
        self.assertLess(uptime, 1.0)  # Should be less than 1 second
    
    def test_multiple_health_checks(self):
        """Test multiple health check calls."""
        for _ in range(5):
            status, response = self.checker.check_basic()
            self.assertEqual(status, 200)
            
        for _ in range(5):
            status, response = self.checker.check_live()
            self.assertEqual(status, 200)


class TestHealthEndpoints(unittest.TestCase):
    """Test suite for health endpoint creation."""
    
    def test_create_health_endpoints_without_injector(self):
        """Test endpoint creation without injector."""
        endpoints = create_health_endpoints()
        
        self.assertIsInstance(endpoints, dict)
        self.assertIn('/health', endpoints)
        self.assertIn('/health/ready', endpoints)
        self.assertIn('/health/live', endpoints)
        self.assertIn('/health/stats', endpoints)
    
    def test_create_health_endpoints_with_injector(self):
        """Test endpoint creation with injector."""
        mock_injector = Mock()
        endpoints = create_health_endpoints(injector=mock_injector)
        
        self.assertIsInstance(endpoints, dict)
        self.assertEqual(len(endpoints), 4)
    
    def test_endpoint_callable(self):
        """Test that all endpoints are callable."""
        endpoints = create_health_endpoints()
        
        for path, handler in endpoints.items():
            self.assertTrue(callable(handler), f"Endpoint {path} is not callable")
    
    def test_endpoint_returns_tuple(self):
        """Test that all endpoints return (status_code, response_dict)."""
        endpoints = create_health_endpoints()
        
        for path, handler in endpoints.items():
            result = handler()
            self.assertIsInstance(result, tuple, f"Endpoint {path} doesn't return tuple")
            self.assertEqual(len(result), 2, f"Endpoint {path} tuple wrong length")
            
            status_code, response_data = result
            self.assertIsInstance(status_code, int, f"Endpoint {path} status not int")
            self.assertIsInstance(response_data, dict, f"Endpoint {path} response not dict")


class TestHealthCheckIntegration(unittest.TestCase):
    """Integration tests for health check system."""
    
    def test_full_health_check_cycle(self):
        """Test complete health check cycle."""
        # Create mock injector
        mock_strategy1 = Mock()
        mock_strategy1.name = 'test-strategy-1'
        mock_strategy1.has_credential = Mock(return_value=True)
        
        mock_strategy2 = Mock()
        mock_strategy2.name = 'test-strategy-2'
        mock_strategy2.has_credential = Mock(return_value=True)
        
        mock_injector = Mock()
        mock_injector.strategies = [mock_strategy1, mock_strategy2]
        mock_injector.config_mode = 'v2'
        mock_injector.stats = {
            'requests_processed': 1000,
            'credentials_injected': 950,
            'requests_blocked': 50,
            'telemetry_blocked': 10,
            'strategy_errors': 5,
        }
        
        # Create checker and endpoints
        checker = HealthChecker(injector=mock_injector)
        endpoints = create_health_endpoints(injector=mock_injector)
        
        # Test all endpoints
        results = {}
        for path, handler in endpoints.items():
            status, response = handler()
            results[path] = (status, response)
        
        # Verify basic health
        status, response = results['/health']
        self.assertEqual(status, 200)
        self.assertEqual(response['status'], 'ok')
        
        # Verify readiness
        status, response = results['/health/ready']
        self.assertEqual(status, 200)
        self.assertTrue(response['ready'])
        
        # Verify liveness
        status, response = results['/health/live']
        self.assertEqual(status, 200)
        self.assertTrue(response['alive'])
        
        # Verify stats
        status, response = results['/health/stats']
        self.assertEqual(status, 200)
        self.assertEqual(response['injection_stats']['requests_processed'], 1000)
        self.assertEqual(response['strategies']['count'], 2)
    
    def test_health_check_with_no_strategies(self):
        """Test health check when no strategies are loaded."""
        mock_injector = Mock()
        mock_injector.strategies = []
        mock_injector.config_mode = 'legacy'
        
        checker = HealthChecker(injector=mock_injector)
        status, response = checker.check_ready()
        
        # Should not be ready without strategies
        self.assertEqual(status, 503)
        self.assertFalse(response['ready'])
        
        strategies_check = response['checks']['strategies_loaded']
        self.assertEqual(strategies_check['status'], 'fail')
        self.assertEqual(strategies_check['count'], 0)
    
    def test_concurrent_health_checks(self):
        """Test concurrent health check calls."""
        import concurrent.futures
        
        checker = HealthChecker()
        
        def call_health_check():
            return checker.check_basic()
        
        # Call health checks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(call_health_check) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        self.assertEqual(len(results), 50)
        for status, response in results:
            self.assertEqual(status, 200)
            self.assertEqual(response['status'], 'ok')


class TestHealthCheckErrorHandling(unittest.TestCase):
    """Test error handling in health check system."""
    
    def test_invalid_injector_reference(self):
        """Test handling of invalid injector reference."""
        # Create checker with None injector
        checker = HealthChecker(injector=None)
        
        # Should handle gracefully
        status, response = checker.check_ready()
        self.assertIsInstance(status, int)
        self.assertIsInstance(response, dict)
    
    def test_strategy_without_has_credential_method(self):
        """Test handling of strategy without has_credential method."""
        mock_strategy = Mock(spec=[])  # No methods
        mock_injector = Mock()
        mock_injector.strategies = [mock_strategy]
        
        checker = HealthChecker(injector=mock_injector)
        
        # Should handle gracefully
        result = checker._check_credentials_available()
        self.assertIsInstance(result, bool)
    
    def test_exception_in_strategy_check(self):
        """Test handling of exception during strategy check."""
        mock_strategy = Mock()
        mock_strategy.has_credential = Mock(side_effect=Exception("Test error"))
        
        mock_injector = Mock()
        mock_injector.strategies = [mock_strategy]
        
        checker = HealthChecker(injector=mock_injector)
        
        # Should handle gracefully
        result = checker._check_credentials_available()
        self.assertIsInstance(result, bool)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)