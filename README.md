# SafeClaude - Zero-Knowledge Agent Environment

A secure, containerized development environment for AI agents implementing a "zero-knowledge" credential management model where the agent never has access to real API keys.

## ✨ NEW: Universal Credential Support

**SafeClaude now supports ANY API credential!** 🎉

Add credentials for **Binance, eBay, Shopify, Stripe, Slack, Discord, or literally any API** without touching code:

- ✅ **No code changes** - Just edit `credentials.yml`
- ✅ **No rebuilds** - Changes take effect on restart
- ✅ **Interactive wizard** - Run `./scripts/add-credential.sh`
- ✅ **View status** - Run `./scripts/list-credentials.sh`

**Example:** Add Binance API in 3 steps:
```bash
# 1. Add to credentials.yml
binance:
  display_name: "Binance API"
  dummy_token: "DUMMY_BINANCE_KEY"
  env_var: "REAL_BINANCE_API_KEY"
  header_locations:
    - name: "X-MBX-APIKEY"
      format: "{token}"
  allowed_hosts:
    - "api.binance.com"
    
# 2. Add to .env
REAL_BINANCE_API_KEY=your-actual-key

# 3. Restart
docker-compose restart proxy
```

📖 **[Full Guide: Adding New Credentials →](./docs/ADDING_CREDENTIALS.md)**

## 🔒 Security Architecture

SafeClaude uses a **sidecar proxy pattern** to inject credentials on-the-fly:

- **Agent Container**: The "untrusted" workspace where the AI operates with dummy tokens
- **Proxy Container**: The "trusted" keyring that holds real credentials and injects them during HTTP requests
- **Zero-Knowledge Principle**: Agent never sees, stores, or can access real credentials

### Key Security Features

✅ **Credential Isolation** - Real API keys exist only in the proxy container  
✅ **Host Whitelisting** - Credentials only work for approved destinations  
✅ **Telemetry Blocking** - Known tracking endpoints automatically blocked  
✅ **Ephemeral Recovery** - Container can be instantly reset if compromised  
✅ **Audit Logging** - All credential injections logged (without revealing secrets)

## 📋 Prerequisites

- **Docker Engine** 24.0+ with Docker Compose v2.0+
- **Minimum 8GB RAM** recommended
- **Internet connection** for initial setup

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone git@github.ibm.com:Andrew-Gibson-CIC/safe-claude.git
cd safe-claude
```

### 2. Configure Credentials

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your real API keys
vim .env  # or your preferred editor
```

**Example `.env` file:**
```bash
REAL_OPENAI_API_KEY=sk-proj-abc123...
REAL_GITHUB_TOKEN=ghp_xyz789...
REAL_ANTHROPIC_API_KEY=sk-ant-def456...
```

⚠️ **CRITICAL**: The `.env` file is gitignored. Never commit it to version control!

### 3. Create Workspace Directory

```bash
mkdir -p workspace
cd workspace
# Place your project code here
```

### 4. Start the Environment

```bash
docker-compose up -d
```

This will:
- Build the proxy and agent containers
- Generate SSL certificates
- Start the secure environment

### 5. Enter the Agent Container

```bash
docker exec -it safeclaude_agent bash
```

You're now inside the secure sandbox! Navigate to your workspace:

```bash
cd workspace
```

### 6. First-Time Authentication (One-Time Setup)

Authenticate with Anthropic Claude:

```bash
claude login
```

This will display a URL. Copy and paste it into your browser to complete OAuth authentication. The refresh token is saved persistently, so you only need to do this once.

## 📚 Usage

### Running Claude Commands

Inside the agent container:

```bash
# Interactive mode
claude

# One-shot command
claude "Analyze the src/ directory and create a README"

# Help
claude --help
```

### Common Operations

```bash
# Check status
docker-compose ps

# View logs
docker logs safeclaude_proxy
docker logs safeclaude_agent

# Restart agent (clean slate recovery)
docker restart safeclaude_agent

# Stop everything
docker-compose down

# Rebuild containers
docker-compose build --no-cache
```

## 🧪 Testing

### Run Unit Tests

```bash
# Python unit tests for proxy logic
python3 -m pytest tests/unit/ -v

# Security penetration tests
python3 -m pytest tests/security/ -v
```

### Test Coverage

```bash
python3 -m pytest --cov=proxy --cov-report=html tests/
```

