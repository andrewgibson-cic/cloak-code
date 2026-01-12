# Universal API Credential Injector v2.0

**A transparent, zero-knowledge credential management proxy for secure API access.**

Transform any application into a credential-safe environment where real API keys never touch your code. Supports AWS, Stripe, GitHub, OpenAI, and any HTTP-based API.

---

## Overview

Universal API Credential Injector is a security proxy that automatically injects authentication credentials into HTTP requests. Originally built for AI agents like Claude, it has evolved into a universal enterprise solution for any application that needs secure API access.

### Key Features

- ✅ **AWS SigV4 Support** - Full AWS Signature Version 4 implementation for all AWS services
- ✅ **Strategy Pattern** - Pluggable authentication protocols (Bearer, AWS SigV4, API keys, custom headers)
- ✅ **Transparent Mode** - Automatic traffic interception (no proxy configuration needed in your app)
- ✅ **Rule-Based Routing** - Priority-based request matching with flexible configuration
- ✅ **Zero-Knowledge Security** - Applications never see real credentials
- ✅ **Host Whitelisting** - Per-credential destination validation prevents credential exfiltration

---

## 🎯 Use Cases

### Enterprise API Security
- **Multi-Cloud Deployments**: Securely access AWS, Azure, GCP without credential exposure
- **Payment Processing**: Stripe, PayPal, Square integration without key leakage
- **Microservices**: Decouple authentication from application code
- **CI/CD Pipelines**: Secure credential injection in build processes

### AI & Development
- **AI Agents**: Claude, GPT, autonomous systems with zero-knowledge credentials
- **Development Containers**: Secure dev environments with production API access
- **Testing**: Integration tests with real APIs without hardcoded keys

---

## 🔒 Security Architecture

### Zero-Knowledge Principle

**The application never sees real credentials.** All authentication happens transparently in the proxy layer.

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
│           Uses: AKIA00000000DUMMYKEY                     │
│                 (Dummy Credential)                       │
└──────────────────────┬──────────────────────────────────┘
                       │ All HTTP traffic automatically
                       │ intercepted (transparent mode)
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Universal Injector Proxy                    │
│  • Detects dummy credentials                             │
│  • Validates destination host                            │
│  • Signs request with real credentials                   │
│  • AWS SigV4, Bearer tokens, HMAC                        │
└──────────────────────┬──────────────────────────────────┘
                       │ Real authenticated request
                       ▼
              ┌────────────────────┐
              │   AWS / Stripe /   │
              │  GitHub / OpenAI   │
              └────────────────────┘
```

### Security Features

- **🔐 Credential Isolation**: Real keys exist only in proxy memory
- **✅ Host Whitelisting**: Per-credential destination validation
- **🚫 Exfiltration Prevention**: Credentials only sent to approved hosts
- **📊 Audit Logging**: Complete request tracking without exposing secrets
- **🛡️ Fail-Closed**: Block requests on error (configurable)
- **🔄 Transparent Mode**: Application unaware of proxy existence

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Docker Engine** 24.0+ with Docker Compose v2+
- **8GB RAM** minimum (16GB recommended for multiple services)
- **Linux/macOS/Windows** (Windows requires WSL2)
- **API credentials** for services you want to use
- **Basic knowledge** of YAML configuration and environment variables

---

## 🚀 Installation & Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd safe-claude
```

### Step 2: Copy Configuration Templates

```bash
# Copy proxy configuration template
cp proxy/config.yaml.example proxy/config.yaml

# Copy environment variables template
cp .env.template .env
```

### Step 3: Configure Your Credentials

This is the most important step. You need to configure two files:

#### A. Configure `proxy/config.yaml`

This file defines **strategies** (how to authenticate) and **rules** (when to apply them).

**Example configuration for AWS + GitHub + OpenAI:**

