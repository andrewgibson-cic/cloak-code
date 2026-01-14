# Cline Setup Guide for CloakCode

This guide explains how to set up and use Cline (AI coding assistant) within your CloakCode agent container, ensuring all API calls go through the secure credential injection proxy.

---

## Overview

Cline is a VS Code extension that provides AI-powered coding assistance. By running Cline in a VS Code Remote Container connected to your CloakCode agent, you get:

- ✅ **Secure credential management** - Real API keys never exposed to Cline
- ✅ **Transparent proxy** - All Cline API calls automatically go through CloakCode
- ✅ **Full IDE integration** - Complete Cline functionality with file editing, command execution
- ✅ **Audit logging** - All credential injections logged for security review
- ✅ **Isolated environment** - Container can be safely reset at any time

---

## Prerequisites

Before starting, ensure you have:

1. **VS Code** installed on your host machine
2. **Docker** and **docker-compose** running
3. **CloakCode containers** built and running (`docker-compose up -d`)
4. **Real API credentials** configured in `.env` file

---

## Installation Steps

### Step 1: Install VS Code Remote - Containers Extension

On your **host machine** (not in the container):

```bash
# Option 1: Via command line
code --install-extension ms-vscode-remote.remote-containers

# Option 2: Via VS Code UI
# 1. Open VS Code
# 2. Go to Extensions (Cmd/Ctrl+Shift+X)
# 3. Search for "Remote - Containers"
# 4. Click Install
```

**Time required:** ~1 minute

---

### Step 2: Rebuild Containers (If Needed)

The `.devcontainer/devcontainer.json` configuration has been created. Rebuild to ensure everything is up to date:

```bash
# Stop containers
docker-compose down

# Rebuild and start
docker-compose up -d --build

# Verify they're running
docker-compose ps
```

**Time required:** ~2 minutes

---

### Step 3: Connect VS Code to the Agent Container

1. **Open VS Code** on your host machine

2. **Open Command Palette:**
   - Mac: `Cmd+Shift+P`
   - Windows/Linux: `Ctrl+Shift+P`

3. **Type and select:**
   ```
   Remote-Containers: Attach to Running Container...
   ```

4. **Select the container:**
   ```
   cloakcode_agent
   ```

5. **Wait for connection** (~30 seconds first time)
   - VS Code will install the VS Code Server in the container
   - Extensions will be automatically installed (including Cline)
   - You'll see a green "Container" indicator in the bottom-left corner

**Time required:** ~1 minute (first time), ~10 seconds (subsequent times)

---

### Step 4: Verify Cline Installation

Once connected to the remote container:

1. **Check the sidebar** - You should see the Cline icon (Claude logo)
2. **If Cline isn't visible:**
   - Go to Extensions (Cmd/Ctrl+Shift+X)
   - Search for "Cline" or "Claude Dev"
   - Click Install (it should auto-install from devcontainer.json)

---

### Step 5: Configure Cline with Dummy Credentials

This is the **critical security step**. You must configure Cline with DUMMY credentials that will be replaced by the proxy.

1. **Open Cline settings:**
   - Click the Cline icon in the sidebar
   - Click the settings gear icon
   - Or: Command Palette → "Cline: Open Settings"

2. **Configure based on your provider:**

#### For Anthropic (Claude):

```
API Provider: Anthropic
API Key: DUMMY_ANTHROPIC_KEY
Model: claude-3-5-sonnet-20241022 (or latest)
```

#### For OpenAI:

```
API Provider: OpenAI
API Key: DUMMY_OPENAI_KEY
Model: gpt-4 (or your preferred model)
```

#### For IBM ICA (OpenAI Compatible):

```
API Provider: OpenAI Compatible
Base URL: https://servicesessentials.ibm.com/apis/v3
API Key: DUMMY_ICA_KEY
Model ID: global/anthropic.claude-sonnet-4-5-20250929-v1:0
```

**Regional ICA URLs:**
- Canada: `https://canada.ica.ibm.com/ica/apis/v3`
- US: `https://us.ica.ibm.com/ica/apis/v3`
- Europe: `https://remea.ica.ibm.com/ica/apis/v3`
- UK: `https://uki.ica.ibm.com/ica/apis/v3`
- Australia: `https://au.ica.ibm.com/ica/apis/v3`
- Japan: `https://japan.ica.ibm.com/ica/apis/v3`
- India: `https://india.ica.ibm.com/ica/apis/v3`

3. **Save the configuration**

**Time required:** ~1 minute

---

### Step 6: Configure Proxy Credential Injection

Now configure the CloakCode proxy to replace your dummy credentials with real ones.

#### A. Update `proxy/config.yaml`

Add a strategy and rule for Cline's API calls:

