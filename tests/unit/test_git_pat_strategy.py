"""
Unit tests for Git PAT (Personal Access Token) injection strategy.
"""

import pytest
import os
import base64
from mitmproxy.test import tflow
from mitmproxy import http

# Import the strategy
import sys
sys.path.insert(0, 'proxy')
from strategies.git_pat import GitPATStrategy


class TestGitPATStrategy:
    """Test suite for GitPATStrategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Set dummy environment variables
        os.environ['GIT_GITHUB_PAT'] = 'ghp_real_token_for_github_123456789012'
        os.environ['GIT_GITLAB_PAT'] = 'glpat-real_gitlab_token'
        
        # Create strategy instance
        self.strategy = GitPATStrategy('test-git-pat', {
            'allowed_hosts': ['github.com', 'gitlab.com']
        })
    
    def teardown_method(self):
        """Clean up after tests."""
        os.environ.pop('GIT_GITHUB_PAT', None)
        os.environ.pop('GIT_GITLAB_PAT', None)
    
    def test_detect_github_git_request(self):
        """Test detection of GitHub git operations."""
        flow = tflow.tflow()
        flow.request = http.Request.make(
            "GET",
            "https://github.com/user/repo.git/info/refs?service=git-upload-pack",
            headers={
                "Authorization": "Basic " + base64.b64encode(b"git:ghp_DUMMY_TOKEN_32_CHARS_XXXXXXXX").decode()
            }
        )
        
        assert self.strategy.detect(flow) is True
    
    def test_detect_gitlab_git_request(self):
        """Test detection of GitLab git operations."""
        flow = tflow.tflow()
        flow.request = http.Request.make(
            "POST",
            "https://gitlab.com/user/repo.git/git-upload-pack",
            headers={
                "Authorization": "Basic " + base64.b64encode(b"oauth2:glpat-DUMMY_TOKEN_20_XXX").decode()
            }
        )
        
        assert self.strategy.detect(flow) is True
    
    def test_no_detect_non_git_request(self):
        """Test that non-git requests are not detected."""
        flow = tflow.tflow()
        flow.request = http.Request.make(
            "GET",
            "https://api.github.com/user",
            headers={
                "Authorization": "Bearer ghp_some_token"
            }
        )
        
        assert self.strategy.detect(flow) is False
    
    def test_no_detect_without_dummy_credentials(self):
        """Test that requests without dummy credentials are not detected."""
        flow = tflow.tflow()
        flow.request = http.Request.make(
            "GET",
            "https://github.com/user/repo.git/info/refs",
            headers={}
        )
        
        assert self.strategy.detect(flow) is False
    
    def test_inject_github_pat(self):
        """Test injection of GitHub PAT token."""
        flow = tflow.tflow()
        flow.request = http.Request.make(
            "GET",
            "https://github.com/user/repo.git/info/refs",
            headers={
                "Authorization": "Basic " + base64.b64encode(b"git:ghp_DUMMY_TOKEN_32_CHARS_XXXXXXXX").decode()
            }
        )
        
        self.strategy.inject(flow)
        
        # Verify Authorization header was replaced
        auth_header = flow.request.headers.get("Authorization")
        assert auth_header.startswith("Basic ")
        
        # Decode and verify it contains the real token
        decoded = base64.b64decode(auth_header[6:]).decode()
        assert "ghp_real_token_for_github_123456789012" in decoded
        assert "git:" in decoded
    
    def test_inject_gitlab_pat(self):
        """Test injection of GitLab PAT token."""
        flow = tflow.tflow()
        flow.request = http.Request.make(
            "POST",
            "https://gitlab.com/user/repo.git/git-receive-pack",
            headers={
                "Authorization": "Basic " + base64.b64encode(b"oauth2:glpat-DUMMY_TOKEN_20_XXX").decode()
            }
        )
        
        self.strategy.inject(flow)
        
        # Verify Authorization header was replaced
        auth_header = flow.request.headers.get("Authorization")
        assert auth_header.startswith("Basic ")
        
        # Decode and verify it contains the real token
        decoded = base64.b64decode(auth_header[6:]).decode()
        assert "glpat-real_gitlab_token" in decoded
        assert "oauth2:" in decoded
    
    def test_inject_fails_for_disallowed_host(self):
        """Test that injection fails for hosts not in allowlist."""
        flow = tflow.tflow()
        flow.request = http.Request.make(
            "GET",
            "https://evil.com/user/repo.git/info/refs",
            headers={
                "Authorization": "Basic " + base64.b64encode(b"git:ghp_DUMMY_TOKEN_32_CHARS_XXXXXXXX").decode()
            }
        )
        
        with pytest.raises(ValueError, match="not in allowed hosts"):
            self.strategy.inject(flow)
    
    def test_inject_fails_without_token(self):
        """Test that injection fails if PAT token not found in environment."""
        # Remove the environment variable
        os.environ.pop('GIT_GITHUB_PAT', None)
        
        flow = tflow.tflow()
        flow.request = http.Request.make(
            "GET",
            "https://github.com/user/repo.git/info/refs",
            headers={
                "Authorization": "Basic " + base64.b64encode(b"git:ghp_DUMMY_TOKEN_32_CHARS_XXXXXXXX").decode()
            }
        )
        
        with pytest.raises(ValueError, match="PAT token not found"):
            self.strategy.inject(flow)
    
    def test_provider_identification(self):
        """Test that the strategy correctly identifies git providers."""
        assert self.strategy._get_provider_for_host('github.com') == 'github.com'
        assert self.strategy._get_provider_for_host('api.github.com') == 'github.com'
        assert self.strategy._get_provider_for_host('gitlab.com') == 'gitlab.com'
        assert self.strategy._get_provider_for_host('unknown.com') is None
