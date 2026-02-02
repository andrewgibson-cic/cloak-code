# CloakCode - Make Commands Reference

Quick reference guide for all available make commands.

## 📋 Quick Start

```bash
# 1. Install dependencies
make install

# 2. Verify installation
make verify

# 3. Start CloakCode
make start

# 4. Check status
make status

# 5. View logs
make logs
```

---

## 🔧 Installation Commands

| Command | Description |
|---------|-------------|
| `make install` | Install Python dependencies (checks Python version) |
| `make install-force` | Force install without version check |
| `make setup-venv` | Create virtual environment with Python 3.12 |
| `make verify` | Verify installation and configuration |

---

## 🐳 Docker Commands

| Command | Description |
|---------|-------------|
| `make start` | Start CloakCode containers (detached) |
| `make stop` | Stop CloakCode containers |
| `make restart` | Restart CloakCode containers |
| `make status` | Show container status |
| `make docker-build` | Build Docker images |
| `make docker-clean` | Remove all containers, images, and volumes |

---

## 📊 Logging Commands

| Command | Description |
|---------|-------------|
| `make logs` | Follow all container logs |
| `make logs-proxy` | Follow proxy container logs only |
| `make logs-agent` | Follow agent container logs only |
| `make docker-logs` | Same as `make logs` |

---

## 🔍 Container Access Commands

| Command | Description |
|---------|-------------|
| `make shell` | Open shell in agent container (default) |
| `make shell-agent` | Open shell in agent container (same as `shell`) |
| `make shell-proxy` | Open shell in proxy container |

---

## 🧪 Testing Commands

| Command | Description |
|---------|-------------|
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make test-security` | Run security tests only |

**Note**: Tests automatically use virtual environment if available.

---

## 🎨 Code Quality Commands

| Command | Description |
|---------|-------------|
| `make lint` | Run code linters (black, pylint) |
| `make format` | Format code with black |
| `make security-scan` | Run security scans (bandit, safety) |
| `make clean` | Clean up cache and build artifacts |

---

## 📖 Help Command

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands with descriptions |

---

## 💡 Common Workflows

### First Time Setup
```bash
make install          # Install dependencies
make verify          # Check everything is configured
make start           # Start containers
make status          # Verify containers are running
make logs            # Watch the logs
```

### Daily Development
```bash
make start           # Start if not running
make test-unit       # Run unit tests
make format          # Format your code
make restart         # Restart after changes
```

### Debugging Issues
```bash
make status          # Check container status
make logs-proxy      # Check proxy logs
make logs-agent      # Check agent logs
make shell-proxy     # Access proxy container
make shell-agent     # Access agent container
```

### Cleaning Up
```bash
make stop            # Stop containers
make clean           # Clean Python artifacts
make docker-clean    # Remove all Docker resources (⚠️ careful!)
```

---

## ⚠️ Important Notes

1. **Virtual Environment**: Most commands automatically use the virtual environment if it exists in `venv/`
2. **Docker Required**: Docker and docker-compose must be installed for container commands
3. **Python Version**: Python 3.12 or 3.13 required (3.14 not compatible with mitmproxy)
4. **Permissions**: Logs directory needs write permissions (`chmod 777 logs/`)

---

## 🆘 Getting Help

```bash
# Show all available commands
make help

# Verify your installation
make verify

# Check container status
make status
```

For more information, see:
- `README.md` - Main documentation
- `QUICK_START.md` - Quick start guide
- `docs/` - Detailed documentation