#!/usr/bin/env python3
"""
Universal API Credential Injector - v2.0

This is a complete rewrite of the credential injection system using a modular
strategy architecture. It supports multiple authentication protocols including:
- AWS Signature Version 4 (SigV4)
- Bearer tokens (Stripe, OpenAI, GitHub)
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
from typing import Dict, List, Optional, Any
from pathlib import Path

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
    
    def _load_configuration(self):
        """
        Load configuration in order of preference:
        1. config.yaml (v2 format) - Strategy-based configuration
        2. credentials.yml (v1 format) - Legacy credential list
        3. Hardcoded defaults - Minimal backward compatibility
        """
        # Try v2 config first
        config_path = Path("/app/config.yaml")
        if not config_path.exists():
            config_path = Path("proxy/config.yaml")
        
        if config_path.exists():
            self._load_v2_config(config_path)
            return
        
        # Try v1 config (credentials.yml)
        v1_config_path = Path("/app/credentials.yml")
        if not v1_config_path.exists():
            v1_config_path = Path("credentials.yml")
        
        if v1_config_path.exists():
            self._load_v1_config(v1_config_path)
            return
        
        # Fall back to legacy hardcoded config
        self._load_legacy_config()
    
    def _load_v2_config(self, config_path: Path):
        """
        Load v2 strategy-based configuration from config.yaml.
        
        Args:
            config_path: Path to config.yaml file
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.config_mode = "v2"
            ctx.log.info(f"✓ Loading v2 configuration from {config_path}")
            
            # Load strategies
            strategy_configs = config.get('strategies', [])
            for strategy_config in strategy_configs:
                strategy_name = strategy_config.get('name')
                strategy_type = strategy_config.get('type')
                strategy_params = strategy_config.get('config', {})
                
                # Get strategy class
                strategy_class = self.STRATEGY_CLASSES.get(strategy_type)
                if not strategy_class:
                    ctx.log.warn(f"Unknown strategy type: {strategy_type}")
                    continue
                
                try:
                    # Instantiate strategy
                    strategy = strategy_class(strategy_name, strategy_params)
                    self.strategies.append(strategy)
                    ctx.log.info(f"  ✓ Loaded strategy: {strategy_name} ({strategy_type})")
                except Exception as e:
                    ctx.log.error(f"  ✗ Failed to load strategy {strategy_name}: {e}")
            
            # Load rules
            self.rules = config.get('rules', [])
            # Sort by priority (higher priority first)
            self.rules.sort(key=lambda r: r.get('priority', 0), reverse=True)
            ctx.log.info(f"✓ Loaded {len(self.rules)} injection rules")
            
            # Load settings
            settings = config.get('settings', {})
            self.fail_mode = settings.get('fail_mode', 'closed')
            self.block_telemetry = settings.get('block_telemetry', True)
            self.telemetry_domains = settings.get('telemetry_domains', [])
            
            ctx.log.info(
                f"✓ Configuration loaded: {len(self.strategies)} strategies, "
                f"{len(self.rules)} rules, fail_mode={self.fail_mode}"
            )
            
        except Exception as e:
            ctx.log.error(f"Failed to load v2 configuration: {e}")
            ctx.log.warn("Falling back to legacy configuration")
            self._load_legacy_config()
    
    def _load_v1_config(self, config_path: Path):
        """
        Load v1 credentials.yml format and convert to strategies.
        
        This provides backward compatibility with the original SafeClaude format.
        
        Args:
            config_path: Path to credentials.yml file
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.config_mode = "v1"
            ctx.log.info(f"✓ Loading v1 configuration from {config_path} (backward compatibility mode)")
            
            # Convert v1 credentials to Bearer strategies
            credentials = config.get('credentials', {})
            for service_name, cred_config in credentials.items():
                # Create a Bearer strategy for each credential
                strategy_config = {
                    'token': cred_config.get('env_var'),
                    'dummy_pattern': cred_config.get('dummy_token'),
                    'allowed_hosts': cred_config.get('allowed_hosts', []),
                }
                
                try:
                    strategy = BearerStrategy(f"v1_{service_name}", strategy_config)
                    self.strategies.append(strategy)
                    ctx.log.info(f"  ✓ Converted v1 credential: {service_name}")
                except Exception as e:
                    ctx.log.error(f"  ✗ Failed to convert v1 credential {service_name}: {e}")
            
            # Load v1 security settings
            security = config.get('security', {})
            self.telemetry_domains = security.get('telemetry_blocklist', [])
            self.block_telemetry = True
            
            ctx.log.info(f"✓ Converted {len(self.strategies)} v1 credentials to strategies")
            
        except Exception as e:
            ctx.log.error(f"Failed to load v1 configuration: {e}")
            ctx.log.warn("Falling back to legacy configuration")
            self._load_legacy_config()
    
    def _load_legacy_config(self):
        """
        Load hardcoded legacy configuration for basic functionality.
        
        This is the last resort fallback for systems with no configuration files.
        """
        self.config_mode = "legacy"
        ctx.log.warn("⚠ Using legacy hardcoded configuration (limited functionality)")
        
        # Create basic Bearer strategies for common services
        legacy_configs = [
            {
                'name': 'openai-legacy',
                'type': 'openai',
                'config': {'token': 'REAL_OPENAI_API_KEY'}
            },
            {
                'name': 'github-legacy',
                'type': 'github',
                'config': {'token': 'REAL_GITHUB_TOKEN'}
            },
        ]
        
        for config in legacy_configs:
            try:
                strategy_class = self.STRATEGY_CLASSES.get(config['type'])
                if strategy_class:
                    strategy = strategy_class(config['name'], config['config'])
                    self.strategies.append(strategy)
            except Exception as e:
                ctx.log.debug(f"Failed to load legacy strategy {config['name']}: {e}")
        
        # Basic telemetry blocking
        self.telemetry_domains = [
            'telemetry.anthropic.com',
            'sentry.io',
            'segment.com',
        ]
        self.block_telemetry = True
        
        ctx.log.info(f"✓ Loaded {len(self.strategies)} legacy strategies")
    
    def _is_telemetry_request(self, host: str) -> bool:
        """
        Check if request is to a telemetry/analytics endpoint.
        
        Args:
            host: The destination hostname
            
        Returns:
            True if this is a telemetry request
        """
        if not self.block_telemetry:
            return False
        
        host_lower = host.lower()
        for domain in self.telemetry_domains:
            domain_lower = domain.lower()
            
            # Exact match or subdomain match
            if host_lower == domain_lower or host_lower.endswith(f".{domain_lower}"):
                return True
            
            # Wildcard match (*.example.com)
            if domain_lower.startswith("*."):
                base_domain = domain_lower[2:]
                if host_lower.endswith(base_domain):
                    return True
        
        return False
    
    def _find_matching_strategy(self, flow: http.HTTPFlow) -> Optional[InjectionStrategy]:
        """
        Find the first strategy that matches this request.
        
        For v2 config: Uses rules to determine strategy
        For v1/legacy: Directly queries strategies
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            Matching strategy instance or None
        """
        if self.config_mode == "v2" and self.rules:
            # Use rule-based matching
            return self._find_strategy_by_rules(flow)
        else:
            # Use direct strategy detection (v1/legacy)
            return self._find_strategy_by_detection(flow)
    
    def _find_strategy_by_rules(self, flow: http.HTTPFlow) -> Optional[InjectionStrategy]:
        """
        Match request to strategy using v2 rules configuration.
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            Matching strategy or None
        """
        host = flow.request.pretty_host
        auth_header = flow.request.headers.get("Authorization", "")
        
        # Evaluate rules in priority order
        for rule in self.rules:
            rule_name = rule.get('name', 'unnamed')
            
            # Check domain match
            domain_regex = rule.get('domain_regex')
            if domain_regex and not re.search(domain_regex, host, re.IGNORECASE):
                continue
            
            # Check trigger pattern match
            trigger_regex = rule.get('trigger_header_regex')
            if trigger_regex and not re.search(trigger_regex, auth_header, re.IGNORECASE):
                continue
            
            # Find the strategy
            strategy_name = rule.get('strategy')
            for strategy in self.strategies:
                if strategy.name == strategy_name:
                    self.logger.debug(f"Rule '{rule_name}' matched, using strategy '{strategy_name}'")
                    return strategy
        
        return None
    
    def _find_strategy_by_detection(self, flow: http.HTTPFlow) -> Optional[InjectionStrategy]:
        """
        Match request to strategy by asking each strategy to detect.
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            First matching strategy or None
        """
        for strategy in self.strategies:
            try:
                if strategy.detect(flow):
                    return strategy
            except Exception as e:
                self.logger.error(f"Strategy {strategy.name} detection failed: {e}")
        
        return None
    
    @concurrent
    def request(self, flow: http.HTTPFlow) -> None:
        """
        Main request handler called by mitmproxy.
        
        Process flow:
        1. Check for telemetry (block if needed)
        2. Find matching strategy
        3. Inject credentials via strategy
        4. Handle errors based on fail_mode
        
        Args:
            flow: The mitmproxy flow object
        """
        self.stats["requests_processed"] += 1
        host = flow.request.pretty_host
        
        # Block telemetry requests
        if self._is_telemetry_request(host):
            ctx.log.info(f"🚫 Blocked telemetry request to: {host}")
            flow.response = http.Response.make(
                418,  # I'm a teapot
                b"Telemetry blocked by Universal Injector",
                {"Content-Type": "text/plain"}
            )
            self.stats["telemetry_blocked"] += 1
            return
        
        # Find matching strategy
        strategy = self._find_matching_strategy(flow)
        
        if not strategy:
            # No strategy matched - pass through
            self.logger.debug(f"No strategy matched for {host}, passing through")
            return
        
        # Inject credentials using strategy
        try:
            strategy.inject(flow)
            self.stats["credentials_injected"] += 1
            
        except Exception as e:
            self.stats["strategy_errors"] += 1
            self.logger.error(f"Strategy {strategy.name} injection failed: {e}")
            
            # Handle based on fail_mode
            if self.fail_mode == "closed":
                # Fail closed: block the request
                flow.response = http.Response.make(
                    500,
                    f"Credential injection failed: {str(e)}".encode(),
                    {"Content-Type": "text/plain"}
                )
                self.stats["requests_blocked"] += 1
            else:
                # Fail open: allow request to pass through
                self.logger.warn(f"Fail-open mode: allowing request to {host} despite injection error")
    
    def done(self):
        """Called when mitmproxy shuts down. Print statistics."""
        ctx.log.info("=" * 70)
        ctx.log.info("Universal API Credential Injector v2.0 - Session Statistics")
        ctx.log.info("=" * 70)
        ctx.log.info(f"Configuration Mode: {self.config_mode}")
        ctx.log.info(f"Strategies Loaded: {len(self.strategies)}")
        ctx.log.info(f"Rules Loaded: {len(self.rules)}")
        ctx.log.info("-" * 70)
        ctx.log.info(f"Total Requests Processed: {self.stats['requests_processed']}")
        ctx.log.info(f"Credentials Injected: {self.stats['credentials_injected']}")
        ctx.log.info(f"Requests Blocked (Security): {self.stats['requests_blocked']}")
        ctx.log.info(f"Telemetry Blocked: {self.stats['telemetry_blocked']}")
        ctx.log.info(f"Strategy Errors: {self.stats['strategy_errors']}")
        ctx.log.info("=" * 70)


# Create global addon instance for mitmproxy
addons = [UniversalInjector()]
