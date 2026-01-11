#!/bin/bash
# setup-cert.sh - Bootstrap CA certificate trust for env-sidecar transparent proxy
# This script downloads and installs the CA certificate from the running env-sidecar proxy

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CERT_URL="${CERT_URL:-http://env-sidecar:8888}"
CERT_OUTPUT="/tmp/env-sidecar-ca.crt"
CERT_DST="/usr/local/share/ca-certificates/env-sidecar-ca.crt"

echo -e "${GREEN}🔒 Bootstrapping trust for env-sidecar transparent proxy...${NC}"

# Check if proxy is reachable
if ! curl -s -o /dev/null --connect-timeout 5 "$CERT_URL" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: Cannot reach env-sidecar at $CERT_URL${NC}"
    echo -e "${YELLOW}   Make sure env-sidecar is running on the sidecar-network${NC}"
    echo -e "${YELLOW}   You can run this script again later manually${NC}"
    exit 0
fi

# Download CA certificate from magic domain via HTTP proxy
echo "📥 Downloading CA certificate from proxy..."
if ! curl -s -x "$CERT_URL" "http://mitm.it/cert/pem" -o "$CERT_OUTPUT"; then
    echo -e "${RED}❌ Failed to download CA certificate${NC}"
    echo "   Make sure env-sidecar is running and accessible"
    exit 1
fi

# Verify we got a valid certificate
if ! grep -q "BEGIN CERTIFICATE" "$CERT_OUTPUT"; then
    echo -e "${RED}❌ Downloaded file is not a valid certificate${NC}"
    cat "$CERT_OUTPUT"
    exit 1
fi

# Detect OS and install appropriately
if [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
    # Debian/Ubuntu
    echo "📦 Detected Debian/Ubuntu-based system"
    echo "📋 Installing CA certificate to system trust store..."

    # Install certificate
    sudo cp "$CERT_OUTPUT" "$CERT_DST"
    sudo chmod 644 "$CERT_DST"

    # Update certificates
    sudo update-ca-certificates >/dev/null 2>&1 || true

    echo -e "${GREEN}✅ CA certificate installed successfully${NC}"

elif [ -f /etc/redhat-release ] || [ -f /etc/centos-release ]; then
    # RHEL/CentOS/Fedora
    echo "📦 Detected RHEL/CentOS/Fedora-based system"
    echo "📋 Installing CA certificate to system trust store..."

    # Install certificate
    sudo cp "$CERT_OUTPUT" "/etc/pki/ca-trust/source/anchors/env-sidecar-ca.crt"
    sudo chmod 644 "/etc/pki/ca-trust/source/anchors/env-sidecar-ca.crt"

    # Update certificates
    sudo update-ca-trust >/dev/null 2>&1 || true

    echo -e "${GREEN}✅ CA certificate installed successfully${NC}"

else
    echo -e "${YELLOW}⚠️  Unknown OS type, installing to /usr/local/share/ca-certificates/${NC}"
    sudo mkdir -p /usr/local/share/ca-certificates
    sudo cp "$CERT_OUTPUT" "$CERT_DST"
    sudo chmod 644 "$CERT_DST"

    echo -e "${YELLOW}⚠️  You may need to manually update your certificate store${NC}"
fi

# Clean up
rm -f "$CERT_OUTPUT"

echo ""
echo -e "${GREEN}✅ Trust established!${NC}"
echo "   Tools like curl, git, and Python requests will now trust the env-sidecar proxy"
echo ""
echo "   To verify, try:"
echo "   curl -v https://api.anthropic.com --proxy $CERT_URL"
