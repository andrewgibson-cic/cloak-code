#!/usr/bin/env python3
"""
Unit Tests for SafeClaude Proxy Credential Injection Logic

Tests the core security functionality of the credential injection system
without requiring actual network requests or Docker containers.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Add proxy directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../proxy'))

from inject import CredentialInjector


class TestCredentialInjectorInitialization(unittest.TestCase):
    """Test initialization and environment validation."""
    
    def setUp(self):
        """Set up test environment."""
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_initialization_with_all_credentials(self):
        """Test successful initialization with all credentials present."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-test-openai',
            'REAL_GITHUB_TOKEN': 'ghp_test_github',
            'REAL_ANTHROPIC_API_KEY': 'sk-ant-test',
            'REAL_AWS_ACCESS_KEY_ID': 'AKIA_test',
            'REAL_AWS_SECRET_ACCESS_KEY': 'secret_test',
        })
        
        injector = CredentialInjector()
        
        self.assertEqual(injector.stats['requests_processed'], 0)
        self.assertEqual(injector.stats['credentials_injected'], 0)
    
    @patch('inject.ctx')
    def test_initialization_with_missing_credentials(self, mock_ctx):
        """Test initialization warns about missing credentials."""
        os.environ.clear()
        
        injector = CredentialInjector()
        
        # Should have warned about missing credentials
        self.assertTrue(mock_ctx.log.warn.called)
        call_args = str(mock_ctx.log.warn.call_args)
        self.assertIn('Missing environment variables', call_args)


class TestHostWhitelisting(unittest.TestCase):
    """Test the critical host whitelisting security feature."""
    
    def setUp(self):
        """Set up test injector."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-real-openai-key',
            'REAL_GITHUB_TOKEN': 'ghp_real_github_token',
        })
        self.injector = CredentialInjector()
    
    def test_openai_whitelist_exact_match(self):
        """Test OpenAI credential only works for api.openai.com."""
        result = self.injector._is_host_whitelisted(
            'DUMMY_OPENAI_KEY',
            'api.openai.com'
        )
        self.assertTrue(result)
    
    def test_openai_whitelist_subdomain(self):
        """Test OpenAI credential works for subdomains."""
        result = self.injector._is_host_whitelisted(
            'DUMMY_OPENAI_KEY',
            'chat.openai.com'
        )
        self.assertTrue(result)
    
    def test_openai_whitelist_blocks_evil_domain(self):
        """Test OpenAI credential is blocked for unauthorized domains."""
        result = self.injector._is_host_whitelisted(
            'DUMMY_OPENAI_KEY',
            'evil-hacker.com'
        )
        self.assertFalse(result)
    
    def test_openai_whitelist_blocks_similar_domain(self):
        """Test credential blocked for similar-looking but different domain."""
        result = self.injector._is_host_whitelisted(
            'DUMMY_OPENAI_KEY',
            'api.openai.com.evil.com'
        )
        self.assertFalse(result)
    
    def test_github_enterprise_whitelist(self):
        """Test GitHub credential works for IBM Enterprise GitHub."""
        result = self.injector._is_host_whitelisted(
            'DUMMY_GITHUB_TOKEN',
            'github.ibm.com'
        )
        self.assertTrue(result)
    
    def test_github_public_whitelist(self):
        """Test GitHub credential works for public GitHub."""
        result = self.injector._is_host_whitelisted(
            'DUMMY_GITHUB_TOKEN',
            'api.github.com'
        )
        self.assertTrue(result)
    
    def test_cross_service_protection(self):
        """Test that credentials don't work across services."""
        # OpenAI key should not work for GitHub
        result = self.injector._is_host_whitelisted(
            'DUMMY_OPENAI_KEY',
            'api.github.com'
        )
        self.assertFalse(result)
        
        # GitHub token should not work for OpenAI
        result = self.injector._is_host_whitelisted(
            'DUMMY_GITHUB_TOKEN',
            'api.openai.com'
        )
        self.assertFalse(result)
    
    def test_case_insensitive_matching(self):
        """Test that host matching is case-insensitive."""
        result = self.injector._is_host_whitelisted(
            'DUMMY_OPENAI_KEY',
            'API.OPENAI.COM'
        )
        self.assertTrue(result)


