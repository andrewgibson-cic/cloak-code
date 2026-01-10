#!/usr/bin/env python3
"""
SafeClaude Credential Injection Proxy Script

This script runs as a mitmproxy addon to intercept HTTP/HTTPS requests
from the agent container and inject real API credentials in place of
dummy tokens, while enforcing strict host whitelisting for security.

Security Features:
- Zero-knowledge: Agent never sees real credentials
- Host whitelisting: Credentials only injected for approved destinations
- No credential logging: Real tokens never written to logs
- Request blocking: Unauthorized destinations receive 403 responses
"""

import os
import sys
from typing import Optional
from mitmproxy import http, ctx
from mitmproxy.script import concurrent


class CredentialInjector:
    """
    Intercepts HTTP requests and replaces dummy tokens with real credentials
    while enforcing strict security policies.
    """
    
    # Define dummy token patterns that the agent uses
    DUMMY_TOKENS = {
        "DUMMY_OPENAI_KEY": "REAL_OPENAI_API_KEY",
        "DUMMY_GITHUB_TOKEN": "REAL_GITHUB_TOKEN",
        "DUMMY_ANTHROPIC_KEY": "REAL_ANTHROPIC_API_KEY",
        "DUMMY_AWS_ACCESS_KEY": "REAL_AWS_ACCESS_KEY_ID",
        "DUMMY_AWS_SECRET_KEY": "REAL_AWS_SECRET_ACCESS_KEY",
    }
    
    # Strict whitelist: Map dummy tokens to allowed destination hosts
    # This prevents credential exfiltration to unauthorized servers
    HOST_WHITELIST = {
        "DUMMY_OPENAI_KEY": [
            "api.openai.com",
            "openai.com",
        ],
        "DUMMY_GITHUB_TOKEN": [
            "api.github.com",
            "github.com",
            "github.ibm.com",  # IBM Enterprise GitHub
            "raw.githubusercontent.com",
        ],
        "DUMMY_ANTHROPIC_KEY": [
            "api.anthropic.com",
            "anthropic.com",
        ],
        "DUMMY_AWS_ACCESS_KEY": [
            "amazonaws.com",
            "aws.amazon.com",
        ],
        "DUMMY_AWS_SECRET_KEY": [
            "amazonaws.com",
            "aws.amazon.com",
        ],
    }
    
    # Known telemetry/tracking endpoints to block
    TELEMETRY_BLOCKLIST = [
        "telemetry.anthropic.com",
        "analytics.anthropic.com",
        "sentry.io",
        "segment.com",
        "mixpanel.com",
        "amplitude.com",
        "google-analytics.com",
        "googletagmanager.com",
    ]
    
    def __init__(self):
        """Initialize the credential injector."""
        self.stats = {
            "requests_processed": 0,
            "credentials_injected": 0,
            "requests_blocked": 0,
            "telemetry_blocked": 0,
        }
        
        # Validate that real credentials are available
        self._validate_environment()
    
    def _validate_environment(self):
        """
        Validate that required environment variables are set.
        Warns if credentials are missing but doesn't fail (allows partial setup).
        """
        missing = []
        for env_var in self.DUMMY_TOKENS.values():
            if not os.environ.get(env_var):
                missing.append(env_var)
        
        if missing:
            ctx.log.warn(
                f"Missing environment variables: {', '.join(missing)}. "
                "Credential injection will fail for these services."
            )
    
    def _is_telemetry_request(self, host: str) -> bool:
        """Check if the request is to a known telemetry endpoint."""
        host_lower = host.lower()
        return any(blocked in host_lower for blocked in self.TELEMETRY_BLOCKLIST)
    
    def _is_host_whitelisted(self, dummy_token: str, host: str) -> bool:
        """
        Verify that the destination host is authorized for this credential type.
        
        Args:
            dummy_token: The dummy token identifier
            host: The destination hostname
            
        Returns:
            True if the host is whitelisted for this credential
        """
        if dummy_token not in self.HOST_WHITELIST:
            return False
        
        allowed_hosts = self.HOST_WHITELIST[dummy_token]
        host_lower = host.lower()
        
        # Check if host matches any whitelisted pattern
        for allowed in allowed_hosts:
            if host_lower == allowed or host_lower.endswith(f".{allowed}"):
                return True
        
        return False
    
    def _get_real_credential(self, dummy_token: str) -> Optional[str]:
        """
        Retrieve the real credential from environment variables.
        
        Args:
            dummy_token: The dummy token to replace
            
        Returns:
            The real credential value, or None if not found
        """
        env_var = self.DUMMY_TOKENS.get(dummy_token)
        if not env_var:
            return None
        
        return os.environ.get(env_var)
    
    def _inject_credentials_in_header(
        self, 
        flow: http.HTTPFlow, 
        header_name: str
    ) -> bool:
        """
        Replace dummy tokens in a specific header with real credentials.
        
        Args:
            flow: The mitmproxy flow object
            header_name: The header to inspect (e.g., "Authorization")
            
        Returns:
            True if credential was injected, False otherwise
        """
        if header_name not in flow.request.headers:
            return False
        
        header_value = flow.request.headers[header_name]
        host = flow.request.pretty_host
        
        # Check each known dummy token
        for dummy_token, env_var in self.DUMMY_TOKENS.items():
            if dummy_token in header_value:
                # Security check: Verify host is whitelisted
                if not self._is_host_whitelisted(dummy_token, host):
                    ctx.log.warn(
                        f"SECURITY: Blocked credential injection for {dummy_token} "
                        f"to unauthorized host: {host}"
                    )
                    flow.response = http.Response.make(
                        403,
                        b"Forbidden: Host not whitelisted for this credential type",
                        {"Content-Type": "text/plain"}
                    )
                    self.stats["requests_blocked"] += 1
                    return False
                
                # Get real credential
                real_credential = self._get_real_credential(dummy_token)
                if not real_credential:
                    ctx.log.error(
                        f"Cannot inject credential: {env_var} not set in environment"
                    )
                    flow.response = http.Response.make(
                        500,
                        b"Internal Error: Credential not configured",
                        {"Content-Type": "text/plain"}
                    )
                    return False
                
                # Inject real credential
                new_header_value = header_value.replace(dummy_token, real_credential)
                flow.request.headers[header_name] = new_header_value
                
                # Log injection (without revealing the real credential)
                ctx.log.info(
                    f"✓ Credential injected: {dummy_token} -> {env_var} "
                    f"for {host}"
                )
                self.stats["credentials_injected"] += 1
                return True
        
        return False
    
    @concurrent
    def request(self, flow: http.HTTPFlow) -> None:
        """
        Process each HTTP request.
        
        This is the main hook called by mitmproxy for every request.
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
        
        # Check Authorization header (most common)
        if self._inject_credentials_in_header(flow, "Authorization"):
            return
        
        # Check other common authentication headers
        for header in ["X-API-Key", "X-Auth-Token", "api-key"]:
            if self._inject_credentials_in_header(flow, header):
                return
        
        # Check query parameters (some APIs use tokens in URL)
        if flow.request.query:
            for dummy_token in self.DUMMY_TOKENS.keys():
                for param_name, param_value in flow.request.query.items():
                    if dummy_token in param_value:
                        if not self._is_host_whitelisted(dummy_token, host):
                            ctx.log.warn(
                                f"SECURITY: Blocked credential in query param "
                                f"to unauthorized host: {host}"
                            )
                            flow.response = http.Response.make(
                                403,
                                b"Forbidden: Host not whitelisted",
                                {"Content-Type": "text/plain"}
                            )
                            self.stats["requests_blocked"] += 1
                            return
                        
                        real_credential = self._get_real_credential(dummy_token)
                        if real_credential:
                            new_value = param_value.replace(dummy_token, real_credential)
                            flow.request.query[param_name] = new_value
                            ctx.log.info(
                                f"✓ Credential injected in query param for {host}"
                            )
                            self.stats["credentials_injected"] += 1
                            return
    
    def done(self):
        """Called when mitmproxy shuts down. Print statistics."""
        ctx.log.info("=" * 60)
        ctx.log.info("SafeClaude Proxy Statistics:")
        ctx.log.info(f"  Total requests processed: {self.stats['requests_processed']}")
        ctx.log.info(f"  Credentials injected: {self.stats['credentials_injected']}")
        ctx.log.info(f"  Requests blocked (security): {self.stats['requests_blocked']}")
        ctx.log.info(f"  Telemetry blocked: {self.stats['telemetry_blocked']}")
        ctx.log.info("=" * 60)


# Create global instance
addons = [CredentialInjector()]
