# SSH Key Setup for CloakCode

## Overview

This guide explains how to enable SSH key authentication for git operations within the CloakCode agent container. SSH keys allow you to perform git clone, push, and pull operations without exposing your credentials in HTTP headers.

## Why SSH Keys?

While CloakCode's proxy can inject credentials into HTTPS git operations, using SSH keys provides several advantages:

- **Industry Standard**: SSH is the standard for git authentication
- **Better Security**: Private keys stay on your machine, never in HTTP traffic
- **Simpler Workflow**: No need to configure git credential helpers
- **Universal**: Works with GitHub, GitLab, Bitbucket, and self-hosted git servers

## Quick Start

### 1. Prepare SSH Keys

Run the setup script to copy your SSH keys to the CloakCode staging area:

```bash
./scripts/setup-ssh-keys.sh
```

This script will:
- Copy your SSH keys from `~/.ssh/` to `./ssh-keys/`
- Create an SSH config file for common git hosts
- Set proper file permissions (600 for private keys)
- Add `ssh-keys/` to `.gitignore` to prevent accidental commits

### 2. Enable SSH in Docker Compose

Add the SSH key volume to your `docker-compose.yml`:

```yaml
services:
  agent:
    volumes:
      - ./ssh-keys:/ssh-keys:ro  # Add this line
      - ./workspace:/home/agent/workspace
      # ... other volumes
```

Or use the provided example:

```bash
docker-compose -f docker-compose.yml -f docker-compose.ssh-example.yml up
```

### 3. Start the Agent Container

```bash
docker-compose up -d agent
```

The entrypoint script will automatically:
- Detect mounted SSH keys
- Copy them to `~/.ssh/` with proper permissions
- Configure git to prefer SSH URLs
- Set up known_hosts for common git servers

### 4. Verify SSH Configuration

Test your SSH connection to GitHub:

```bash
docker-compose exec agent ssh -T git@github.com
```

Expected output:
```
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

## Supported Authentication Methods

CloakCode supports two methods for SSH authentication:

### Method 1: Volume-Mounted Keys (Recommended)

**How it works:**
- SSH keys are copied to a staging directory (`./ssh-keys/`)
- Directory is mounted read-only into the agent container
- Keys are copied to `~/.ssh/` at container startup
- Keys are cleared when container exits

**Setup:**
```bash
./scripts/setup-ssh-keys.sh
# Then add volume mount to docker-compose.yml
```

**Pros:**
- Simple and reliable
- Works on all platforms
- Keys secured with proper permissions

**Cons:**
- Keys temporarily in container filesystem (though cleared on exit)
- Requires manual setup step

### Method 2: SSH Agent Forwarding (Alternative)

**How it works:**
- Your host's SSH agent socket is mounted into the container
- Container uses your host's SSH agent for authentication
- No keys are copied into the container

**Setup:**
```yaml
services:
  agent:
    volumes:
      - ${SSH_AUTH_SOCK}:/ssh-agent:ro
    environment:
      - SSH_AUTH_SOCK=/ssh-agent
```

**Pros:**
- Zero keys in container
- Most secure option
- Dynamic key management

**Cons:**
- Requires SSH agent running on host
- May not work on Windows
- Socket permissions can be tricky

## Supported Key Types

CloakCode supports all standard SSH key types:

| Key Type | File Name | Recommended | Notes |
|----------|-----------|-------------|-------|
| **Ed25519** | `id_ed25519` | ✅ Yes | Modern, secure, fast |
| **RSA** | `id_rsa` | ⚠️ Legacy | Use 4096-bit minimum |
| **ECDSA** | `id_ecdsa` | ⚠️ Legacy | Ed25519 preferred |

### Generating SSH Keys

If you don't have SSH keys, generate them:

```bash
# Ed25519 (recommended)
ssh-keygen -t ed25519 -C "your_email@example.com"

# RSA (if Ed25519 not supported)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

Then add your public key to your git hosting service:
- **GitHub**: Settings → SSH and GPG keys
- **GitLab**: Preferences → SSH Keys
- **Bitbucket**: Personal settings → SSH keys

## Configuration

### SSH Config File

The setup script creates `./ssh-keys/config` with sensible defaults:

```ssh-config
# GitHub
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new

# GitLab
Host gitlab.com
    HostName gitlab.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
```

### Customizing for Multiple Keys

If you use different keys for different services:

```ssh-config
# GitHub Personal
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_personal
    IdentitiesOnly yes

# GitHub Work
Host github-work
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_work
    IdentitiesOnly yes
```

Then clone with:
```bash
git clone git@github-work:company/repo.git
```

### Git URL Rewriting

The entrypoint script automatically configures git to use SSH for GitHub and GitLab:

