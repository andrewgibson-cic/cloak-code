#!/bin/bash
set -e

# Source logging utilities
if [ -f /usr/local/bin/logging_utils.sh ]; then
    source /usr/local/bin/logging_utils.sh
    ensure_log_dir
    log_container_start
else
    echo "Warning: Logging utilities not found"
fi

echo "=========================================="
echo "CloakCode Agent Container Starting..."
echo "=========================================="

# Certificate installation function
install_certificate() {
    local cert_file="/certs/mitmproxy-ca-cert.pem"
    local cert_dest="/usr/local/share/ca-certificates/mitmproxy-ca-cert.crt"
    local cert_pem="/usr/local/share/ca-certificates/mitmproxy-ca-cert.pem"
    local timeout=60
    local elapsed=0
    
    echo "Waiting for proxy certificate..."
    
    # Check if we're in a CI/test environment (no proxy container)
    if ! getent hosts proxy > /dev/null 2>&1; then
        echo "ℹ  Proxy container not found in DNS"
        echo "  Skipping certificate installation (likely CI environment)"
        echo "  Container will run without proxy certificate"
        return 0
    fi
    
    # Check if proxy port is reachable
    if ! timeout 10 bash -c 'cat < /dev/null > /dev/tcp/proxy/8080' 2>/dev/null; then
        echo "⚠️  WARNING: Proxy container not reachable on port 8080"
        echo "  Skipping certificate installation"
        echo "  This is expected in CI environments or standalone mode"
        return 0
    fi
    
    # Wait for certificate file to exist
    while [ ! -f "$cert_file" ]; do
        if [ $elapsed -ge $timeout ]; then
            echo "ERROR: Timeout waiting for certificate after ${timeout}s"
            echo "The proxy container may not be running or certificate generation failed."
            exit 1
        fi
        
        echo "  Certificate not found yet... (${elapsed}s/${timeout}s)"
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    echo "✓ Certificate found: $cert_file"
    
    # Copy certificate (needs sudo)
    echo "Installing certificate..."
    sudo cp "$cert_file" "$cert_dest"
    
    # Create symlink for Node.js (NODE_EXTRA_CA_CERTS expects .pem)
    echo "Creating certificate symlink for Node.js..."
    sudo ln -sf "$cert_file" "$cert_pem"
    
    # Update CA certificates (needs sudo)
    echo "Updating CA certificate store..."
    sudo update-ca-certificates
    
    echo "✓ Certificate installed successfully"
    
    # Verify the certificates are readable
    if [ -f "$cert_dest" ] && [ -f "$cert_pem" ]; then
        echo "✓ Certificates verified:"
        echo "  - System: $cert_dest"
        echo "  - Node.js: $cert_pem"
    else
        echo "WARNING: Certificate not found after installation"
    fi
}

# Verify proxy connectivity
verify_proxy() {
    echo "Verifying proxy connectivity..."
    
    # Check if proxy host exists
    if ! getent hosts proxy > /dev/null 2>&1; then
        echo "ℹ  Proxy not configured (standalone mode)"
        return 0
    fi
    
    # Check if proxy port is reachable (without making a proxied request)
    # Using nc (netcat) to just check if the port is open
    if nc -z -w5 proxy 8080 2>/dev/null; then
        echo "✓ Proxy is reachable at $HTTP_PROXY"
        return 0
    elif timeout 5 bash -c 'cat < /dev/null > /dev/tcp/proxy/8080' 2>/dev/null; then
        echo "✓ Proxy is reachable at $HTTP_PROXY"
        return 0
    else
        echo "WARNING: Unable to reach proxy at $HTTP_PROXY"
        echo "This may cause network issues."
        return 1
    fi
}

# Setup git credential helper for PAT token injection
setup_git_credentials() {
    echo "Setting up git credential helper for PAT token injection..."
    
    # Configure git to use HTTPS (required for proxy injection)
    git config --global credential.helper store
    
    # Create credentials file with dummy tokens
    # Real tokens will be injected by the proxy on-the-fly
    local creds_file="$HOME/.git-credentials"
    
    cat > "$creds_file" <<'EOF'
https://ghp_DUMMY_TOKEN_32_CHARS_XXXXXXXX@github.com
https://oauth2:glpat-DUMMY_TOKEN_20_XXX@gitlab.com
https://x-token-auth:DUMMY_BITBUCKET_TOKEN@bitbucket.org
https://user:DUMMY_AZURE_TOKEN_52_CHARS_XXXXXXXXXXXXXXXXXXXXXXXXX@dev.azure.com
EOF
    
    chmod 600 "$creds_file"
    
    # Configure git user (if not already set)
    if [ -z "$(git config --global user.email)" ]; then
        git config --global user.email "agent@cloakcode.local"
        git config --global user.name "CloakCode Agent"
        echo "  ✓ Set default git user"
    fi
    
    echo "✓ Git credential helper configured"
    echo "  Git operations will use HTTPS with PAT token injection via proxy"
    
    if type log_event >/dev/null 2>&1; then
        log_event "Git credential helper configured for PAT token injection"
    fi
}

