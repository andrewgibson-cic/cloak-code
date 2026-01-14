# SSH Key Injection Investigation

## Overview

This document investigates approaches for enabling SSH-based git operations within the CloakCode agent container while maintaining the security model of credential injection through the proxy.

**Status**: Investigation & Design Phase  
**Branch**: `feature/ssh-key-injection`  
**Date**: 2026-12-01

## Problem Statement

The current CloakCode architecture successfully injects API credentials (Bearer tokens, AWS SigV4, etc.) by intercepting HTTP/HTTPS traffic through an mitmproxy-based proxy. However, git operations over SSH present unique challenges:

1. **SSH traffic cannot be intercepted** by HTTP(S) proxy (operates on port 22, not 80/443)
2. **SSH keys are file-based** credentials (not HTTP headers)
3. **Git requires direct filesystem access** to `~/.ssh/` for key-based authentication
4. **Security requirement**: Real SSH keys must never be stored permanently in the agent container

## Current Architecture Review

### Credential Injection Flow (HTTP/HTTPS)
```
Agent Container                Proxy Container
┌─────────────┐               ┌──────────────┐
│             │               │              │
│ Dummy Creds │──HTTP(S)───►│ Intercept    │
│ in ENV vars │               │ via mitmproxy│
│             │               │              │
│             │◄──Modified───│ Inject Real  │
│             │   Request     │ Credentials  │
└─────────────┘               └──────────────┘
                               ▲
                               │ Real credentials
                               │ from .env file
```

### SSH Key Challenge
```
Agent Container                Git Server (GitHub, etc.)
┌─────────────┐               ┌──────────────┐
│             │               │              │
│ Git client  │───SSH:22────►│ Requires SSH │
│             │   (Direct)    │ Private Key  │
│             │               │              │
│ ❌ No SSH   │◄──Rejected───│              │
│   keys      │               │              │
└─────────────┘               └──────────────┘
       ▲
       │ No HTTP proxy can intercept
       │ SSH protocol (port 22)
```

## Proposed Solutions

### Option 1: Direct Volume Mount with Runtime Injection (RECOMMENDED)

**Architecture**: Mount SSH keys from host into agent container at runtime through a secure volume.

```
Host Filesystem               Agent Container
┌─────────────┐               ┌──────────────┐
│             │               │              │
│ ~/.ssh/     │───Mount──────►│ /ssh-keys/   │
│ id_ed25519  │   (read-only) │ (tmpfs)      │
│ id_rsa      │               │              │
│             │               │ entrypoint.sh│
│             │               │ ↓            │
│             │               │ Copy to      │
│             │               │ ~/.ssh/      │
│             │               │ Set perms    │
│             │               │ 600          │
└─────────────┘               └──────────────┘
```

**Implementation Steps**:

1. **Modify docker-compose.yml**:
```yaml
services:
  agent:
    volumes:
      - cloakcode_ssh_keys:/ssh-keys:ro  # Read-only mount
      - ./workspace:/home/agent/workspace

volumes:
  cloakcode_ssh_keys:
    driver: local
    driver_opts:
      type: tmpfs  # Memory-backed for security
      device: tmpfs
```

2. **Update agent/entrypoint.sh**:
```bash
setup_ssh_keys() {
    local ssh_keys_source="/ssh-keys"
    local ssh_dir="$HOME/.ssh"
    
    if [ -d "$ssh_keys_source" ] && [ "$(ls -A $ssh_keys_source 2>/dev/null)" ]; then
        echo "Setting up SSH keys..."
        
        # Create SSH directory with proper permissions
        mkdir -p "$ssh_dir"
        chmod 700 "$ssh_dir"
        
        # Copy keys from mounted volume
        if [ -f "$ssh_keys_source/id_ed25519" ]; then
            cp "$ssh_keys_source/id_ed25519" "$ssh_dir/"
            chmod 600 "$ssh_dir/id_ed25519"
            echo "✓ Installed Ed25519 key"
        fi
        
        if [ -f "$ssh_keys_source/id_rsa" ]; then
            cp "$ssh_keys_source/id_rsa" "$ssh_dir/"
            chmod 600 "$ssh_dir/id_rsa"
            echo "✓ Installed RSA key"
        fi
        
        # Copy SSH config if provided
        if [ -f "$ssh_keys_source/config" ]; then
            cp "$ssh_keys_source/config" "$ssh_dir/"
            chmod 600 "$ssh_dir/config"
            echo "✓ Installed SSH config"
        fi
        
        # Generate known_hosts for common git servers
        ssh-keyscan github.com >> "$ssh_dir/known_hosts" 2>/dev/null
        ssh-keyscan gitlab.com >> "$ssh_dir/known_hosts" 2>/dev/null
        chmod 644 "$ssh_dir/known_hosts"
        
        echo "✓ SSH keys configured"
    else
        echo "ℹ No SSH keys found (git operations will use HTTPS)"
    fi
}

# Add cleanup trap
cleanup_ssh_keys() {
    if [ -d "$HOME/.ssh" ]; then
        echo "Cleaning up SSH keys..."
        rm -rf "$HOME/.ssh"
    fi
}

trap cleanup_ssh_keys EXIT
```

