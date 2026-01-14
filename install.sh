#!/bin/bash
# CloakCode Installation Script
# This script provides a guided installation experience

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   ██████╗██╗      ██████╗  █████╗ ██╗  ██╗                ║
║  ██╔════╝██║     ██╔═══██╗██╔══██╗██║ ██╔╝                ║
║  ██║     ██║     ██║   ██║███████║█████╔╝                 ║
║  ██║     ██║     ██║   ██║██╔══██║██╔═██╗                 ║
║  ╚██████╗███████╗╚██████╔╝██║  ██║██║  ██╗                ║
║   ╚═════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝                ║
║                                                            ║
║   ██████╗ ██████╗ ██████╗ ███████╗                        ║
║  ██╔════╝██╔═══██╗██╔══██╗██╔════╝                        ║
║  ██║     ██║   ██║██║  ██║█████╗                          ║
║  ██║     ██║   ██║██║  ██║██╔══╝                          ║
║  ╚██████╗╚██████╔╝██████╔╝███████╗                        ║
║   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝                        ║
║                                                            ║
║          Zero-Knowledge Credential Management             ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${CYAN}Welcome to the CloakCode installer!${NC}"
echo ""
echo "This script will help you set up CloakCode on your system."
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Docker version
check_docker_version() {
    local version=$(docker version --format '{{.Server.Version}}' 2>/dev/null)
    if [ -z "$version" ]; then
        return 1
    fi
    
    local major=$(echo $version | cut -d. -f1)
    if [ "$major" -ge 20 ]; then
        return 0
    else
        return 1
    fi
}

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"
echo ""

MISSING_DEPS=()

# Check Docker
if command_exists docker; then
    if check_docker_version; then
        echo -e "${GREEN}✓${NC} Docker $(docker version --format '{{.Server.Version}}') installed"
    else
        echo -e "${RED}✗${NC} Docker version is too old (need 20.0+)"
        MISSING_DEPS+=("docker")
    fi
else
    echo -e "${RED}✗${NC} Docker not found"
    MISSING_DEPS+=("docker")
fi

# Check Docker Compose
if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker Compose installed"
else
    echo -e "${RED}✗${NC} Docker Compose not found"
    MISSING_DEPS+=("docker-compose")
fi

# Check Git (optional)
if command_exists git; then
    echo -e "${GREEN}✓${NC} Git installed"
else
    echo -e "${YELLOW}⚠${NC} Git not found (optional, but recommended)"
fi

echo ""

# If dependencies are missing, provide installation instructions
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${RED}Missing dependencies: ${MISSING_DEPS[*]}${NC}"
    echo ""
    echo "Please install the required dependencies:"
    echo ""
    
    if [[ " ${MISSING_DEPS[@]} " =~ " docker " ]]; then
        echo "Docker installation:"
        echo "  macOS:   https://docs.docker.com/desktop/install/mac-install/"
        echo "  Linux:   https://docs.docker.com/engine/install/"
        echo "  Windows: https://docs.docker.com/desktop/install/windows-install/"
        echo ""
    fi
    
    if [[ " ${MISSING_DEPS[@]} " =~ " docker-compose " ]]; then
        echo "Docker Compose installation:"
        echo "  https://docs.docker.com/compose/install/"
        echo ""
    fi
    
    exit 1
fi

# Step 2: Setup configuration files
echo -e "${YELLOW}Step 2: Setting up configuration files...${NC}"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.template ]; then
        cp .env.template .env
        echo -e "${GREEN}✓${NC} Created .env from template"
    else
        echo -e "${YELLOW}⚠${NC} No .env.template found, creating basic .env"
        cat > .env << 'ENVEOF'
# CloakCode Environment Variables
# Edit this file with your real API credentials

# Example: OpenAI
# REAL_OPENAI_API_KEY=sk-proj-your-key-here

# Example: GitHub
# REAL_GITHUB_TOKEN=ghp_your-token-here

# Example: AWS
# REAL_AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
# REAL_AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
ENVEOF
        echo -e "${GREEN}✓${NC} Created basic .env file"
    fi
    
    echo -e "${CYAN}   → Edit .env with your real API credentials${NC}"
else
    echo -e "${GREEN}✓${NC} .env file already exists"
fi

# Create proxy/config.yaml if it doesn't exist
if [ ! -f proxy/config.yaml ]; then
    if [ -f proxy/config.yaml.example ]; then
        cp proxy/config.yaml.example proxy/config.yaml
        echo -e "${GREEN}✓${NC} Created proxy/config.yaml from example"
    else
        echo -e "${YELLOW}⚠${NC} No proxy/config.yaml.example found"
    fi
else
    echo -e "${GREEN}✓${NC} proxy/config.yaml already exists"
fi

echo ""

# Step 3: Build containers
echo -e "${YELLOW}Step 3: Building Docker containers...${NC}"
echo ""
echo "This may take a few minutes on first run..."
echo ""

if docker-compose build; then
    echo ""
    echo -e "${GREEN}✓${NC} Containers built successfully"
else
    echo ""
    echo -e "${RED}✗${NC} Failed to build containers"
    exit 1
fi

echo ""

# Step 4: Start services
echo -e "${YELLOW}Step 4: Starting services...${NC}"
echo ""

if docker-compose up -d; then
    echo ""
    echo -e "${GREEN}✓${NC} Services started successfully"
else
    echo ""
    echo -e "${RED}✗${NC} Failed to start services"
    exit 1
fi

echo ""

# Step 5: Wait for services to be healthy
echo -e "${YELLOW}Step 5: Waiting for services to be ready...${NC}"
echo ""

echo -n "Waiting for proxy."
for i in {1..30}; do
    if docker inspect cloakcode_proxy --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
        echo ""
        echo -e "${GREEN}✓${NC} Proxy is healthy"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""

# Installation complete!
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║            ✓ Installation Complete!                       ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Show next steps
echo -e "${CYAN}Next Steps:${NC}"
echo ""
echo -e "  1. ${YELLOW}Configure your API credentials:${NC}"
echo "     Edit the .env file with your real API keys"
echo "     ${BLUE}vim .env${NC}"
echo ""
echo -e "  2. ${YELLOW}Access the agent container:${NC}"
echo "     ${BLUE}docker exec -it cloakcode_agent bash${NC}"
echo ""
echo -e "  3. ${YELLOW}View logs:${NC}"
echo "     ${BLUE}make logs${NC}"
echo "     or"
echo "     ${BLUE}docker-compose logs -f${NC}"
echo ""
echo -e "  4. ${YELLOW}Add more API credentials:${NC}"
echo "     ${BLUE}./scripts/add-credential.sh${NC}"
echo ""
echo -e "  5. ${YELLOW}See all available commands:${NC}"
echo "     ${BLUE}make help${NC}"
echo ""

# Show current status
echo -e "${CYAN}Current Status:${NC}"
echo ""
docker-compose ps
echo ""

echo -e "${GREEN}Ready to securely manage your API credentials! 🛡️${NC}"
echo ""

# Offer to open .env for editing
read -p "Would you like to edit .env now? (y/n): " edit_env
if [ "$edit_env" = "y" ] || [ "$edit_env" = "Y" ]; then
    if command_exists code; then
        code .env
    elif command_exists vim; then
        vim .env
    elif command_exists nano; then
        nano .env
    else
        echo "Please edit .env with your preferred editor"
    fi
fi

echo ""
echo -e "${YELLOW}Don't forget to restart the proxy after editing .env:${NC}"
echo -e "  ${BLUE}make restart${NC}"
echo ""
