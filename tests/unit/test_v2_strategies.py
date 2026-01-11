#!/usr/bin/env python3
"""
Unit Tests for Universal Injector v2 - Strategy Architecture

Tests the new strategy-based architecture including AWS SigV4, Bearer tokens,
and the orchestration layer.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Add proxy directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../proxy'))

from strategies.base import InjectionStrategy
from strategies.bearer import BearerStrategy, StripeStrategy, GitHubStrategy, OpenAIStrategy
from strategies.aws_sigv4 import AWSSigV4Strategy


class TestBearerStrategy(unittest.TestCase):
    """Test Bearer token strategy."""
    
    def setUp(self):
        """Set up test environment."""
        os.environ['TEST_TOKEN'] = 'real-secret-token-12345'
        
    def tearDown(self):
        """Clean up environment."""
        if 'TEST_TOKEN' in os.environ:
            del os.environ['TEST_TOKEN']
    
    def test_bearer_strategy_initialization(self):
        """Test Bearer strategy initializes correctly."""
        config = {
            'token': 'TEST_TOKEN',
            'dummy_pattern': r'DUMMY_TEST_.*',
            'allowed_hosts': ['api.example.com']
        }
        
        strategy = BearerStrategy('test-bearer', config)
        
        self.assertEqual(strategy.name, 'test-bearer')
        self.assertEqual(strategy.token, 'real-secret-token-12345')
        self.assertEqual(strategy.allowed_hosts, ['api.example.com'])
    
    def test_bearer_detect_with_dummy_token(self):
        """Test Bearer strategy detects dummy tokens."""
        config = {
            'token': 'TEST_TOKEN',
            'dummy_pattern': r'DUMMY_TEST_.*',
            'allowed_hosts': ['api.example.com']
        }
        strategy = BearerStrategy('test', config)
        
        # Create mock flow
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = Mock()
        mock_flow.request.headers.get = Mock(return_value='Bearer DUMMY_TEST_TOKEN')
        
        result = strategy.detect(mock_flow)
        self.assertTrue(result)
    
    def test_bearer_no_detect_without_dummy(self):
        """Test Bearer strategy doesn't detect real tokens."""
        config = {
            'token': 'TEST_TOKEN',
            'dummy_pattern': r'DUMMY_TEST_.*',
            'allowed_hosts': ['api.example.com']
        }
        strategy = BearerStrategy('test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = Mock()
        mock_flow.request.headers.get = Mock(return_value='Bearer real-token-here')
        
        result = strategy.detect(mock_flow)
        self.assertFalse(result)
    
    def test_bearer_inject_success(self):
        """Test Bearer strategy injects credentials successfully."""
        config = {
            'token': 'TEST_TOKEN',
            'dummy_pattern': r'DUMMY_.*',
            'allowed_hosts': ['api.example.com']
        }
        strategy = BearerStrategy('test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {'Authorization': 'Bearer DUMMY_TOKEN'}
        mock_flow.request.pretty_host = 'api.example.com'
        
        strategy.inject(mock_flow)
        
        self.assertEqual(
            mock_flow.request.headers['Authorization'],
            'Bearer real-secret-token-12345'
        )
    
    def test_bearer_inject_blocks_unauthorized_host(self):
        """Test Bearer strategy blocks unauthorized hosts."""
        config = {
            'token': 'TEST_TOKEN',
            'dummy_pattern': r'DUMMY_.*',
            'allowed_hosts': ['api.example.com']
        }
        strategy = BearerStrategy('test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.headers = {'Authorization': 'Bearer DUMMY_TOKEN'}
        mock_flow.request.pretty_host = 'evil.com'
        
        with self.assertRaises(ValueError) as context:
            strategy.inject(mock_flow)
        
        self.assertIn('not in allowed hosts', str(context.exception))


class TestSpecializedBearerStrategies(unittest.TestCase):
    """Test specialized Bearer strategies (Stripe, GitHub, OpenAI)."""
    
    def setUp(self):
        """Set up test environment."""
        os.environ['STRIPE_KEY'] = 'sk_test_real_stripe_key'
        os.environ['GITHUB_TOKEN'] = 'ghp_real_github_token'
        os.environ['OPENAI_KEY'] = 'sk-proj-real_openai_key'
    
    def tearDown(self):
        """Clean up environment."""
        for key in ['STRIPE_KEY', 'GITHUB_TOKEN', 'OPENAI_KEY']:
            if key in os.environ:
                del os.environ[key]
    
    def test_stripe_strategy_defaults(self):
        """Test Stripe strategy has correct defaults."""
        config = {'token': 'STRIPE_KEY'}
        strategy = StripeStrategy('stripe', config)
        
        self.assertIn('api.stripe.com', strategy.allowed_hosts)
        self.assertIn('sk_', strategy.dummy_pattern)
    
    def test_github_strategy_defaults(self):
        """Test GitHub strategy has correct defaults."""
        config = {'token': 'GITHUB_TOKEN'}
        strategy = GitHubStrategy('github', config)
        
        self.assertIn('api.github.com', strategy.allowed_hosts)
        self.assertIn('ghp_', strategy.dummy_pattern)
    
    def test_openai_strategy_defaults(self):
        """Test OpenAI strategy has correct defaults."""
        config = {'token': 'OPENAI_KEY'}
        strategy = OpenAIStrategy('openai', config)
        
        self.assertIn('api.openai.com', strategy.allowed_hosts)
        self.assertIn('sk-proj-', strategy.dummy_pattern)


class TestAWSSigV4Strategy(unittest.TestCase):
    """Test AWS Signature Version 4 strategy."""
    
    def setUp(self):
        """Set up test environment."""
        os.environ['AWS_ACCESS_KEY_ID'] = 'AKIAIOSFODNN7EXAMPLE'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
    
    def tearDown(self):
        """Clean up environment."""
        for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN']:
            if key in os.environ:
                del os.environ[key]
    
    def test_aws_strategy_initialization(self):
        """Test AWS SigV4 strategy initializes correctly."""
        config = {
            'access_key_id': 'AWS_ACCESS_KEY_ID',
            'secret_access_key': 'AWS_SECRET_ACCESS_KEY',
            'region': 'us-east-1'
        }
        
        strategy = AWSSigV4Strategy('aws-test', config)
        
        self.assertEqual(strategy.name, 'aws-test')
        self.assertEqual(strategy.access_key_id, 'AKIAIOSFODNN7EXAMPLE')
        self.assertEqual(strategy.default_region, 'us-east-1')
    
    def test_aws_detect_with_dummy_credentials(self):
        """Test AWS strategy detects dummy AWS credentials."""
        config = {
            'access_key_id': 'AWS_ACCESS_KEY_ID',
            'secret_access_key': 'AWS_SECRET_ACCESS_KEY'
        }
        strategy = AWSSigV4Strategy('aws-test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.pretty_host = 's3.us-west-2.amazonaws.com'
        mock_flow.request.headers = Mock()
        mock_flow.request.headers.get = Mock(return_value='AWS4-HMAC-SHA256 Credential=AKIA00000000DUMMYKEY/...')
        mock_flow.request.pretty_url = 'https://s3.us-west-2.amazonaws.com/bucket'
        
        result = strategy.detect(mock_flow)
        self.assertTrue(result)
    
    def test_aws_no_detect_non_aws_host(self):
        """Test AWS strategy doesn't detect non-AWS hosts."""
        config = {
            'access_key_id': 'AWS_ACCESS_KEY_ID',
            'secret_access_key': 'AWS_SECRET_ACCESS_KEY'
        }
        strategy = AWSSigV4Strategy('aws-test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.pretty_host = 'api.example.com'
        mock_flow.request.headers = Mock()
        mock_flow.request.headers.get = Mock(return_value='')
        
        result = strategy.detect(mock_flow)
        self.assertFalse(result)
    
    def test_aws_extract_region_from_url(self):
        """Test region extraction from AWS URL."""
        config = {
            'access_key_id': 'AWS_ACCESS_KEY_ID',
            'secret_access_key': 'AWS_SECRET_ACCESS_KEY'
        }
        strategy = AWSSigV4Strategy('aws-test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.pretty_host = 's3.us-west-2.amazonaws.com'
        mock_flow.request.pretty_url = 'https://s3.us-west-2.amazonaws.com'
        
        region = strategy._extract_region(mock_flow)
        self.assertEqual(region, 'us-west-2')
    
    def test_aws_extract_service_from_url(self):
        """Test service extraction from AWS URL."""
        config = {
            'access_key_id': 'AWS_ACCESS_KEY_ID',
            'secret_access_key': 'AWS_SECRET_ACCESS_KEY'
        }
        strategy = AWSSigV4Strategy('aws-test', config)
        
        test_cases = [
            ('s3.amazonaws.com', 's3'),
            ('ec2.us-east-1.amazonaws.com', 'ec2'),
            ('lambda.us-west-2.amazonaws.com', 'lambda'),
        ]
        
        for host, expected_service in test_cases:
            with self.subTest(host=host):
                mock_flow = Mock()
                mock_flow.request = Mock()
                mock_flow.request.pretty_host = host
                mock_flow.request.pretty_url = f'https://{host}'
                
                service = strategy._extract_service(mock_flow)
                self.assertEqual(service, expected_service)
    
    def test_aws_default_region_fallback(self):
        """Test AWS strategy falls back to default region."""
        config = {
            'access_key_id': 'AWS_ACCESS_KEY_ID',
            'secret_access_key': 'AWS_SECRET_ACCESS_KEY',
            'region': 'eu-central-1'
        }
        strategy = AWSSigV4Strategy('aws-test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.pretty_host = 's3.amazonaws.com'  # No region in URL
        mock_flow.request.pretty_url = 'https://s3.amazonaws.com'
        
        region = strategy._extract_region(mock_flow)
        self.assertEqual(region, 'eu-central-1')


class TestHostValidation(unittest.TestCase):
    """Test host validation in base strategy."""
    
    def test_exact_host_match(self):
        """Test exact host matching."""
        config = {
            'token': 'TEST_TOKEN',
            'allowed_hosts': ['api.example.com']
        }
        strategy = BearerStrategy('test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.pretty_host = 'api.example.com'
        
        result = strategy.validate_host(mock_flow, ['api.example.com'])
        self.assertTrue(result)
    
    def test_wildcard_subdomain_match(self):
        """Test wildcard subdomain matching."""
        config = {
            'token': 'TEST_TOKEN',
            'allowed_hosts': ['*.amazonaws.com']
        }
        strategy = BearerStrategy('test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        
        # Should match subdomains
        test_cases = [
            ('s3.amazonaws.com', True),
            ('ec2.us-east-1.amazonaws.com', True),
            ('amazonaws.com', True),
            ('evil.com', False),
            ('amazonaws.com.evil.com', False),
        ]
        
        for host, should_match in test_cases:
            with self.subTest(host=host):
                mock_flow.request.pretty_host = host
                result = strategy.validate_host(mock_flow, ['*.amazonaws.com'])
                self.assertEqual(result, should_match, f"Failed for {host}")
    
    def test_case_insensitive_matching(self):
        """Test host matching is case-insensitive."""
        config = {
            'token': 'TEST_TOKEN',
            'allowed_hosts': ['api.example.com']
        }
        strategy = BearerStrategy('test', config)
        
        mock_flow = Mock()
        mock_flow.request = Mock()
        mock_flow.request.pretty_host = 'API.EXAMPLE.COM'
        
        result = strategy.validate_host(mock_flow, ['api.example.com'])
        self.assertTrue(result)


class TestCredentialLoading(unittest.TestCase):
    """Test credential loading from environment variables."""
    
    def setUp(self):
        """Set up test environment."""
        os.environ['MY_TOKEN'] = 'secret-value-123'
        os.environ['MY_KEY_ID'] = 'key-id-456'
    
    def tearDown(self):
        """Clean up environment."""
        for key in ['MY_TOKEN', 'MY_KEY_ID']:
            if key in os.environ:
                del os.environ[key]
    
    def test_load_from_env_var_reference(self):
        """Test loading credential from environment variable reference."""
        config = {'token': 'MY_TOKEN'}
        strategy = BearerStrategy('test', config)
        
        self.assertEqual(strategy.token, 'secret-value-123')
    
    def test_load_direct_value(self):
        """Test loading credential as direct value (not recommended)."""
        config = {'token': 'direct-token-value', 'allowed_hosts': ['test.com']}
        strategy = BearerStrategy('test', config)
        
        self.assertEqual(strategy.token, 'direct-token-value')
    
    def test_missing_required_credential(self):
        """Test error when required credential is missing."""
        config = {'token': 'NONEXISTENT_VAR', 'allowed_hosts': ['test.com']}
        
        with self.assertRaises(ValueError) as context:
            strategy = BearerStrategy('test', config)
        
        self.assertIn('not set', str(context.exception))


if __name__ == '__main__':
    unittest.main()
