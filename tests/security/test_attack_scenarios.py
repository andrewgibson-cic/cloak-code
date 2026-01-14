#!/usr/bin/env python3
"""
Security Penetration Tests for SafeClaude

Tests various attack scenarios to validate the security model,
including credential exfiltration attempts, prompt injection,
and bypass techniques.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../proxy'))
from inject import CredentialInjector


class TestCredentialExfiltrationAttempts(unittest.TestCase):
    """
    Test Risk R-04: Prompt Injection (Exfiltration)
    Simulate an attacker trying to exfiltrate credentials to unauthorized hosts.
    """
    
    def setUp(self):
        """Set up test environment with real credentials."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-SENSITIVE-KEY-DO-NOT-LEAK',
            'REAL_GITHUB_TOKEN': 'ghp_SENSITIVE-TOKEN-DO-NOT-LEAK',
        })
        self.injector = CredentialInjector()
    
    @patch('inject.ctx')
    def test_exfiltration_to_attacker_domain(self, mock_ctx):
        """Test: Agent tries to send OpenAI key to attacker's server."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {
            'Authorization': 'Bearer DUMMY_OPENAI_KEY'
        }
        mock_flow.request.pretty_host = 'attacker.evil.com'
        mock_flow.response = None
        
        # Attempt injection
        result = self.injector._inject_credentials_in_header(
            mock_flow,
            'Authorization'
        )
        
        # Should be blocked
        self.assertFalse(result, "Exfiltration attempt should be blocked")
        self.assertIsNotNone(mock_flow.response, "Should return error response")
        self.assertEqual(mock_flow.response.status_code, 403)
        
        # Verify statistics
        self.assertEqual(self.injector.stats['requests_blocked'], 1)
        self.assertEqual(self.injector.stats['credentials_injected'], 0)
        
        # Verify warning was logged
        self.assertTrue(mock_ctx.log.warn.called)
        warning_msg = str(mock_ctx.log.warn.call_args)
        self.assertIn('SECURITY', warning_msg)
        self.assertIn('unauthorized host', warning_msg.lower())
    
    @patch('inject.ctx')
    def test_exfiltration_via_subdomain_spoofing(self, mock_ctx):
        """Test: Attacker uses openai.com.evil.com to bypass whitelist."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {
            'Authorization': 'Bearer DUMMY_OPENAI_KEY'
        }
        # Attempt subdomain spoofing
        mock_flow.request.pretty_host = 'api.openai.com.evil-domain.com'
        mock_flow.response = None
        
        result = self.injector._inject_credentials_in_header(
            mock_flow,
            'Authorization'
        )
        
        # Should be blocked - our whitelist checks for proper domain ending
        self.assertFalse(result)
        self.assertEqual(mock_flow.response.status_code, 403)
    
    @patch('inject.ctx')
    def test_exfiltration_via_homograph_attack(self, mock_ctx):
        """Test: Attacker uses unicode lookalike characters (homograph)."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {
            'Authorization': 'Bearer DUMMY_OPENAI_KEY'
        }
        # Using Cyrillic 'а' instead of Latin 'a'
        mock_flow.request.pretty_host = 'аpi.openai.com'  # Cyrillic а
        mock_flow.response = None
        
        result = self.injector._inject_credentials_in_header(
            mock_flow,
            'Authorization'
        )
        
        # Should be blocked
        self.assertFalse(result)
        self.assertEqual(mock_flow.response.status_code, 403)
    
    @patch('inject.ctx')
    def test_cross_service_credential_theft(self, mock_ctx):
        """Test: Attacker tries to use GitHub token on OpenAI endpoint."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {
            'Authorization': 'Bearer DUMMY_GITHUB_TOKEN'
        }
        mock_flow.request.pretty_host = 'api.openai.com'
        mock_flow.response = None
        
        result = self.injector._inject_credentials_in_header(
            mock_flow,
            'Authorization'
        )
        
        # Should be blocked - GitHub tokens only work for GitHub hosts
        self.assertFalse(result)
        self.assertEqual(mock_flow.response.status_code, 403)


