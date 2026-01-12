.PHONY: help install start stop restart logs clean test build setup

# CloakCode - Easy Deployment Makefile

help: ## Show this help message
	@echo "🛡️  CloakCode - Zero-Knowledge Credential Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Initial setup - copy config templates and setup SSH keys
	@echo "🔧 Setting up CloakCode..."
	@if [ ! -f .env ]; then \
		cp .env.template .env; \
		echo "✓ Created .env from template"; \
		echo "⚠️  Edit .env with your real API keys!"; \
	else \
		echo "ℹ️  .env already exists"; \
	fi
	@if [ ! -f proxy/config.yaml ]; then \
		cp proxy/config.yaml.example proxy/config.yaml 2>/dev/null || echo "ℹ️  No config.yaml.example found"; \
	fi
	@echo ""
	@echo "🔑 Setting up SSH keys for git operations..."
	@if [ -d "${HOME}/.ssh" ] && ([ -f "${HOME}/.ssh/id_ed25519" ] || [ -f "${HOME}/.ssh/id_rsa" ]); then \
		./scripts/setup-ssh-keys.sh; \
		echo "✓ SSH keys configured for git operations"; \
	else \
		echo "ℹ️  No SSH keys found in ~/.ssh"; \
		echo "   Git will use HTTPS (credentials via proxy)"; \
		echo "   To enable SSH: generate keys with 'ssh-keygen -t ed25519' and run 'make setup-ssh'"; \
	fi
	@echo "✓ Setup complete!"

install: setup build ## Full installation - setup and build containers
	@echo "📦 Installing CloakCode..."
	docker-compose build
	@echo "✓ Installation complete!"

build: ## Build Docker containers
	@echo "🏗️  Building containers..."
	docker-compose build

start: ## Start CloakCode services
	@echo "🚀 Starting CloakCode..."
	docker-compose up -d
	@echo "✓ Services started!"
	@echo ""
	@echo "Access the agent container:"
	@echo "  docker exec -it cloakcode_agent bash"

stop: ## Stop CloakCode services
	@echo "🛑 Stopping CloakCode..."
	docker-compose down
	@echo "✓ Services stopped"

restart: ## Restart CloakCode services
	@echo "🔄 Restarting CloakCode..."
	docker-compose restart
	@echo "✓ Services restarted"

logs: ## View container logs
	docker-compose logs -f

logs-proxy: ## View proxy logs only
	docker-compose logs -f proxy

logs-agent: ## View agent logs only
	docker-compose logs -f agent

status: ## Show container status
	@echo "📊 CloakCode Status:"
	@docker-compose ps

shell: ## Open shell in agent container
	@echo "🐚 Opening shell in agent container..."
	docker exec -it cloakcode_agent bash

shell-proxy: ## Open shell in proxy container
	@echo "🐚 Opening shell in proxy container..."
	docker exec -it cloakcode_proxy sh

setup-ssh: ## Setup SSH keys for git operations
	@echo "🔑 Setting up SSH keys..."
	@./scripts/setup-ssh-keys.sh
	@echo "✓ SSH keys configured!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Add public keys to your git hosting service (GitHub, GitLab, etc.)"
	@echo "2. Run 'make start' to start containers with SSH support"
	@echo "3. Test with: make test-ssh"

test: ## Run all tests
	@echo "🧪 Running all tests..."
	@echo ""
	@echo "Running unit tests..."
	@./tests/unit/test_ssh_key_setup.sh || true
	@echo ""
	@echo "Running security tests..."
	@./tests/security/test_ssh_key_security.sh || true
	@echo ""
	@if docker ps | grep -q cloakcode_agent; then \
		echo "Running integration tests..."; \
		./tests/integration/test_ssh_keys_integration.sh || true; \
	else \
		echo "⚠️  Skipping integration tests (containers not running)"; \
		echo "   Run 'make start' first to enable integration tests"; \
	fi
	@if [ -f tests/run_tests.sh ]; then \
		echo ""; \
		echo "Running additional tests..."; \
		bash tests/run_tests.sh; \
	fi

test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	@./tests/unit/test_ssh_key_setup.sh

test-security: ## Run security tests only
	@echo "🔒 Running security tests..."
	@./tests/security/test_ssh_key_security.sh

test-integration: ## Run integration tests only
	@echo "🔗 Running integration tests..."
	@if docker ps | grep -q cloakcode_agent; then \
		./tests/integration/test_ssh_keys_integration.sh; \
	else \
		echo "❌ Error: Containers not running"; \
		echo "   Run 'make start' first"; \
		exit 1; \
	fi

test-ssh: ## Test SSH connectivity in container
	@echo "🔑 Testing SSH connectivity..."
	@if docker ps | grep -q cloakcode_agent; then \
		echo "Testing SSH to GitHub..."; \
		docker exec cloakcode_agent ssh -T git@github.com || true; \
		echo ""; \
		echo "Testing git clone..."; \
		docker exec cloakcode_agent sh -c 'cd /tmp && git clone --depth 1 https://github.com/github/gitignore.git test-ssh-clone && rm -rf test-ssh-clone' && echo "✓ Git operations working!"; \
	else \
		echo "❌ Error: Container not running"; \
		echo "   Run 'make start' first"; \
		exit 1; \
	fi

clean: ## Remove containers and volumes
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	@echo "✓ Containers and volumes removed"

clean-all: clean ## Remove containers, volumes, and images
	@echo "🗑️  Removing images..."
	docker-compose down -v --rmi all
	@echo "✓ Full cleanup complete"

config: ## Show current configuration
	@echo "⚙️  CloakCode Configuration:"
	@echo ""
	@echo "Config files:"
	@ls -lh .env proxy/config.yaml credentials.yml 2>/dev/null || echo "  Some config files missing"
	@echo ""
	@echo "Credentials:"
	@./scripts/list-credentials.sh 2>/dev/null || echo "  Run './scripts/list-credentials.sh' for details"

add-credential: ## Add a new API credential
	@./scripts/add-credential.sh

list-credentials: ## List configured credentials
	@./scripts/list-credentials.sh

update: ## Pull latest changes and rebuild
	@echo "⬇️  Updating CloakCode..."
	git pull
	docker-compose build
	docker-compose up -d
	@echo "✓ Update complete!"

dev: ## Start in development mode (with logs)
	@echo "🔧 Starting in development mode..."
	docker-compose up

healthcheck: ## Check if services are healthy
	@echo "🏥 Checking service health..."
	@docker inspect cloakcode_proxy --format='Proxy: {{.State.Health.Status}}' 2>/dev/null || echo "Proxy: not running"
	@docker inspect cloakcode_agent --format='Agent: {{.State.Health.Status}}' 2>/dev/null || echo "Agent: not running"
