# CloakCode Makefile - Fixed and Enhanced

.PHONY: help install test clean docker-build docker-up docker-down docker-logs check-python start stop restart status logs

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

check-python: ## Check Python version compatibility
	@echo "Checking Python version compatibility..."
	@python3 --version | grep -q "Python 3.14" && \
		(echo "⚠️  WARNING: Python 3.14 detected. This version is not compatible with cffi/mitmproxy." && \
		 echo "   Please use Python 3.12 or 3.13 instead." && \
		 echo "   See docs/PYTHON_COMPATIBILITY.md for solutions." && \
		 exit 1) || \
		(echo "✅ Python version is compatible" && python3 --version)

install: check-python ## Install Python dependencies (requires Python 3.12 or 3.13)
	@echo "Installing CloakCode dependencies..."
	pip install --upgrade pip setuptools wheel
	pip install -r requirements-dev.txt
	@echo "✅ Installation complete!"
	@echo ""
	@echo "To verify installation:"
	@echo "  python -c 'import mitmproxy; print(mitmproxy.__version__)'"

install-force: ## Force install without Python version check (may fail on 3.14)
	@echo "⚠️  Forcing installation without version check..."
	pip install --upgrade pip setuptools wheel
	pip install -r requirements-dev.txt

test: ## Run all tests (automatically uses venv if available)
	@if [ -d "venv/bin" ]; then \
		echo "Running tests in virtual environment..."; \
		./venv/bin/pytest tests/ -v --cov=proxy --cov-report=term-missing; \
	else \
		echo "Running tests with system Python..."; \
		pytest tests/ -v --cov=proxy --cov-report=term-missing; \
	fi

test-unit: ## Run unit tests only
	@if [ -d "venv/bin" ]; then \
		./venv/bin/pytest tests/unit/ -v; \
	else \
		pytest tests/unit/ -v; \
	fi

test-integration: ## Run integration tests only
	@if [ -d "venv/bin" ]; then \
		./venv/bin/pytest tests/integration/ -v; \
	else \
		pytest tests/integration/ -v; \
	fi

test-security: ## Run security tests only
	@if [ -d "venv/bin" ]; then \
		./venv/bin/pytest tests/security/ -v; \
	else \
		pytest tests/security/ -v; \
	fi

clean: ## Clean up Python cache and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ 2>/dev/null || true

docker-build: ## Build Docker containers
	@echo "Building Docker containers..."
	docker-compose build

docker-up: ## Start Docker containers (detached)
	@echo "Generating dummy .env for agent container..."
	@./scripts/generate-dummy-env.sh .env .env.agent
	@echo "Starting Docker containers..."
	docker-compose up -d
	@sleep 3
	@echo ""
	@docker-compose ps
	@echo ""
	@echo "✅ Containers started!"
	@echo "View logs: make docker-logs or make logs"
	@echo "Check status: make status"

docker-down: ## Stop and remove Docker containers
	@echo "Stopping Docker containers..."
	docker-compose down

docker-logs: ## Show Docker container logs (follow mode)
	docker-compose logs -f

docker-clean: ## Remove all Docker containers, images, and volumes
	@echo "⚠️  This will remove all containers, images, and volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --remove-orphans; \
		docker system prune -f; \
		echo "✅ Docker cleaned!"; \
	else \
		echo "Cancelled."; \
	fi

# Convenience aliases
start: docker-up ## Alias for docker-up (start containers)

stop: docker-down ## Alias for docker-down (stop containers)

restart: ## Restart Docker containers
	@echo "Restarting Docker containers..."
	@make docker-down
	@sleep 2
	@make docker-up

status: ## Show status of Docker containers
	@echo "Docker Container Status:"
	@docker-compose ps
	@echo ""
	@echo "To view logs: make logs"

logs: docker-logs ## Alias for docker-logs (view logs)

logs-proxy: ## Show only proxy container logs
	docker-compose logs -f proxy

