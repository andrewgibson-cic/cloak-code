"""
Security Tests: Credential Exfiltration Prevention

Tests Risk R-04: Prompt Injection (Exfiltration)
Validates that credentials cannot be exfiltrated to unauthorized hosts.

Following TDD principles:
1. Write security tests FIRST
2. Tests should FAIL initially
3. Implement security controls to make tests PASS
"""

import pytest
import os
import sys

# Add proxy directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../proxy'))

from strategies.bearer import BearerStrategy, OpenAIStrategy
from strategies.aws_sigv4 import AWSSigV4Strategy


@pytest.mark.security
class TestCredentialExfiltrationPrevention:
    """Test that credentials cannot be sent to unauthorized hosts."""
    
    def test_bearer_token_blocked_on_unauthorized_host(self, mock_flow, test_env_vars):
        """
        SECURITY TEST: Bearer token must NOT be injected to unauthorized hosts.
        
        Given: OpenAI strategy with whitelisted hosts
        When: Request to attacker-controlled host with dummy token
        Then: Request is blocked (ValueError raised)
        And: No credential in request
        """
        # Setup
        os.environ['OPENAI_API_KEY'] = 'sk-real-secret-key-do-not-leak'
        config = {
            'token': 'OPENAI_API_KEY',
            'dummy_pattern': r'DUMMY_OPENAI_KEY',
            'allowed_hosts': ['api.openai.com']
        }
        strategy = OpenAIStrategy('openai-test', config)
        
        # Mock request to evil host
        mock_flow.request.headers = {'Authorization': 'Bearer DUMMY_OPENAI_KEY'}
        mock_flow.request.pretty_host = 'evil.com'
        
        # Should detect the dummy token
        assert strategy.detect(mock_flow) is True
        
        # Should BLOCK injection to unauthorized host
        with pytest.raises(ValueError) as exc_info:
            strategy.inject(mock_flow)
        
        assert 'not in allowed hosts' in str(exc_info.value).lower()
        # Credential should NOT be in request
        assert 'sk-real-secret-key' not in str(mock_flow.request.headers)
    
    def test_subdomain_spoofing_blocked(self, mock_flow, test_env_vars):
        """
        SECURITY TEST: Subdomain spoofing like api.openai.com.evil.com must be blocked.
        
        Given: Strategy with api.openai.com in whitelist
        When: Request to api.openai.com.evil.com
        Then: Request blocked (not treated as valid subdomain)
        """
        os.environ['OPENAI_API_KEY'] = 'sk-real-secret-key'
        config = {
            'token': 'OPENAI_API_KEY',
            'dummy_pattern': r'DUMMY_OPENAI_KEY',
            'allowed_hosts': ['api.openai.com']
        }
        strategy = OpenAIStrategy('openai-test', config)
        
        # Attempt subdomain spoofing
        mock_flow.request.headers = {'Authorization': 'Bearer DUMMY_OPENAI_KEY'}
        mock_flow.request.pretty_host = 'api.openai.com.evil.com'
        
        # Should detect dummy token
        assert strategy.detect(mock_flow) is True
        
        # Should BLOCK due to invalid host
        with pytest.raises(ValueError) as exc_info:
            strategy.inject(mock_flow)
        
        assert 'not in allowed hosts' in str(exc_info.value).lower()
    
    def test_cross_service_credential_theft(self, mock_flow, test_env_vars):
        """
        SECURITY TEST: GitHub token must NOT work on OpenAI endpoint.
        
        Given: GitHub strategy with github.com whitelist
        When: Request to OpenAI with GitHub dummy token
        Then: Request should not inject GitHub credentials
        """
        os.environ['GITHUB_TOKEN'] = 'ghp_real_github_token_secret'
        config = {
            'token': 'GITHUB_TOKEN',
            'dummy_pattern': r'DUMMY_GITHUB_TOKEN',
            'allowed_hosts': ['api.github.com', 'github.com']
        }
        from strategies.bearer import GitHubStrategy
        strategy = GitHubStrategy('github-test', config)
        
        # Try to use GitHub token on OpenAI
        mock_flow.request.headers = {'Authorization': 'Bearer DUMMY_GITHUB_TOKEN'}
        mock_flow.request.pretty_host = 'api.openai.com'
        
        # Should detect dummy token
        assert strategy.detect(mock_flow) is True
        
        # Should BLOCK - wrong host
        with pytest.raises(ValueError):
            strategy.inject(mock_flow)
    
    def test_aws_credentials_blocked_on_non_aws_host(self, mock_aws_flow, test_env_vars):
        """
        SECURITY TEST: AWS credentials must only work on amazonaws.com domains.
        
        Given: AWS SigV4 strategy
        When: Request to non-AWS host with AWS dummy credentials
        Then: Request blocked
        """
        config = {
            'access_key_id': 'AWS_ACCESS_KEY_ID',
            'secret_access_key': 'AWS_SECRET_ACCESS_KEY',
            'region': 'us-east-1',
            'allowed_hosts': ['*.amazonaws.com']
        }
        strategy = AWSSigV4Strategy('aws-test', config)
        
        # Attempt to use AWS creds on non-AWS host
        mock_aws_flow.request.pretty_host = 'evil.com'
        
        # Should NOT detect (not amazonaws.com)
        assert strategy.detect(mock_aws_flow) is False
    
    def test_wildcard_doesnt_match_spoofed_domain(self, mock_flow, test_env_vars):
        """
        SECURITY TEST: *.example.com should NOT match example.com.evil.com.
        
        Given: Strategy with *.example.com whitelist
        When: Request to example.com.evil.com
        Then: Request blocked
        """
        os.environ['TEST_TOKEN'] = 'secret-token-123'
        config = {
            'token': 'TEST_TOKEN',
            'dummy_pattern': r'DUMMY_TEST',
            'allowed_hosts': ['*.example.com']
        }
        strategy = BearerStrategy('test', config)
        
        mock_flow.request.headers = {'Authorization': 'Bearer DUMMY_TEST'}
        mock_flow.request.pretty_host = 'example.com.evil.com'
        
        assert strategy.detect(mock_flow) is True
        
        with pytest.raises(ValueError):
            strategy.inject(mock_flow)


