"""
AWS Signature Version 4 (SigV4) Injection Strategy

This strategy implements the AWS SigV4 signing protocol for authenticating requests
to AWS services. It handles region/service detection, canonical request creation,
and signature calculation.

References:
- https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html
"""

import os
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
from mitmproxy import http

try:
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials
    BOTO_AVAILABLE = True
except ImportError:
    BOTO_AVAILABLE = False

from .base import InjectionStrategy


class AWSSigV4Strategy(InjectionStrategy):
    """
    AWS Signature Version 4 authentication strategy.
    
    This strategy:
    1. Detects AWS API requests by dummy credential patterns and host
    2. Extracts region and service from the URL
    3. Removes dummy AWS headers
    4. Calculates proper SigV4 signature using real credentials
    5. Injects signed headers into the request
    """
    
    # AWS service endpoint patterns
    AWS_HOST_PATTERNS = [
        r".*\.amazonaws\.com$",
        r".*\.amazonaws\.com\.cn$",  # China regions
    ]
    
    # Dummy credential patterns to detect
    DUMMY_PATTERNS = [
        r"AKIA[0-9A-Z]{16}DUMMY",
        r"AKIA00000000DUMMYKEY",
    ]
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize AWS SigV4 strategy.
        
        Expected config keys:
        - access_key_id: AWS Access Key ID (or env var name)
        - secret_access_key: AWS Secret Access Key (or env var name)
        - session_token: (optional) AWS Session Token for temporary credentials
        - region: (optional) Default AWS region (auto-detected if not provided)
        - allowed_hosts: List of allowed AWS hosts (default: *.amazonaws.com)
        """
        super().__init__(name, config)
        
        if not BOTO_AVAILABLE:
            raise ImportError(
                "boto3 and botocore are required for AWS SigV4 strategy. "
                "Install with: pip install boto3"
            )
        
        # Load credentials
        self.access_key_id = self._load_credential("access_key_id")
        self.secret_access_key = self._load_credential("secret_access_key")
        self.session_token = self._load_credential("session_token", required=False)
        
        # Default region (can be overridden per-request)
        self.default_region = config.get("region", "us-east-1")
        
        # Allowed hosts for security validation
        self.allowed_hosts = config.get("allowed_hosts", ["*.amazonaws.com", "*.amazonaws.com.cn"])
    
    def _load_credential(self, key: str, required: bool = True) -> Optional[str]:
        """
        Load credential from config (supports direct value or env var reference).
        
        Args:
            key: Configuration key
            required: Whether the credential is required
            
        Returns:
            The credential value, or None if not required and not found
        """
        value = self.config.get(key)
        
        if value is None:
            if required:
                raise ValueError(f"Required AWS credential '{key}' not found in strategy config")
            return None
        
        # If value looks like an env var reference (e.g., "AWS_ACCESS_KEY_ID")
        if isinstance(value, str) and value.isupper() and "_" in value:
            env_value = os.environ.get(value)
            if env_value:
                return env_value
            elif required:
                raise ValueError(
                    f"Environment variable '{value}' referenced in config "
                    f"for '{key}' is not set"
                )
            return None
        
        return value
    
    def detect(self, flow: http.HTTPFlow) -> bool:
        """
        Detect if this is an AWS request with dummy credentials.
        
        Detection logic:
        1. Check if host matches AWS patterns
        2. Check for dummy AWS credentials in Authorization header or query params
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            True if this appears to be an AWS request with dummy credentials
        """
        host = flow.request.pretty_host.lower()
        
        # Check if host matches AWS patterns
        is_aws_host = any(
            re.match(pattern, host) 
            for pattern in self.AWS_HOST_PATTERNS
        )
        
        if not is_aws_host:
            return False
        
        # Check Authorization header for dummy credentials
        auth_header = flow.request.headers.get("Authorization", "")
        if any(re.search(pattern, auth_header) for pattern in self.DUMMY_PATTERNS):
            self.logger.debug(f"Detected dummy AWS credentials in Authorization header for {host}")
            return True
        
        # Check query parameters for dummy credentials (pre-signed URLs)
        url = flow.request.pretty_url
        if "X-Amz-Credential" in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            credential = params.get("X-Amz-Credential", [""])[0]
            if any(re.search(pattern, credential) for pattern in self.DUMMY_PATTERNS):
                self.logger.debug(f"Detected dummy AWS credentials in query params for {host}")
                return True
        
        return False
    
    def inject(self, flow: http.HTTPFlow) -> None:
        """
        Inject AWS SigV4 signature into the request.
        
        Steps:
        1. Validate host is in allowlist
        2. Extract region and service from URL
        3. Remove dummy AWS headers
        4. Create AWSRequest object
        5. Calculate SigV4 signature
        6. Inject signed headers
        
        Args:
            flow: The mitmproxy flow object to modify
            
        Raises:
            ValueError: If host validation fails or region/service cannot be detected
        """
        # Security check: validate host
        if not self.validate_host(flow, self.allowed_hosts):
            raise ValueError(
                f"Host {flow.request.pretty_host} not in AWS allowed hosts list. "
                f"Refusing to inject credentials."
            )
        
        # Extract region and service from URL
        region = self._extract_region(flow)
        service = self._extract_service(flow)
        
        self.logger.debug(f"Detected AWS service={service}, region={region}")
        
        # Remove dummy AWS headers
        self._sanitize_aws_headers(flow)
        
        # Handle S3 UNSIGNED-PAYLOAD optimization for large uploads
        if service == "s3" and flow.request.method in ["PUT", "POST"]:
            self._set_unsigned_payload(flow)
        
        # Create AWS credentials object
        credentials = Credentials(
            access_key=self.access_key_id,
            secret_key=self.secret_access_key,
            token=self.session_token
        )
        
        # Create AWSRequest object from mitmproxy flow
        aws_request = AWSRequest(
            method=flow.request.method,
            url=flow.request.pretty_url,
            data=flow.request.content,
            headers=dict(flow.request.headers)
        )
        
        # Create SigV4 signer and sign the request
        signer = SigV4Auth(credentials, service, region)
        signer.add_auth(aws_request)
        
        # Copy signed headers back to the flow
        for key, value in aws_request.headers.items():
            flow.request.headers[key] = value
        
        self.log_injection(flow, f"(service={service}, region={region})")
    
    def _extract_region(self, flow: http.HTTPFlow) -> str:
        """
        Extract AWS region from the request URL.
        
        Examples:
        - s3.us-west-2.amazonaws.com -> us-west-2
        - ec2.eu-central-1.amazonaws.com -> eu-central-1
        - s3.amazonaws.com -> us-east-1 (default)
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            AWS region string
        """
        host = flow.request.pretty_host.lower()
        
        # Pattern: service.region.amazonaws.com
        match = re.search(r"\.([a-z]{2}-[a-z]+-\d+)\.amazonaws\.com", host)
        if match:
            return match.group(1)
        
        # Check for region in X-Amz-Credential query param (pre-signed URLs)
        url = flow.request.pretty_url
        if "X-Amz-Credential" in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            credential = params.get("X-Amz-Credential", [""])[0]
            # Format: ACCESS_KEY/20240101/us-west-2/s3/aws4_request
            parts = credential.split("/")
            if len(parts) >= 3:
                return parts[2]
        
        # Default region
        self.logger.debug(f"Could not extract region from {host}, using default: {self.default_region}")
        return self.default_region
    
    def _extract_service(self, flow: http.HTTPFlow) -> str:
        """
        Extract AWS service name from the request URL.
        
        Examples:
        - s3.us-west-2.amazonaws.com -> s3
        - ec2.amazonaws.com -> ec2
        - lambda.us-east-1.amazonaws.com -> lambda
        
        Args:
            flow: The mitmproxy flow object
            
        Returns:
            AWS service name string
        """
        host = flow.request.pretty_host.lower()
        
        # Pattern: service.region.amazonaws.com or service.amazonaws.com
        match = re.match(r"([a-z0-9-]+)\.(?:[a-z]{2}-[a-z]+-\d+\.)?amazonaws\.com", host)
        if match:
            service = match.group(1)
            # Handle special cases
            if service == "execute-api":
                return "execute-api"  # API Gateway
            return service
        
        # Check X-Amz-Credential for service name
        url = flow.request.pretty_url
        if "X-Amz-Credential" in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            credential = params.get("X-Amz-Credential", [""])[0]
            parts = credential.split("/")
            if len(parts) >= 4:
                return parts[3]
        
        # Default to s3 (most common)
        self.logger.warning(f"Could not extract service from {host}, defaulting to 's3'")
        return "s3"
    
    def _sanitize_aws_headers(self, flow: http.HTTPFlow) -> None:
        """
        Remove AWS-specific headers that contain dummy credentials.
        
        Args:
            flow: The mitmproxy flow object
        """
        # Headers to remove (they'll be regenerated by SigV4Auth)
        headers_to_remove = [
            "Authorization",
            "X-Amz-Date",
            "X-Amz-Security-Token",
            "X-Amz-Signature",
        ]
        
        for header in headers_to_remove:
            if header in flow.request.headers:
                self.logger.debug(f"Removing header: {header}")
                del flow.request.headers[header]
    
    def _set_unsigned_payload(self, flow: http.HTTPFlow) -> None:
        """
        Set X-Amz-Content-Sha256 to UNSIGNED-PAYLOAD for large S3 uploads.
        
        This optimization tells AWS to trust the TLS connection integrity
        rather than calculating a SHA256 hash of potentially large payloads.
        
        Args:
            flow: The mitmproxy flow object
        """
        content_length = len(flow.request.content) if flow.request.content else 0
        
        # Use UNSIGNED-PAYLOAD for uploads larger than 1MB
        if content_length > 1024 * 1024:
            flow.request.headers["X-Amz-Content-Sha256"] = "UNSIGNED-PAYLOAD"
            self.logger.debug(
                f"Set UNSIGNED-PAYLOAD for large S3 upload "
                f"({content_length} bytes)"
            )
