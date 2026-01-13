#!/bin/bash
# CloakCode Cline Setup Helper Script
# This script helps set up Cline integration with the CloakCode agent container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local all_good=true
    
    # Check Docker
    if command -v docker &> /dev/null; then
        print_success "Docker installed"
    else
        print_error "Docker not found. Please install Docker first."
        all_good=false
    fi
    
    # Check docker-compose
    if command -v docker-compose &> /dev/null; then
        print_success "docker-compose installed"
    else
        print_error "docker-compose not found. Please install docker-compose first."
        all_good=false
    fi
    
    # Check VS Code
    if command -v code &> /dev/null; then
        print_success "VS Code CLI available"
    else
        print_warning "VS Code CLI (code) not found. You may need to install it manually."
        print_info "In VS Code: Cmd/Ctrl+Shift+P → 'Shell Command: Install code command in PATH'"
    fi
    
    # Check if .env exists
    if [ -f "$PROJECT_ROOT/.env" ]; then
        print_success ".env file exists"
    else
        print_warning ".env file not found. You'll need to create it from .env.template"
    fi
    
    # Check if containers are running
    if docker ps | grep -q "cloakcode_agent"; then
        print_success "CloakCode agent container is running"
    else
        print_warning "CloakCode agent container is not running"
        print_info "Run: docker-compose up -d"
    fi
    
    echo ""
    
    if [ "$all_good" = false ]; then
        print_error "Some prerequisites are missing. Please install them first."
        exit 1
    fi
}

# Install VS Code Remote - Containers extension
install_vscode_extension() {
    print_header "Installing VS Code Extensions"
    
    if command -v code &> /dev/null; then
        print_info "Installing Remote - Containers extension..."
        if code --install-extension ms-vscode-remote.remote-containers 2>/dev/null; then
            print_success "Remote - Containers extension installed"
        else
            print_warning "Failed to install extension automatically"
            print_info "Please install manually: Extensions → Search 'Remote - Containers'"
        fi
    else
        print_warning "VS Code CLI not available. Skipping extension installation."
        print_info "Install manually: Extensions → Search 'Remote - Containers'"
    fi
    
    echo ""
}

# Check devcontainer configuration
check_devcontainer() {
    print_header "Checking DevContainer Configuration"
    
    if [ -f "$PROJECT_ROOT/.devcontainer/devcontainer.json" ]; then
        print_success "devcontainer.json exists"
    else
        print_error "devcontainer.json not found!"
        print_info "This should have been created automatically. Something went wrong."
        exit 1
    fi
    
    if [ -f "$PROJECT_ROOT/.clinerules" ]; then
        print_success ".clinerules exists"
    else
        print_warning ".clinerules not found (optional)"
    fi
    
    echo ""
}

# Rebuild containers
rebuild_containers() {
    print_header "Rebuilding Containers"
    
    read -p "Do you want to rebuild the containers now? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Stopping containers..."
        docker-compose -f "$PROJECT_ROOT/docker-compose.yml" down
        
        print_info "Building containers (this may take a few minutes)..."
        docker-compose -f "$PROJECT_ROOT/docker-compose.yml" up -d --build
        
        print_success "Containers rebuilt and started"
        
        # Wait for containers to be healthy
        print_info "Waiting for containers to be ready..."
        sleep 5
        
        if docker ps | grep -q "cloakcode_agent.*Up"; then
            print_success "Agent container is running"
        else
            print_error "Agent container failed to start. Check: docker logs cloakcode_agent"
        fi
        
        if docker ps | grep -q "cloakcode_proxy.*Up"; then
            print_success "Proxy container is running"
        else
            print_error "Proxy container failed to start. Check: docker logs cloakcode_proxy"
        fi
    else
        print_info "Skipping container rebuild"
        print_warning "Remember to rebuild later: docker-compose down && docker-compose up -d --build"
    fi
    
    echo ""
}

# Display next steps
show_next_steps() {
    print_header "Setup Complete! Next Steps"
    
    echo ""
    echo "1. Connect VS Code to the container:"
    echo "   • Open VS Code"
    echo "   • Press Cmd/Ctrl+Shift+P"
    echo "   • Select: Remote-Containers: Attach to Running Container..."
    echo "   • Choose: cloakcode_agent"
    echo ""
    echo "2. Verify Cline is installed:"
    echo "   • Look for the Cline icon in the VS Code sidebar"
    echo "   • If missing, go to Extensions and search for 'Cline'"
    echo ""
    echo "3. Configure Cline with DUMMY credentials:"
    echo "   • Click the Cline icon → Settings"
    echo "   • API Provider: Anthropic (or OpenAI/OpenAI Compatible)"
    echo "   • API Key: DUMMY_ANTHROPIC_KEY (or DUMMY_OPENAI_KEY)"
    echo ""
    echo "4. Configure the proxy to inject real credentials:"
    echo "   • Edit proxy/config.yaml - add strategy and rule"
    echo "   • Edit .env - add your real API key"
    echo "   • Restart proxy: docker-compose restart proxy"
    echo ""
    echo "5. Test the setup:"
    echo "   • Ask Cline to help with a task"
    echo "   • Monitor logs: tail -f logs/proxy_injections.log"
    echo "   • Verify credential injection is working"
    echo ""
    echo "📚 For detailed instructions, see: docs/CLINE_SETUP.md"
    echo ""
    print_success "Happy coding with Cline!"
    echo ""
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    print_header "CloakCode Cline Setup"
    echo ""
    print_info "This script will help you set up Cline integration"
    echo ""
    
    check_prerequisites
    install_vscode_extension
    check_devcontainer
    rebuild_containers
    show_next_steps
}

# Run main function
main "$@"
