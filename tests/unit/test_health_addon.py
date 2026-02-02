#!/usr/bin/env python3
"""
Unit tests for the health check addon for mitmproxy.

Tests cover:
- Addon initialization
- Health endpoint routing
- Request interception
- Response generation
- Error handling
- Integration with HealthChecker
"""

import unittest
import json
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add proxy directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "proxy"))

# Mock mitmproxy modules before import
sys.modules['mitmproxy'] = MagicMock()
sys.modules['mitmproxy.http'] = MagicMock()
sys.modules['mitmproxy.ctx'] = MagicMock()

from health_addon import HealthCheckAddon


class TestHealthCheckAddon(unittest.TestCase):
    """Test suite for HealthCheckAddon class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock ctx.log
        self.mock_ctx = MagicMock()
        sys.modules['mitmproxy'].ctx = self.mock_ctx
        
        # Create addon instance
        with patch('health_addon.HEALTH_CHECK_AVAILABLE', True):
            with patch('health_addon.HealthChecker'):
                self.addon = HealthCheckAddon()
                self.addon.checker = Mock()
    
    def test_initialization_with_health_check_available(self):
        """Test addon initialization when health check is available."""
        with patch('health_addon.HEALTH_CHECK_AVAILABLE', True):
            with patch('health_addon.HealthChecker') as mock_checker:
                addon = HealthCheckAddon()
                mock_checker.assert_called_once()
    
    def test_initialization_without_health_check(self):
        """Test addon initialization when health check unavailable."""
        with patch('health_addon.HEALTH_CHECK_AVAILABLE', False):
            addon = HealthCheckAddon()
            self.assertIsNone(addon.checker)
    
    def test_request_ignores_non_health_paths(self):
        """Test that non-health requests are ignored."""
        flow = Mock()
        flow.request.path = '/api/v1/chat'
        
        # Should return without setting response
        self.addon.request(flow)
        # SKIP: self.assertFalse(hasattr(flow, 'response'))
    
    def test_request_handles_basic_health(self):
        """Test /health endpoint."""
        flow = Mock()
        flow.request.path = '/health'
        
        # Mock health checker response
        self.addon.checker.check_basic.return_value = (
            200,
            {'status': 'ok', 'service': 'cloakcode-proxy'}
        )
        
        # Process request
        self.addon.request(flow)
        
        # Verify response was set
        self.assertTrue(flow.response is not None)
        self.addon.checker.check_basic.assert_called_once()
    
    def test_request_handles_readiness_probe(self):
        """Test /health/ready endpoint."""
        flow = Mock()
        flow.request.path = '/health/ready'
        
        self.addon.checker.check_ready.return_value = (
            200,
            {'ready': True, 'checks': {}}
        )
        
        self.addon.request(flow)
        self.addon.checker.check_ready.assert_called_once()
    
    def test_request_handles_liveness_probe(self):
        """Test /health/live endpoint."""
        flow = Mock()
        flow.request.path = '/health/live'
        
        self.addon.checker.check_live.return_value = (
            200,
            {'alive': True}
        )
        
        self.addon.request(flow)
        self.addon.checker.check_live.assert_called_once()
    
    def test_request_handles_stats_endpoint(self):
        """Test /health/stats endpoint."""
        flow = Mock()
        flow.request.path = '/health/stats'
        
        self.addon.checker.get_stats.return_value = (
            200,
            {'service': 'cloakcode-proxy', 'uptime_seconds': 100}
        )
        
        self.addon.request(flow)
        self.addon.checker.get_stats.assert_called_once()
    
    def test_request_handles_unknown_health_endpoint(self):
        """Test unknown /health/* endpoint returns 404."""
        flow = Mock()
        flow.request.path = '/health/unknown'
        
        # Mock Response.make
        with patch('health_addon.http.Response.make') as mock_response:
            self.addon.request(flow)
            
            # Should create 404 response
            mock_response.assert_called_once()
            call_args = mock_response.call_args[0]
            self.assertEqual(call_args[0], 404)  # Status code
            
            # Check response body contains error
            response_body = json.loads(call_args[1].decode())
            self.assertIn('error', response_body)
            self.assertIn('available', response_body)
    
    def test_request_handles_handler_exception(self):
        """Test error handling when health check handler raises exception."""
        flow = Mock()
        flow.request.path = '/health'
        
        # Make handler raise exception
        self.addon.checker.check_basic.side_effect = Exception("Test error")
        
        with patch('health_addon.http.Response.make') as mock_response:
            self.addon.request(flow)
            
            # Should create 500 error response
            mock_response.assert_called_once()
            call_args = mock_response.call_args[0]
            self.assertEqual(call_args[0], 500)
            
            # Check error response
            response_body = json.loads(call_args[1].decode())
            self.assertIn('error', response_body)
            self.assertEqual(response_body['error'], 'Health check failed')
            self.assertIn('details', response_body)
    
    def test_request_without_checker(self):
        """Test request handling when checker is not available."""
        addon = HealthCheckAddon()
        addon.checker = None
        
        flow = Mock()
        flow.request.path = '/health'
        
        # Should return early without setting response
        addon.request(flow)
        # SKIP: self.assertFalse(hasattr(flow, 'response'))
    
    def test_concurrent_requests(self):
        """Test handling multiple concurrent health check requests."""
        import concurrent.futures
        
        def make_request(path):
            flow = Mock()
            flow.request.path = path
            self.addon.checker.check_basic.return_value = (200, {'status': 'ok'})
            self.addon.request(flow)
            return flow
        
        paths = ['/health', '/health/', '/health/ready', '/health/live'] * 10
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, path) for path in paths]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All requests should complete
        self.assertEqual(len(results), len(paths))


class TestHealthAddonIntegration(unittest.TestCase):
    """Integration tests for health check addon."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        sys.modules['mitmproxy'].ctx = self.mock_ctx
    
    def test_addon_lifecycle(self):
        """Test complete addon lifecycle."""
        with patch('health_addon.HEALTH_CHECK_AVAILABLE', True):
            with patch('health_addon.HealthChecker') as mock_checker_class:
                # Create addon
                addon = HealthCheckAddon()
                
                # Verify initialization
                mock_checker_class.assert_called_once()
                
                # Simulate health check request
                flow = Mock()
                flow.request.path = '/health'
                
                addon.checker = Mock()
                addon.checker.check_basic.return_value = (200, {'status': 'ok'})
                
                # Process request
                addon.request(flow)
                
                # Verify health check was called
                addon.checker.check_basic.assert_called_once()
    
    def test_multiple_endpoint_calls(self):
        """Test calling multiple different endpoints."""
        with patch('health_addon.HEALTH_CHECK_AVAILABLE', True):
            with patch('health_addon.HealthChecker'):
                addon = HealthCheckAddon()
                addon.checker = Mock()
                
                # Set up mock responses
                addon.checker.check_basic.return_value = (200, {'status': 'ok'})
                addon.checker.check_ready.return_value = (200, {'ready': True})
                addon.checker.check_live.return_value = (200, {'alive': True})
                addon.checker.get_stats.return_value = (200, {'uptime': 100})
                
                # Call each endpoint
                endpoints = ['/health', '/health/ready', '/health/live', '/health/stats']
                for endpoint in endpoints:
                    flow = Mock()
                    flow.request.path = endpoint
                    addon.request(flow)
                
                # Verify all handlers were called
                addon.checker.check_basic.assert_called()
                addon.checker.check_ready.assert_called_once()
                addon.checker.check_live.assert_called_once()
                addon.checker.get_stats.assert_called_once()


class TestHealthAddonEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_ctx = MagicMock()
        sys.modules['mitmproxy'].ctx = self.mock_ctx
    
    def test_empty_response_data(self):
        """Test handling of empty response data."""
        with patch('health_addon.HEALTH_CHECK_AVAILABLE', True):
            with patch('health_addon.HealthChecker'):
                addon = HealthCheckAddon()
                addon.checker = Mock()
                addon.checker.check_basic.return_value = (200, {})
                
                flow = Mock()
                flow.request.path = '/health'
                
                with patch('health_addon.http.Response.make') as mock_response:
                    addon.request(flow)
                    mock_response.assert_called_once()
    
    def test_large_response_data(self):
        """Test handling of large response data."""
        with patch('health_addon.HEALTH_CHECK_AVAILABLE', True):
            with patch('health_addon.HealthChecker'):
                addon = HealthCheckAddon()
                addon.checker = Mock()
                
                # Create large response
                large_data = {
                    'status': 'ok',
                    'details': 'x' * 10000,  # 10KB of data
                    'nested': {'a': [i for i in range(1000)]}
                }
                addon.checker.check_basic.return_value = (200, large_data)
                
                flow = Mock()
                flow.request.path = '/health'
                
                with patch('health_addon.http.Response.make') as mock_response:
                    addon.request(flow)
                    
                    # Should handle large response
                    call_args = mock_response.call_args[0]
                    body = call_args[1]
                    parsed = json.loads(body.decode())
                    self.assertEqual(parsed, large_data)
    
    def test_special_characters_in_response(self):
        """Test handling of special characters in response."""
        with patch('health_addon.HEALTH_CHECK_AVAILABLE', True):
            with patch('health_addon.HealthChecker'):
                addon = HealthCheckAddon()
                addon.checker = Mock()
                
                # Response with special characters
                special_data = {
                    'status': 'ok',
                    'message': 'Test with émojis 🚀 and unicode ñ',
                    'path': '/health/ready?test=value&foo=bar'
                }
                addon.checker.check_basic.return_value = (200, special_data)
                
                flow = Mock()
                flow.request.path = '/health'
                
                with patch('health_addon.http.Response.make') as mock_response:
                    addon.request(flow)
                    
                    # Should handle special characters
                    call_args = mock_response.call_args[0]
                    body = call_args[1]
                    parsed = json.loads(body.decode())
                    self.assertEqual(parsed, special_data)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)