#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building env-sidecar...${NC}"

# Create output directory
OUTPUT_DIR="env-sidecar"
mkdir -p "$OUTPUT_DIR"

# Build the binary
echo -e "${GREEN}→ Building binary...${NC}"
go build -o "$OUTPUT_DIR/env-sidecar"

# Copy and rename example files
echo -e "${GREEN}→ Copying configuration files...${NC}"
cp .env.vault.example "$OUTPUT_DIR/.env.vault"
cp sidecar.json.example "$OUTPUT_DIR/sidecar.json"

# Create certs directory if it doesn't exist
if [ ! -d "certs" ]; then
    echo -e "${GREEN}→ Creating certs directory...${NC}"
    mkdir -p "$OUTPUT_DIR/certs"
else
    echo -e "${GREEN}→ Copying certs...${NC}"
    cp -r certs "$OUTPUT_DIR/"
fi

# Make binary executable
chmod +x "$OUTPUT_DIR/env-sidecar"

echo ""
echo -e "${GREEN}✓ Build complete!${NC}"
echo ""
echo "Output directory: $OUTPUT_DIR/"
echo "  - env-sidecar (binary)"
echo "  - sidecar.json (config)"
echo "  - .env.vault (secrets)"
if [ -d "certs" ]; then
    echo "  - certs/ (CA certificates)"
fi
echo ""
echo "To get started:"
echo "  1. cd $OUTPUT_DIR"
echo "  2. Edit .env.vault with your real API keys"
echo "  3. Edit sidecar.json if needed"
echo "  4. ./env-sidecar"
