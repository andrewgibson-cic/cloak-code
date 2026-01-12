# Runtime Installation Guide

This document shows how to install AI CLI tools inside the Universal Injector agent container at runtime.

## Container Overview

The agent container starts **clean and fresh** with:
- Node.js 20 (with npm)
- Python 3 (with pip)
- Essential build tools
- sudo access for the `agent` user (passwordless)
- All network traffic routed through the credential-injecting proxy

## Installing Claude Code CLI

```bash
# Enter the container
docker-compose exec agent bash

# Install Claude Code globally (requires sudo for global npm packages)
sudo npm install -g @anthropic-ai/claude-code

# Run Claude Code (credentials will be automatically injected by proxy)
claude-code
```

## Installing Google Gemini CLI

```bash
# Enter the container
docker-compose exec agent bash

# Install Gemini CLI globally (requires sudo for global npm packages)
sudo npm install -g @google/gemini-cli

# Run Gemini (credentials will be automatically injected by proxy)
gemini
```

## Installing Other AI Tools

The container has all the necessary build tools to install most AI CLI applications:

### npm-based tools (Global Installation)
```bash
# Global install requires sudo
sudo npm install -g <package-name>

# Or install locally without sudo
npm install <package-name>
```

### Python-based tools
```bash
# User-level install (no sudo needed)
pip install --user <package-name>

# Or system-wide with sudo
sudo pip install <package-name>
```

### Git-based tools
```bash
git clone <repository-url>
cd <repository>
npm install  # Local install, no sudo needed
# or
pip install --user .  # User install, no sudo needed
```

## Permission Notes

The agent container runs as the `agent` user (non-root) for security:
- **Global npm packages** (`npm install -g`) require `sudo`
- **Local npm packages** (`npm install`) work without sudo
- **Python user packages** (`pip install --user`) work without sudo
- The `agent` user has passwordless sudo access for convenience

## Persistent Installations

**Important:** By default, installations are ephemeral and will be lost when the container is destroyed.

To make installations persistent across container restarts, you have two options:

### Option 1: Volume Mount
Add a volume for node/python packages in `docker-compose.yml`:
```yaml
volumes:
  - agent_node_modules:/usr/local/lib/node_modules
  - agent_python_packages:/usr/local/lib/python3.11/site-packages
```

### Option 2: Custom Image
Create a custom Dockerfile that extends the agent image:
```dockerfile
FROM universal-injector-agent:latest

USER root
RUN npm install -g @anthropic-ai/claude-code
RUN npm install -g @google/gemini-cli
USER agent
```

## Why Start Clean?

Starting with a clean container provides:
- ✅ **Flexibility**: Install only the tools you need
- ✅ **Faster builds**: No waiting for tool installations during image build
- ✅ **Easy testing**: Try different tools without rebuilding the image
- ✅ **Version control**: Choose specific versions at runtime
- ✅ **Smaller image**: Base image is leaner without pre-installed tools

## Proxy Integration

All installed tools automatically work with the credential-injecting proxy because:
1. `HTTP_PROXY` and `HTTPS_PROXY` environment variables are pre-configured
2. Custom CA certificates are trusted
3. Dummy API keys are set (will be replaced by real credentials from the proxy)

## Example Workflow

```bash
# Start the containers
docker-compose up -d

# Enter the agent container
docker-compose exec agent bash

# Install your preferred AI CLI tool
sudo npm install -g @anthropic-ai/claude-code

# Use the tool (credentials automatically injected)
cd workspace
claude-code --help

# Your API calls go through the proxy, credentials are injected transparently