```yaml
# proxy/config.yaml

strategies:
  # AWS Strategy - for all AWS services (S3, EC2, Lambda, etc.)
  - name: aws-prod
    type: aws_sigv4
    config:
      access_key_id: AWS_ACCESS_KEY_ID        # Reads from .env
      secret_access_key: AWS_SECRET_ACCESS_KEY # Reads from .env
      region: us-east-1
      allowed_hosts:
        - "*.amazonaws.com"
  
  # GitHub Strategy
  - name: github
    type: github
    config:
      token: GITHUB_TOKEN  # Reads from .env
  
  # OpenAI Strategy
  - name: openai
    type: openai
    config:
      token: OPENAI_API_KEY  # Reads from .env

rules:
  # When app uses dummy AWS credentials, inject real ones
  - name: aws-injection
    domain_regex: ".*\\.amazonaws\\.com$"
    trigger_header_regex: "AKIA[0-9A-Z]{16}DUMMY"
    strategy: aws-prod
    priority: 100
  
  # When app uses dummy GitHub token, inject real one
  - name: github-injection
    domain_regex: "^(api\\.)?github\\.com$"
    trigger_header_regex: "(ghp_[a-zA-Z0-9]{36}DUMMY|DUMMY_GITHUB_TOKEN)"
    strategy: github
    priority: 100
  
  # When app uses dummy OpenAI key, inject real one
  - name: openai-injection
    domain_regex: "^api\\.openai\\.com$"
    trigger_header_regex: "(sk-proj-[a-zA-Z0-9]{32}DUMMY|DUMMY_OPENAI_KEY)"
    strategy: openai
    priority: 100

settings:
  log_level: INFO
  log_format: json
  fail_mode: closed  # Block requests on error (secure default)
```

