#!/usr/bin/env python3
"""
Health Check Addon for mitmproxy

This addon handles health check requests before they reach the main injector.
It intercepts requests to /health/* paths and returns appropriate responses.

Usage:
    mitmproxy -s inject.py -s health_addon.py

Endpoints:
    GET /health        - Basic health check
    GET /health/ready  - Readiness probe
    GET /health/live   - Liveness probe
    GET /health/stats  - Statistics
"""

import json
import logging
from mitmproxy import http, ctx

# Import health check module
try:
    from health_check import HealthChecker
    HEALTH_CHECK_AVAILABLE = True
except ImportError as e:
    ctx.log.warn(f"Health check module not available: {e}")
    HEALTH_CHECK_AVAILABLE = False

logger = logging.getLogger("HealthAddon")


class HealthCheckAddon:
    """
    Mitmproxy addon that intercepts health check requests.
    
    This runs before the main injection addon and handles health
    endpoints directly without processing them as API requests.
    """
    
    def __init__(self):
        """Initialize the health check addon."""
        self.checker = None
        if HEALTH_CHECK_AVAILABLE:
            self.checker = HealthChecker()
            ctx.log.info("✓ Health check addon initialized")
        else:
            ctx.log.warn("⚠ Health check addon unavailable")
    
    def request(self, flow: http.HTTPFlow) -> None:
        """
        Intercept requests to health check endpoints.
        
        Args:
            flow: The mitmproxy flow object
        """
        if not self.checker:
            return
        
        path = flow.request.path
        
        # Check if this is a health check request
        if not path.startswith('/health'):
            return
        
        # Route to appropriate health check
        handler_map = {
            '/health': self.checker.check_basic,
            '/health/': self.checker.check_basic,
            '/health/ready': self.checker.check_ready,
            '/health/live': self.checker.check_live,
            '/health/stats': self.checker.get_stats,
        }
        
        # Find matching handler
        handler = handler_map.get(path)
        if not handler:
            # Unknown health endpoint
            flow.response = http.Response.make(
                404,
                json.dumps({
                    "error": "Unknown health endpoint",
                    "available": list(handler_map.keys())
                }).encode(),
                {"Content-Type": "application/json"}
            )
            return
        
        # Call handler and create response
        try:
            status_code, response_data = handler()
            
            flow.response = http.Response.make(
                status_code,
                json.dumps(response_data, indent=2).encode(),
                {"Content-Type": "application/json"}
            )
            
            # Log health check
            ctx.log.info(f"Health check: {path} -> {status_code}")
            
        except Exception as e:
            # Error handling
            ctx.log.error(f"Health check error for {path}: {e}")
            flow.response = http.Response.make(
                500,
                json.dumps({
                    "error": "Health check failed",
                    "details": str(e)
                }).encode(),
                {"Content-Type": "application/json"}
            )


# Create addon instance for mitmproxy
addons = [HealthCheckAddon()]