"""
Credential Injection Strategies Module

This module provides various authentication strategies for the Universal Injector.
Each strategy implements a specific authentication protocol.
"""

from .base import InjectionStrategy
from .bearer import BearerStrategy, StripeStrategy, GitHubStrategy, OpenAIStrategy
from .aws_sigv4 import AWSSigV4Strategy
from .gemini import GeminiStrategy

__all__ = [
    "InjectionStrategy",
    "BearerStrategy",
    "StripeStrategy",
    "GitHubStrategy",
    "OpenAIStrategy",
    "AWSSigV4Strategy",
    "GeminiStrategy",
]
