"""
Git PAT (Personal Access Token) Injection Strategy

This strategy implements credential injection for git HTTPS operations using
Personal Access Tokens. It replaces the need for SSH key management by
intercepting git operations and injecting real PAT tokens from environment variables.

Supported Git Providers:
- GitHub (ghp_* tokens)
- GitLab (glpat-* tokens)
- Bitbucket (app passwords)
- Azure DevOps (PATs)
"""

import os
import re
import base64
from typing import Dict, Any, Optional
from mitmproxy import http

from .base import InjectionStrategy


class GitPATStrategy(InjectionStrategy):
    """
    Git Personal Access Token injection strategy.
    
    This strategy:
    1. Detects git HTTPS operations (git-upload-pack, git-receive-pack)
    2. Identifies the git provider (GitHub, GitLab, etc.)
    3. Injects the appropriate PAT token using HTTP Basic Auth
    4. Maintains zero-knowledge principle (agent never sees real tokens)
    """
    
    # Git provider patterns and their configuration
    PROVIDERS = {
        'github.com': {
            'env_var': 'GIT_GITHUB_PAT',
            'dummy_pattern': r'ghp_[a-zA-Z0-9]{36}DUMMY',
            'token_prefix': 'ghp_',
            'username': 'git',  # GitHub uses 'git' as username for HTTPS
        },
        'gitlab.com': {
            'env_var': 'GIT_GITLAB_PAT',
            'dummy_pattern': r'glpat-[a-zA-Z0-9_-]{20}DUMMY',
            'token_prefix': 'glpat-',
            'username': 'oauth2',  # GitLab uses 'oauth2' as username
        },
        'bitbucket.org': {
            'env_var': 'GIT_BITBUCKET_PAT',
            'dummy_pattern': r'DUMMY_BITBUCKET_[A-Z0-9]{20}',
            'token_prefix': '',
            'username': 'x-token-auth',  # Bitbucket app password username
        },
        'dev.azure.com': {
            'env_var': 'GIT_AZURE_PAT',
            'dummy_pattern': r'DUMMY_AZURE_[a-zA-Z0-9]{52}',
            'token_prefix': '',
            'username': 'user',  # Azure DevOps username (can be anything)
        },
    }
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize Git PAT strategy.
        
        Expected config keys:
        - providers: Dict mapping provider domains to PAT env var names (optional)
        - allowed_hosts: List of allowed git hosts (for security)
        """
        super().__init__(name, config)
        
        # Use custom provider config if provided, otherwise use defaults
        self.providers = config.get('providers', self.PROVIDERS)
        
        # Allowed hosts for security validation
        self.allowed_hosts = config.get('allowed_hosts', list(self.providers.keys()))
        
        # Cache loaded tokens
        self._token_cache: Dict[str, Optional[str]] = {}
    
    def _get_provider_for_host(self, host: str) -> Optional[str]:
        """
        Determine which git provider a host belongs to.
        
        Args:
            host: The request hostname
            
        Returns:
            Provider key (e.g., 'github.com') or None if not recognized
        """
        host_lower = host.lower()
        
        # Check for exact match or subdomain match
        for provider in self.providers.keys():
            if host_lower == provider or host_lower.endswith(f'.{provider}'):
                return provider
        
        return None
    
    def _load_pat_token(self, provider: str) -> Optional[str]:
        """
        Load PAT token for a specific provider from environment.
        
        Args:
            provider: Provider key (e.g., 'github.com')
            
        Returns:
            The real PAT token or None if not found
        """
        # Check cache first
        if provider in self._token_cache:
            return self._token_cache[provider]
        
        provider_config = self.providers.get(provider)
        if not provider_config:
            return None
        
        env_var = provider_config.get('env_var')
        if not env_var:
            return None
        
        token = os.environ.get(env_var)
        
        # Cache the result (including None to avoid repeated lookups)
        self._token_cache[provider] = token
        
        if not token:
            self.logger.warning(
                f"PAT token not found for {provider}. "
                f"Set environment variable: {env_var}"
            )
        
        return token
    
    def _is_git_request(self, flow: http.HTTPFlow) -> bool:
        """
        Determine if this is a git protocol request.
        
        Git HTTPS requests typically:
        - Have paths ending in .git or containing /info/refs or /git-upload-pack
        - Use GET/POST methods
        - May have User-Agent containing 'git'
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            True if this appears to be a git request
        """
        path = flow.request.path.lower()
        
        # Check for git-specific paths
        git_patterns = [
            r'/info/refs',
            r'/git-upload-pack',
            r'/git-receive-pack',
            r'\.git(/|$)',
        ]
        
        for pattern in git_patterns:
            if re.search(pattern, path):
                return True
        
        # Check User-Agent as secondary indicator
        user_agent = flow.request.headers.get('User-Agent', '').lower()
        if 'git' in user_agent and any(p in path for p in ['/info/', '/git-']):
            return True
        
        return False
    
    def _has_dummy_credentials(self, flow: http.HTTPFlow) -> bool:
        """
        Check if request contains dummy git credentials.
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            True if dummy credentials are detected
        """
        auth_header = flow.request.headers.get('Authorization', '')
        
        if not auth_header:
            return False
        
        # Check for Basic Auth with dummy patterns
        if auth_header.startswith('Basic '):
            try:
                # Decode Basic Auth
                encoded = auth_header[6:]  # Remove 'Basic ' prefix
                decoded = base64.b64decode(encoded).decode('utf-8')
                
                # Check if credentials contain dummy patterns
                for provider_config in self.providers.values():
                    dummy_pattern = provider_config.get('dummy_pattern', '')
                    if dummy_pattern and re.search(dummy_pattern, decoded):
                        return True
                
                # Also check for generic DUMMY markers
                if 'DUMMY' in decoded.upper():
                    return True
                    
            except Exception as e:
                self.logger.debug(f"Failed to decode Basic Auth: {e}")
        
        return False
    
    def detect(self, flow: http.HTTPFlow) -> bool:
        """
        Detect if this request should be handled by Git PAT strategy.
        
        Detection criteria:
        1. Request looks like a git operation
        2. Host is a known git provider
        3. Request contains dummy credentials
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            True if this request should be handled by this strategy
        """
        # Must be a git request
        if not self._is_git_request(flow):
            return False
        
        host = flow.request.pretty_host
        
        # Must be a known provider
        provider = self._get_provider_for_host(host)
        if not provider:
            return False
        
        # Must have dummy credentials
        if not self._has_dummy_credentials(flow):
            return False
        
        self.logger.debug(
            f"Detected git PAT request for {host} "
            f"(provider: {provider}, strategy: {self.name})"
        )
        return True
    
    def inject(self, flow: http.HTTPFlow) -> None:
        """
        Inject real PAT token into git request.
        
        Steps:
        1. Validate host is in allowlist
        2. Determine git provider
        3. Load real PAT token
        4. Create Basic Auth header with token
        5. Replace Authorization header
        
        Args:
            flow: The mitmproxy flow object to modify
            
        Raises:
            ValueError: If host validation fails or token not found
        """
        host = flow.request.pretty_host
        
        # Security check: validate host
        if not self.validate_host(flow, self.allowed_hosts):
            raise ValueError(
                f"Host {host} not in allowed hosts list "
                f"for Git PAT strategy '{self.name}'. Refusing to inject credentials."
            )
        
        # Determine provider
        provider = self._get_provider_for_host(host)
        if not provider:
            raise ValueError(
                f"Unable to determine git provider for host {host}"
            )
        
        provider_config = self.providers[provider]
        
        # Load real PAT token
        real_token = self._load_pat_token(provider)
        if not real_token:
            env_var = provider_config.get('env_var')
            raise ValueError(
                f"PAT token not found for {provider}. "
                f"Please set environment variable: {env_var}"
            )
        
        # Get provider-specific username
        username = provider_config.get('username', 'git')
        
        # Create Basic Auth header
        # Format: username:token
        credentials = f"{username}:{real_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode('ascii')
        
        # Replace Authorization header
        flow.request.headers['Authorization'] = f'Basic {encoded_credentials}'
        
        self.log_injection(
            flow,
            f"(Git PAT for {provider}, path: {flow.request.path})"
        )