See the [Configuration Reference](#⚙️-configuration-guide) section below for all options.

#### B. Configure `.env` File

This file contains your **real API credentials**. Never commit this file!

```bash
# .env

# ============================================================================
# AWS CREDENTIALS
# ============================================================================
# Get from: https://console.aws.amazon.com/iam/home#/security_credentials
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# Optional: For temporary credentials
# AWS_SESSION_TOKEN=your-session-token

# ============================================================================
# GITHUB CREDENTIALS
# ============================================================================
# Get from: https://github.com/settings/tokens
GITHUB_TOKEN=ghp_YourGitHubPersonalAccessTokenHere

# ============================================================================
# OPENAI CREDENTIALS
# ============================================================================
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-YourOpenAIKeyHere

# ============================================================================
# STRIPE CREDENTIALS (if using)
# ============================================================================
# Get from: https://stripe.com/docs/keys
# STRIPE_SECRET_KEY=sk_live_YourStripeKeyHere

# ============================================================================
# ADD MORE CREDENTIALS AS NEEDED
# ============================================================================
```

⚠️ **Important**: The `.env` file is already in `.gitignore`. Never commit it to version control!

### Step 4: Start the Services

```bash
# Start in detached mode
docker-compose up -d

# View logs to verify startup
docker-compose logs -f
```

You should see output like:
```
proxy_1  | ✓ Loaded 3 strategies: aws-prod, github, openai
proxy_1  | ✓ Loaded 3 rules
proxy_1  | ✓ Proxy listening on :8080
agent_1  | ✓ Transparent mode configured
```

### Step 5: Verify Installation

```bash
# Check container status
docker-compose ps

# Should show both containers running:
# NAME                  STATUS
# safe-claude-proxy-1   Up
# safe-claude-agent-1   Up

# Test the proxy
docker-compose exec agent curl -v http://httpbin.org/headers
```

---

## 🎯 How to Use

### Method 1: Transparent Mode (Recommended)

In transparent mode, your application doesn't need to know about the proxy. Traffic is automatically intercepted.

**Example: Python with AWS S3**

```python
import boto3

# Use dummy credentials - they'll be replaced with real ones automatically
s3 = boto3.client(
    's3',
    aws_access_key_id='AKIA00000000DUMMYKEY',
    aws_secret_access_key='DUMMY_SECRET_KEY_THAT_WILL_BE_REPLACED'
)

# This works! Real credentials injected transparently
response = s3.list_buckets()
print(f"Found {len(response['Buckets'])} buckets")
```

**Example: Python with GitHub API**

```python
import requests

# Use dummy token
headers = {
    'Authorization': 'Bearer DUMMY_GITHUB_TOKEN',
    'Accept': 'application/vnd.github.v3+json'
}

# Real token injected automatically
response = requests.get('https://api.github.com/user', headers=headers)
print(response.json())
```

**Example: cURL with OpenAI**

```bash
# Inside the agent container
docker-compose exec agent bash

# Use dummy key - it gets replaced
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer DUMMY_OPENAI_KEY"
```

### Method 2: Explicit Proxy Mode

Set proxy environment variables in your application:

```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
export NO_PROXY=localhost,127.0.0.1

# Now all HTTP/HTTPS traffic goes through the proxy
python your_application.py
```

---

## 🔧 Adding Different Credentials

You can add support for any API that uses HTTP-based authentication. Here's how:

### Quick Method: Use the Interactive Script

```bash
./scripts/add-credential.sh
```

The script will guide you through:
1. Choosing an authentication type
2. Configuring the service details
3. Setting up the matching rules
4. Adding environment variables

### Manual Method: Step-by-Step

#### Example: Adding Stripe

**1. Add strategy to `proxy/config.yaml`:**

```yaml
strategies:
  - name: stripe-live
    type: stripe  # Pre-configured Stripe support
    config:
      token: STRIPE_SECRET_KEY  # Environment variable name
```

**2. Add rule to `proxy/config.yaml`:**

```yaml
rules:
  - name: stripe-injection
    domain_regex: "^(api\\.)?stripe\\.com$"
    trigger_header_regex: "sk_(test|live)_00000000"
    strategy: stripe-live
    priority: 100
```

**3. Add credential to `.env`:**

```bash
# Get from: https://stripe.com/docs/keys
STRIPE_SECRET_KEY=sk_live_YourRealStripeSecretKey
```

**4. Restart the proxy:**

```bash
docker-compose restart proxy
```

**5. Use in your application:**

```python
import stripe

# Use dummy key
stripe.api_key = "sk_live_00000000"

# Real key injected automatically
customers = stripe.Customer.list(limit=3)
```

#### Example: Adding a Custom API

For APIs not pre-configured, use the generic `bearer` type:

**1. Add strategy:**

```yaml
strategies:
  - name: my-custom-api
    type: bearer
    config:
      token: CUSTOM_API_TOKEN
      dummy_pattern: "DUMMY_CUSTOM_TOKEN"
      allowed_hosts:
        - "api.mycustomapi.com"
        - "*.mycustomapi.com"
```

**2. Add rule:**

```yaml
rules:
  - name: custom-api-injection
    domain_regex: "^(.*\\.)?mycustomapi\\.com$"
    trigger_header_regex: "DUMMY_CUSTOM_TOKEN"
    strategy: my-custom-api
    priority: 100
```

**3. Add credential to `.env`:**

```bash
CUSTOM_API_TOKEN=your-real-custom-api-token
```

**4. Restart and use:**

```bash
docker-compose restart proxy

# Use dummy token in your app
curl https://api.mycustomapi.com/data \
  -H "Authorization: Bearer DUMMY_CUSTOM_TOKEN"
```

#### More Examples: Common APIs

**Slack:**

```yaml
strategies:
  - name: slack
    type: bearer
    config:
      token: SLACK_BOT_TOKEN
      dummy_pattern: "xoxb-DUMMY"
      allowed_hosts:
        - "slack.com"
        - "*.slack.com"

rules:
  - name: slack-injection
    domain_regex: "^(.*\\.)?slack\\.com$"
    trigger_header_regex: "xoxb-DUMMY"
    strategy: slack
    priority: 100
```

```bash
# .env
SLACK_BOT_TOKEN=xoxb-your-real-slack-bot-token
```

**Twilio:**

```yaml
strategies:
  - name: twilio
    type: bearer
    config:
      token: TWILIO_AUTH_TOKEN
      dummy_pattern: "DUMMY_TWILIO"
      allowed_hosts:
        - "api.twilio.com"
        - "*.twilio.com"

rules:
  - name: twilio-injection
    domain_regex: "^(.*\\.)?twilio\\.com$"
    trigger_header_regex: "DUMMY_TWILIO"
    strategy: twilio
    priority: 100
```

```bash
# .env
TWILIO_AUTH_TOKEN=your-real-twilio-auth-token
```

**Google Gemini:**

```yaml
strategies:
  - name: gemini
    type: gemini  # Specialized strategy for Google Gemini
    config:
      api_key: GEMINI_API_KEY

rules:
  - name: gemini-injection
    domain_regex: "^(.*\\.)?googleapis\\.com$"
    trigger_header_regex: "(AIza[a-zA-Z0-9_-]{35}DUMMY|DUMMY_GEMINI_KEY)"
    strategy: gemini
    priority: 100
```

```bash
# .env
GEMINI_API_KEY=AIzaSyYourRealGeminiAPIKey
```

```python
# Usage example
import google.generativeai as genai

# Configure with dummy key
genai.configure(api_key="DUMMY_GEMINI_KEY")

# Or use header directly
import requests
response = requests.get(
    "https://generativelanguage.googleapis.com/v1/models",
    headers={"x-goog-api-key": "DUMMY_GEMINI_KEY"}
)
```

For more detailed examples and authentication methods, see [docs/ADDING_CREDENTIALS.md](docs/ADDING_CREDENTIALS.md).

---

## 📚 Supported Authentication Protocols

### AWS Signature Version 4 (SigV4)

Full implementation for all AWS services:

```yaml
- name: aws-prod
  type: aws_sigv4
  config:
    access_key_id: AWS_ACCESS_KEY_ID
    secret_access_key: AWS_SECRET_ACCESS_KEY
    session_token: AWS_SESSION_TOKEN  # Optional, for STS
    region: us-east-1
    allowed_hosts:
      - "*.amazonaws.com"
```

**Supports:**
- S3, EC2, Lambda, DynamoDB, etc.
- All AWS regions
- Temporary credentials (STS)
- UNSIGNED-PAYLOAD for large uploads
- Pre-signed URLs

### Bearer Token

For APIs using `Authorization: Bearer <token>`:

```yaml
- name: openai
  type: openai  # Pre-configured for OpenAI
  config:
    token: OPENAI_API_KEY

- name: github
  type: github  # Pre-configured for GitHub
  config:
    token: GITHUB_TOKEN

- name: stripe
  type: stripe  # Pre-configured for Stripe
  config:
    token: STRIPE_SECRET_KEY

- name: custom-api
  type: bearer  # Generic Bearer token
  config:
    token: CUSTOM_API_TOKEN
    dummy_pattern: "DUMMY_CUSTOM_.*"
    allowed_hosts:
      - "api.example.com"
```

### HMAC (Coming Soon)

For crypto exchanges and HMAC-signed APIs:

```yaml
- name: binance
  type: hmac
  config:
    api_key: BINANCE_API_KEY
    secret_key: BINANCE_SECRET_KEY
```

---

## ⚙️ Configuration Guide

### Strategy Types

| Type | Description | Use Case |
|------|-------------|----------|
| `aws_sigv4` | AWS Signature Version 4 | All AWS services |
| `bearer` | Generic Bearer token | Most REST APIs |
| `stripe` | Stripe-specific Bearer | Stripe API |
| `github` | GitHub-specific Bearer | GitHub API |
| `openai` | OpenAI-specific Bearer | OpenAI API |
| `gemini` | Google Gemini API key | Google Gemini AI |
| `hmac` | HMAC-SHA256 signing | Crypto exchanges (future) |

### Rule Matching

Rules are evaluated in **priority order** (highest first):

```yaml
rules:
  - name: aws-dev
    domain_regex: ".*\\.amazonaws\\.com$"
    trigger_header_regex: "AKIA00000000DEVKEY"
    strategy: aws-dev
    priority: 110  # Higher priority

  - name: aws-prod
    domain_regex: ".*\\.amazonaws\\.com$"
    trigger_header_regex: "AKIA[0-9A-Z]{16}DUMMY"
    strategy: aws-prod
    priority: 100  # Lower priority
```

### Global Settings

```yaml
settings:
  log_level: INFO  # DEBUG, INFO, WARNING, ERROR
  log_format: json  # json or text
  fail_mode: closed  # closed (block on error) or open (pass through)
  max_body_size_mb: 100
  block_telemetry: true
  telemetry_domains:
    - "telemetry.anthropic.com"
    - "*.sentry.io"
```

---

## 🔧 Advanced Usage

### Multiple Credential Sets

Support dev/staging/prod environments:

```yaml
strategies:
  - name: aws-dev
    type: aws_sigv4
    config:
      access_key_id: AWS_DEV_ACCESS_KEY_ID
      secret_access_key: AWS_DEV_SECRET_ACCESS_KEY
      region: us-west-2

  - name: aws-prod
    type: aws_sigv4
    config:
      access_key_id: AWS_PROD_ACCESS_KEY_ID
      secret_access_key: AWS_PROD_SECRET_ACCESS_KEY
      region: us-east-1

rules:
  - name: dev-injection
    domain_regex: ".*\\.amazonaws\\.com$"
    trigger_header_regex: "AKIA00000000DEVKEY"
    strategy: aws-dev

  - name: prod-injection
    domain_regex: ".*\\.amazonaws\\.com$"
    trigger_header_regex: "AKIA00000000PRODKEY"
    strategy: aws-prod
```

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: Pod
meta
  name: app-with-injector
spec:
  initContainers:
  - name: setup-iptables
    image: universal-injector-proxy
    securityContext:
      capabilities:
        add: ["NET_ADMIN"]
    command: ["/setup-iptables.sh"]
  
  containers:
  - name: proxy
    image: universal-injector-proxy
    ports:
    - containerPort: 8080
  
  - name: app
    image: your-application
    # Shares network namespace with proxy
```

### CI/CD Integration

```yaml
# GitHub Actions example
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      proxy:
        image: universal-injector-proxy
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_KEY }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET }}
    steps:
      - run: |
          export HTTP_PROXY=http://proxy:8080
          # Run tests with real API access
          pytest tests/integration/
