# CloakCode Makefile
# Simple, universal commands for managing CloakCode

.PHONY: help start stop restart status logs clean shell test build install

# Default target - show help
help:
	@echo "╔══════════════════════════════════════════════════════════╗"
	@echo "║         CloakCode Control Commands                       ║"
	@echo "╚══════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 Setup & Control:"
	@echo "  make install        - Install dependencies (first time)"
	@echo "  make start          - Start all services"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make status         - Show service status"
	@echo ""
	@echo "🔍 Access Containers:"
	@echo "  make shell          - Open shell in agent container"
	@echo "  make shell-agent    - Open bash shell in agent"
	@echo "  make shell-proxy    - Open shell in proxy"
	@echo ""
	@echo "📋 Logs & Debugging:"
	@echo "  make logs           - Follow all logs"
	@echo "  make logs-proxy     - Follow proxy logs only"
	@echo "  make logs-agent     - Follow agent logs only"
	@echo "  make logs-file      - View persistent file logs"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-security  - Run security tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-startup   - Run startup verification tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make test-html      - Generate HTML coverage report"
	@echo "  make test-fast      - Run tests in parallel (quick)"
	@echo ""
	@echo "🔧 Code Quality:"
	@echo "  make lint           - Run linters (pylint, flake8)"
	@echo "  make format         - Format code with black"
	@echo "  make format-check   - Check code formatting"
	@echo "  make type-check     - Run mypy type checking"
	@echo "  make security-scan  - Run security scanners"
	@echo ""
	@echo "🛠️  Maintenance:"
	@echo "  make build          - Rebuild all containers"
	@echo "  make clean          - Remove generated files"
	@echo "  make clean-all      - Remove everything (containers + volumes)"
	@echo "  make update         - Update dependencies"
	@echo ""
	@echo "📖 Documentation:"
	@echo "  README.md           - Main documentation"
	@echo "  QUICK_START.md      - Quick start guide"
	@echo "  docs/TESTING.md     - Testing guide"
	@echo ""
	@echo "💡 Common Workflows:"
	@echo "  First time:    make install && make start"
	@echo "  Run tests:     make test"
	@echo "  Quick restart: make restart"
	@echo "  View coverage: make test-html"
	@echo ""

# ============================================================================
# Setup & Installation
# ============================================================================

install:
	@echo "📦 Installing development dependencies..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Installing packages..."
	@. venv/bin/activate && pip install --upgrade pip && pip install -r requirements-dev.txt
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Configure credentials: cp .env.template .env"
	@echo "  2. Edit .env with your credentials"
	@echo "  3. Start services: make start"

install-prod:
	@echo "📦 Installing production dependencies only..."
	@cd proxy && pip install -r requirements.txt
	@echo "✅ Production dependencies installed"

# ============================================================================
# Docker Control
# ============================================================================

start:
	@echo "🚀 Starting CloakCode services..."
	@if [ -f "./cloakcode" ]; then \
		./cloakcode start; \
	else \
		docker-compose up -d; \
		echo "✅ Services started"; \
		echo "View logs: make logs"; \
	fi

stop:
	@echo "🛑 Stopping CloakCode services..."
	@if [ -f "./cloakcode" ]; then \
		./cloakcode stop; \
	else \
		docker-compose down; \
		echo "✅ Services stopped"; \
	fi

restart:
	@echo "🔄 Restarting CloakCode services..."
	@if [ -f "./cloakcode" ]; then \
		./cloakcode restart; \
	else \
		docker-compose restart; \
		echo "✅ Services restarted"; \
	fi

status:
	@echo "📊 Service Status:"
	@if [ -f "./cloakcode" ]; then \
		./cloakcode status; \
	else \
		docker-compose ps; \
	fi

build:
	@echo "🔨 Rebuilding containers..."
	@docker-compose build --no-cache
	@echo "✅ Build complete"

# ============================================================================
# Container Access
# ============================================================================

shell: shell-agent

shell-agent:
	@echo "🐚 Opening shell in agent container..."
	@docker-compose exec agent /bin/bash

shell-proxy:
	@echo "🐚 Opening shell in proxy container..."
	@docker-compose exec proxy /bin/bash

# ============================================================================
# Logs
# ============================================================================

logs:
	@echo "📋 Following all logs (Ctrl+C to exit)..."
	@docker-compose logs -f

logs-proxy:
	@echo "📋 Following proxy logs (Ctrl+C to exit)..."
	@docker-compose logs -f proxy