## 🔐 Security

### Threat Model

SafeClaude is designed to protect against:

- **R-01**: Context Pollution (credentials in LLM history)
- **R-02**: Filesystem Destruction (agent breaks its own environment)
- **R-03**: Host Contamination (agent affects host system)
- **R-04**: Credential Exfiltration (prompt injection attacks)
- **R-05**: Shadow Dependencies (typosquatting, malware)
- **R-06**: Telemetry Leakage (usage data sent to third parties)

See [SECURITY_REVIEW.md](./SECURITY_REVIEW.md) for the complete security analysis.

### Security Best Practices

1. **Never mount your entire home directory** - Only mount specific project folders
2. **Use version control** - Commit frequently; treat agent changes as untrusted
3. **Review agent modifications** - Don't blindly accept all changes
4. **Keep .env secure** - Never commit, share, or expose this file
5. **Update regularly** - Pull latest images for security patches

## 📖 Documentation

- [Architecture Design](./SafeClaude%20Architecture%20Design.md) - System architecture and design philosophy
- [Detailed Specification](./SafeClaude%20Detailed%20Specification.md) - Complete technical requirements
- [Implementation Plan](./SafeClaude%20Phased%20Implementation%20Plan%20%26%20Roadmap.md) - Step-by-step build guide
- [Risk Assessment](./SafeClaude%20Risks%20and%20Mitigations.md) - Threat model and mitigations
- [Security Review](./SECURITY_REVIEW.md) - Comprehensive security analysis

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  Host Machine                    │
│                                                  │
│  ┌────────────────┐      ┌──────────────────┐  │
│  │  Proxy (8080)  │◄─────│  Agent Container │  │
│  │                │      │                   │  │
│  │  • mitmproxy   │      │  • Claude CLI     │  │
│  │  • inject.py   │      │  • Node.js 20     │  │
│  │  • Real Keys   │      │  • Dummy Tokens   │  │
│  │  • Whitelist   │      │  • Workspace      │  │
│  └────────┬───────┘      └──────────┬────────┘  │
│           │                         │           │
│           │   Certificate Trust     │           │
│           └─────────────────────────┘           │
│                                                  │
│           │                                      │
│           ▼                                      │
│    External APIs                                 │
│    (OpenAI, GitHub, etc.)                        │
└─────────────────────────────────────────────────┘
```

### How It Works

1. **Agent** makes HTTP request with `DUMMY_OPENAI_KEY`
2. **Proxy** intercepts the request
3. **Whitelist Check**: Proxy validates destination is `api.openai.com`
4. **Injection**: Proxy replaces dummy with `REAL_OPENAI_API_KEY`
5. **Forward**: Request sent to external API with real credential
6. **Response**: API response returned to agent

## 🛠️ Troubleshooting

### Agent Won't Start

```bash
# Check proxy is healthy
docker-compose ps

# View agent logs
docker logs safeclaude_agent

# Certificate issue? Rebuild
docker-compose down
docker volume rm safeclaude_certs
docker-compose up -d
```

### Network Issues

```bash
# Verify proxy is reachable
docker exec safeclaude_agent curl -v http://proxy:8080

# Check proxy logs for blocks
docker logs safeclaude_proxy | grep SECURITY
```

### Permission Errors

```bash
# Fix workspace permissions
sudo chown -R 1000:1000 workspace/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest tests/`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linters
bandit -r proxy/
pylint proxy/inject.py

# Run full test suite
pytest tests/ -v --cov=proxy
```

## 📜 License

This project is proprietary IBM software. See LICENSE file for details.

## 🙏 Acknowledgments

- **Anthropic** - Claude API and CLI
- **mitmproxy** - HTTP interception framework
- **Docker** - Container platform

## ⚠️ Disclaimer

This tool is designed for development and testing environments. While it implements strong security controls, it should be thoroughly evaluated before use in production scenarios. See [SECURITY_REVIEW.md](./SECURITY_REVIEW.md) for detailed security analysis and recommendations.

## 📞 Support

For issues, questions, or contributions:
- **GitHub Issues**: [Report a bug](https://github.ibm.com/Andrew-Gibson-CIC/safe-claude/issues)
- **Documentation**: See `/docs` directory
- **Security**: Report security issues privately to the maintainers

---

**Built with ❤️ for secure AI development**
