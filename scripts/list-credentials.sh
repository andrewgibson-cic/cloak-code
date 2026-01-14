#!/bin/bash
# CloakCode - List Configured Credentials
# Shows all configured API services and their status

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CREDENTIALS_FILE="$PROJECT_ROOT/credentials.yml"
ENV_FILE="$PROJECT_ROOT/.env"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   CloakCode - Configured API Credentials                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if credentials.yml exists
if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo -e "${RED}Error: credentials.yml not found at $CREDENTIALS_FILE${NC}"
    exit 1
fi

# Check if .env exists
ENV_EXISTS=false
if [ -f "$ENV_FILE" ]; then
    ENV_EXISTS=true
fi

# Parse YAML and display credentials (simplified parsing)
echo -e "${CYAN}Configured Services:${NC}"
echo -e "${YELLOW}────────────────────────────────────────────────────────────${NC}"

# Use Python to parse YAML properly
python3 << 'EOF'
import yaml
import os
import sys

credentials_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.yml')
env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

try:
    with open(credentials_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Load .env if it exists
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    credentials = config.get('credentials', {})
    
    # Header
    print(f"{'Service':<20} {'Display Name':<30} {'Status':<15} {'Hosts'}")
    print("─" * 100)
    
    for service_name, cred in credentials.items():
        display_name = cred.get('display_name', service_name)[:28]
        env_var = cred.get('env_var', '')
        hosts = cred.get('allowed_hosts', [])
        
        # Check if configured in .env
        if env_var in env_vars and env_vars[env_var] and not env_vars[env_var].startswith('your-'):
            status = '\033[0;32m✓ Configured\033[0m'
        else:
            status = '\033[0;31m✗ Missing\033[0m'
        
        # Format hosts
        if len(hosts) > 2:
            host_str = f"{hosts[0]}, {hosts[1]}, +{len(hosts)-2} more"
        elif hosts:
            host_str = ", ".join(hosts[:2])
        else:
            host_str = "None"
        
        print(f"{service_name:<20} {display_name:<30} {status:<24} {host_str[:40]}")
    
    print("")
    
    # Summary
    configured = sum(1 for _, cred in credentials.items() 
                     if cred.get('env_var') in env_vars 
                     and env_vars.get(cred.get('env_var'), '').strip() 
                     and not env_vars.get(cred.get('env_var'), '').startswith('your-'))
    total = len(credentials)
    
    print(f"Summary: {configured}/{total} credentials configured")
    
    if configured < total:
        print(f"\n\033[1;33mTo add missing credentials:\033[0m")
        print(f"  1. Run: ./scripts/add-credential.sh")
        print(f"  2. Or manually edit .env and add the required keys")

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF

echo ""
echo -e "${CYAN}Configuration Files:${NC}"
echo -e "${YELLOW}────────────────────────────────────────────────────────────${NC}"
echo "  credentials.yml: $CREDENTIALS_FILE"
if [ "$ENV_EXISTS" = true ]; then
    echo -e "  .env:            $ENV_FILE ${GREEN}(exists)${NC}"
else
    echo -e "  .env:            $ENV_FILE ${RED}(not found - copy from .env.template)${NC}"
fi
echo ""

echo -e "${CYAN}Quick Commands:${NC}"
echo -e "${YELLOW}────────────────────────────────────────────────────────────${NC}"
echo "  Add credential:    ./scripts/add-credential.sh"
echo "  Edit config:       vim credentials.yml"
echo "  Edit secrets:      vim .env"
echo "  Restart proxy:     docker-compose restart proxy"
echo ""
