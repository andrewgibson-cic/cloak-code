"""
Strategy module for credential injection.

This module exports all available injection strategies.
"""

from .base import InjectionStrategy
from .bearer import (
    BearerStrategy,
    StripeStrategy,
    GitHubStrategy,
    OpenAIStrategy,
)
from .aws_sigv4 import AWSSigV4Strategy
from .gemini import GeminiStrategy
from .ibm_openai import IBMOpenAIStrategy
from .mistral import MistralStrategy
from .git_pat import GitPATStrategy

__all__ = [
    'InjectionStrategy',
    'BearerStrategy',
    'StripeStrategy',
    'GitHubStrategy',
    'OpenAIStrategy',
    'AWSSigV4Strategy',
    'GeminiStrategy',
    'IBMOpenAIStrategy',
    'MistralStrategy',
    'GitPATStrategy',
]