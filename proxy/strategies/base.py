"""
Base Strategy Interface for Credential Injection

This module defines the abstract base class that all injection strategies must implement.
Each strategy is responsible for detecting when it should be applied and performing
the actual credential injection/signing.
"""

from abc import ABC, abstractmethod
from mitmproxy import http
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class InjectionStrategy(ABC):
    """
    Abstract base class for credential injection strategies.
    
    Each strategy implements a specific authentication protocol (Bearer, AWS SigV4, HMAC, etc.)
    and handles detection, validation, and injection for that protocol.
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
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def detect(self, flow: http.HTTPFlow) -> bool:
        """
        Determine if this strategy should handle the given request.
        
        Args:
            flow: The mitmproxy flow object containing request/response
            
        Returns:
            True if this strategy should process the request, False otherwise
        """
        pass
    
    @abstractmethod
    def inject(self, flow: http.HTTPFlow) -> None:
        """
        Inject credentials into the request.
        
        This method modifies the flow.request object in-place, adding or replacing
        authentication headers/parameters as needed for the specific protocol.
        
        Args:
            flow: The mitmproxy flow object to modify
            
        Raises:
            Exception: If credential injection fails
        """
        pass
    
    def validate_host(self, flow: http.HTTPFlow, allowed_hosts: list) -> bool:
        """
        Validate that the request destination matches allowed hosts.
        
        This is a critical security check to prevent credential exfiltration
        to unauthorized domains.
        
        Args:
            flow: The mitmproxy flow object
            allowed_hosts: List of allowed host patterns (can include wildcards)
            
        Returns:
            True if host is allowed, False otherwise
        """
        host = flow.request.pretty_host.lower()
        
        for allowed in allowed_hosts:
            allowed_lower = allowed.lower()
            
            # Exact match
            if host == allowed_lower:
                return True
            
            # Wildcard subdomain match (*.example.com)
            if allowed_lower.startswith("*."):
                domain = allowed_lower[2:]
                if host.endswith(domain) or host == domain[1:] if domain.startswith(".") else host == domain:
                    return True
        
        self.logger.warning(
            f"Host validation failed for {host}. "
            f"Not in allowed list: {allowed_hosts}"
        )
        return False
    
    def get_credential(self, key: str, required: bool = True) -> Optional[str]:
        """
        Retrieve a credential from the strategy's configuration.
        
        Args:
            key: The configuration key to retrieve
            required: If True, raises exception if key is missing
            
        Returns:
            The credential value, or None if not found and not required
            
        Raises:
            ValueError: If credential is required but not found
        """
        value = self.config.get(key)
        
        if value is None and required:
            raise ValueError(
                f"Required credential '{key}' not found in configuration "
                f"for strategy '{self.name}'"
            )
        
        return value
    
    def sanitize_dummy_credentials(self, flow: http.HTTPFlow) -> None:
        """
        Remove dummy credentials from the request before injection.
        
        This ensures that dummy tokens don't interfere with real authentication.
        Override this method if your strategy needs custom sanitization.
        
        Args:
            flow: The mitmproxy flow object to sanitize
        """
        # Default implementation removes Authorization header if present
        if "Authorization" in flow.request.headers:
            auth_value = flow.request.headers.get("Authorization", "")
            if "DUMMY" in auth_value.upper() or "00000000" in auth_value:
                self.logger.debug(f"Removing dummy Authorization header")
                del flow.request.headers["Authorization"]
    
    def log_injection(self, flow: http.HTTPFlow, details: str = "") -> None:
        """
        Log a credential injection event (without exposing secrets).
        
        Args:
            flow: The mitmproxy flow object
            details: Additional context to log
        """
        self.logger.info(
            f"Strategy '{self.name}' injected credentials for "
            f"{flow.request.method} {flow.request.pretty_host}{flow.request.path} "
            f"{details}"
        )