```

---

## 🧪 Testing

### Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Security tests
pytest tests/security/ -v

# Integration tests (requires credentials)
pytest tests/integration/ -v
```

### Test AWS SigV4

```python
# tests/integration/test_aws.py
def test_s3_list_buckets():
    s3 = boto3.client('s3',
        aws_access_key_id='AKIA00000000DUMMYKEY',
        aws_secret_access_key='DUMMY'
    )
    response = s3.list_buckets()
    assert 'Buckets' in response
```

---

## 📊 Monitoring & Debugging

### View Logs

```bash
# Proxy logs
docker logs universal_injector_proxy

# Filter for injections
docker logs universal_injector_proxy | grep "injected credentials"

# Filter for blocks
docker logs universal_injector_proxy | grep "SECURITY"
```

### Statistics

On shutdown, the proxy displays session statistics:

```
======================================================================
Universal API Credential Injector v2.0 - Session Statistics
======================================================================
Configuration Mode: v2
Strategies Loaded: 5
Rules Loaded: 8
----------------------------------------------------------------------
Total Requests Processed: 1,247
Credentials Injected: 856
Requests Blocked (Security): 3
Telemetry Blocked: 12
Strategy Errors: 0
======================================================================
```

---

## ️ Troubleshooting

### Certificate Issues

