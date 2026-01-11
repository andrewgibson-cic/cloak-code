# Universal API Credential Injector v2.0

**A transparent, zero-knowledge credential management proxy for secure API access.**

Transform any application into a credential-safe environment where real API keys never touch your code. Supports AWS, Stripe, GitHub, OpenAI, and any HTTP-based API.

---

## 🚀 What's New in v2.0

### Major Architecture Overhaul

- ✅ **AWS SigV4 Support** - Full AWS Signature Version 4 implementation for S3, EC2, Lambda, and all AWS services
- ✅ **Strategy Pattern** - Pluggable authentication protocols (Bearer, AWS SigV4, HMAC)
- ✅ **Transparent Mode** - Automatic traffic interception with iptables (no proxy environment variables needed)
- ✅ **Rule-Based Routing** - Priority-based request matching with flexible configuration
- ✅ **Backward Compatible** - Automatically detects and converts v1 configurations

### From SafeClaude to Universal Injector

This project has evolved from an AI agent-specific tool to a **universal enterprise credential management solution**. While it still works perfectly for AI development, it now supports any application that makes HTTP API calls.

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

- **Docker Engine** 24.0+ with Docker Compose v2+
- **8GB RAM** minimum
- **Linux/macOS/Windows** (with WSL2)
- API credentials for services you want to use

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone <repo-url>
cd safe-claude

# Copy configuration template
cp proxy/config.yaml.example proxy/config.yaml
```

### 2. Configure Credentials

Edit `proxy/config.yaml`:

```yaml
strategies:
  # AWS Strategy
  - name: aws-prod
    type: aws_sigv4
    config:
      access_key_id: AWS_ACCESS_KEY_ID     # Environment variable name
      secret_access_key: AWS_SECRET_ACCESS_KEY
      region: us-east-1

  # Stripe Strategy
  - name: stripe
    type: stripe
    config:
      token: STRIPE_SECRET_KEY

rules:
  - name: aws-injection
    domain_regex: ".*\\.amazonaws\\.com$"
    trigger_header_regex: "AKIA00000000DUMMYKEY"
    strategy: aws-prod
    priority: 100
```

Create `.env` file with real credentials:

```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
STRIPE_SECRET_KEY=sk_live_...
```

### 3. Start the System

```bash
docker-compose up -d
```

### 4. Use Your Application

**With Transparent Mode (Recommended):**

Your application automatically uses the proxy - no configuration needed!

```python
# Python example - just use dummy credentials
import boto3

# This will be automatically signed with real credentials
s3 = boto3.client('s3',
    aws_access_key_id='AKIA00000000DUMMYKEY',
    aws_secret_access_key='DUMMY_SECRET'
)

# Works! Real credentials injected transparently
buckets = s3.list_buckets()
```

**With Explicit Proxy Mode:**

```bash
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Now all HTTP traffic goes through proxy
curl https://api.github.com/user -H "Authorization: Bearer DUMMY_GITHUB_TOKEN"
```

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

## 🔄 Migration from v1

### Automatic Conversion

v2 automatically detects and converts v1 `credentials.yml`:

```yaml
# v1 format (still supported)
credentials:
  openai:
    display_name: "OpenAI API"
    dummy_token: "DUMMY_OPENAI_KEY"
    env_var: "REAL_OPENAI_API_KEY"
    allowed_hosts:
      - "api.openai.com"
```

Converts to v2 Bearer strategy automatically!

### Manual Migration

For full v2 features, migrate to `config.yaml`:

```bash
# 1. Copy your old credentials.yml
cp credentials.yml credentials.yml.backup

# 2. Create new config.yaml
cp proxy/config.yaml.example proxy/config.yaml

# 3. Migrate each credential to a strategy
# 4. Define rules for matching
# 5. Test thoroughly
```

---

## 🛠️ Troubleshooting

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
