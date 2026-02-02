"""
IBM OpenAI-Compatible API Strategy
Handles Bearer token authentication for IBM Consulting Assistants (ICA)
"""

import os
import re
from mitmproxy import http
from .base import InjectionStrategy


class IBMOpenAIStrategy(InjectionStrategy):
    """
    Strategy for IBM's OpenAI-compatible API endpoint
    
    IBM provides Claude models through an OpenAI-compatible interface at:
    https://servicesessentials.ibm.com/apis/v3
    
    This strategy handles:
    - Bearer token injection in Authorization header
    - Dummy token detection and replacement
    - Request validation for IBM endpoints
    """
    
    def __init__(self, name: str, config: dict):
        """
        Initialize IBM OpenAI strategy
        
        Args:
            name: Unique identifier for this strategy instance
            config: Strategy configuration containing:
                - api_key: Real IBM API key (or env var name)
                - base_url: IBM API base URL
                - dummy_pattern: Pattern to detect dummy tokens
                - allowed_hosts: List of allowed IBM hostnames
        """
        super().__init__(name, config)
        
        self.api_key = self._get_env_value(config.get("api_key", "IBM_API_KEY"))
        self.base_url = self._get_env_value(
            config.get("base_url", "IBM_BASE_URL"),
            "https://servicesessentials.ibm.com/apis/v3"
        )
        self.dummy_pattern = config.get("dummy_pattern", "DUMMY_IBM_KEY")
        self.allowed_hosts = config.get("allowed_hosts", [
            "servicesessentials.ibm.com",
            "*.ibm.com"
        ])
        
        # Compile regex pattern for dummy detection
        self.dummy_regex = re.compile(self.dummy_pattern)
        
        # Validate configuration
        if not self.api_key or self.api_key == "IBM_API_KEY":
            self.logger.warning(
                "IBM API key not found in environment. "
                "Set IBM_API_KEY in .env file."
            )
    
    def detect(self, flow: http.HTTPFlow) -> bool:
        """
        Detect if this request should use IBM API credential injection
        
        Detection criteria:
        1. Request is to an IBM hostname
        2. Authorization header contains dummy token pattern
        
        Args:
            flow: mitmproxy HTTP flow object
            
        Returns:
            bool: True if this strategy should handle the request
        """
        request = flow.request
        
        # Check if host matches allowed hosts
        if not self._host_matches(request.host, self.allowed_hosts):
            return False
        
        # Check for Authorization header with Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False
        
        # Check if token matches dummy pattern
        token = auth_header.replace("Bearer ", "")
        if self.dummy_regex.search(token):
            self.logger.debug(
                f"IBM dummy token detected in request to {request.host}"
            )
            return True
        
        return False
    
    def inject(self, flow: http.HTTPFlow) -> bool:
        """
        Inject real IBM API key into the request
        
        Replaces the dummy token in the Authorization header with the real
        IBM API key from environment variables.
        
        Args:
            flow: mitmproxy HTTP flow object
            
        Returns:
            bool: True if injection was successful
        """
        request = flow.request
        
        # Verify we have a real API key
        if not self.api_key or self.api_key == "IBM_API_KEY":
            self.logger.error(
                "Cannot inject IBM API key: not configured. "
                "Set IBM_API_KEY in .env file."
            )
            return False
        
        try:
            # Get current authorization header
            old_auth = request.headers.get("Authorization", "")
            
            # Replace with real API key
            new_auth = f"Bearer {self.api_key}"
            request.headers["Authorization"] = new_auth
            
            self.logger.info(
                f"IBM API key injected for {request.host}{request.path}"
            )
            self.logger.debug(
                f"  Method: {request.method}"
            )
            self.logger.debug(
                f"  Replaced: {old_auth[:30]}... -> Bearer {self.api_key[:20]}..."
            )
            
            # Log the injection (using base class method)
            self.log_injection(flow, "IBM OpenAI API - Bearer Token")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to inject IBM API key: {e}", exc_info=True)
            return False
    
    def _get_env_value(self, value: str, default: str = None) -> str:
        """
        Get value from environment variable if it looks like an env var reference.
        
        Args:
            value: The value or env var name
            default: Default value if env var not found
            
        Returns:
            The actual value (from env or direct)
        """
        if not value:
            return default
        
        # If it looks like an env var reference (all caps with underscores)
        if isinstance(value, str) and value.isupper() and "_" in value:
            env_value = os.environ.get(value)
            if env_value:
                return env_value
            elif default:
                return default
            else:
                self.logger.warning(f"Environment variable '{value}' not set")
                return value
        
        return value
    
    def _host_matches(self, host: str, patterns: list) -> bool:
        """
        Check if host matches any of the allowed patterns
        
        Supports wildcards: *.ibm.com matches api.ibm.com, services.ibm.com, etc.
        
        Args:
            host: Hostname to check
            patterns: List of allowed hostname patterns
            
        Returns:
            bool: True if host matches any pattern
        """
        for pattern in patterns:
            if pattern.startswith("*."):
                # Wildcard subdomain matching
                domain = pattern[2:]  # Remove *.
                if host.endswith(domain) or host == domain:
                    return True
            elif host == pattern:
                # Exact match
                return True
        
        return False
    
    def validate_response(self, flow: http.HTTPFlow) -> bool:
        """
        Validate IBM API response
        
        Checks for common error patterns that might indicate
        authentication issues.
        
        Args:
            flow: mitmproxy HTTP flow object
            
        Returns:
            bool: True if response appears valid
        """
        if not flow.response:
            return True
        
        response = flow.response
        
        # Check for authentication errors
        if response.status_code == 401:
            self.logger.error(
                f"IBM API authentication failed (401 Unauthorized). "
                f"Check IBM_API_KEY in .env file."
            )
            return False
        
        if response.status_code == 403:
            self.logger.error(
                f"IBM API access forbidden (403 Forbidden). "
                f"Check API key permissions."
            )
            return False
        
        # Check for rate limiting
        if response.status_code == 429:
            self.logger.warning(
                f"IBM API rate limit exceeded (429 Too Many Requests)"
            )
            return True  # Still valid, just rate limited
        
        # Success
        if 200 <= response.status_code < 300:
            self.logger.debug(
                f"IBM API request successful: {response.status_code}"
            )
            return True
        
        # Other errors
        if response.status_code >= 400:
            self.logger.warning(
                f"IBM API request failed: {response.status_code}"
            )
        
        return True
