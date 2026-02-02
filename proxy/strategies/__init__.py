"""
Credential Injection Strategies

This module provides pluggable authentication strategies for different
API providers and authentication protocols.
"""

from .base import InjectionStrategy
from .bearer import BearerStrategy, StripeStrategy, GitHubStrategy, OpenAIStrategy
from .aws_sigv4 import AWSSigV4Strategy
from .gemini import GeminiStrategy
from .ibm_openai import IBMOpenAIStrategy
from .mistral import MistralStrategy

__all__ = [
    "InjectionStrategy",
    "BearerStrategy",
    "StripeStrategy",
    "GitHubStrategy",
    "OpenAIStrategy",
    "AWSSigV4Strategy",
    "GeminiStrategy",
    "IBMOpenAIStrategy",
    "MistralStrategy",
]
