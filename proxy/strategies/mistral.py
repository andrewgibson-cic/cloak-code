"""
Mistral AI API Injection Strategy

This strategy implements Bearer token authentication for Mistral AI API.
Mistral uses the "Authorization: Bearer <token>" pattern.

API Documentation: https://docs.mistral.ai/
"""

from typing import Dict, Any
from .bearer import BearerStrategy


class MistralStrategy(BearerStrategy):
    """
    Specialized Bearer strategy for Mistral AI API.
    
    This is a convenience subclass that pre-configures defaults for Mistral AI.
    
    Mistral AI uses Bearer token authentication with API keys.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize Mistral strategy with defaults.
        
        Expected config keys:
        - token: Mistral API key (or env var name like "MISTRAL_API_KEY")
        
        Example config:
        ```yaml
        - name: mistral
          type: mistral
          config:
            token: MISTRAL_API_KEY  # Read from env var
        ```
        """
        # Set Mistral-specific defaults
        if "dummy_pattern" not in config:
            # Mistral API keys typically start with a specific prefix
            # Using a generic DUMMY pattern for now
            config["dummy_pattern"] = r"(DUMMY_MISTRAL_[A-Z0-9_]+|DUMMY_MISTRAL_KEY)"
        
        if "allowed_hosts" not in config:
            config["allowed_hosts"] = [
                "api.mistral.ai",
                "*.mistral.ai"
            ]
        
        super().__init__(name, config)
