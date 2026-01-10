#!/bin/bash
# SafeClaude - Interactive Credential Addition Tool
# This script helps users add new API credentials to the system without editing files manually

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CREDENTIALS_FILE="$PROJECT_ROOT/credentials.yml"
ENV_TEMPLATE="$PROJECT_ROOT/.env.template"
ENV_FILE="$PROJECT_ROOT/.env"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   SafeClaude - Add New API Credential                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if credentials.yml exists
if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo -e "${RED}Error: credentials.yml not found at $CREDENTIALS_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}This wizard will help you add a new API credential to SafeClaude.${NC}"
echo -e "${YELLOW}You'll need to edit credentials.yml and add the key to your .env file.${NC}"
echo ""

# Gather information
echo -e "${BLUE}Step 1: Service Information${NC}"
echo -e "${YELLOW}────────────────────────────${NC}"
read -p "Service identifier (lowercase, e.g., 'coinbase', 'shopify'): " SERVICE_NAME
read -p "Display name (e.g., 'Coinbase API', 'Shopify Admin API'): " DISPLAY_NAME
echo ""

echo -e "${BLUE}Step 2: Token Configuration${NC}"
echo -e "${YELLOW}────────────────────────────${NC}"
read -p "Dummy token name (e.g., 'DUMMY_COINBASE_KEY'): " DUMMY_TOKEN
read -p "Environment variable name (e.g., 'REAL_COINBASE_API_KEY'): " ENV_VAR
echo ""

echo -e "${BLUE}Step 3: Authentication Method${NC}"
echo -e "${YELLOW}────────────────────────────${NC}"
echo "How does this API authenticate?"
echo "  1) Authorization: Bearer <token>"
echo "  2) Authorization: <token> (no prefix)"
echo "  3) Custom header with Bearer"
echo "  4) Custom header without Bearer"
echo "  5) Query parameter"
read -p "Select option (1-5): " AUTH_METHOD

HEADER_NAME=""
HEADER_FORMAT=""
QUERY_PARAM=""

case $AUTH_METHOD in
    1)
        HEADER_NAME="Authorization"
        HEADER_FORMAT="Bearer {token}"
        ;;
    2)
        HEADER_NAME="Authorization"
        HEADER_FORMAT="{token}"
        ;;
    3)
        read -p "Header name (e.g., 'X-API-Key'): " HEADER_NAME
        HEADER_FORMAT="Bearer {token}"
        ;;
    4)
        read -p "Header name (e.g., 'X-API-Key'): " HEADER_NAME
        HEADER_FORMAT="{token}"
        ;;
    5)
        read -p "Query parameter name (e.g., 'api_key'): " QUERY_PARAM
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac
echo ""

echo -e "${BLUE}Step 4: Host Whitelist (Security)${NC}"
echo -e "${YELLOW}────────────────────────────────────${NC}"
echo "Enter allowed hostnames (one per line, empty line to finish):"
echo "Examples: api.example.com, *.example.com"
ALLOWED_HOSTS=()
while true; do
    read -p "Host: " HOST
    if [ -z "$HOST" ]; then
        break
    fi
    ALLOWED_HOSTS+=("$HOST")
done

if [ ${#ALLOWED_HOSTS[@]} -eq 0 ]; then
    echo -e "${RED}Error: At least one allowed host is required for security${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 5: Documentation${NC}"
echo -e "${YELLOW}───────────────────────${NC}"
read -p "API documentation URL (optional): " DOCS_URL
echo ""

# Generate YAML configuration
echo -e "${GREEN}Generating configuration...${NC}"
echo ""
echo -e "${YELLOW}Add the following to your credentials.yml file:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

cat << EOF

  # $DISPLAY_NAME
  $SERVICE_NAME:
    display_name: "$DISPLAY_NAME"
    dummy_token: "$DUMMY_TOKEN"
    env_var: "$ENV_VAR"
EOF

if [ -n "$HEADER_NAME" ]; then
cat << EOF
    header_locations:
      - name: "$HEADER_NAME"
        format: "$HEADER_FORMAT"
EOF
fi

if [ -n "$QUERY_PARAM" ]; then
cat << EOF
    query_param_names:
      - "$QUERY_PARAM"
EOF
fi

cat << EOF
    allowed_hosts:
EOF

for HOST in "${ALLOWED_HOSTS[@]}"; do
    echo "      - \"$HOST\""
done

if [ -n "$DOCS_URL" ]; then
    echo "    docs_url: \"$DOCS_URL\""
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Generate .env entry
echo -e "${YELLOW}Add the following to your .env file:${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
cat << EOF

# $DISPLAY_NAME
EOF
if [ -n "$DOCS_URL" ]; then
    echo "# Get from: $DOCS_URL"
fi
echo "$ENV_VAR=your-${SERVICE_NAME}-key-here"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Offer to open files for editing
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Copy the YAML configuration above to credentials.yml"
echo "  2. Add your real API key to .env (never commit this file!)"
echo "  3. Rebuild the proxy container: docker-compose build proxy"
echo "  4. Restart services: docker-compose restart"
echo ""

read -p "Open credentials.yml for editing now? (y/n): " OPEN_CREDS
if [ "$OPEN_CREDS" = "y" ] || [ "$OPEN_CREDS" = "Y" ]; then
    if command -v code &> /dev/null; then
        code "$CREDENTIALS_FILE"
    elif command -v vim &> /dev/null; then
        vim "$CREDENTIALS_FILE"
    else
        echo "Please edit: $CREDENTIALS_FILE"
    fi
fi

read -p "Open .env for editing now? (y/n): " OPEN_ENV
if [ "$OPEN_ENV" = "y" ] || [ "$OPEN_ENV" = "Y" ]; then
    # Create .env from template if it doesn't exist
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}Creating .env from template...${NC}"
        cp "$ENV_TEMPLATE" "$ENV_FILE"
    fi
    
    if command -v code &> /dev/null; then
        code "$ENV_FILE"
    elif command -v vim &> /dev/null; then
        vim "$ENV_FILE"
    else
        echo "Please edit: $ENV_FILE"
    fi
fi

echo ""
echo -e "${GREEN}✓ Configuration generated successfully!${NC}"
echo -e "${YELLOW}Don't forget to rebuild and restart: docker-compose up -d --build proxy${NC}"