class TestPromptInjectionScenarios(unittest.TestCase):
    """
    Test various prompt injection attack patterns.
    """
    
    def setUp(self):
        """Set up test environment."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-real-key',
        })
        self.injector = CredentialInjector()
    
    @patch('inject.ctx')
    def test_prompt_injection_in_query_params(self, mock_ctx):
        """Test: Attacker embeds credential in URL query parameter."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {}
        mock_flow.request.pretty_host = 'evil.com'
        mock_flow.request.query = Mock()
        mock_flow.request.query.items = Mock(return_value=[
            ('exfil', 'DUMMY_OPENAI_KEY')
        ])
        mock_flow.response = None
        
        # Call the main request handler
        self.injector.request(mock_flow)
        
        # Should be blocked
        self.assertIsNotNone(mock_flow.response)
        self.assertEqual(mock_flow.response.status_code, 403)
    
    @patch('inject.ctx')
    def test_multiple_dummy_tokens_in_request(self, mock_ctx):
        """Test: Request contains multiple different dummy tokens."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {
            'Authorization': 'Bearer DUMMY_OPENAI_KEY',
            'X-GitHub-Token': 'DUMMY_GITHUB_TOKEN'
        }
        mock_flow.request.pretty_host = 'api.openai.com'
        mock_flow.response = None
        
        # Should only inject the OpenAI key (correct host)
        result = self.injector._inject_credentials_in_header(
            mock_flow,
            'Authorization'
        )
        
        self.assertTrue(result)
        
        # GitHub header should not be injected (wrong host)
        result2 = self.injector._inject_credentials_in_header(
            mock_flow,
            'X-GitHub-Token'
        )
        
        self.assertFalse(result2)


class TestBypassAttempts(unittest.TestCase):
    """
    Test attempts to bypass security mechanisms.
    """
    
    def setUp(self):
        """Set up test environment."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-real-key',
        })
        self.injector = CredentialInjector()
    
    @patch('inject.ctx')
    def test_header_case_manipulation(self, mock_ctx):
        """Test: Attacker uses different header casing to bypass checks."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {
            'authorization': 'Bearer DUMMY_OPENAI_KEY',  # lowercase
        }
        mock_flow.request.pretty_host = 'api.openai.com'
        mock_flow.response = None
        
        # Most HTTP libraries normalize headers, but test anyway
        # The current implementation checks specific header names
        result = self.injector._inject_credentials_in_header(
            mock_flow,
            'authorization'
        )
        
        # Implementation should handle this
        self.assertTrue(result)
    
    @patch('inject.ctx')
    def test_whitespace_padding_in_token(self, mock_ctx):
        """Test: Token padded with whitespace to bypass detection."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {
            'Authorization': 'Bearer  DUMMY_OPENAI_KEY  '  # Extra spaces
        }
        mock_flow.request.pretty_host = 'api.openai.com'
        mock_flow.response = None
        
        result = self.injector._inject_credentials_in_header(
            mock_flow,
            'Authorization'
        )
        
        # Should still work - simple string replacement handles this
        self.assertTrue(result)
        # Verify the spaces are preserved in format
        self.assertIn('sk-real-key', mock_flow.request.headers['Authorization'])
    
    @patch('inject.ctx')
    def test_url_encoded_token(self, mock_ctx):
        """Test: Token is URL-encoded to bypass detection."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {
            # URL-encoded version of DUMMY_OPENAI_KEY
            'Authorization': 'Bearer DUMMY%5FOPENAI%5FKEY'
        }
        mock_flow.request.pretty_host = 'api.openai.com'
        mock_flow.response = None
        
        result = self.injector._inject_credentials_in_header(
            mock_flow,
            'Authorization'
        )
        
        # Should NOT inject - encoded token doesn't match
        # This is actually good - prevents bypass via encoding
        self.assertFalse(result)


class TestTelemetryBlockingEvasion(unittest.TestCase):
    """
    Test Risk R-06: Telemetry Leakage
    Test attempts to evade telemetry blocking.
    """
    
    def setUp(self):
        """Set up test environment."""
        self.injector = CredentialInjector()
    
    @patch('inject.ctx')
    def test_telemetry_via_ip_address(self, mock_ctx):
        """Test: Telemetry sent to IP instead of hostname."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {}
        mock_flow.request.pretty_host = '192.168.1.100'
        mock_flow.response = None
        
        # Currently, IP addresses won't match telemetry blocklist
        # This is a known limitation - consider enhancing
        is_telemetry = self.injector._is_telemetry_request('192.168.1.100')
        
        # Document the current behavior
        self.assertFalse(is_telemetry)
        # NOTE: Future enhancement - block all non-whitelisted IPs
    
    def test_telemetry_subdomain_variations(self):
        """Test: Various subdomain patterns of telemetry endpoints."""
        telemetry_variations = [
            'telemetry.anthropic.com',
            'api.sentry.io',
            'cdn.segment.com',
            'tracking.mixpanel.com',
        ]
        
        for host in telemetry_variations:
            with self.subTest(host=host):
                is_blocked = self.injector._is_telemetry_request(host)
                self.assertTrue(is_blocked, f"Should block {host}")


