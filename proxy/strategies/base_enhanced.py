"""
Enhanced Base Strategy with P1 Security Features

This module provides an enhanced base class with:
- Input validation (RFC 7230)
- Rate limiting
- DNS rebinding protection
- Error message sanitization
"""

from abc import ABC, abstractmethod
from mitmproxy import http
from typing import Optional, Dict, Any, List
import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from security_utils import (
        SecureLogger,
        InputValidator,
        CredentialScrubber,
        RateLimiter,
        DNSProtection
    )
except ImportError:
    # Fallback if security_utils not available
    SecureLogger = None
    InputValidator = None
    CredentialScrubber = None
    RateLimiter = None
    DNSProtection = None


# Global instances (shared across all strategies)
_rate_limiter = RateLimiter() if RateLimiter else None
_dns_protection = DNSProtection() if DNSProtection else None


class EnhancedInjectionStrategy(ABC):
    """
    Enhanced base class for credential injection strategies.
    
    Security features:
    - Automatic credential scrubbing in logs
    - Input validation for headers (RFC 7230)
    - Rate limiting per credential
    - DNS rebinding protection
    - Error message sanitization
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize the strategy with configuration.
        
        Args:
            name: Unique identifier for this strategy instance
            config: Strategy-specific configuration dictionary
        """
        self.name = name
        self.config = config
        
        # Use SecureLogger if available
        base_logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger = SecureLogger(base_logger) if SecureLogger else base_logger
        
        # Initialize security components
        self.validator = InputValidator() if InputValidator else None
        self.rate_limiter = _rate_limiter
        self.dns_protection = _dns_protection
        
        # Rate limiting configuration
        self.rate_limit_enabled = config.get('rate_limit_enabled', True)
        self.rate_limit_rpm = config.get('rate_limit_rpm', 1000)  # requests per minute
        self.rate_limit_burst = config.get('rate_limit_burst', 100)
        
        # DNS protection configuration
        self.dns_protection_enabled = config.get('dns_protection_enabled', True)
    
    @abstractmethod
    def detect(self, flow: http.HTTPFlow) -> bool:
        """
        Determine if this strategy should handle the given request.
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            True if this strategy should process the request
        """
        pass
    
    @abstractmethod
    def inject(self, flow: http.HTTPFlow) -> None:
        """
        Inject credentials into the request.
        
        Args:
            flow: The mitmproxy flow object to modify
            
        Raises:
            SecurityError: If security validation fails
            ValueError: If credential injection fails
        """
        pass
    
    def validate_and_inject(self, flow: http.HTTPFlow, allowed_hosts: List[str]) -> None:
        """
        Perform security validations then inject credentials.
        
        This is the recommended method to call instead of inject() directly.
        
        Args:
            flow: The mitmproxy flow object
            allowed_hosts: List of allowed host patterns
            
        Raises:
            SecurityError: If security validation fails
            ValueError: If injection fails
        """
        host = flow.request.pretty_host
        
        # 1. Rate limiting check
        if self.rate_limit_enabled and self.rate_limiter:
            credential_id = f"{self.name}:{host}"
            if not self.rate_limiter.check_rate_limit(
                credential_id, 
                self.rate_limit_rpm, 
                self.rate_limit_burst
            ):
                raise SecurityError(
                    f"Rate limit exceeded for {self.name}. "
                    "Please wait before retrying."
                )
        
        # 2. DNS rebinding protection
        if self.dns_protection_enabled and self.dns_protection:
            is_valid, reason, resolved_ip = self.dns_protection.resolve_and_validate(
                host, 
                allowed_hosts
            )
            if not is_valid:
                raise SecurityError(f"DNS validation failed: {reason}")
        
        # 3. Host validation (additional layer)
        if not self.validate_host(flow, allowed_hosts):
            raise SecurityError(
                f"Host {host} is not in the allowed hosts list. "
                "Credential injection blocked for security."
            )
        
        # 4. Input validation on existing headers
        if self.validator:
            for header_name, header_value in flow.request.headers.items():
                if not self.validator.validate_header_value(header_value):
                    # Sanitize invalid header
                    sanitized = self.validator.sanitize_header_value(header_value)
                    flow.request.headers[header_name] = sanitized
                    self.logger.warning(
                        f"Sanitized invalid header {header_name} for {host}"
                    )
        
        # 5. Perform actual injection
        try:
            self.inject(flow)
        except Exception as e:
            # Sanitize error message before re-raising
            safe_message = self._sanitize_error_message(str(e))
            raise ValueError(safe_message) from None
    
    def validate_host(self, flow: http.HTTPFlow, allowed_hosts: List[str]) -> bool:
        """
        Validate that the request destination matches allowed hosts.
        
        Args:
            flow: The mitmproxy flow object
            allowed_hosts: List of allowed host patterns
            
        Returns:
            True if host is allowed, False otherwise
        """
        if not allowed_hosts:
            return False
        
        host = flow.request.pretty_host.lower()
        
        for allowed in allowed_hosts:
            allowed_lower = allowed.lower()
            
            # Exact match
            if host == allowed_lower:
                return True
            
            # Wildcard subdomain match (*.example.com)
            if allowed_lower.startswith('*.'):
                base_domain = allowed_lower[2:]
                if host.endswith('.' + base_domain) or host == base_domain:
                    return True
            
            # Subdomain match
            elif host.endswith('.' + allowed_lower):
                return True
        
        self.logger.warning(
            f"Host validation failed for {host}. "
            f"Not in allowed list: {allowed_hosts[:3]}..."  # Only show first 3 for security
        )
        return False
    
    def get_credential(self, key: str, required: bool = True) -> Optional[str]:
        """
        Retrieve a credential from the strategy's configuration.
        
        Args:
            key: The configuration key
            required: If True, raises exception if missing
            
        Returns:
            The credential value, or None if not found and not required
            
        Raises:
            ValueError: If credential is required but not found
        """
        value = self.config.get(key)
        
        if value is None and required:
            raise ValueError(f"Required credential '{key}' not found in configuration")
        
        return value