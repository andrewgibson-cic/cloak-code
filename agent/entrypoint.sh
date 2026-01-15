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

# Setup SSH keys for git operations
setup_ssh_keys() {
    local ssh_keys_source="/ssh-keys"
    local ssh_dir="$HOME/.ssh"
    
    # Check for SSH agent forwarding first
    if [ -S "$SSH_AUTH_SOCK" ]; then
        echo "✓ SSH agent forwarding detected"
        echo "  Git operations will use host SSH agent"
        return 0
    fi
    
    # Check for mounted SSH keys
    if [ -d "$ssh_keys_source" ] && [ "$(ls -A $ssh_keys_source 2>/dev/null)" ]; then
        echo "Setting up SSH keys from mounted volume..."
        
        # Create SSH directory with proper permissions
        mkdir -p "$ssh_dir"
        chmod 700 "$ssh_dir"
        
        # Copy Ed25519 key (preferred)
        if [ -f "$ssh_keys_source/id_ed25519" ]; then
            cp "$ssh_keys_source/id_ed25519" "$ssh_dir/"
            chmod 600 "$ssh_dir/id_ed25519"
            echo "  ✓ Installed Ed25519 private key"
            
            if [ -f "$ssh_keys_source/id_ed25519.pub" ]; then
                cp "$ssh_keys_source/id_ed25519.pub" "$ssh_dir/"
                chmod 644 "$ssh_dir/id_ed25519.pub"
            fi
        fi
        
        # Copy RSA key (fallback)
        if [ -f "$ssh_keys_source/id_rsa" ]; then
            cp "$ssh_keys_source/id_rsa" "$ssh_dir/"
            chmod 600 "$ssh_dir/id_rsa"
            echo "  ✓ Installed RSA private key"
            
            if [ -f "$ssh_keys_source/id_rsa.pub" ]; then
                cp "$ssh_keys_source/id_rsa.pub" "$ssh_dir/"
                chmod 644 "$ssh_dir/id_rsa.pub"
            fi
        fi
        
        # Copy ECDSA key (if present)
        if [ -f "$ssh_keys_source/id_ecdsa" ]; then
            cp "$ssh_keys_source/id_ecdsa" "$ssh_dir/"
            chmod 600 "$ssh_dir/id_ecdsa"
            echo "  ✓ Installed ECDSA private key"
            
            if [ -f "$ssh_keys_source/id_ecdsa.pub" ]; then
                cp "$ssh_keys_source/id_ecdsa.pub" "$ssh_dir/"
                chmod 644 "$ssh_dir/id_ecdsa.pub"
            fi
        fi
        
        # Copy SSH config if provided
        if [ -f "$ssh_keys_source/config" ]; then
            cp "$ssh_keys_source/config" "$ssh_dir/"
            chmod 600 "$ssh_dir/config"
            echo "  ✓ Installed SSH config"
        fi
        
        # Generate known_hosts for common git servers
        echo "  Generating known_hosts for git servers..."
        touch "$ssh_dir/known_hosts"
        ssh-keyscan -H github.ibm.com >> "$ssh_dir/known_hosts" 2>/dev/null || true
        ssh-keyscan -H github.com >> "$ssh_dir/known_hosts" 2>/dev/null || true
        ssh-keyscan -H gitlab.com >> "$ssh_dir/known_hosts" 2>/dev/null || true
        ssh-keyscan -H bitbucket.org >> "$ssh_dir/known_hosts" 2>/dev/null || true
        chmod 644 "$ssh_dir/known_hosts"
        
        # Configure git to prefer SSH for common hosts
        git config --global url."git@github.com:".insteadOf "https://github.com/" || true
        git config --global url."git@gitlab.com:".insteadOf "https://gitlab.com/" || true
        
        echo "✓ SSH keys configured successfully"
        echo "  Git will use SSH for authenticated operations"
        return 0
    fi
    
    echo "ℹ  No SSH keys found"
    echo "  Git operations will use HTTPS (credentials via proxy)"
    echo "  To enable SSH: run ./scripts/setup-ssh-keys.sh on host"
}

# Cleanup SSH keys on exit
cleanup_ssh_keys() {
    if [ -d "$HOME/.ssh" ]; then
        echo "Cleaning up SSH keys..."
        if type log_event >/dev/null 2>&1; then
            log_event "Cleaning up SSH keys on exit"
        fi
        rm -rf "$HOME/.ssh"
        echo "✓ SSH keys cleared"
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
    
    # Show SSH status
    if [ -d "$HOME/.ssh" ]; then
        echo "SSH: Enabled (keys present)"
    elif [ -S "$SSH_AUTH_SOCK" ]; then
        echo "SSH: Enabled (agent forwarding)"
    else
        echo "SSH: Disabled (using HTTPS for git)"
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
    trap cleanup_ssh_keys EXIT
    
    # Install certificate (critical for HTTPS)
    install_certificate
    
    # Setup workspace
    setup_workspace
    
    # Setup SSH keys for git operations
    setup_ssh_keys
    
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
    
    # Add SSH-specific help if keys are available
    if [ -d "$HOME/.ssh" ] || [ -S "$SSH_AUTH_SOCK" ]; then
        echo ""
        echo "Git/SSH Operations:"
        echo "  - SSH keys are configured for git"
        echo "  - Test with: ssh -T git@github.com"
        echo "  - Clone repos: git clone git@github.com:user/repo.git"
    fi
    
    echo ""
    echo "Logging:"
    echo "  - Activity logs: tail -f ~/logs/agent_activity.log"
    echo "  - Audit trail: cat ~/logs/audit.json | jq"
    echo "  - All commands (npm, git, pip) are automatically logged"
    echo ""
    echo "Security Notes:"
    echo "  - All API calls are routed through the proxy"
    echo "  - Real credentials are never stored in this container"
    echo "  - SSH keys are cleared automatically on exit"
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