# Cleanup git credentials on exit
cleanup_git_credentials() {
    if [ -f "$HOME/.git-credentials" ]; then
        echo "Cleaning up git credentials..."
        if type log_event >/dev/null 2>&1; then
            log_event "Cleaning up git credentials on exit"
        fi
        rm -f "$HOME/.git-credentials"
        echo "✓ Git credentials cleared"
    fi
    
    # Log container stop
    if type log_container_stop >/dev/null 2>&1; then
        log_container_stop
    fi
}

# Display environment information
display_environment() {
    echo ""
    echo "=========================================="
    echo "Environment Configuration:"
    echo "=========================================="
    echo "User: $(whoami)"
    echo "Home: $HOME"
    echo "Working Directory: $(pwd)"
    echo "Node Version: $(node --version)"
    echo "NPM Version: $(npm --version)"
    echo "Python Version: $(python3 --version)"
    echo "Proxy: $HTTP_PROXY"
    
    # Show git authentication status
    if [ -f "$HOME/.git-credentials" ]; then
        echo "Git: HTTPS with PAT injection via proxy"
    else
        echo "Git: Not configured"
    fi
    
    echo ""
    echo "Dummy Credentials (for reference):"
    echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:0:20}..."
    echo "  GITHUB_TOKEN: ${GITHUB_TOKEN:0:20}..."
    echo "  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:20}..."
    echo ""
    echo "Note: These are DUMMY tokens. Real credentials"
    echo "are injected by the proxy on-the-fly."
    echo "=========================================="
    echo ""
}

# Create workspace if it doesn't exist
setup_workspace() {
    if [ ! -d "$HOME/workspace" ]; then
        echo "Creating workspace directory..."
        mkdir -p "$HOME/workspace"
    fi
    
    echo "✓ Workspace ready at: $HOME/workspace"
}

# Main initialization sequence
main() {
    # Register cleanup trap
    trap cleanup_git_credentials EXIT
    
    # Install certificate (critical for HTTPS)
    install_certificate
    
    # Setup workspace
    setup_workspace
    
    # Setup aider (AI coding assistant) - DISABLED
    # Automatic aider venv creation is disabled to keep workspace clean
    # Users can manually install aider if needed: pip install aider-chat
    
    # Setup git credential helper for PAT token injection
    setup_git_credentials
    
    # Verify proxy
    verify_proxy
    
    # Display environment
    display_environment
    
    echo "=========================================="
    echo "CloakCode Agent Ready!"
    echo "=========================================="
    echo ""
    echo "Quick Start Guide:"
    echo "  1. Navigate to workspace: cd workspace"
    echo "  2. Install tools: npm install -g @google/gemini-cli"
    echo "  3. Or: npm install -g @anthropic-ai/claude-code"
    echo ""
    echo "Git Operations (HTTPS with PAT injection):"
    echo "  - Clone repos: git clone https://github.com/user/repo.git"
    echo "  - Push changes: git push origin main"
    echo "  - Real PAT tokens are injected automatically by proxy"
    echo "  - Dummy credentials in ~/.git-credentials are replaced on-the-fly"
    
    echo ""
    echo "Logging:"
    echo "  - Activity logs: tail -f ~/logs/agent_activity.log"
    echo "  - Audit trail: cat ~/logs/audit.json | jq"
    echo "  - All commands (npm, git, pip) are automatically logged"
    echo ""
    echo "Security Notes:"
    echo "  - All API calls are routed through the proxy"
    echo "  - Real credentials are never stored in this container"
    echo "  - Git credentials are cleared automatically on exit"
    echo "  - This container can be safely reset at any time"
    echo ""
    echo "For help with tools, check their documentation"
    echo "=========================================="
    echo ""
    
    # Setup bash history logging for interactive sessions
    if type setup_bash_history_logging >/dev/null 2>&1; then
        setup_bash_history_logging
    fi
    
    # Execute the command passed to the container
    exec "$@"
}

# Run main function
main "$@"