class TestTelemetryBlocking(unittest.TestCase):
    """Test the telemetry/tracking endpoint blocking feature."""
    
    def setUp(self):
        """Set up test injector."""
        self.injector = CredentialInjector()
    
    def test_blocks_anthropic_telemetry(self):
        """Test blocking of Anthropic telemetry endpoints."""
        self.assertTrue(
            self.injector._is_telemetry_request('telemetry.anthropic.com')
        )
        self.assertTrue(
            self.injector._is_telemetry_request('analytics.anthropic.com')
        )
    
    def test_blocks_sentry(self):
        """Test blocking of Sentry error reporting."""
        self.assertTrue(
            self.injector._is_telemetry_request('sentry.io')
        )
        self.assertTrue(
            self.injector._is_telemetry_request('app.sentry.io')
        )
    
    def test_blocks_analytics_services(self):
        """Test blocking of common analytics services."""
        telemetry_hosts = [
            'segment.com',
            'mixpanel.com',
            'amplitude.com',
            'google-analytics.com',
            'googletagmanager.com',
        ]
        
        for host in telemetry_hosts:
            with self.subTest(host=host):
                self.assertTrue(
                    self.injector._is_telemetry_request(host),
                    f"Should block {host}"
                )
    
    def test_allows_legitimate_api_calls(self):
        """Test that legitimate API endpoints are not blocked."""
        legitimate_hosts = [
            'api.openai.com',
            'api.github.com',
            'api.anthropic.com',
        ]
        
        for host in legitimate_hosts:
            with self.subTest(host=host):
                self.assertFalse(
                    self.injector._is_telemetry_request(host),
                    f"Should allow {host}"
                )
    
    def test_case_insensitive_telemetry_matching(self):
        """Test telemetry blocking is case-insensitive."""
        self.assertTrue(
            self.injector._is_telemetry_request('SENTRY.IO')
        )
        self.assertTrue(
            self.injector._is_telemetry_request('Telemetry.Anthropic.Com')
        )


