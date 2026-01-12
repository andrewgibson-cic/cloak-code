#!/bin/bash
# CloakCode SSH Key Setup Script
#
# This script prepares SSH keys for use in the CloakCode agent container.
# Keys are copied to a staging directory that can be mounted into the container.
#
# Usage:
#   ./scripts/setup-ssh-keys.sh [--source ~/.ssh] [--dest ./ssh-keys]

set -e

# Default paths
SOURCE_SSH_DIR="${HOME}/.ssh"
DEST_SSH_DIR="./ssh-keys"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --source)
            SOURCE_SSH_DIR="$2"
            shift 2
            ;;
        --dest)
            DEST_SSH_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--source ~/.ssh] [--dest ./ssh-keys]"
            echo ""
            echo "Options:"
            echo "  --source DIR    Source SSH directory (default: ~/.ssh)"
            echo "  --dest DIR      Destination directory (default: ./ssh-keys)"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "CloakCode SSH Key Setup"
echo "=========================================="
echo ""

# Validate source directory
if [ ! -d "$SOURCE_SSH_DIR" ]; then
    echo "❌ Error: Source SSH directory not found: $SOURCE_SSH_DIR"
    echo ""
    echo "Please ensure you have SSH keys configured on your system."
    echo "Generate keys with: ssh-keygen -t ed25519 -C 'your_email@example.com'"
    exit 1
fi

# Create destination directory
echo "Creating destination directory: $DEST_SSH_DIR"
mkdir -p "$DEST_SSH_DIR"
chmod 700 "$DEST_SSH_DIR"

# Track copied keys
KEYS_COPIED=0

# Copy Ed25519 key (preferred)
if [ -f "$SOURCE_SSH_DIR/id_ed25519" ]; then
    echo "✓ Found Ed25519 private key"
    cp "$SOURCE_SSH_DIR/id_ed25519" "$DEST_SSH_DIR/"
    chmod 600 "$DEST_SSH_DIR/id_ed25519"
    KEYS_COPIED=$((KEYS_COPIED + 1))
    
    if [ -f "$SOURCE_SSH_DIR/id_ed25519.pub" ]; then
        cp "$SOURCE_SSH_DIR/id_ed25519.pub" "$DEST_SSH_DIR/"
        chmod 644 "$DEST_SSH_DIR/id_ed25519.pub"
        echo "✓ Copied Ed25519 public key"
    fi
fi

# Copy RSA key (fallback)
if [ -f "$SOURCE_SSH_DIR/id_rsa" ]; then
    echo "✓ Found RSA private key"
    cp "$SOURCE_SSH_DIR/id_rsa" "$DEST_SSH_DIR/"
    chmod 600 "$DEST_SSH_DIR/id_rsa"
    KEYS_COPIED=$((KEYS_COPIED + 1))
    
    if [ -f "$SOURCE_SSH_DIR/id_rsa.pub" ]; then
        cp "$SOURCE_SSH_DIR/id_rsa.pub" "$DEST_SSH_DIR/"
        chmod 644 "$DEST_SSH_DIR/id_rsa.pub"
        echo "✓ Copied RSA public key"
    fi
fi

# Copy ECDSA key (if present)
if [ -f "$SOURCE_SSH_DIR/id_ecdsa" ]; then
    echo "✓ Found ECDSA private key"
    cp "$SOURCE_SSH_DIR/id_ecdsa" "$DEST_SSH_DIR/"
    chmod 600 "$DEST_SSH_DIR/id_ecdsa"
    KEYS_COPIED=$((KEYS_COPIED + 1))
    
    if [ -f "$SOURCE_SSH_DIR/id_ecdsa.pub" ]; then
        cp "$SOURCE_SSH_DIR/id_ecdsa.pub" "$DEST_SSH_DIR/"
        chmod 644 "$DEST_SSH_DIR/id_ecdsa.pub"
        echo "✓ Copied ECDSA public key"
    fi
fi

# Check if any keys were copied
if [ $KEYS_COPIED -eq 0 ]; then
    echo ""
    echo "❌ Error: No SSH keys found in $SOURCE_SSH_DIR"
    echo ""
    echo "Please generate SSH keys first:"
    echo "  ssh-keygen -t ed25519 -C 'your_email@example.com'"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Create SSH config file
echo ""
echo "Creating SSH config..."
cat > "$DEST_SSH_DIR/config" <<'EOF'
# CloakCode SSH Configuration
# This file configures SSH for use with common git hosting services

# GitHub
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new

# GitHub (alternative for RSA keys)
Host github.com-rsa
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_rsa
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new

# GitLab
Host gitlab.com
    HostName gitlab.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new

# Bitbucket
Host bitbucket.org
    HostName bitbucket.org
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new

# Generic git server (customize as needed)
# Host my-git-server.com
#     HostName my-git-server.com
#     User git
#     IdentityFile ~/.ssh/id_ed25519
#     IdentitiesOnly yes
EOF

chmod 600 "$DEST_SSH_DIR/config"
echo "✓ Created SSH config"

# Add .gitignore entry to prevent accidental commits
if [ ! -f ".gitignore" ] || ! grep -q "^ssh-keys/$" .gitignore 2>/dev/null; then
    echo ""
    echo "Adding ssh-keys/ to .gitignore..."
    echo "ssh-keys/" >> .gitignore
    echo "✓ Updated .gitignore"
fi

# Summary
echo ""
echo "=========================================="
echo "✓ SSH Key Setup Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Keys copied: $KEYS_COPIED"
echo "  - Destination: $DEST_SSH_DIR"
echo "  - Permissions: 700 (directory), 600 (private keys)"
echo ""
echo "Next Steps:"
echo ""
echo "1. Mount the keys in docker-compose.yml:"
echo "   volumes:"
echo "     - ./$DEST_SSH_DIR:/ssh-keys:ro"
echo ""
echo "2. Start the agent container:"
echo "   docker-compose up -d agent"
echo ""
echo "3. The keys will be automatically configured in the container"
echo ""
echo "⚠️  Security Notes:"
echo "  - Keys are stored in $DEST_SSH_DIR on your host"
echo "  - This directory is in .gitignore to prevent accidental commits"
echo "  - Keys are mounted read-only into the container"
echo "  - Keys are cleared when the container exits"
echo "  - NEVER commit SSH keys to version control!"
echo ""
echo "To verify keys are working in the container:"
echo "  docker-compose exec agent ssh -T git@github.com"
echo ""

# Show public keys for verification
echo "Public Keys (add these to your git hosting service):"
echo "─────────────────────────────────────────────────────"
for pubkey in "$DEST_SSH_DIR"/*.pub; do
    if [ -f "$pubkey" ]; then
        echo ""
        echo "$(basename "$pubkey"):"
        cat "$pubkey"
    fi
done
echo ""
echo "=========================================="
