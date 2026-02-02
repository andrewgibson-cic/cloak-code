#!/usr/bin/env python3
"""
Universal API Credential Injector - v2.0

This is a complete rewrite of the credential injection system using a modular
strategy architecture. It supports multiple authentication protocols including:
- AWS Signature Version 4 (SigV4)
- Bearer tokens (Stripe, OpenAI, GitHub)
- Git PAT tokens (GitHub, GitLab, Bitbucket, Azure DevOps)
- HMAC signing (Binance, crypto exchanges)

Features:
- Dynamic configuration via config.yaml
- Pluggable strategy architecture
- Backward compatibility with v1 (fallback mode)
- Enhanced security validation
- Comprehensive logging

Architecture:
- Each authentication protocol is implemented as a Strategy class
- Rules in config.yaml determine which strategy applies to each request
- Strategies are evaluated in priority order
- Fail-closed by default for security
"""

import os
import sys
import yaml
import re
import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from mitmproxy import http, ctx
from mitmproxy.script import concurrent

# Import strategy classes
try:
    from strategies import (
        InjectionStrategy,
        BearerStrategy,
        StripeStrategy,
        GitHubStrategy,
        OpenAIStrategy,
        AWSSigV4Strategy,
        GeminiStrategy,
        GitPATStrategy,
    )
    STRATEGIES_AVAILABLE = True
except ImportError as e:
    ctx.log.error(f"Failed to import strategies: {e}")
    STRATEGIES_AVAILABLE = False


class UniversalInjector:
    """
    Main orchestrator for the Universal API Credential Injector.
    
    Responsibilities:
    - Load configuration from config.yaml
    - Initialize strategy instances
    - Match requests to appropriate strategies
    - Handle telemetry blocking
    - Provide backward compatibility
    """
    
    # Strategy type mapping
    STRATEGY_CLASSES = {
        "bearer": BearerStrategy,
        "stripe": StripeStrategy,
        "github": GitHubStrategy,
        "openai": OpenAIStrategy,
        "aws_sigv4": AWSSigV4Strategy,
        "gemini": GeminiStrategy,
        "git_pat": GitPATStrategy,
    }
    
    def __init__(self):
        """Initialize the universal injector."""
        self.strategies: List[InjectionStrategy] = []
        self.rules: List[Dict[str, Any]] = []
        self.telemetry_domains: List[str] = []
        self.fail_mode: str = "closed"
        self.block_telemetry: bool = True
        
        # Statistics
        self.stats = {
            "requests_processed": 0,
            "credentials_injected": 0,
            "requests_blocked": 0,
            "telemetry_blocked": 0,
            "strategy_errors": 0,
        }
        
        # Configuration mode
        self.config_mode: str = "unknown"  # v2, v1, or legacy
        
        # Setup logging
        self._setup_logging()
        
        # Load configuration
        self._load_configuration()
    
    def _setup_logging(self):
        """Configure logging based on environment."""
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        self.logger = logging.getLogger("UniversalInjector")
        
        # Setup persistent log files
        self.log_dir = Path("/logs")
        self.log_dir.mkdir(exist_ok=True)
        
        self.injection_log = self.log_dir / "proxy_injections.log"
        self.security_log = self.log_dir / "security_events.log"
        self.audit_log = self.log_dir / "audit.json"

# Backward compatibility alias for v1 tests
CredentialInjector = UniversalInjector
