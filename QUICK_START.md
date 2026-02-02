# CloakCode Quick Start Guide

Get CloakCode up and running in 5 minutes!

## 📋 Prerequisites

Before you begin, ensure you have:

- ✅ **Docker** installed and running ([Download Docker](https://www.docker.com/products/docker-desktop))
- ✅ **docker-compose** installed (included with Docker Desktop)
- ✅ **Python 3.12 or 3.13** (3.14 not yet supported)
- ✅ **Git** for cloning the repository
- ✅ **macOS, Linux, or WSL2** (Windows with WSL2)

Check versions:
```bash
docker --version          # Should be 20.10+
docker-compose --version  # Should be 2.0+
python3 --version         # Should be 3.12.x or 3.13.x
```

---

## 🚀 Installation (5 Steps)

### Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/andrewgibson-cic/cloak-code.git
cd cloak-code
```

### Step 2: Install Python Dependencies

```bash
# Install dependencies (checks Python version automatically)
make install

# If you need Python 3.12:
make setup-venv  # Creates a Python 3.12 virtual environment
source venv/bin/activate
make install
```

Expected output:
```
✅ Python version is compatible
Python 3.12.12
Installing CloakCode dependencies...
✅ Installation complete!
```

### Step 3: Verify Installation

```bash
make verify
```

Expected output:
```
1. Checking Python packages...
✅ mitmproxy: 10.4.2

2. Checking configuration files...
✅ .env exists
✅ proxy/config.yaml exists
✅ credentials.yml exists

3. Checking Docker...
✅ Docker installed
✅ docker-compose installed

4. Checking logs directory...
✅ logs/ directory exists
```

### Step 4: Configure Credentials

The installation already created `.env` with DUMMY credentials. To use real APIs:

```bash
# Edit .env with your favorite editor
nano .env
# or
code .env
```

Replace DUMMY values with your real credentials:

```bash
# Example .env configuration
OPENAI_API_KEY=sk-proj-your-real-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-real-anthropic-key-here
GITHUB_TOKEN=ghp_your-real-github-token-here
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=your-real-aws-secret-key
```

**Important**: Never commit `.env` to version control! It's already in `.gitignore`.

### Step 5: Start CloakCode

```bash
make start
```

Expected output:
```
Starting Docker containers...
✅ Containers started!
View logs: make logs
Check status: make status
```

Verify containers are running:
```bash
make status
```

---

## 🎯 Configure Your AI Assistant

### For Cline (Claude Code / VS Code)

1. Open VS Code Command Palette (`Cmd/Ctrl + Shift + P`)
2. Select "Cline: Open Settings"
3. Configure API:
   - **Provider**: Anthropic
   - **API Key**: `DUMMY_ANTHROPIC_KEY`
   - **Model**: claude-sonnet-4-5-20250929-v1:0

The CloakCode proxy will automatically replace `DUMMY_ANTHROPIC_KEY` with your real key!

### For Cursor

1. Open Cursor Settings (`Cmd/Ctrl + ,`)
2. Search for "API Key"
3. Set OpenAI API Key: `DUMMY_OPENAI_KEY`

### For Aider (Command Line)

```bash
# Set environment variable
export OPENAI_API_KEY=DUMMY_OPENAI_KEY
export ANTHROPIC_API_KEY=DUMMY_ANTHROPIC_KEY

# Configure to use proxy
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Run aider
aider
```

---

## ✅ Verify It's Working

### Watch Credentials Being Injected

Open a new terminal and watch the proxy logs:

```bash
make logs-proxy
```

Now use your AI assistant to make an API call. You should see logs like:

```
[INFO] Detected dummy credential: DUMMY_ANTHROPIC_KEY
[INFO] Host validated: api.anthropic.com ✓
[INFO] Injecting real credential for: anthropic
[INFO] Request forwarded to: https://api.anthropic.com/v1/messages
```

**Note**: The real credential is NEVER logged - only the dummy token and host information!

### Test with a Simple API Call

```bash
# From inside the agent container
docker-compose exec agent bash

# Test OpenAI API (using dummy credential)
curl -X POST https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer DUMMY_OPENAI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"Hi"}]}'
```

The proxy will automatically inject your real OpenAI key!

---

## 📊 Common Commands

### Container Management

```bash
make start          # Start CloakCode
make stop           # Stop CloakCode
make restart        # Restart containers
make status         # Show container status
```

### Viewing Logs

```bash
make logs           # Follow all logs
make logs-proxy     # Watch proxy credential injection
make logs-agent     # Watch agent container
```

### Development

```bash
make test           # Run all tests
make test-unit      # Run unit tests only
make format         # Format code
make clean          # Clean artifacts
```

### Help

```bash
make help           # Show all commands