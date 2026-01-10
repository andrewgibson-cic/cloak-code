#!/usr/bin/env python3
"""
SafeClaude Universal Credential Injection Proxy Script

This script runs as a mitmproxy addon to intercept HTTP/HTTPS requests
from the agent container and inject real API credentials in place of
dummy tokens, while enforcing strict host whitelisting for security.

NOW WITH DYNAMIC CONFIGURATION SUPPORT - Add new credentials in credentials.yml!

Security Features:
- Zero-knowledge: Agent never sees real credentials
- Host whitelisting: Credentials only injected for approved destinations
- No credential logging: Real tokens never written to logs
- Request blocking: Unauthorized destinations receive 403 responses
- Dynamic configuration: No code changes needed to add new services
"""

import os
import sys
import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from mitmproxy import http, ctx
from mitmproxy.script import concurrent


@dataclass
class CredentialConfig:
    """Represents a single credential configuration."""
    service_name: str
    display_name: str
    dummy_token: str
    env_var: str
    header_locations: List[Dict[str, str]] = field(default_factory=list)
    query_param_names: List[str] = field(default_factory=list)
    allowed_hosts: List[str] = field(default_factory=list)
    docs_url: str = ""
    requires_signature: bool = False


class UniversalCredentialInjector:
    """
    Dynamically loads credential configurations from YAML
    and injects them based on runtime rules.
    
    This replaces the old hardcoded DUMMY_TOKENS and HOST_WHITELIST
    dictionaries with a flexible, configuration-driven approach.
    """
    
    def __init__(self):
        """Initialize the universal credential injector."""
        self.credentials: Dict[str, CredentialConfig] = {}
        self.dummy_to_service: Dict[str, str] = {}  # Quick lookup: dummy_token -> service_name
        self.telemetry_blocklist: List[str] = []
        self.unknown_host_policy: str = "block"
        self.verbose_logging: bool = False
        
        self.stats = {
            "requests_processed": 0,
            "credentials_injected": 0,
            "requests_blocked": 0,
            "telemetry_blocked": 0,
        }
        
        # Load configuration and validate environment
        self._load_config()
        self._validate_environment()
    
    def _load_config(self):
        """
        Load credentials from YAML configuration file.
        Falls back to legacy hardcoded values if config file not found.
        """
        config_path = os.environ.get(
            'CREDENTIAL_CONFIG_PATH', 
            '/app/credentials.yml'
        )
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Parse credential definitions
            for service_name, cred_data in config.get('credentials', {}).items():
                cred = CredentialConfig(
                    service_name=service_name,
                    display_name=cred_data.get('display_name', service_name),
                    dummy_token=cred_data['dummy_token'],
                    env_var=cred_data['env_var'],
                    header_locations=cred_data.get('header_locations', []),
                    query_param_names=cred_data.get('query_param_names', []),
                    allowed_hosts=cred_data.get('allowed_hosts', []),
                    docs_url=cred_data.get('docs_url', ''),
                    requires_signature=cred_data.get('requires_signature', False)
                )
                
                self.credentials[service_name] = cred
                self.dummy_to_service[cred.dummy_token] = service_name
            
            # Load security settings
            security = config.get('security', {})
            self.telemetry_blocklist = security.get('telemetry_blocklist', [])
            self.unknown_host_policy = security.get('unknown_host_policy', 'block')
            self.verbose_logging = security.get('verbose_logging', False)
            
            ctx.log.info(f"✓ Loaded {len(self.credentials)} credential configurations from {config_path}")
            
            if self.verbose_logging:
                ctx.log.info("Configured services:")
                for service_name, cred in self.credentials.items():
                    ctx.log.info(f"  - {cred.display_name} ({service_name})")
            
        except FileNotFoundError:
            ctx.log.warn(
                f"Configuration file not found: {config_path}. "
                "Falling back to legacy hardcoded credentials."
            )
            self._load_legacy_config()
            
        except Exception as e:
            ctx.log.error(f"Failed to load credentials.yml: {e}")
            ctx.log.warn("Falling back to legacy hardcoded credentials.")
            self._load_legacy_config()
    
    def _load_legacy_config(self):
        """
        Fallback to legacy hardcoded configuration for backward compatibility.
        This maintains support for systems without credentials.yml.
        """
        legacy_credentials = {
            'openai': CredentialConfig(
                service_name='openai',
                display_name='OpenAI API',
                dummy_token='DUMMY_OPENAI_KEY',
                env_var='REAL_OPENAI_API_KEY',
                header_locations=[{'name': 'Authorization', 'format': 'Bearer {token}'}],
                allowed_hosts=['api.openai.com', 'openai.com']
            ),
            'github': CredentialConfig(
                service_name='github',
                display_name='GitHub Token',
                dummy_token='DUMMY_GITHUB_TOKEN',
                env_var='REAL_GITHUB_TOKEN',
                header_locations=[
                    {'name': 'Authorization', 'format': 'token {token}'},
                    {'name': 'X-GitHub-Token', 'format': '{token}'}
                ],
                allowed_hosts=['api.github.com', 'github.com', 'github.ibm.com', 'raw.githubusercontent.com']
            ),
            'anthropic': CredentialConfig(
                service_name='anthropic',
                display_name='Anthropic API',
                dummy_token='DUMMY_ANTHROPIC_KEY',
                env_var='REAL_ANTHROPIC_API_KEY',
                header_locations=[{'name': 'x-api-key', 'format': '{token}'}],
                allowed_hosts=['api.anthropic.com', 'anthropic.com']
            ),
            'aws_access': CredentialConfig(
                service_name='aws_access',
                display_name='AWS Access Key',
                dummy_token='DUMMY_AWS_ACCESS_KEY',
                env_var='REAL_AWS_ACCESS_KEY_ID',
                header_locations=[{'name': 'Authorization', 'format': 'AWS4-HMAC-SHA256 Credential={token}'}],
                allowed_hosts=['*.amazonaws.com', 'aws.amazon.com']
            ),
            'aws_secret': CredentialConfig(
                service_name='aws_secret',
                display_name='AWS Secret Key',
                dummy_token='DUMMY_AWS_SECRET_KEY',
                env_var='REAL_AWS_SECRET_ACCESS_KEY',
                allowed_hosts=['*.amazonaws.com', 'aws.amazon.com']
            ),
        }
        
        for service_name, cred in legacy_credentials.items():
            self.credentials[service_name] = cred
            self.dummy_to_service[cred.dummy_token] = service_name
        
        # Legacy telemetry blocklist
        self.telemetry_blocklist = [
            'telemetry.anthropic.com',
            'analytics.anthropic.com',
            'sentry.io',
            'segment.com',
            'mixpanel.com',
            'amplitude.com',
            'google-analytics.com',
            'googletagmanager.com',
        ]
        
        ctx.log.info(f"✓ Loaded {len(self.credentials)} legacy credential configurations")
    
    def _validate_environment(self):
        """
        Validate that required environment variables are set.
        Warns if credentials are missing but doesn't fail (allows partial setup).
        """
        missing = []
        configured = []
        
        for service_name, cred in self.credentials.items():
            if os.environ.get(cred.env_var):
                configured.append(cred.display_name)
            else:
                missing.append(f"{cred.env_var} ({cred.display_name})")
        
        if configured:
            ctx.log.info(f"✓ {len(configured)} credentials configured and available")
            if self.verbose_logging:
                for name in configured:
                    ctx.log.info(f"  ✓ {name}")
        
        if missing:
            ctx.log.warn(
                f"⚠ {len(missing)} credentials not configured. "
                "Injection will fail for these services:"
            )
            for env_var in missing:
                ctx.log.warn(f"  ✗ {env_var}")
    
    def _is_telemetry_request(self, host: str) -> bool:
        """Check if the request is to a known telemetry endpoint."""
        host_lower = host.lower()
        return any(blocked in host_lower for blocked in self.telemetry_blocklist)
    
    def _is_host_whitelisted(self, cred: CredentialConfig, host: str) -> bool:
        """
        Verify that the destination host is authorized for this credential type.
        Supports exact matches, subdomain matches, and wildcard patterns (*.example.com).
        
        Args:
            cred: The credential configuration
            host: The destination hostname
            
        Returns:
            True if the host is whitelisted for this credential
        """
        host_lower = host.lower()
        
        for allowed in cred.allowed_hosts:
            allowed_lower = allowed.lower()
            
            # Exact match
            if host_lower == allowed_lower:
                return True
            
            # Wildcard subdomain match (*.example.com)
            if allowed_lower.startswith('*.'):
                domain = allowed_lower[2:]  # Remove "*."
                if host_lower.endswith(f".{domain}") or host_lower == domain:
                    return True
            
            # Standard subdomain check (example.com matches api.example.com)
            if host_lower.endswith(f".{allowed_lower}"):
                return True
        
        return False
    
    def _get_real_credential(self, cred: CredentialConfig) -> Optional[str]:
        """
        Retrieve the real credential from environment variables.
        
        Args:
            cred: The credential configuration
            
        Returns:
            The real credential value, or None if not found
        """
        return os.environ.get(cred.env_var)
    
    def _inject_credential_in_headers(
        self, 
        flow: http.HTTPFlow,
        cred: CredentialConfig
    ) -> bool:
        """
        Replace dummy tokens in headers with real credentials.
        Supports multiple header locations and format templating.
        
        Args:
            flow: The mitmproxy flow object
            cred: The credential configuration
            
        Returns:
            True if credential was injected, False otherwise
        """
        host = flow.request.pretty_host
        
        for header_config in cred.header_locations:
            header_name = header_config['name']
            format_template = header_config.get('format', '{token}')
            
            if header_name not in flow.request.headers:
                continue
            
            header_value = flow.request.headers[header_name]
            
            # Check if dummy token is present
            if cred.dummy_token not in header_value:
                continue
            
            # Security check: Verify host is whitelisted
            if not self._is_host_whitelisted(cred, host):
                ctx.log.warn(
                    f"SECURITY: Blocked {cred.display_name} credential "
                    f"to unauthorized host: {host}"
                )
                flow.response = http.Response.make(
                    403,
                    f"Forbidden: {host} not whitelisted for {cred.display_name}".encode(),
                    {"Content-Type": "text/plain"}
                )
                self.stats["requests_blocked"] += 1
                return False
            
            # Get real credential
            real_credential = self._get_real_credential(cred)
            if not real_credential:
                ctx.log.error(
                    f"Cannot inject credential: {cred.env_var} not set in environment. "
                    f"See: {cred.docs_url}"
                )
                flow.response = http.Response.make(
                    500,
                    f"Internal Error: {cred.display_name} not configured".encode(),
                    {"Content-Type": "text/plain"}
                )
                return False
            
            # Apply format template and inject
            formatted_credential = format_template.replace('{token}', real_credential)
            
            # If the dummy token is the entire value, replace it entirely
            # Otherwise, do a string replacement
            if header_value == cred.dummy_token:
                new_header_value = formatted_credential
            else:
                new_header_value = header_value.replace(cred.dummy_token, formatted_credential)
            
            flow.request.headers[header_name] = new_header_value
            
            # Log injection (without revealing the real credential)
            ctx.log.info(
                f"✓ {cred.display_name} credential injected for {host} "
                f"(header: {header_name})"
            )
            self.stats["credentials_injected"] += 1
            return True
        
        return False
    
    def _inject_credential_in_query_params(
        self,
        flow: http.HTTPFlow,
        cred: CredentialConfig
    ) -> bool:
        """
        Replace dummy tokens in query parameters with real credentials.
        
        Args:
            flow: The mitmproxy flow object
            cred: The credential configuration
            
        Returns:
            True if credential was injected, False otherwise
        """
        if not flow.request.query or not cred.query_param_names:
            return False
        
        host = flow.request.pretty_host
        
        for param_name in cred.query_param_names:
            if param_name not in flow.request.query:
                continue
            
            param_value = flow.request.query[param_name]
            
            if cred.dummy_token not in param_value:
                continue
            
            # Security check
            if not self._is_host_whitelisted(cred, host):
                ctx.log.warn(
                    f"SECURITY: Blocked {cred.display_name} in query param "
                    f"to unauthorized host: {host}"
                )
                flow.response = http.Response.make(
                    403,
                    f"Forbidden: Host not whitelisted".encode(),
                    {"Content-Type": "text/plain"}
                )
                self.stats["requests_blocked"] += 1
                return False
            
            # Get real credential
            real_credential = self._get_real_credential(cred)
            if not real_credential:
                ctx.log.error(f"{cred.env_var} not set in environment")
                flow.response = http.Response.make(
                    500,
                    f"Internal Error: {cred.display_name} not configured".encode(),
                    {"Content-Type": "text/plain"}
                )
                return False
            
            # Inject credential
            new_param_value = param_value.replace(cred.dummy_token, real_credential)
            flow.request.query[param_name] = new_param_value
            
            ctx.log.info(
                f"✓ {cred.display_name} credential injected in query param for {host}"
            )
            self.stats["credentials_injected"] += 1
            return True
        
        return False
    
    @concurrent
    def request(self, flow: http.HTTPFlow) -> None:
        """
        Process each HTTP request with dynamic credential injection.
        
        This is the main hook called by mitmproxy for every request.
        It iterates through all configured credentials and attempts injection.
        """
        self.stats["requests_processed"] += 1
        host = flow.request.pretty_host
        
        # Block known telemetry endpoints
        if self._is_telemetry_request(host):
            ctx.log.info(f"🚫 Blocked telemetry request to: {host}")
            flow.response = http.Response.make(
                418,  # I'm a teapot (playful status for blocked requests)
                b"Telemetry blocked by SafeClaude proxy",
                {"Content-Type": "text/plain"}
            )
            self.stats["telemetry_blocked"] += 1
            return
        
        # Try to inject credentials from any configured service
        # Check headers first (most common)
        for cred in self.credentials.values():
            if self._inject_credential_in_headers(flow, cred):
                return
        
        # Check query parameters
        for cred in self.credentials.values():
            if self._inject_credential_in_query_params(flow, cred):
                return
        
        # No credentials were injected - request passes through as-is
        if self.verbose_logging:
            ctx.log.info(f"→ Passing through request to {host} (no credential injection needed)")
    
    def done(self):
        """Called when mitmproxy shuts down. Print statistics."""
        ctx.log.info("=" * 60)
        ctx.log.info("SafeClaude Proxy Statistics:")
        ctx.log.info(f"  Total requests processed: {self.stats['requests_processed']}")
        ctx.log.info(f"  Credentials injected: {self.stats['credentials_injected']}")
        ctx.log.info(f"  Requests blocked (security): {self.stats['requests_blocked']}")
        ctx.log.info(f"  Telemetry blocked: {self.stats['telemetry_blocked']}")
        ctx.log.info("=" * 60)


# Create global instance for mitmproxy
addons = [UniversalCredentialInjector()]