```bash
# Regenerate certificates
docker-compose down
docker volume rm safe-claude_certs
docker-compose up -d
```

### AWS Signature Errors

```bash
# Check dummy credential format
# Must match: AKIA[0-9A-Z]{16}DUMMY

# Enable debug logging
docker-compose down
docker-compose up  # Without -d to see logs

# Check region detection
docker logs universal_injector_proxy | grep "Detected AWS"
```

### Proxy Not Intercepting

```bash
# Verify transparent mode
docker exec universal_injector_proxy iptables -t nat -L

# Check network mode
docker inspect universal_injector_agent | grep NetworkMode

# Test explicit proxy
export HTTP_PROXY=http://localhost:8080
curl -v https://api.github.com
```

---

## 📖 Documentation

- [Architecture Design](./docs/Universal%20Injector%20Architecture.md)
- [Detailed Specification](./docs/Universal%20Injector%20Specification.md)
- [Implementation Plan](./docs/Universal%20Injector%20Implementation%20Plan.md)
- [Risks & Mitigations](./docs/Universal%20Injector%20Risks%20and%20Mitigations.md)

### v1 Documentation (Archived)

- [v1 SafeClaude Docs](./docs/archive/v1-safeclaude/)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new strategies
4. Submit a pull request

### Adding New Strategies

```python
# proxy/strategies/my_protocol.py
from .base import InjectionStrategy

class MyProtocolStrategy(InjectionStrategy):
    def detect(self, flow):
        # Detection logic
        return "DUMMY" in flow.request.headers.get("X-My-Auth", "")
    
    def inject(self, flow):
        # Injection logic
        real_token = self.get_credential("token")
        flow.request.headers["X-My-Auth"] = real_token
        self.log_injection(flow)
```

Register in `proxy/strategies/__init__.py` and `proxy/inject.py`.

---

## 📜 License

This project is proprietary IBM software. See LICENSE file for details.

---

## 🙏 Acknowledgments

- **Anthropic** - Claude API
- **mitmproxy** - HTTP interception framework  
- **AWS** - boto3 and botocore libraries
- **Docker** - Container platform

---

## ⚠️ Production Recommendations

While Universal Injector v2 implements strong security controls, consider these enhancements for production:

- ✅ Use HSM/KMS for credential storage
- ✅ Implement mTLS between proxy and application
- ✅ Add rate limiting to prevent DoS
- ✅ Enable comprehensive audit logging
- ✅ Use short-lived credentials (STS, OAuth)
- ✅ Deploy in a dedicated security zone
- ✅ Regular security audits and penetration testing

---

## 📞 Support

- **GitHub Issues**: [Report bugs or request features](https://github.ibm.com/Andrew-Gibson-CIC/safe-claude/issues)
- **Documentation**: See `/docs` directory
- **Security**: Report security issues privately to maintainers

---

**Built with ❤️ for secure enterprise API access**

*Universal Injector v2.0 - Zero-Knowledge Credential Management*
