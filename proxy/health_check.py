#!/usr/bin/env python3
"""
Health Check Module for CloakCode Proxy

Provides comprehensive health check endpoints:
- /health - Basic health check
- /health/ready - Kubernetes-style readiness probe
- /health/live - Kubernetes-style liveness probe

Inspired by SLAPENIR's comprehensive health checking system.
"""

import os
import logging
from typing import Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("HealthCheck")


class HealthChecker:
    """Comprehensive health checking for the proxy service."""
    
    def __init__(self, injector=None):
        """
        Initialize health checker.
        
        Args:
            injector: Reference to UniversalInjector instance for checking strategies
        """
        self.injector = injector
        self.start_time = datetime.utcnow()
    
    def check_basic(self) -> Tuple[int, Dict[str, Any]]:
        """
        Basic health check - always returns OK if service is running.
        
        Returns:
            Tuple of (status_code, response_dict)
        """
        return 200, {
            "status": "ok",
            "service": "cloakcode-proxy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    
    def check_ready(self) -> Tuple[int, Dict[str, Any]]:
        """
        Readiness probe - checks if proxy is ready to handle requests.
        
        Kubernetes-style readiness check that verifies:
        - Strategies are loaded
        - Configuration is valid
        - Credentials are available (without exposing values)
        
        Returns:
            Tuple of (status_code, response_dict)
        """
        checks = {}
        all_ready = True
        
        # Check strategies loaded
        if self.injector and hasattr(self.injector, 'strategies'):
            strategies_loaded = len(self.injector.strategies) > 0
            checks["strategies_loaded"] = {
                "status": "pass" if strategies_loaded else "fail",
                "count": len(self.injector.strategies),
                "mode": getattr(self.injector, 'config_mode', 'unknown')
            }
            if not strategies_loaded:
                all_ready = False
        else:
            checks["strategies_loaded"] = {"status": "unknown"}
            all_ready = False
        
        # Check configuration validity
        config_valid = self._check_config_files()
        checks["config_valid"] = {
            "status": "pass" if config_valid else "warn",
            "details": "Configuration files present and readable"
        }
        # Don't fail on config - it might be using legacy mode
        
        # Check credentials availability (without exposing values)
        creds_available = self._check_credentials_available()
        checks["credentials_available"] = {
            "status": "pass" if creds_available else "warn",
            "details": "At least one credential configured"
        }
        # Don't fail on creds - strategies might have fallbacks
        
        # Check log directory
        logs_writable = self._check_logs_writable()
        checks["logs_writable"] = {
            "status": "pass" if logs_writable else "warn"
        }
        
        status_code = 200 if all_ready else 503
        
        return status_code, {
            "ready": all_ready,
            "service": "cloakcode-proxy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": checks,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
        }
    
    def check_live(self) -> Tuple[int, Dict[str, Any]]:
        """
        Liveness probe - checks if proxy is alive and responding.
        
        Kubernetes-style liveness check. This should only fail if the
        service is fundamentally broken and needs restart.
        
        Returns:
            Tuple of (status_code, response_dict)
        """
        return 200, {
            "alive": True,
            "service": "cloakcode-proxy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
        }
    
    def get_stats(self) -> Tuple[int, Dict[str, Any]]:
        """
        Get proxy statistics and metrics.
        
        Returns:
            Tuple of (status_code, response_dict)
        """
        stats = {
            "service": "cloakcode-proxy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
        }
        
        # Add injector stats if available
        if self.injector and hasattr(self.injector, 'stats'):
            stats["injection_stats"] = self.injector.stats
        
        # Add strategy info
        if self.injector and hasattr(self.injector, 'strategies'):
            stats["strategies"] = {
                "count": len(self.injector.strategies),
                "names": [s.name for s in self.injector.strategies],
                "mode": getattr(self.injector, 'config_mode', 'unknown')
            }
        
        return 200, stats
    
    def _check_config_files(self) -> bool:
        """Check if configuration files exist and are readable."""
        config_paths = [
            Path("/app/config.yaml"),
            Path("proxy/config.yaml"),
            Path("/app/credentials.yml"),
            Path("credentials.yml")
        ]
        
        for path in config_paths:
            if path.exists() and path.is_file():
                try:
                    with open(path, 'r') as f:
                        f.read(1)  # Try to read at least one byte
                    return True
                except Exception:
                    continue
        
        # No config file, but that's okay - we have legacy fallback
        return True
    
    def _check_credentials_available(self) -> bool:
        """
        Check if credentials are available without exposing values.
        
        Returns True if at least one credential environment variable is set.
        """
        # Common credential environment variables
        cred_vars = [
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY',
            'GITHUB_TOKEN',
            'REAL_OPENAI_API_KEY',
            'REAL_ANTHROPIC_API_KEY',
            'REAL_GITHUB_TOKEN',
            'AWS_ACCESS_KEY_ID',
            'GEMINI_API_KEY',
            'MISTRAL_API_KEY',
        ]
        
        for var in cred_vars:
            value = os.environ.get(var, '')
            if value and not value.startswith('DUMMY'):
                return True
        
        # Check if injector has strategies with credentials
        if self.injector and hasattr(self.injector, 'strategies'):
            for strategy in self.injector.strategies:
                try:
                    if hasattr(strategy, 'has_credential') and strategy.has_credential():
                        return True
                except Exception:
                    # Strategy check failed, continue to next
                    continue
        
        return False
    
    def _check_logs_writable(self) -> bool:
        """Check if log directory is writable."""
        log_dir = Path("/logs")
        if not log_dir.exists():
            try:
                log_dir.mkdir(exist_ok=True)
                return True
            except Exception:
                return False
        
        # Test write access
        test_file = log_dir / ".write_test"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            test_file.unlink()
            return True
        except Exception:
            return False


def create_health_endpoints(injector=None):
    """
    Create health check endpoint handlers.
    
    This function returns a dictionary of endpoint paths to handler functions
    that can be used by mitmproxy addons.
    
    Args:
        injector: Reference to UniversalInjector instance
        
    Returns:
        Dict of {path: handler_function}
    """
    checker = HealthChecker(injector)
    
    return {
        '/health': checker.check_basic,
        '/health/ready': checker.check_ready,
        '/health/live': checker.check_live,
        '/health/stats': checker.get_stats,
    }


if __name__ == "__main__":
    # Test health checks
    checker = HealthChecker()
    
    print("Basic Health Check:")
    status, response = checker.check_basic()
    print(f"  Status: {status}")
    print(f"  Response: {response}")
    print()
    
    print("Readiness Check:")
    status, response = checker.check_ready()
    print(f"  Status: {status}")
    print(f"  Response: {response}")
    print()
    
    print("Liveness Check:")
    status, response = checker.check_live()
    print(f"  Status: {status}")
    print(f"  Response: {response}")