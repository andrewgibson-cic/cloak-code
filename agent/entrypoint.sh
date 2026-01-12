#!/bin/bash
set -e

echo "=========================================="
echo "CloakCode Agent Container Starting..."
echo "=========================================="

# Certificate installation function
install_certificate() {
    local cert_file="/certs/mitmproxy-ca-cert.pem"
    local cert_dest="/usr/local/share/ca-certificates/mitmproxy-ca-cert.crt"
    local cert_pem="/usr/local/share/ca-certificates/mitmproxy-ca-cert.pem"
    local timeout=30
    local elapsed=0
    
    echo "Waiting for proxy certificate..."
    
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
    # Install certificate (critical for HTTPS)
    install_certificate
    
    # Setup workspace
    setup_workspace
    
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
    echo "Security Notes:"
    echo "  - All API calls are routed through the proxy"
    echo "  - Real credentials are never stored in this container"
    echo "  - This container can be safely reset at any time"
    echo ""
    echo "For help with tools, check their documentation"
    echo "=========================================="
    echo ""
    
    # Execute the command passed to the container
    exec "$@"
}

# Run main function
main "$@"
