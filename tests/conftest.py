"""
Pytest Configuration and Shared Fixtures

This file provides common fixtures and configuration for all tests.
"""

import os
import sys
from unittest.mock import Mock
import pytest

# Add proxy directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../proxy'))


# ============================================================================
# Environment Setup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before and after each test."""
    # Store original environment
    original_env = os.environ.copy()
    
    # Clear test-related env vars
    test_vars = [
        'TEST_TOKEN', 'TEST_API_KEY', 'TEST_SECRET',
        'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN',
        'OPENAI_API_KEY', 'GITHUB_TOKEN', 'STRIPE_SECRET_KEY',
        'SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'MISTRAL_API_KEY',
        'S2_API_KEY', 'GEMINI_API_KEY'
    ]
    
    for var in test_vars:
        os.environ.pop(var, None)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def test_env_vars():
    """Provide test environment variables."""
    env = {
        'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',
        'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
        'OPENAI_API_KEY': 'sk-proj-test-key-1234567890',
        'GITHUB_TOKEN': 'ghp_test_token_1234567890',
        'STRIPE_SECRET_KEY': 'sk_test_1234567890',
    }
    
    for key, value in env.items():
        os.environ[key] = value
    
    return env


# ============================================================================
# Mock Request/Response Fixtures
# ============================================================================

@pytest.fixture
def mock_flow():
    """Create a mock mitmproxy flow object."""
    flow = Mock()
    flow.request = Mock()
    flow.request.headers = {}
    flow.request.pretty_host = 'api.example.com'
    flow.request.pretty_url = 'https://api.example.com/endpoint'
    flow.request.method = 'GET'
    flow.request.path = '/endpoint'
    flow.request.query = Mock()
    flow.request.query.items = Mock(return_value=[])
    flow.request.content = b''
    flow.response = None
    return flow


@pytest.fixture
def mock_aws_flow():
    """Create a mock flow for AWS requests."""
    flow = Mock()
    flow.request = Mock()
    flow.request.headers = {
        'Authorization': 'AWS4-HMAC-SHA256 Credential=AKIA00000000DUMMYKEY/...',
        'Host': 's3.us-east-1.amazonaws.com'
    }
    flow.request.pretty_host = 's3.us-east-1.amazonaws.com'
    flow.request.pretty_url = 'https://s3.us-east-1.amazonaws.com/bucket'
    flow.request.method = 'GET'
    flow.request.path = '/bucket'
    flow.request.query = Mock()
    flow.request.query.items = Mock(return_value=[])
    flow.request.content = b''
    flow.response = None
    return flow


@pytest.fixture
def mock_openai_flow():
    """Create a mock flow for OpenAI requests."""
    flow = Mock()
    flow.request = Mock()
    flow.request.headers = {
        'Authorization': 'Bearer DUMMY_OPENAI_KEY'
    }
    flow.request.pretty_host = 'api.openai.com'
    flow.request.pretty_url = 'https://api.openai.com/v1/models'
    flow.request.method = 'GET'
    flow.request.path = '/v1/models'
    flow.request.query = Mock()
    flow.request.query.items = Mock(return_value=[])
    flow.request.content = b''
    flow.response = None
    return flow


# ============================================================================
# Strategy Configuration Fixtures
# ============================================================================

@pytest.fixture
def bearer_strategy_config():
    """Provide Bearer token strategy configuration."""
    return {
        'token': 'TEST_TOKEN',
        'dummy_pattern': r'DUMMY_TEST_.*',
        'allowed_hosts': ['api.example.com', '*.example.com']
    }


@pytest.fixture
def aws_strategy_config():
    """Provide AWS SigV4 strategy configuration."""
    return {
        'access_key_id': 'AWS_ACCESS_KEY_ID',
        'secret_access_key': 'AWS_SECRET_ACCESS_KEY',
        'region': 'us-east-1',
        'allowed_hosts': ['*.amazonaws.com']
    }


@pytest.fixture
def openai_strategy_config():
    """Provide OpenAI strategy configuration."""
    return {
        'token': 'OPENAI_API_KEY',
        'dummy_pattern': r'(sk-proj-[a-zA-Z0-9]{32}DUMMY|DUMMY_OPENAI_KEY)',
        'allowed_hosts': ['api.openai.com', '*.openai.com']
    }


# ============================================================================
# Security Test Fixtures
# ============================================================================

@pytest.fixture
def malicious_hosts():
    """Provide list of malicious hosts for security testing."""
    return [
        'evil.com',
        'attacker.example.com',
        'api.openai.com.evil.com',  # Subdomain spoofing
        'аpi.openai.com',  # Homograph attack (Cyrillic 'а')
    ]


@pytest.fixture
def telemetry_hosts():
    """Provide list of telemetry hosts that should be blocked."""
    return [
        'telemetry.anthropic.com',
        'api.sentry.io',
        'cdn.segment.com',
        'tracking.mixpanel.com'
    ]


# ============================================================================
# Logging Fixtures
# ============================================================================

@pytest.fixture
def capture_logs(tmp_path):
    """Capture log output to temporary file."""
    log_file = tmp_path / "test.log"
    
    class LogCapture:
        def __init__(self, path):
            self.path = path
            self.logs = []
        
        def write(self, message):
            self.logs.append(message)
            with open(self.path, 'a') as f:
                f.write(message + '\n')
        
        def read(self):
            if self.path.exists():
                return self.path.read_text()
            return ""
        
        def contains(self, text):
            return text in self.read()
        
        def clear(self):
            self.logs = []
            if self.path.exists():
                self.path.unlink()
    
    return LogCapture(log_file)


# ============================================================================
# Performance Test Fixtures
# ============================================================================

@pytest.fixture
def performance_threshold():
    """Provide performance thresholds for tests."""
    return {
        'passthrough_latency_ms': 5,
        'bearer_injection_latency_ms': 10,
        'aws_sigv4_latency_ms': 100,
        'max_memory_mb': 512,
        'max_cpu_percent': 50
    }


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "security: Security tests"
    )
    config.addinivalue_line(
        "markers", "performance: Performance tests"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their location."""
    for item in items:
        # Auto-mark based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)