logs-agent: ## Show only agent container logs
	docker-compose logs -f agent

shell: ## Open shell in agent container (default)
	docker-compose exec agent /bin/bash

shell-proxy: ## Open shell in proxy container
	docker-compose exec proxy /bin/sh

shell-agent: ## Open shell in agent container (alias for 'shell')
	docker-compose exec agent /bin/bash

lint: ## Run code linters
	@if [ -d "venv/bin" ]; then \
		./venv/bin/black --check proxy/ tests/; \
		./venv/bin/pylint proxy/ tests/ || true; \
	else \
		black --check proxy/ tests/; \
		pylint proxy/ tests/ || true; \
	fi

format: ## Format code with black
	@if [ -d "venv/bin" ]; then \
		./venv/bin/black proxy/ tests/; \
	else \
		black proxy/ tests/; \
	fi

security-scan: ## Run security scans
	@if [ -d "venv/bin" ]; then \
		./venv/bin/bandit -r proxy/ -ll; \
		./venv/bin/safety check --json || true; \
	else \
		bandit -r proxy/ -ll; \
		safety check --json || true; \
	fi

setup-venv: ## Create a virtual environment with Python 3.12
	@echo "Creating virtual environment with Python 3.12..."
	@which python3.12 >/dev/null 2>&1 || (echo "❌ Python 3.12 not found. Install with: brew install python@3.12" && exit 1)
	python3.12 -m venv venv
	@echo "✅ Virtual environment created!"
	@echo ""
	@echo "Activate with:"
	@echo "  source venv/bin/activate"
	@echo ""
	@echo "Then run:"
	@echo "  make install"

verify: ## Verify installation and configuration
	@echo "Verifying CloakCode installation..."
	@echo ""
	@echo "1. Checking Python packages..."
	@if [ -d "venv/bin" ]; then \
		./venv/bin/python -c "import mitmproxy; import sys; print('✅ mitmproxy installed'); sys.exit(0)" 2>&1 || (echo "❌ mitmproxy not installed" && exit 1); \
	else \
		python3 -c "import mitmproxy; import sys; print('✅ mitmproxy installed'); sys.exit(0)" 2>&1 || (echo "❌ mitmproxy not installed" && exit 1); \
	fi
	@if [ -d "venv/bin" ]; then \
		./venv/bin/python -c "import yaml; print('✅ PyYAML installed')" 2>&1 || echo "❌ PyYAML not installed"; \
	else \
		python3 -c "import yaml; print('✅ PyYAML installed')" 2>&1 || echo "❌ PyYAML not installed"; \
	fi
	@if [ -d "venv/bin" ]; then \
		./venv/bin/python -c "import pytest; print('✅ pytest installed')" 2>&1 || echo "❌ pytest not installed"; \
	else \
		python3 -c "import pytest; print('✅ pytest installed')" 2>&1 || echo "❌ pytest not installed"; \
	fi
	@echo ""
	@echo "2. Checking configuration files..."
	@test -f .env && echo "✅ .env exists" || echo "❌ .env missing (copy from .env.template)"
	@test -f proxy/config.yaml && echo "✅ proxy/config.yaml exists" || echo "❌ proxy/config.yaml missing"
	@test -f credentials.yml && echo "✅ credentials.yml exists" || echo "❌ credentials.yml missing"
	@echo ""
	@echo "3. Checking Docker..."
	@docker --version >/dev/null 2>&1 && echo "✅ Docker installed" || echo "❌ Docker not found"
	@docker-compose --version >/dev/null 2>&1 && echo "✅ docker-compose installed" || echo "❌ docker-compose not found"
	@echo ""
	@echo "4. Checking logs directory..."
	@test -d logs && echo "✅ logs/ directory exists" || echo "❌ logs/ directory missing"
	@echo ""
	@echo "Run 'make start' to start CloakCode containers"

.DEFAULT_GOAL := help