3. **Create scripts/setup-ssh-keys.sh**:
```bash
#!/bin/bash
# Script to prepare SSH keys for CloakCode agent container

set -e

SSH_KEYS_DIR="./ssh-keys"
SOURCE_SSH_DIR="${HOME}/.ssh"

echo "CloakCode SSH Key Setup"
echo "======================="

# Create directory
mkdir -p "$SSH_KEYS_DIR"
chmod 700 "$SSH_KEYS_DIR"

# Copy keys
if [ -f "$SOURCE_SSH_DIR/id_ed25519" ]; then
    cp "$SOURCE_SSH_DIR/id_ed25519" "$SSH_KEYS_DIR/"
    chmod 600 "$SSH_KEYS_DIR/id_ed25519"
    echo "✓ Copied Ed25519 key"
fi

if [ -f "$SOURCE_SSH_DIR/id_rsa" ]; then
    cp "$SOURCE_SSH_DIR/id_rsa" "$SSH_KEYS_DIR/"
    chmod 600 "$SSH_KEYS_DIR/id_rsa"
    echo "✓ Copied RSA key"
fi

# Create SSH config
cat > "$SSH_KEYS_DIR/config" <<EOF
# GitHub
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

# GitLab
Host gitlab.com
    HostName gitlab.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
EOF

chmod 600 "$SSH_KEYS_DIR/config"
echo "✓ Created SSH config"

echo ""
echo "SSH keys prepared in: $SSH_KEYS_DIR"
echo "Mount this directory as a volume in docker-compose.yml"
```

**Pros**:
- ✅ Simple to implement
- ✅ Consistent with existing certificate injection pattern
- ✅ Keys in memory only (tmpfs)
- ✅ Cleaned up on container exit
- ✅ Works immediately without additional services

**Cons**:
- ⚠️ Keys temporarily in container filesystem (even if tmpfs)
- ⚠️ Requires manual key setup step
- ⚠️ Less dynamic than HTTP credential injection

---

### Option 2: SSH Proxy/Bastion Pattern

**Architecture**: Create an SSH proxy container that holds keys and performs git operations on behalf of the agent.

```
Agent Container          SSH Proxy Container        Git Server
┌─────────────┐         ┌──────────────┐          ┌──────────┐
│             │         │              │          │          │
│ Git client  │─SSH────►│ SSH Server   │─SSH─────►│ GitHub   │
│ (dummy key) │  Port   │ + Real Keys  │  Port 22 │          │
│             │  2222   │              │          │          │
│             │         │ Key Swapping │          │          │
└─────────────┘         └──────────────┘          └──────────┘
```

**Implementation Complexity**: High

**Required Components**:
- SSH server in proxy container (sshd)
- SSH key swapping logic
- ProxyJump configuration in agent
- Network routing for SSH traffic

**Pros**:
- ✅ True zero-trust model (keys never in agent)
- ✅ Consistent with HTTP proxy pattern
- ✅ Centralized key management

**Cons**:
- ❌ Complex to implement and maintain
- ❌ Additional container and service
- ❌ SSH-over-SSH performance overhead
- ❌ Requires custom SSH server logic

---

### Option 3: SSH Agent Forwarding

**Architecture**: Forward host's SSH agent socket into container.

```
Host OS                  Agent Container
┌─────────────┐         ┌──────────────┐
│             │         │              │
│ ssh-agent   │─Socket──►│ SSH client   │
│ (daemon)    │  Mount  │              │
│             │         │ Uses agent   │
│ Real Keys   │         │ for auth     │
└─────────────┘         └──────────────┘
```

**Implementation**:
```yaml
# docker-compose.yml
services:
  agent:
    volumes:
      - ${SSH_AUTH_SOCK}:/ssh-agent:ro
    environment:
      - SSH_AUTH_SOCK=/ssh-agent
```

**Pros**:
- ✅ No keys in container filesystem
- ✅ Transparent to git client
- ✅ Minimal setup

**Cons**:
- ⚠️ Requires ssh-agent running on host
- ⚠️ May not work on all platforms (Windows)
- ⚠️ Socket permissions can be tricky

---

## Recommended Approach: Hybrid Solution

