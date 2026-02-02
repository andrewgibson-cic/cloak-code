"""
Enhanced Base Strategy Interface with Security Controls

This is an updated version of base.py with integrated security features.
"""

from abc import ABC, abstractmethod
from mitmproxy import http
from typing import Optional, Dict, Any, List
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security_utils import SecureLogger, InputValidator, CredentialScrubber


class InjectionStrategy(ABC):
    """
    Abstract base class for credential injection strategies with security enhancements.
    
    Security features:
    - Automatic credential scrubbing in logs
    - Input validation for headers
    - Host validation with strict checks
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
        
        # Use SecureLogger instead of regular logger
        base_logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger = SecureLogger(base_logger)
        
        # Initialize validator
        self.validator = InputValidator()
    
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
    
    def validate_host(self, flow: http.HTTPFlow, allowed_hosts: List[str]) -> bool:
        """
        Validate that the request destination matches allowed hosts.
        
        This is a critical security check to prevent credential ex