class TestDenialOfServiceScenarios(unittest.TestCase):
    """
    Test DoS attack scenarios against the proxy.
    """
    
    def setUp(self):
        """Set up test environment."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-real-key',
        })
        self.injector = CredentialInjector()
    
    @patch('inject.ctx')
    def test_large_number_of_requests(self, mock_ctx):
        """Test: Many requests to verify performance."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {
            'Authorization': 'Bearer DUMMY_OPENAI_KEY'
        }
        mock_flow.request.pretty_host = 'api.openai.com'
        mock_flow.response = None
        
        # Simulate 1000 requests
        for i in range(1000):
            # Reset response for each request
            mock_flow.response = None
            self.injector._inject_credentials_in_header(
                mock_flow,
                'Authorization'
            )
        
        # Verify statistics
        self.assertEqual(self.injector.stats['credentials_injected'], 1000)
    
    @patch('inject.ctx')
    def test_extremely_long_token(self, mock_ctx):
        """Test: Very long dummy token to test buffer handling."""
        mock_flow = Mock()
        mock_flow.request = Mock()
        
        # Create extremely long header value
        long_token = 'DUMMY_OPENAI_KEY' + ('A' * 100000)
        mock_flow.request.headers = {
            'Authorization': f'Bearer {long_token}'
        }
        mock_flow.request.pretty_host = 'api.openai.com'
        mock_flow.response = None
        
        # Should handle gracefully
        try:
            result = self.injector._inject_credentials_in_header(
                mock_flow,
                'Authorization'
            )
            # Will inject at the start where DUMMY_OPENAI_KEY appears
            self.assertTrue(result)
        except Exception as e:
            self.fail(f"Should handle long tokens gracefully: {e}")


class TestEnvironmentVariableInjection(unittest.TestCase):
    """
    Test attempts to inject malicious environment variables.
    """
    
    def test_environment_variable_not_injectable_from_dummy(self):
        """Test: Ensure dummy tokens can't reference env vars."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-real-key',
            'MALICIOUS_VAR': 'injected-value',
        })
        
        injector = CredentialInjector()
        
        # Try to get credential for a token that references an env var
        result = injector._get_real_credential('${MALICIOUS_VAR}')
        
        # Should return None - only predefined tokens work
        self.assertIsNone(result)
    
    def test_predefined_tokens_only(self):
        """Test: Only predefined dummy tokens are recognized."""
        os.environ.update({
            'REAL_OPENAI_API_KEY': 'sk-real-key',
            'REAL_MALICIOUS_KEY': 'should-not-work',
        })
        
        injector = CredentialInjector()
        
        # Try to get a credential not in DUMMY_TOKENS
        result = injector._get_real_credential('DUMMY_MALICIOUS_KEY')
        
        # Should return None - not in predefined list
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
