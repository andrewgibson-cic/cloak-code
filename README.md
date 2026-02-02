# CloakCode - Universal API Credential Injector

**Secure, transparent credential injection for AI coding assistants and development tools.**

CloakCode is a zero-knowledge credential management system that allows AI assistants (like Claude, Cursor, Aider) to make authenticated API calls without ever seeing your real credentials. It works by intercepting requests with dummy credentials and transparently replacing them with real ones via a proxy.

## 🎯 Key Features

- **🔐 Zero-Knowledge Security** - AI never sees your real API keys
- **🌐 Universal Support** - Works with ANY API (OpenAI, Anthropic, AWS, GitHub, Stripe, etc.)
- **🔌 Transparent Proxy** - No code changes required
- **📦 Docker Isolated** - Runs in isolated containers for maximum security
- **🎨 Strategy-Based** - Pluggable authentication protocols (Bearer, AWS SigV4, OAuth, etc.)
- **🚫 Telemetry Blocking** - Automatically blocks tracking and analytics
- **📊 Audit Logging** - Complete audit trail of all credential usage
- **🛡️ Host Whitelisting** - Credentials only work for authorized domains

## 🚀 Quick Start

### Prerequisites

- Docker and docker-compose
- Python 3.12 or 3.13 (3.14 not supported yet)
- macOS, Linux, or WSL2

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/andrewgibson-cic/cloak-code.git
cd cloak-code

# 2. Install Python dependencies
make install

# 3. Verify installation
make verify

# 4. Start CloakCode
make start

# 5. Check status
make status
```

### Configuration

1. **Configure credentials** (already created):
   - `.env` - Your real API credentials (git-ignored)
   - `credentials.yml` - Credential mapping configuration
   - `proxy/config.yaml` - Proxy rules and strategies

2. **Add your API keys** to `.env`:
   ```bash
   # Edit .env and replace DUMMY values with real credentials
   OPENAI_API_KEY=sk-proj-your-real-key-here
   ANTHROPIC_API_KEY=sk-ant-your-real-key-here
   GITHUB_TOKEN=ghp_your-real-token-here
   ```

3. **Configure your AI assistant** with DUMMY credentials:
   ```bash
   # In Cline/Claude Code settings:
   API Key: DUMMY_ANTHROPIC_KEY
   
   # In Cursor settings:
   OpenAI Key: DUMMY_OPENAI_KEY
   ```

4. **Verify it works**:
   ```bash
   make logs-proxy  # Watch credential injection in action
   ```

## 📖 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Detailed setup guide
- **[COMMANDS.md](COMMANDS.md)** - Complete make commands reference
- **[docs/](docs/)** - Architecture and implementation details

## 🔧 Usage

### Common Commands

```bash
# Start/Stop
make start          # Start CloakCode containers
make stop           # Stop containers
make restart        # Restart containers
make status         # Show container status

# Logging
make logs           # Follow all logs
make logs-proxy     # Watch proxy credential injection
make logs-agent     # Watch agent container logs

# Development
make test           # Run all tests
make test-unit      # Run unit tests only
make format         # Format code with black

# Maintenance
make clean          # Clean Python artifacts
make docker-clean   # Remove all Docker resources
```

See [COMMANDS.md](COMMANDS.md) for complete command reference.

### How It Works

1. **AI Assistant** makes API call with dummy credential (e.g., `DUMMY_OPENAI_KEY`)
2. **Proxy** intercepts the request
3. **Strategy** detects dummy credential and validates target host
4. **Injection** replaces dummy with real credential from `.env`
5. **Request** proceeds to API with real credential
6. **Audit Log** records the injection (without logging real credential)

```
┌─────────────────┐
│  AI Assistant   │  Uses: DUMMY_OPENAI_KEY
│  (Cline/Cursor) │
└────────┬────────┘
         │ HTTP Request
         ▼
┌─────────────────┐
│  CloakCode      │  Intercepts request
│  Proxy          │  Validates host: api.openai.com ✓
└────────┬────────┘  Injects: sk-proj-real-key-***
         │
         ▼
┌─────────────────┐
│  OpenAI API     │  Receives real credential
│  api.openai.com │  Processes request
└─────────────────┘
```

## 🔐 Security Features

### Host Whitelisting
- Credentials only work for authorized domains
- Prevents credential theft via domain spoofing
- Cross-service protection (OpenAI key won't work for GitHub)

### Telemetry Blocking
- Automatically blocks tracking/analytics domains
- Prevents credential leakage via telemetry
- Configurable blocklist

### Fail-Closed Mode
- Blocks requests on error (security over convenience)
- Prevents accidental credential exposure
- Comprehensive error handling

### Audit Logging
- Complete audit trail in `logs/audit.json`
- Records all credential injections
- Never logs real credentials (only dummy tokens)

## 🎨 Supported Services

CloakCode supports ANY API! Pre-configured strategies for:

- **AI/ML**: OpenAI, Anthropic, Google Gemini, Mistral AI, IBM WatsonX
- **Version Control**: GitHub, GitLab, Bitbucket, Azure DevOps
- **Cloud**: AWS (SigV4), Google Cloud, Azure
- **Payments**: Stripe, PayPal
- **Communication**: Slack, Discord, Twilio, SendGrid
- **Custom**: Easy to add your own via `credentials.yml`

## 📊 Project Status

- ✅ Core credential injection working
- ✅ Multiple authentication strategies (Bearer, AWS SigV4, Git PAT)
- ✅ Docker containerization
- ✅ Comprehensive test suite
- ✅ Documentation complete
- ⚠️ Docker proxy container has permission issue (being debugged)
- 🚧 Production hardening in progress

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

[MIT License](LICENSE)

## 🆘 Troubleshooting

### Tests Failing?
```bash
# Make sure you're using the virtual environment
source venv/bin/activate
make test
```

### Containers Not Starting?
```bash
# Check logs for errors
make logs-proxy

# Verify configuration
make verify

# Try rebuilding
make docker-clean
make start
```

### Credentials Not Being Injected?
```bash
# Watch the proxy logs
make logs-proxy

# Verify your .env has real credentials
cat .env

# Check credentials.yml configuration
cat credentials.yml
```

### Need Help?
```bash
# Show all available commands
make help

# Verify installation
make verify

# Check container status
make status
```

## 🔗 Links

- **GitHub**: [andrewgibson-cic/cloak-code](https://github.com/andrewgibson-cic/cloak-code)
- **Issues**: [Report bugs or request features](https://github.com/andrewgibson-cic/cloak-code/issues)
- **Discussions**: [Ask questions](https://github.com/andrewgibson-cic/cloak-code/discussions)

---

**⚠️ Security Notice**: Never commit your `.env` file or share your real API credentials. CloakCode is designed to keep credentials secure, but always follow security best practices.

**💡 Pro Tip**: Use `make logs-proxy` to watch credential injection happen in real-time. It's educational and helps debug issues!