**For Anthropic:**

```yaml
strategies:
  - name: anthropic-cline
    type: bearer
    config:
      token: ANTHROPIC_API_KEY  # Reads from .env
      dummy_pattern: "DUMMY_ANTHROPIC_KEY"
      allowed_hosts:
        - "api.anthropic.com"
        - "*.anthropic.com"

rules:
  - name: cline-anthropic-injection
    domain_regex: "^(.*\\.)?anthropic\\.com$"
    trigger_header_regex: "DUMMY_ANTHROPIC_KEY"
    strategy: anthropic-cline
    priority: 100
```

**For OpenAI:**

```yaml
strategies:
  - name: openai-cline
    type: bearer
    config:
      token: OPENAI_API_KEY  # Reads from .env
      dummy_pattern: "DUMMY_OPENAI_KEY"
      allowed_hosts:
        - "api.openai.com"
        - "*.openai.com"

rules:
  - name: cline-openai-injection
    domain_regex: "^(.*\\.)?openai\\.com$"
    trigger_header_regex: "DUMMY_OPENAI_KEY"
    strategy: openai-cline
    priority: 100
```

**For IBM ICA:**

```yaml
strategies:
  - name: ica-cline
    type: bearer
    config:
      token: ICA_API_KEY  # Reads from .env
      dummy_pattern: "DUMMY_ICA_KEY"
      allowed_hosts:
        - "servicesessentials.ibm.com"
        - "*.ica.ibm.com"

rules:
  - name: cline-ica-injection
    domain_regex: "^(.*servicesessentials\\.ibm\\.com|.*\\.ica\\.ibm\\.com)$"
    trigger_header_regex: "DUMMY_ICA_KEY"
    strategy: ica-cline
    priority: 100
```

#### B. Add Real Credential to `.env`

Add your real API key to the `.env` file (never commit this!):

```bash
# For Anthropic
ANTHROPIC_API_KEY=sk-ant-your-real-anthropic-key-here

# For OpenAI
OPENAI_API_KEY=sk-proj-your-real-openai-key-here

# For IBM ICA
ICA_API_KEY=your-real-ica-composite-key-here
```

#### C. Restart Proxy

```bash
docker-compose restart proxy

# Verify proxy loaded the new configuration
docker logs cloakcode_proxy
```

**Time required:** ~2 minutes

---

### Step 7: Test the Setup

1. **Open a terminal in VS Code** (remote session)
   - Terminal → New Terminal
   - You should be in `/home/agent/workspace`

2. **Create a test file:**
   ```bash
   cd workspace
   echo "# Test File" > test.md
   ```

3. **Ask Cline to help:**
   - Open Cline from the sidebar
   - Type: "Read test.md and add a section about CloakCode"
   - Press Enter

4. **Monitor the logs:**
   - Open a new terminal on your **host machine**
   - Run: `tail -f logs/proxy_injections.log`
   - You should see entries showing credential injection when Cline makes API calls

5. **Verify credential replacement:**
   ```bash
   # In the host terminal
   grep "DUMMY_ANTHROPIC_KEY" logs/proxy_injections.log
   # You should see log entries showing the dummy key being detected and replaced
   ```

**Expected log output:**
```
[2026-01-13 07:30:45] INJECTION: api.anthropic.com
  Trigger: DUMMY_ANTHROPIC_KEY detected
  Strategy: anthropic-cline
  Status: SUCCESS
  Duration: 0.002s
```

---

## Using Cline Securely

### Best Practices

1. **Always use DUMMY credentials** in Cline configuration
2. **Never hardcode real API keys** in your code
3. **Monitor logs** regularly: `tail -f logs/proxy_injections.log`
4. **Review audit trail** for security: `cat logs/audit.json | jq`
5. **Reset container** if compromised: `docker-compose down && docker-compose up -d`

### Common Workflows

#### Code Generation
```
Prompt: "Create a Python script that lists S3 buckets using boto3"
```
Cline will:
- Generate code with `AKIA00000000DUMMYKEY` credentials
- Proxy will replace with real AWS credentials when code runs
- You get working code without ever exposing real keys

#### File Operations
```
Prompt: "Read all .py files in workspace/ and add docstrings"
```
Cline can:
- Read and edit files in the container
- Execute commands via the terminal
- All within the secure, isolated environment

#### Git Operations
```
Prompt: "Create a new branch and commit these changes"
```
If SSH keys are configured:
- Git operations use SSH authentication
- SSH keys are automatically available in the container
- Proxy doesn't need to inject credentials for git

---

## Troubleshooting

### Cline Can't Connect to API

**Symptom:** Cline shows connection errors

**Solutions:**

