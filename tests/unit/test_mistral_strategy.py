"""
Unit tests for Mistral AI API injection strategy.
"""

import os
import pytest
from mitmproxy.test import tflow
from proxy.strategies.mistral import MistralStrategy


class TestMistralStrategy:
    """Test cases for Mistral AI strategy."""
    
    def setup_method(self):
        """Setup test environment."""
        # Set environment variable for testing
        os.environ["MISTRAL_API_KEY"] = "test_mistral_key_12345"
        
        # Create strategy instance
        self.config = {
            "token": "MISTRAL_API_KEY"
        }
        self.strategy = MistralStrategy("mistral-test", self.config)
    
    def teardown_method(self):
        """Cleanup test environment."""
        if "MISTRAL_API_KEY" in os.environ:
            del os.environ["MISTRAL_API_KEY"]
    
    def test_initialization(self):
        """Test strategy initialization."""
        assert self.strategy.name == "mistral-test"
        assert self.strategy.token == "test_mistral_key_12345"
        assert "api.mistral.ai" in self.strategy.allowed_hosts
        assert "*.mistral.ai" in self.strategy.allowed_hosts
    
    def test_detect_dummy_token(self):
        """Test detection of dummy Mistral API key."""
        flow = tflow.tflow()
        flow.request.host = "api.mistral.ai"
        flow.request.headers["Authorization"] = "Bearer DUMMY_MISTRAL_KEY"
        
        assert self.strategy.detect(flow) is True
    
    def test_detect_no_bearer_token(self):
        """Test that requests without Bearer token are not detected."""
        flow = tflow.tflow()
        flow.request.host = "api.mistral.ai"
        flow.request.headers["Authorization"] = "Basic some_token"
        
        assert self.strategy.detect(flow) is False
    
    def test_detect_real_token(self):
        """Test that real tokens are not detected as dummy."""
        flow = tflow.tflow()
        flow.request.host = "api.mistral.ai"
        flow.request.headers["Authorization"] = "Bearer real_mistral_key_xyz"
        
        assert self.strategy.detect(flow) is False
    
    def test_inject_replaces_token(self):
        """Test that injection replaces dummy token with real token."""
        flow = tflow.tflow()
        flow.request.host = "api.mistral.ai"
        flow.request.headers["Authorization"] = "Bearer DUMMY_MISTRAL_KEY"
        
        self.strategy.inject(flow)
        
        assert flow.request.headers["Authorization"] == "Bearer test_mistral_key_12345"
    
    def test_inject_validates_host(self):
        """Test that injection validates allowed hosts."""
        flow = tflow.tflow()
        flow.request.host = "evil.example.com"
        flow.request.headers["Authorization"] = "Bearer DUMMY_MISTRAL_KEY"
        
        with pytest.raises(ValueError, match="not in allowed hosts"):
            self.strategy.inject(flow)
    
    def test_allowed_hosts_wildcard(self):
        """Test that wildcard hosts work correctly."""
        flow = tflow.tflow()
        flow.request.host = "eu.api.mistral.ai"
        flow.request.headers["Authorization"] = "Bearer DUMMY_MISTRAL_KEY"
        
        # Should not raise an exception
        self.strategy.inject(flow)
        assert flow.request.headers["Authorization"] == "Bearer test_mistral_key_12345"
    
    def test_missing_env_var(self):
        """Test that missing environment variable raises error."""
        del os.environ["MISTRAL_API_KEY"]
        
        with pytest.raises(ValueError, match="is not set"):
            MistralStrategy("mistral-test", self.config)
    
    def test_custom_dummy_pattern(self):
        """Test that custom dummy pattern can be provided."""
        config = {
            "token": "MISTRAL_API_KEY",
            "dummy_pattern": "CUSTOM_DUMMY_.*"
        }
        strategy = MistralStrategy("mistral-custom", config)
        
        flow = tflow.tflow()
        flow.request.host = "api.mistral.ai"
        flow.request.headers["Authorization"] = "Bearer CUSTOM_DUMMY_TOKEN"
        
        assert strategy.detect(flow) is True