class TestCredentialRetrieval(unittest.TestCase):
    """Test credential retrieval from environment variables."""
    
    def setUp(self):
        """Set up test environment."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-real-openai-secret-key',
            'REAL_GITHUB_TOKEN': 'ghp_real_github_secret_token',
        })
        self.injector = CredentialInjector()
    
    def test_get_openai_credential(self):
        """Test retrieving OpenAI credential."""
        result = self.injector._get_real_credential('DUMMY_OPENAI_KEY')
        self.assertEqual(result, 'sk-real-openai-secret-key')
    
    def test_get_github_credential(self):
        """Test retrieving GitHub credential."""
        result = self.injector._get_real_credential('DUMMY_GITHUB_TOKEN')
        self.assertEqual(result, 'ghp_real_github_secret_token')
    
    def test_get_nonexistent_credential(self):
        """Test retrieving non-existent credential returns None."""
        result = self.injector._get_real_credential('DUMMY_UNKNOWN_KEY')
        self.assertIsNone(result)
    
    def test_missing_env_var_returns_none(self):
        """Test that missing environment variable returns None."""
        # Remove the credential from environment
        if 'REAL_ANTHROPIC_API_KEY' in os.environ:
            del os.environ['REAL_ANTHROPIC_API_KEY']
        
        result = self.injector._get_real_credential('DUMMY_ANTHROPIC_KEY')
        self.assertIsNone(result)


class TestHeaderInjection(unittest.TestCase):
    """Test credential injection in HTTP headers."""
    
    def setUp(self):
        """Set up test environment and mock flow."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-real-openai-key',
            'REAL_GITHUB_TOKEN': 'ghp_real_github_token',
        })
        self.injector = CredentialInjector()
        
        # Create mock flow object
        self.mock_flow = Mock()
        self.mock_flow.request = Mock()
        self.mock_flow.request.headers = {}
        self.mock_flow.request.pretty_host = 'api.openai.com'
        self.mock_flow.response = None
    
    @patch('inject.ctx')
    def test_inject_authorization_header(self, mock_ctx):
        """Test successful credential injection in Authorization header."""
        self.mock_flow.request.headers['Authorization'] = 'Bearer DUMMY_OPENAI_KEY'
        
        result = self.injector._inject_credentials_in_header(
            self.mock_flow,
            'Authorization'
        )
        
        self.assertTrue(result)
        self.assertEqual(
            self.mock_flow.request.headers['Authorization'],
            'Bearer sk-real-openai-key'
        )
        self.assertEqual(self.injector.stats['credentials_injected'], 1)
    
    @patch('inject.ctx')
    def test_inject_api_key_header(self, mock_ctx):
        """Test credential injection in X-API-Key header."""
        self.mock_flow.request.headers['X-API-Key'] = 'DUMMY_OPENAI_KEY'
        
        result = self.injector._inject_credentials_in_header(
            self.mock_flow,
            'X-API-Key'
        )
        
        self.assertTrue(result)
        self.assertEqual(
            self.mock_flow.request.headers['X-API-Key'],
            'sk-real-openai-key'
        )
    
    @patch('inject.ctx')
    def test_block_injection_to_unauthorized_host(self, mock_ctx):
        """Test that injection is blocked for unauthorized hosts."""
        self.mock_flow.request.pretty_host = 'evil-hacker.com'
        self.mock_flow.request.headers['Authorization'] = 'Bearer DUMMY_OPENAI_KEY'
        
        result = self.injector._inject_credentials_in_header(
            self.mock_flow,
            'Authorization'
        )
        
        self.assertFalse(result)
        # Should have created a 403 response
        self.assertIsNotNone(self.mock_flow.response)
        self.assertEqual(self.mock_flow.response.status_code, 403)
        self.assertEqual(self.injector.stats['requests_blocked'], 1)
    
    @patch('inject.ctx')
    def test_no_injection_when_no_dummy_token(self, mock_ctx):
        """Test no injection occurs when no dummy token is present."""
        self.mock_flow.request.headers['Authorization'] = 'Bearer sk-real-key-already'
        
        result = self.injector._inject_credentials_in_header(
            self.mock_flow,
            'Authorization'
        )
        
        self.assertFalse(result)
        # Header should remain unchanged
        self.assertEqual(
            self.mock_flow.request.headers['Authorization'],
            'Bearer sk-real-key-already'
        )
        self.assertEqual(self.injector.stats['credentials_injected'], 0)
    
    @patch('inject.ctx')
    def test_error_when_credential_not_configured(self, mock_ctx):
        """Test error response when real credential is not configured."""
        # Remove the credential
        if 'REAL_ANTHROPIC_API_KEY' in os.environ:
            del os.environ['REAL_ANTHROPIC_API_KEY']
        
        self.mock_flow.request.pretty_host = 'api.anthropic.com'
        self.mock_flow.request.headers['Authorization'] = 'Bearer DUMMY_ANTHROPIC_KEY'
        
        result = self.injector._inject_credentials_in_header(
            self.mock_flow,
            'Authorization'
        )
        
        self.assertFalse(result)
        # Should have created a 500 response
        self.assertIsNotNone(self.mock_flow.response)
        self.assertEqual(self.mock_flow.response.status_code, 500)


class TestSecurityLogging(unittest.TestCase):
    """Test that sensitive information is never logged."""
    
    def setUp(self):
        """Set up test environment."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-SUPER-SECRET-KEY-12345',
        })
        self.injector = CredentialInjector()
        
        self.mock_flow = Mock()
        self.mock_flow.request = Mock()
        self.mock_flow.request.headers = {'Authorization': 'Bearer DUMMY_OPENAI_KEY'}
        self.mock_flow.request.pretty_host = 'api.openai.com'
        self.mock_flow.response = None
    
    @patch('inject.ctx')
    def test_real_credential_not_in_logs(self, mock_ctx):
        """Test that real credentials are never written to logs."""
        self.injector._inject_credentials_in_header(
            self.mock_flow,
            'Authorization'
        )
        
        # Check all log calls
        for call in mock_ctx.log.info.call_args_list:
            call_str = str(call)
            self.assertNotIn('sk-SUPER-SECRET-KEY-12345', call_str,
                           "Real credential found in log output!")
        
        # Verify dummy token IS mentioned (for debugging)
        found_dummy = False
        for call in mock_ctx.log.info.call_args_list:
            if 'DUMMY_OPENAI_KEY' in str(call):
                found_dummy = True
        self.assertTrue(found_dummy, "Should log dummy token for audit trail")


if __name__ == '__main__':
    unittest.main()