Combine **Option 1** (volume mount) with **Option 3** (agent forwarding) as fallback:

1. **Primary**: Try SSH agent forwarding (if available on host)
2. **Fallback**: Volume-mounted keys with proper security

### Implementation Plan

```bash
# In agent/entrypoint.sh
setup_ssh_authentication() {
    # Try SSH agent forwarding first
    if [ -S "$SSH_AUTH_SOCK" ]; then
        echo "✓ Using SSH agent forwarding"
        return 0
    fi
    
    # Fall back to mounted keys
    if [ -d "/ssh-keys" ]; then
        setup_ssh_keys_from_volume
        return 0
    fi
    
    echo "ℹ No SSH authentication available"
    echo "  Git will use HTTPS (requires credentials in proxy)"
}
```

## Security Considerations

### Key Protection Measures

1. **File Permissions**:
   - Private keys: `600` (owner read/write only)
   - SSH directory: `700` (owner access only)
   - Known_hosts: `644` (world-readable)

2. **Memory-Only Storage**:
   - Use tmpfs for key volume (no disk persistence)
   - Keys cleared on container exit
   - No keys in container image layers

3. **Host Validation**:
   - Restrict keys to specific git hosts in SSH config
   - Use `IdentitiesOnly yes` to prevent key probing
   - Pre-populate known_hosts to prevent MITM

4. **Access Control**:
   - Keys mounted read-only
   - Non-root user in container
   - No sudo access for key operations

### Configuration Example

```yaml
# config.yaml extension for SSH keys
ssh_configuration:
  enabled: true
  mode: volume_mount  # or: agent_forwarding
  
  keys:
    - name: github-deploy-key
      type: ed25519
      source: /ssh-keys/id_ed25519
      allowed_hosts:
        - github.com
        - "*.github.com"
    
    - name: gitlab-personal
      type: rsa
      source: /ssh-keys/id_rsa
      allowed_hosts:
        - gitlab.com

  security:
    clear_on_exit: true
    use_tmpfs: true
    file_permissions: "600"
```

## Git Configuration

### Automatic HTTPS → SSH Conversion

Configure git to use SSH for authenticated operations:

```bash
# In entrypoint.sh
setup_git_ssh() {
    if [ -d "$HOME/.ssh" ]; then
        # Convert GitHub HTTPS URLs to SSH
        git config --global url."git@github.com:".insteadOf "https://github.com/"
        
        # Convert GitLab HTTPS URLs to SSH
        git config --global url."git@gitlab.com:".insteadOf "https://gitlab.com/"
        
        echo "✓ Git configured to use SSH"
    fi
}
```

### Per-Repository Configuration

```bash
# For specific repositories
cd /home/agent/workspace/my-repo
git config url."git@github.com:".insteadOf "https://github.com/"
```

## Testing Plan

### Unit Tests

```bash
# Test SSH key setup
test_ssh_key_permissions() {
    local key="$HOME/.ssh/id_ed25519"
    [ -f "$key" ] || fail "Key not found"
    
    local perms=$(stat -c %a "$key")
    [ "$perms" = "600" ] || fail "Wrong permissions: $perms"
}

# Test SSH agent forwarding
test_ssh_agent_forwarding() {
    [ -S "$SSH_AUTH_SOCK" ] || skip "No agent socket"
    ssh-add -l || fail "Agent not responding"
}
```

### Integration Tests

```bash
# Test git clone over SSH
test_git_clone_ssh() {
    cd /home/agent/workspace
    git clone git@github.com:user/test-repo.git
    [ -d "test-repo" ] || fail "Clone failed"
}

# Test git operations
test_git_operations() {
    cd /home/agent/workspace/test-repo
    git pull origin main
    echo "test" > test.txt
    git add test.txt
    git commit -m "test"
    git push origin main
}
```

## Documentation Requirements

1. **User Guide**: `docs/SSH_KEY_SETUP.md`
   - How to prepare SSH keys for CloakCode
   - Supported key types (Ed25519, RSA)
   - Security best practices

2. **Quick Start Update**: Add SSH key section
   - Quick setup command
   - Common troubleshooting

3. **Security Documentation**: Update with SSH-specific risks
   - Key exposure scenarios
   - Mitigation strategies

## Migration Path

### Phase 1: Basic Implementation
- ✅ Volume-mounted keys
- ✅ Entrypoint setup script
- ✅ Basic git configuration

### Phase 2: Enhanced Security
- [ ] SSH agent forwarding support
- [ ] Key encryption at rest
- [ ] Per-host key configuration

### Phase 3: Advanced Features
- [ ] SSH proxy container (optional)
- [ ] Multi-key management
- [ ] Key rotation automation

## Alternative: Continue