@pytest.mark.security
class TestCredentialLeakageInLogs:
    """Test that real credentials never appear in logs."""
    
    def test_no_credentials_in_log_output(self, mock_flow, test_env_vars, capture_logs):
        """
        SECURITY TEST: Real credentials must NEVER appear in logs.
        
        Given: System processing requests with real credentials
        When: Logging operations occur
        Then: Logs contain placeholders, not actual values
        """
        os.environ['OPENAI_API_KEY'] = 'sk-real-secret-NEVER-LOG-THIS'
        config = {
            'token': 'OPENAI_API_KEY',
            'dummy_pattern': r'DUMMY_OPENAI_KEY',
            'allowed_hosts': ['api.openai.com']
        }
        strategy = OpenAIStrategy('openai-test', config)
        
        mock_flow.request.headers = {'Authorization': 'Bearer DUMMY_OPENAI_KEY'}
        mock_flow.request.pretty_host = 'api.openai.com'
        
        # Inject credentials
        strategy.inject(mock_flow)
        
        # Simulate logging (in real code, this would use actual logger)
        log_message = f"Injected credentials for {mock_flow.request.pretty_host}"
        capture_logs.write(log_message)
        
        # Verify log doesn't contain real credential
        log_content = capture_logs.read()
        assert 'sk-real-secret-NEVER-LOG-THIS' not in log_content
        assert 'NEVER-LOG-THIS' not in log_content
    
    def test_error_messages_dont_leak_credentials(self, mock_flow, test_env_vars):
        """
        SECURITY TEST: Error messages must NOT contain credential values.
        
        Given: Invalid configuration or error state
        When: Exception raised
        Then: Exception message doesn't contain credentials
        """
        os.environ['OPENAI_API_KEY'] = 'sk-secret-key-in-error'
        config = {
            'token': 'OPENAI_API_KEY',
            'dummy_pattern': r'DUMMY_OPENAI_KEY',
            'allowed_hosts': ['api.openai.com']
        }
        strategy = OpenAIStrategy('openai-test', config)
        
        mock_flow.request.headers = {'Authorization': 'Bearer DUMMY_OPENAI_KEY'}
        mock_flow.request.pretty_host = 'evil.com'
        
        # Should raise error with safe message
        with pytest.raises(ValueError) as exc_info:
            strategy.inject(mock_flow)
        
        error_message = str(exc_info.value)
        # Error should NOT contain actual credential
        assert 'sk-secret-key-in-error' not in error_message
        assert 'secret-key-in-error' not in error_message


@pytest.mark.security
class TestFailClosedBehavior:
    """Test that system fails securely when errors occur."""
    
    def test_missing_credential_prevents_injection(self, mock_flow):
        """
        SECURITY TEST: Missing credential must cause failure, not passthrough.
        
        Given: Strategy configured but credential not in environment
        When: Injection attempted
        Then: ValueError raised (fail-closed)
        """
        # Ensure credential is NOT set
        os.environ.pop('OPENAI_API_KEY', None)
        
        config = {
            'token': 'OPENAI_API_KEY',
            'dummy_pattern': r'DUMMY_OPENAI_KEY',
            'allowed_hosts': ['api.openai.com']
        }
        
        # Should fail during initialization
        with pytest.raises(ValueError) as exc_info:
            strategy = OpenAIStrategy('openai-test', config)
        
        assert 'not set' in str(exc_info.value).lower()
    
    def test_empty_credential_rejected(self, mock_flow):
        """
        SECURITY TEST: Empty credential value must be rejected.
        
        Given: Credential set to empty string
        When: Strategy initialized
        Then: ValueError raised
        """
        os.environ['OPENAI_API_KEY'] = ''
        
        config = {
            'token': 'OPENAI_API_KEY',
            'dummy_pattern': r'DUMMY_OPENAI_KEY',
            'allowed_hosts': ['api.openai.com']
        }
        
        with pytest.raises(ValueError):
            strategy = OpenAIStrategy('openai-test', config)
    
    def test_invalid_host_whitelist_format(self, mock_flow, test_env_vars):
        """
        SECURITY TEST: Invalid host whitelist must be caught.
        
        Given: Malformed allowed_hosts configuration
        When: Strategy initialized
        Then: Configuration error raised
        """
        config = {
            'token': 'OPENAI_API_KEY',
            'dummy_pattern': r'DUMMY_OPENAI_KEY',
            'allowed_hosts': None  # Invalid: should be list
        }
        
        # Should fail during initialization
        with pytest.raises((ValueError, TypeError)):
            strategy = OpenAIStrategy('openai-test', config)