logs-agent:
	@echo "📋 Following agent logs (Ctrl+C to exit)..."
	@docker-compose logs -f agent

logs-file:
	@echo "📋 Viewing persistent file logs..."
	@echo ""
	@echo "=== Recent Agent Activity ==="
	@tail -n 20 logs/agent_activity.log 2>/dev/null || echo "No agent activity log found"
	@echo ""
	@echo "=== Recent Proxy Injections ==="
	@tail -n 20 logs/proxy_injections.log 2>/dev/null || echo "No proxy injection log found"
	@echo ""
	@echo "=== Recent Security Events ==="
	@tail -n 10 logs/security_events.log 2>/dev/null || echo "No security events"

# ============================================================================
# Testing
# ============================================================================

test:
	@echo "🧪 Running all tests..."
	@. venv/bin/activate && pytest tests/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	@. venv/bin/activate && pytest tests/unit/ -v -m unit

test-security:
	@echo "🔒 Running security tests..."
	@. venv/bin/activate && pytest tests/security/ -v -m security

test-integration:
	@echo "🔗 Running integration tests..."
	@. venv/bin/activate && pytest tests/integration/ -v -m integration

test-startup:
	@echo "🚀 Running startup verification tests..."
	@bash tests/startup/run_startup_tests.sh

test-fast:
	@echo "⚡ Running tests in parallel..."
	@. venv/bin/activate && pytest tests/ -n auto -v

test-coverage:
	@echo "📊 Running tests with coverage..."
	@. venv/bin/activate && pytest tests/ --cov=proxy --cov-report=term-missing

test-html:
	@echo "📊 Generating HTML coverage report..."
	@. venv/bin/activate && pytest tests/ --cov=proxy --cov-report=html
	@echo "✅ Coverage report generated!"
	@echo "   Open: htmlcov/index.html"

test-watch:
	@echo "👀 Running tests in watch mode..."
	@. venv/bin/activate && pytest-watch tests/ -v

# ============================================================================
# Code Quality
# ============================================================================

lint:
	@echo "🔍 Running linters..."
	@echo ""
	@echo "=== Pylint ==="
	@. venv/bin/activate && pylint proxy/ --rcfile=.pylintrc 2>/dev/null || true
	@echo ""
	@echo "=== Flake8 ==="
	@. venv/bin/activate && flake8 proxy/ tests/ --max-line-length=100 2>/dev/null || true
	@echo ""
	@echo "✅ Linting complete"

format:
	@echo "✨ Formatting code..."
	@. venv/bin/activate && black proxy/ tests/ --line-length=100
	@. venv/bin/activate && isort proxy/ tests/
	@echo "✅ Code formatted"

format-check:
	@echo "🔍 Checking code format..."
	@. venv/bin/activate && black proxy/ tests/ --check --line-length=100
	@. venv/bin/activate && isort proxy/ tests/ --check-only

type-check:
	@echo "🔍 Running type checks..."
	@. venv/bin/activate && mypy proxy/ --ignore-missing-imports
	@echo "✅ Type checking complete"

security-scan:
	@echo "🔒 Running security scanners..."
	@echo ""
	@echo "=== Bandit (Security Issues) ==="
	@. venv/bin/activate && bandit -r proxy/ -ll 2>/dev/null || true
	@echo ""
	@echo "=== Safety (Dependencies) ==="
	@. venv/bin/activate && safety check 2>/dev/null || true
	@echo ""
	@echo "✅ Security scan complete"

# ============================================================================
# Maintenance
# ============================================================================

clean:
	@echo "🧹 Cleaning generated files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .pytest_cache/ .coverage coverage.xml 2>/dev/null || true
	@echo "✅ Cleanup complete"

clean-all: clean
	@echo "🧹 Deep cleaning (containers + volumes)..."
	@docker-compose down -v 2>/dev/null || true
	@rm -rf venv/ .mypy_cache/ .tox/ dist/ build/ 2>/dev/null || true
	@echo "✅ Deep cleanup complete"

update:
	@echo "📦 Updating dependencies..."
	@. venv/bin/activate && pip install --upgrade pip
	@. venv/bin/activate && pip install --upgrade -r requirements-dev.txt
	@echo "✅ Dependencies updated"

# ============================================================================
# Quick Commands
# ============================================================================

quick-test:
	@. venv/bin/activate && pytest tests/ -x -q

quick-status:
	@echo "Tests: $$(. venv/bin/activate && pytest tests/ -q --co | wc -l) total"
	@echo "Containers: $$(docker-compose ps -q | wc -l) running"

# ============================================================================