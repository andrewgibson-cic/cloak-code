"""
Bearer Token Injection Strategy

This strategy implements simple Bearer token authentication for APIs that use
the "Authorization: Bearer <token>" pattern (e.g., Stripe, OpenAI, GitHub).

This is the simplest strategy and is used for backward compatibility with v1.
"""

import os
import re
from typing import Dict, Any
from mitmproxy import http

from .base import InjectionStrategy


class BearerStrategy(InjectionStrategy):
    """
    Bearer token authentication strategy.
    
    This strategy:
    1. Detects requests with dummy Bearer tokens
    2. Validates the destination host
    3. Replaces the dummy token with the real token
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize Bearer strategy.
        
        Expected config keys:
        - token: The real bearer token (or env var name)
        - dummy_pattern: Regex pattern to match dummy tokens
        - allowed_hosts: List of allowed hosts for this token
        """
        super().__init__(name, config)
        
        # Load the real token
        self.token = self._load_token()
        
        # Dummy pattern to detect
        self.dummy_pattern = config.get(
            "dummy_pattern",
            r"(DUMMY_[A-Z0-9_]+|sk_test_00000000|ghp_[a-zA-Z0-9]{36}DUMMY)"
        )
        
        # Allowed hosts for security validation
        self.allowed_hosts = config.get("allowed_hosts", [])
        if not self.allowed_hosts:
            raise ValueError(
                f"Bearer strategy '{name}' requires 'allowed_hosts' configuration "
                "for security validation"
            )
    
    def _load_token(self) -> str:
        """
        Load the real bearer token from config.
        
        Supports both direct token values and environment variable references.
        
        Returns:
            The real token string
            
        Raises:
            ValueError: If token is not found
        """
        token_value = self.config.get("token")
        
        if not token_value:
            raise ValueError(
                f"Bearer strategy '{self.name}' requires 'token' configuration"
            )
        
        # If it looks like an env var reference (all caps with underscores)
        if isinstance(token_value, str) and token_value.isupper() and "_" in token_value:
            env_token = os.environ.get(token_value)
            if env_token:
                return env_token
            else:
                raise ValueError(
                    f"Environment variable '{token_value}' referenced in "
                    f"Bearer strategy '{self.name}' is not set"
                )
        
        return token_value
    
    def detect(self, flow: http.HTTPFlow) -> bool:
        """
        Detect if this request should be handled by this Bearer strategy.
        
        Detection logic:
        1. Check if Authorization header exists
        2. Check if it contains "Bearer" keyword
        3. Check if the token matches the dummy pattern
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            True if this request contains a dummy Bearer token
        """
        auth_header = flow.request.headers.get("Authorization", "")
        
        # Must contain "Bearer" keyword
        if "Bearer" not in auth_header:
            return False
        
        # Check if token matches dummy pattern
        if re.search(self.dummy_pattern, auth_header):
            host = flow.request.pretty_host
            self.logger.debug(
                f"Detected dummy Bearer token for {host} "
                f"(strategy: {self.name})"
            )
            return True
        
        return False
    
    def inject(self, flow: http.HTTPFlow) -> None:
        """
        Inject the real Bearer token into the request.
        
        Steps:
        1. Validate host is in allowlist
        2. Replace Authorization header with real token
        
        Args:
            flow: The mitmproxy flow object to modify
            
        Raises:
            ValueError: If host validation fails
        """
        # Security check: validate host
        if not self.validate_host(flow, self.allowed_hosts):
            raise ValueError(
                f"Host {flow.request.pretty_host} not in allowed hosts list "
                f"for Bearer strategy '{self.name}'. Refusing to inject credentials."
            )
        
        # Replace Authorization header with real token
        flow.request.headers["Authorization"] = f"Bearer {self.token}"
        
        self.log_injection(flow, f"(Bearer token)")


class StripeStrategy(BearerStrategy):
    """
    Specialized Bearer strategy for Stripe API.
    
    This is a convenience subclass that pre-configures defaults for Stripe.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize Stripe strategy with defaults.
        
        Expected config keys:
        - token: Stripe API key (or env var name like "STRIPE_SECRET_KEY")
        """
        # Set Stripe-specific defaults
        if "dummy_pattern" not in config:
            config["dummy_pattern"] = r"sk_(test|live)_00000000000000000000000000"
        
        if "allowed_hosts" not in config:
            config["allowed_hosts"] = ["api.stripe.com", "*.stripe.com"]
        
        super().__init__(name, config)


class GitHubStrategy(BearerStrategy):
    """
    Specialized Bearer strategy for GitHub API.
    
    This is a convenience subclass that pre-configures defaults for GitHub.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize GitHub strategy with defaults.
        
        Expected config keys:
        - token: GitHub personal access token (or env var name like "GITHUB_TOKEN")
        """
        # Set GitHub-specific defaults
        if "dummy_pattern" not in config:
            config["dummy_pattern"] = r"(ghp_[a-zA-Z0-9]{36}DUMMY|DUMMY_GITHUB_TOKEN)"
        
        if "allowed_hosts" not in config:
            config["allowed_hosts"] = ["api.github.com", "*.github.com", "github.com"]
        
        super().__init__(name, config)


class OpenAIStrategy(BearerStrategy):
    """
    Specialized Bearer strategy for OpenAI API.
    
    This is a convenience subclass that pre-configures defaults for OpenAI.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize OpenAI strategy with defaults.
        
        Expected config keys:
        - token: OpenAI API key (or env var name like "OPENAI_API_KEY")
        """
        # Set OpenAI-specific defaults
        if "dummy_pattern" not in config:
            config["dummy_pattern"] = r"(sk-proj-[a-zA-Z0-9]{32}DUMMY|DUMMY_OPENAI_KEY)"
        
        if "allowed_hosts" not in config:
            config["allowed_hosts"] = ["api.openai.com", "*.openai.com"]
        
        super().__init__(name, config)