1. **Verify proxy is running:**
   ```bash
   docker-compose ps
   # Both proxy and agent should show "Up"
   ```

2. **Check proxy logs:**
   ```bash
   docker logs cloakcode_proxy
   # Look for errors or blocked requests
   ```

3. **Verify dummy credential in Cline settings:**
   - Must exactly match the pattern in `proxy/config.yaml`
   - Common mistake: Using real key instead of dummy key

4. **Test proxy connectivity:**
   ```bash
   docker exec cloakcode_agent curl -v http://proxy:8080
   ```

### Credential Not Being Replaced

**Symptom:** API calls fail with "invalid API key"

**Solutions:**

1. **Check proxy configuration:**
   ```bash
   # Verify strategy is loaded
   docker logs cloakcode_proxy | grep "Loaded.*strategies"
   
   # Verify rule is loaded
   docker logs cloakcode_proxy | grep "Loaded.*rules"
   ```

2. **Verify dummy pattern matches:**
   - In `proxy/config.yaml`: `dummy_pattern: "DUMMY_ANTHROPIC_KEY"`
   - In Cline settings: API Key must be exactly `DUMMY_ANTHROPIC_KEY`

3. **Check .env file:**
   ```bash
   # Verify real credential exists
   grep ANTHROPIC_API_KEY .env
   ```

4. **Restart proxy after config changes:**
   ```bash
   docker-compose restart proxy
   ```

### VS Code Can't Connect to Container

**Symptom:** "Failed to connect" error

**Solutions:**

1. **Verify container is running:**
   ```bash
   docker ps | grep cloakcode_agent
   ```

2. **Check container logs:**
   ```bash
   docker logs cloakcode_agent
   ```

3. **Rebuild container:**
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

4. **Check VS Code Remote extension:**
   - Ensure "Remote - Containers" extension is installed
   - Try reloading VS Code window

### Extensions Not Installing

**Symptom:** Cline or other extensions missing after connecting

**Solutions:**

1. **Check devcontainer.json:**
   ```bash
   cat .devcontainer/devcontainer.json
   # Verify "saoudrizwan.claude-dev" is in extensions list
   ```

2. **Manual install:**
   - In remote session: Extensions → Search "Cline" → Install

3. **Check extension logs:**
   - View → Output → Select "Extension Host"

---

## Advanced Configuration

### Enable Memory Bank

For complex projects, enable Cline's memory bank feature:

1. **Update `.clinerules`:**
   ```json
   {
     "memoryBank": {
       "enabled": true,
       "contextFiles": [
         "memory-bank/activeContext.md",
         "memory-bank/projectbrief.md",
         "memory-bank/systemPatterns.md"
       ]
     }
   }
   ```

2. **Create memory bank files:**
   ```bash
   mkdir -p workspace/memory-bank
   cd workspace/memory-bank
   
   # Create initial context files
   cat > projectbrief.md << 'EOF'
   # CloakCode Project Brief
   
   ## Purpose
   Universal credential injection proxy for secure API access
   
   ## Key Components
   - Proxy: mitmproxy-based credential injector
   - Agent: Isolated execution environment
   - Strategies: Pluggable authentication protocols
   EOF
   
   cat > activeContext.md << 'EOF'
   # Active Context
   
   ## Current Focus
   Setting up Cline integration with secure credential management
   
   ## Recent Changes
   - Added .devcontainer configuration
   - Configured VS Code Remote Containers
   - Set up Cline with dummy credentials
   EOF
   ```

### Custom Port Forwarding

If you need to access additional services from the container:

1. **Update `.devcontainer/devcontainer.json`:**
   ```json
   {
     "forwardPorts": [
       3000,  // Your custom port
       5432   // PostgreSQL, etc.
     ]
   }
   ```

2. **Reconnect VS Code** to apply changes

---

## Security Checklist

Before using Cline in production:

- [ ] Verified `.env` file is in `.gitignore`
- [ ] Configured Cline with DUMMY credentials only
- [ ] Tested credential injection in logs
- [ ] Verified real credentials not exposed in container
- [ ] Set up audit log monitoring
- [ ] Tested container reset procedure
- [ ] Documented emergency procedures
- [ ] Trained team on secure usage

---

## Next Steps

Now that Cline is set up:

1. **Explore Cline features** - Try different prompts and workflows
2. **Review logs regularly** - Monitor `logs/proxy_injections.log`
3. **Customize .clinerules** - Add project-specific guidelines
4. **Set up memory bank** - For better context retention
5. **Read Cline docs** - Learn advanced features

---

## Support

- **CloakCode Issues:** Check main README.md and docs/
- **Cline Issues:** Visit https://github.com/cline/cline
- **VS Code Remote
