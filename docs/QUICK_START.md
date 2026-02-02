# CloakCode Quick Start

**Get up and running in 5 minutes**

---

## Prerequisites

- Docker & Docker Compose
- Python 3.9+
- Basic understanding of API credentials

---

## 1. Install

```bash
# Clone and install
git clone <repository-url>
cd cloak-code
make install
```

---

## 2. Configure

```bash
# Copy templates
cp .env.template .env
cp proxy/config.yaml.example proxy/config.yaml

# Edit .env with your real credentials
nano .env
```

**Example `.env`:**
```bash
# AWS
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# OpenAI
OPENAI_API_KEY=sk-proj-YourRealKeyHere

# GitHub
GITHUB_TOKEN=ghp_YourRealTokenHere
```

---

## 3. Start

```bash
make start
```

That's it! Services are running.

---

## 4. Test

```bash
# Run tests
make test

# View coverage
make test-html
```

---

## Usage

### In Your Code

```python
import boto3

# Use DUMMY credentials - they're automatically replaced!
s3 = boto3.client(
    's3',
    aws_access_key_id='AKIA00000000DUMMYKEY',
    aws_secret_access_key='DUMMY_SECRET'
)

# This works! Real credentials injected transparently
buckets = s3.list_buckets()
```

### Access Container

```bash
make shell
# Now in agent container with secure credential injection
```

---

## Common Commands

```bash
make start          # Start services
make stop           # Stop services
make restart        # Restart
make logs           # View logs
make test           # Run tests
make shell          # Open shell
```

---

## What's Happening?

1. Your code uses **DUMMY** credentials
2. Proxy detects dummy credentials
3. Proxy injects **real** credentials
4. API call succeeds
5. Your code never sees real credentials ✨

---

## Security

- ✅ Zero-knowledge: Agent never sees real credentials
- ✅ Host whitelist: Credentials only sent to approved APIs
- ✅ Audit logging: All injections logged
- ✅ Fail-closed: Errors block requests

---

## Next Steps

- **Full Guide:** [README.md](../README.md)
- **Testing:** [TESTING.md](TESTING.md)
- **Add APIs:** Edit `proxy/config.yaml`

---

**Need Help?**
- Check logs: `make logs`
- Run tests: `make test`
- View status: `make status`