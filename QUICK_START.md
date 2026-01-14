# 🚀 CloakCode Quick Start Guide

Get up and running with CloakCode in 5 minutes!

---

## What is CloakCode?

**CloakCode** shields your API credentials from your code. Your applications use dummy tokens, and CloakCode automatically injects real credentials on-the-fly. Even if your code is compromised, your real API keys stay safe.

### Key Features
- 🛡️ **Zero-knowledge security** - Apps never see real credentials
- 🔌 **Works with any API** - AWS, OpenAI, GitHub, Stripe, and more
- 🚀 **No code changes required** - Drop-in replacement for existing apps
- 🐳 **Docker-based** - Isolated, containerized environment

---

## Installation

### Option 1: One-Command Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/andrewgibson-cic/cloak-code/master/install.sh | bash
```

Or download and run:

```bash
git clone git@github.com:andrewgibson-cic/cloak-code.git
cd cloak-code
./install.sh
```

### Option 2: Manual Install

```bash
# Clone the repository
git clone git@github.com:andrewgibson-cic/cloak-code.git
cd cloakcode

# Copy configuration templates
cp .env.template .env

# Build and start
make install
make start
```

---

## Quick Setup (3 Steps)

### Step 1: Add Your API Credentials

Edit the `.env` file with your real API keys:

```bash
vim .env
```

Example:

```bash
# OpenAI
REAL_OPENAI_API_KEY=sk-proj-YourRealOpenAIKeyHere

# GitHub
REAL_GITHUB_TOKEN=ghp_YourRealGitHubTokenHere

# AWS
REAL_AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
REAL_AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### Step 2: Restart Services

```bash
make restart
```

### Step 3: Access the Secure Environment

```bash
docker exec -it cloakcode_agent bash
```

That's it! You're now in a secure environment where all API calls are automatically protected.

---

## Your First API Call

Once inside the agent container, try making an API call with a **dummy credential**:

### Example 1: OpenAI

```bash
cd workspace

# Create a test script
cat > test_openai.py << 'EOF'
import openai

# Use a DUMMY key - it will be replaced automatically!
openai.api_key = "DUMMY_OPENAI_KEY"

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
EOF

# Run it
python3 test_openai.py
```

The dummy key `DUMMY_OPENAI_KEY` is automatically replaced with your real key!

### Example 2: AWS S3

```python
import boto3

# Use DUMMY credentials
s3 = boto3.client('s3',
    aws_access_key_id='AKIA00000000DUMMYKEY',
    aws_secret_access_key='DUMMY_SECRET_KEY'
)

# This works! Real credentials injected automatically
buckets = s3.list_buckets()
print(f"Found {len(buckets['Buckets'])} buckets")
```

### Example 3: GitHub API

```bash
# Use dummy token in curl
curl -H "Authorization: Bearer DUMMY_GITHUB_TOKEN" \
     https://api.github.com/user

# Real token is injected automatically!
```

---

## Common Commands

```bash
# Start CloakCode
make start

# Stop CloakCode
make stop

# View logs
make logs

# Access agent shell
make shell

# Add new API credential
make add-credential

# List all configured credentials
make list-credentials

# Run tests
make test

# Clean up (remove containers & volumes)
make clean

# See all commands
make help
```

---

## Adding More APIs

### Interactive Method

```bash
./scripts/add-credential.sh
```

Follow the wizard to configure any API you need.

### Manual Method

1. Add strategy to `proxy/config.yaml`:

```yaml
strategies:
  - name: my-api
    type: bearer
    config:
      token: MY_API_TOKEN
      allowed_hosts:
        - "api.myservice.com"
```

2. Add rule to `proxy/config.yaml`:

```yaml
rules:
  - name: my-api-injection
    domain_regex: "^api\\.myservice\\.com$"
    trigger_header_regex: "DUMMY_MY_API"
    strategy: my-api
    priority: 100
```

3. Add real credential to `.env`:

```bash
MY_API_TOKEN=your-real-token-here
```

4. Restart:

```bash
make restart
```

---

## How It Works

```
┌─────────────────────┐
│   Your Application  │
│  (Uses DUMMY keys)  │
└──────────┬──────────┘
           │ All HTTP traffic
           ▼
┌─────────────────────┐
│   CloakCode Proxy   │
│  • Detects dummy    │
│  • Validates host   │
│  • Injects real key │
└──────────┬──────────┘
           │ Authenticated request
           ▼
┌─────────────────────┐
│    External API     │
│ (AWS, OpenAI, etc.) │
└─────────────────────┘
```

---

## Troubleshooting

### Proxy Not Intercepting Requests

```bash
# Check proxy is running
docker ps | grep cloakcode_proxy

# View proxy logs
make logs-proxy

# Restart services
make restart
```

### Certificate Errors

```bash
# Regenerate certificates
make clean
make start
```

### API Call Not Working

```bash
# Check if credential is configured
make list-credentials

# Verify .env has the real key
cat .env | grep YOUR_API_KEY

# Check proxy logs for errors
make logs-proxy
```

### Can't Access Container

```bash
# Check container status
docker ps -a | grep cloakcode

# Restart everything
make stop
make start
```

---

## Security Best Practices

✅ **DO:**
- Keep `.env` file secret (never commit it!)
- Use specific host whitelists for each credential
- Review proxy logs regularly
- Use short-lived credentials when possible

❌ **DON'T:**
- Commit `.env` to version control
- Share your `.env` file
- Disable host validation
- Use production keys in development

---

## What's Next?

### Learn More

- **Full Documentation**: See [README.md](README.md) for detailed information
- **Architecture**: Read [docs/Universal Injector Architecture.md](docs/Universal%20Injector%20Architecture.md)
- **Security**: Review [SECURITY_REVIEW.md](SECURITY_REVIEW.md)

### Advanced Topics

- **Kubernetes Deployment**: [docs/deployment/kubernetes.md](docs/deployment/kubernetes.md)
- **Custom Strategies**: [docs/reference/strategies.md](docs/reference/strategies.md)
- **Production Setup**: [docs/deployment/production.md](docs/deployment/production.md)

### Get Help

- **GitHub Issues**: Report bugs or request features
- **Documentation**: Check the `docs/` directory
- **Community**: Join discussions

---

## Example Use Cases

### 1. AI Agent Development

```python
# Your AI agent code
import anthropic

client = anthropic.Client(api_key="DUMMY_ANTHROPIC_KEY")

# Agent can make API calls safely
response = client.messages.create(...)
```

### 2. Microservices

```yaml
# Each microservice uses CloakCode
services:
  api-service:
    environment:
      STRIPE_KEY: DUMMY_STRIPE_KEY  # Real key injected
```

### 3. CI/CD Pipelines

```yaml
# GitHub Actions
- name: Run integration tests
  run: |
    docker-compose up -d cloakcode
    npm test  # Uses dummy keys, real ones injected
```

### 4. Development Environments

```bash
# Developers use dummy keys locally
export OPENAI_API_KEY=DUMMY_OPENAI_KEY

# CloakCode handles the rest
python my_app.py
```

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Install | `./install.sh` |
| Start | `make start` |
| Stop | `make stop` |
| Shell | `make shell` |
| Logs | `make logs` |
| Add credential | `make add-credential` |
| List credentials | `make list-credentials` |
| Restart | `make restart` |
| Clean up | `make clean` |
| Help | `make help` |

---

**Ready to go! 🚀 Start protecting your credentials with CloakCode.**

Questions? Check the [full documentation](README.md) or [open an issue](https://github.com/andrewgibson-cic/cloak-code/issues).
