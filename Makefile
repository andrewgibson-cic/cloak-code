.PHONY: help install start stop restart logs clean test build setup

# CloakCode - Easy Deployment Makefile

help: ## Show this help message
	@echo "🛡️  CloakCode - Zero-Knowledge Credential Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Initial setup - copy config templates
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

test: ## Run test suite
	@echo "🧪 Running tests..."
	@if [ -f tests/run_tests.sh ]; then \
		bash tests/run_tests.sh; \
	else \
		pytest tests/ -v; \
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
