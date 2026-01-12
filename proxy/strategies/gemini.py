"""
Google Gemini API Injection Strategy

This strategy implements authentication for Google's Gemini API which uses
the "x-goog-api-key" header pattern for API key authentication.

Reference: https://ai.google.dev/gemini-api/docs/api-key
"""

import os
import re
from typing import Dict, Any
from mitmproxy import http

from .base import InjectionStrategy


class GeminiStrategy(InjectionStrategy):
    """
    Google Gemini API key authentication strategy.
    
    Gemini uses the x-goog-api-key header for authentication.
    This strategy:
    1. Detects requests with dummy Gemini API keys
    2. Validates the destination host
    3. Replaces the dummy key with the real API key
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize Gemini strategy.
        
        Expected config keys:
        - api_key: The real Gemini API key (or env var name)
        - dummy_pattern: Regex pattern to match dummy API keys (optional)
        - allowed_hosts: List of allowed hosts for this key (optional)
        """
        super().__init__(name, config)
        
        # Load the real API key
        self.api_key = self._load_api_key()
        
        # Dummy pattern to detect
        self.dummy_pattern = config.get(
            "dummy_pattern",
            r"(DUMMY_GEMINI_KEY|AIza[a-zA-Z0-9_-]{35}DUMMY)"
        )
        
        # Allowed hosts for security validation
        self.allowed_hosts = config.get(
            "allowed_hosts",
            [
                "generativelanguage.googleapis.com",
                "*.googleapis.com"
            ]
        )
    
    def _load_api_key(self) -> str:
        """
        Load the real Gemini API key from config.
        
        Supports both direct key values and environment variable references.
        
        Returns:
            The real API key string
            
        Raises:
            ValueError: If API key is not found
        """
        key_value = self.config.get("api_key")
        
        if not key_value:
            raise ValueError(
                f"Gemini strategy '{self.name}' requires 'api_key' configuration"
            )
        
        # If it looks like an env var reference (all caps with underscores)
        if isinstance(key_value, str) and key_value.isupper() and "_" in key_value:
            env_key = os.environ.get(key_value)
            if env_key:
                return env_key
            else:
                raise ValueError(
                    f"Environment variable '{key_value}' referenced in "
                    f"Gemini strategy '{self.name}' is not set"
                )
        
        return key_value
    
    def detect(self, flow: http.HTTPFlow) -> bool:
        """
        Detect if this request should be handled by this Gemini strategy.
        
        Detection logic:
        1. Check if x-goog-api-key header exists
        2. Check if the key matches the dummy pattern
        
        Alternatively, Gemini API keys can also be passed as query parameters:
        3. Check if API key is in query parameters
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            True if this request contains a dummy Gemini API key
        """
        # Check header for API key
        api_key_header = flow.request.headers.get("x-goog-api-key", "")
        if api_key_header and re.search(self.dummy_pattern, api_key_header):
            host = flow.request.pretty_host
            self.logger.debug(
                f"Detected dummy Gemini API key in header for {host} "
                f"(strategy: {self.name})"
            )
            return True
        
        # Check query parameters for API key
        query = flow.request.query
        if query and "key" in query:
            query_key = query["key"]
            if re.search(self.dummy_pattern, query_key):
                host = flow.request.pretty_host
                self.logger.debug(
                    f"Detected dummy Gemini API key in query param for {host} "
                    f"(strategy: {self.name})"
                )
                return True
        
        return False
    
    def inject(self, flow: http.HTTPFlow) -> None:
        """
        Inject the real Gemini API key into the request.
        
        Steps:
        1. Validate host is in allowlist
        2. Replace x-goog-api-key header with real key
        3. If key was in query params, replace it there too
        
        Args:
            flow: The mitmproxy flow object to modify
            
        Raises:
            ValueError: If host validation fails
        """
        # Security check: validate host
        if not self.validate_host(flow, self.allowed_hosts):
            raise ValueError(
                f"Host {flow.request.pretty_host} not in allowed hosts list "
                f"for Gemini strategy '{self.name}'. Refusing to inject credentials."
            )
        
        # Check if dummy key is in header
        api_key_header = flow.request.headers.get("x-goog-api-key", "")
        if api_key_header and re.search(self.dummy_pattern, api_key_header):
            # Replace header with real API key
            flow.request.headers["x-goog-api-key"] = self.api_key
            self.log_injection(flow, "(Gemini API key in header)")
            return
        
        # Check if dummy key is in query parameters
        query = flow.request.query
        if query and "key" in query:
            query_key = query["key"]
            if re.search(self.dummy_pattern, query_key):
                # Replace query param with real API key
                query["key"] = self.api_key
                flow.request.query = query
                self.log_injection(flow, "(Gemini API key in query param)")
                return
        
        self.logger.warning(
            f"Gemini strategy detected but couldn't find dummy key to replace "
            f"for {flow.request.pretty_host}"
        )