```bash
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

This means HTTPS URLs are automatically converted to SSH:
```bash
# Both work the same:
git clone https://github.com/user/repo.git
git clone git@github.com:user/repo.git
```

## Usage Examples

### Clone a Repository

```bash
docker-compose exec agent bash
cd workspace
git clone git@github.com:username/repository.git
```

### Push Changes

```bash
cd workspace/repository
git add .
git commit -m "Update files"
git push origin main
```

### Pull Updates

```bash
cd workspace/repository
git pull origin main
```

## Security Considerations

### Key Protection

1. **File Permissions**: Private keys must have 600 permissions (owner read/write only)
2. **Read-Only Mount**: Keys are mounted read-only into the container
3. **Automatic Cleanup**: Keys are deleted from container on exit
4. **Never Commit**: The `ssh-keys/` directory is in `.gitignore`

### Host Validation

The setup includes host key verification for common git servers:
- **StrictHostKeyChecking=accept-new**: Accept new hosts, reject changed hosts
- **known_hosts**: Pre-populated with GitHub, GitLab, Bitbucket keys
- **Hash known_hosts**: Prevents information disclosure

### Key Isolation

- Keys are isolated to the agent container
- No keys are embedded in Docker images
- Keys are not accessible from the proxy container
- Container can be safely destroyed without losing keys

## Troubleshooting

### Permission Denied (publickey)

**Problem**: `git clone` fails with "Permission denied (publickey)"

**Solutions**:
1. Verify your public key is added to the git hosting service
2. Test SSH connection: `docker-compose exec agent ssh -T git@github.com`
3. Check key permissions: `docker-compose exec agent ls -la ~/.ssh/`
4. Verify key is loaded: `docker-compose exec agent ssh-add -l`

### No SSH Keys Found

**Problem**: Container starts but says "No SSH keys found"

**Solutions**:
1. Run `./scripts/setup-ssh-keys.sh` on the host
2. Verify volume mount in `docker-compose.yml`: `- ./ssh-keys:/ssh-keys:ro`
3. Check directory exists: `ls -la ./ssh-keys/`
4. Restart container: `docker-compose restart agent`

### Wrong Key Being Used

**Problem**: Git tries to use the wrong SSH key

**Solutions**:
1. Edit `./ssh-keys/config` to specify the correct key
2. Use `IdentitiesOnly yes` to prevent trying multiple keys
3. Specify key in git command: `GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa" git clone ...`

### Host Key Verification Failed

**Problem**: SSH warns about host key mismatch

**Solutions**:
1. Remove the old key: `docker-compose exec agent ssh-keygen -R github.com`
2. Accept new key: `docker-compose exec agent ssh -T git@github.com`
3. Or pre-add key: `docker-compose exec agent ssh-keyscan github.com >> ~/.ssh/known_hosts`

### Keys Not Cleared on Exit

**Problem**: SSH keys remain in container after exit

**Solutions**:
1. The cleanup trap should handle this automatically
2. Manually clear: `docker-compose exec agent rm -rf ~/.ssh/`
3. Destroy container: `docker-compose down agent`

## Advanced Configuration

### Using Multiple Keys

Create separate configs for different environments:

```bash
./scripts/setup-ssh-keys.sh --source ~/.ssh-personal --dest ./ssh-keys-personal
./scripts/setup-ssh-keys.sh --source ~/.ssh-work --dest ./ssh-keys-work
```

Mount the appropriate directory based on your needs.

### Encrypted Keys

If your SSH keys have passphrases:

1. **Option 1**: Use SSH agent forwarding (recommended)
2. **Option 2**: Remove passphrase (less secure):
   ```bash
   ssh-keygen -p -f ~/.ssh/id_ed25519
   ```

### Custom Git Hosts

For self-hosted git servers, add to `./ssh-keys/config`:

```ssh-config
Host git.company.com
    HostName git.company.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    Port 2222  # If non-standard port
    IdentitiesOnly yes
```

## Comparison: SSH vs HTTPS

| Feature | SSH Keys | HTTPS (Proxy) |
|---------|----------|---------------|
| **Setup Complexity** | Medium | Low |
| **Security** | High | High |
| **Git Standard** | Yes | No |
| **Credential Rotation** | Manual | Automatic |
| **Works Offline** | Yes | Requires proxy |
| **Platform Support** | Universal | Universal |

**Recommendation**: Use SSH keys for git operations and let the proxy handle API credentials (OpenAI, AWS, etc.).

## Related Documentation

- [CloakCode Architecture](../docs/Universal%20Injector%20Architecture.md)
- [SSH Key Injection Investigation](./SSH_KEY_INJECTION_INVESTIGATION.md)
- [Docker Compose Configuration](../docker-compose.yml)
- [Agent Entrypoint Script](../agent/entrypoint.sh)

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the investigation document: `docs/SSH_KEY_INJECTION_INVESTIGATION.md`
3. Check container logs: `docker-compose logs agent`
4. File an issue on GitHub

---

**Remember**: Never commit SSH private keys to version control! The `ssh-keys/` directory is in `.gitignore` to protect you.
