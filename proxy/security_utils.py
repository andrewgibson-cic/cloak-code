"""
Security utilities for CloakCode proxy.

Provides credential scrubbing, input validation, rate limiting, and DNS protection.
"""

import re
import logging
import time
import socket
from typing import Any, Dict, List, Pattern, Optional, Tuple
from functools import wraps


class CredentialScrubber:
    """Scrubs sensitive credentials from logs, error messages, and other outputs."""
    
    CREDENTIAL_PATTERNS: List[Pattern] = [
        re.compile(r'AKIA[0-9A-Z]{16}', re.IGNORECASE),
        re.compile(r'aws_secret_access_key["\s:=]+[A-Za-z0-9/+=]{40}', re.IGNORECASE),
        re.compile(r'sk-[a-zA-Z0-9]{32,}', re.IGNORECASE),
        re.compile(r'ghp_[a-zA-Z0-9]{36,}', re.IGNORECASE),
        re.compile(r'glpat-[a-zA-Z0-9_-]{20,}', re.IGNORECASE),
        re.compile(r'AIza[a-zA-Z0-9_-]{35}', re.IGNORECASE),
        re.compile(r'Bearer\s+[a-zA-Z0-9_\-\.]{20,}', re.IGNORECASE),
        re.compile(r'Authorization:\s*Bearer\s+[^\s]+', re.IGNORECASE),
        re.compile(r'Basic\s+[A-Za-z0-9+/=]{20,}', re.IGNORECASE),
        re.compile(r'Authorization:\s*Basic\s+[^\s]+', re.IGNORECASE),
        re.compile(r'api[_-]?key["\s:=]+[a-zA-Z0-9_\-]{20,}', re.IGNORECASE),
        re.compile(r'token["\s:=]+[a-zA-Z0-9_\-]{20,}', re.IGNORECASE),
        re.compile(r'secret["\s:=]+[a-zA-Z0-9_\-]{20,}', re.IGNORECASE),
        re.compile(r'password["\s:=]+[^\s"\']{8,}', re.IGNORECASE),
    ]
    
    REDACTED = "[REDACTED]"
    
    @classmethod
    def scrub_string(cls, text: str) -> str:
        """Scrub credentials from a string."""
        if not text:
            return text
        scrubbed = text
        for pattern in cls.CREDENTIAL_PATTERNS:
            scrubbed = pattern.sub(cls.REDACTED, scrubbed)
        return scrubbed
    
    @classmethod
    def scrub_dict(cls,  Dict[str, Any], scrub_keys: List[str] = None) -> Dict[str, Any]:
        """Scrub credentials from dictionary values."""
        if not 
            return data
        
        scrub_keys = scrub_keys or []
        sensitive_keys = [
            'password', 'token', 'secret', 'api_key', 'apikey',
            'access_key', 'secret_key', 'authorization', 'auth'
        ] + scrub_keys
        
        scrubbed = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                scrubbed[key] = cls.REDACTED
            elif isinstance(value, str):
                scrubbed[key] = cls.scrub_string(value)
            elif isinstance(value, dict):
                scrubbed[key] = cls.scrub_dict(value, scrub_keys)
            elif isinstance(value, list):
                scrubbed[key] = [
                    cls.scrub_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                scrubbed[key] = value
        return scrubbed
    
    @classmethod
    def scrub_exception(cls, exc: Exception) -> str:
        """Scrub credentials from exception message."""
        return cls.scrub_string(str(exc))


class SecureLogger:
    """Logger wrapper that automatically scrubs credentials."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def _scrub_message(self, msg: str, *args) -> str:
        scrubbed_msg = CredentialScrubber.scrub_string(str(msg))
        if args:
            scrubbed_args = tuple(
                CredentialScrubber.scrub_string(str(arg)) for arg in args
            )
            return scrubbed_msg % scrubbed_args
        return scrubbed_msg
    
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(self._scrub_message(msg, *args), **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self.logger.info(self._scrub_message(msg, *args), **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(self._scrub_message(msg, *args), **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self.logger.error(self._scrub_message(msg, *args), **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        self.logger.critical(self._scrub_message(msg, *args), **kwargs)
    
    def exception(self, msg, *args, exc_info=True, **kwargs):
        scrubbed_msg = self._scrub_message(msg, *args)
        self.logger.exception(scrubbed_msg, exc_info=exc_info, **kwargs)


class RateLimiter:
    """Token bucket rate limiter for credential injection."""
    
    def __init__(self):
        self.buckets: Dict[str, Dict[str, Any]] = {}
        self.default_rate = 1000
        self.default_burst = 100
    
    def check_rate_limit(self, credential_id: str, rate: int = None, burst: int = None) -> bool:
        """Check if request is within rate limit."""
        rate = rate or self.default_rate
        burst = burst or self.default_burst
        now = time.time()
        
        if credential_id not in self.buckets:
            self.buckets[credential_id] = {
                'tokens': burst,
                'last_update': now,
                'requests': 0,
                'blocked': 0
            }
        
        bucket = self.buckets[credential_id]
        time_passed = now - bucket['last_update']
        tokens_to_add = time_passed * (rate / 60.0)
        bucket['tokens'] = min(burst, bucket['tokens'] + tokens_to_add)
        bucket['last_update'] = now
        
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            bucket['requests'] += 1
            return True
        else:
            bucket['blocked'] += 1
            return False
    
    def get_stats(self, credential_id: str) -> Dict[str, Any]:
        return self.buckets.get(credential_id, {})
    
    def reset(self, credential_id: str = None):
        if credential_id:
            self.buckets.pop(credential_id, None)
        else:
            self.buckets.clear()


class DNSProtection:
    """DNS rebinding and SSRF protection."""
    
    def __init__(self):
        self.dns_cache: Dict[str, Tuple[str, float]] = {}
        self.cache_ttl = 300
    
    def resolve_and_validate(self, host: str, allowed_hosts: List[str]) -> Tuple[bool, str, Optional[str]]:
        """Resolve hostname and validate it's not a private IP."""
        # Check cache
        if host in self.dns_cache:
            cached_ip, cached_time = self.dns_cache[host]
            if time.time() - cached_time < self.cache_ttl:
                if self._is_private_ip(cached_ip):
                    return (False, f"Resolved to private IP: {cached_ip}", cached_ip)
                return (True, "Cached resolution valid", cached_ip)
        
        # Resolve hostname
        try:
            resolved_ip = socket.gethostbyname(host)
        except socket.gaierror as e:
            return (False, f"DNS resolution failed: {str(e)}", None)
        
        self.dns_cache[host] = (resolved_ip, time.time())
        
        if self._is_private_ip(resolved_ip):
            return (False, f"Resolved to private IP: {resolved_ip}", resolved_ip)
        
        if not self._validate_host_pattern(host, allowed_hosts):
            return (False, f"Host {host} not in allowed list", resolved_ip)
        
        return (True, "Valid", resolved_ip)
    
    def _is_private_ip(self, ip: str) -> bool:
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except (ValueError, ImportError):
            private_patterns = [
                r'^10\.', r'^172\.(1[6-9]|2[0-9]|3[01])\.', r'^192\.168\.',
                r'^127\.', r'^169\.254\.', r'^::1$', r'^fe80:', r'^fc00:', r'^fd00:'
            ]
            return any(re.match(pattern, ip) for pattern in private_patterns)
    
    def _validate_host_pattern(self, host: str, allowed_hosts: List[str]) -> bool:
        if not allowed_hosts:
            return False
        host_lower = host.lower()
        for allowed in allowed_hosts:
            allowed_lower = allowed.lower()
            if host_lower == allowed_lower:
                return True
            if allowed_lower.startswith('*.'):
                base_domain = allowed_lower[2:]
                if host_lower.endswith('.' + base_domain) or host_lower == base_domain:
                    return True
            elif host_lower.endswith('.' + allowed_lower):
                return True
        return False


class InputValidator:
    """Validates and sanitizes inputs to prevent injection attacks."""
    
    @staticmethod
    def validate_header_value(value: str, max_length: int = 8192) -> bool:
        """Validate HTTP header value according to RFC 7230."""
        if not value:
            return True
        if len(value) > max_length:
            return False
        for char in value:
            code = ord(char)
            if not (code == 9 or code == 32 or (33 <= code <= 126) or (128 <= code <= 255)):
                return False
        if '\r' in value or '\n' in value:
            return False
        return True
    
    @staticmethod
    def sanitize_header_value(value: str, max_length: int = 8192) -> str:
        """Sanitize header value by removing invalid characters."""
        if not value:
            return value
        sanitized = value[:max_length]
        sanitized = ''.join(
            char for char in sanitized
            if ord(char) == 9 or ord(char) == 32 or 
            (33 <= ord(char) <= 126) or (128 <= ord(char) <= 255)
        )
        sanitized = sanitized.replace('\r', '').replace('\n', '')
        return sanitized


class SecurityError(Exception):
    """Custom exception for security validation failures."""
    pass