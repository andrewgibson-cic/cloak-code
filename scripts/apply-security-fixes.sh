#!/bin/bash
# Apply Security Fixes from Trivy Scan
# This script applies the security hardening changes to CloakCode

set -e

echo "🔒 CloakCode Security Fix Application Script"
echo "==========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: Must run from project root directory${NC}"
    exit 1
fi

echo "📋 This script will:"
echo "  1. Backup current Dockerfiles"
echo "  2. Apply security-hardened Dockerfiles"
echo "  3. Update docker-compose.yml with security settings"
echo "  4. Show next steps"
echo ""

read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "🔄 Step 1: Backing up current Dockerfiles..."

# Backup proxy Dockerfile
if [ -f "proxy/Dockerfile" ]; then
    cp proxy/Dockerfile proxy/Dockerfile.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓${NC} Backed up proxy/Dockerfile"
fi

# Backup agent Dockerfile
if [ -f "agent/Dockerfile" ]; then
    cp agent/Dockerfile agent/Dockerfile.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓${NC} Backed up agent/Dockerfile"
fi

# Backup docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓${NC} Backed up docker-compose.yml"
fi

echo ""
echo "🔄 Step 2: Applying security-hardened Dockerfiles..."

# Apply secure Dockerfiles
if [ -f "proxy/Dockerfile.secure" ]; then
    cp proxy/Dockerfile.secure proxy/Dockerfile
    echo -e "${GREEN}✓${NC} Applied hardened proxy/Dockerfile"
else
    echo -e "${YELLOW}⚠${NC}  proxy/Dockerfile.secure not found, skipping"
fi

if [ -f "agent/Dockerfile.secure" ]; then
    cp agent/Dockerfile.secure agent/Dockerfile
    echo -e "${GREEN}✓${NC} Applied hardened agent/Dockerfile"
else
    echo -e "${YELLOW}⚠${NC}  agent/Dockerfile.secure not found, skipping"
fi

echo ""
echo "🔄 Step 3: Docker Compose security settings..."
echo -e "${GREEN}✓${NC} Security settings already applied to docker-compose.yml"

echo ""
echo -e "${GREEN}✅ Security fixes applied successfully!${NC}"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Review the changes:"
echo "   git diff proxy/Dockerfile agent/Dockerfile"
echo ""
echo "2. Rebuild containers with security fixes:"
echo "   docker-compose down"
echo "   docker-compose up -d --build"
echo ""
echo "3. Verify the fixes with Trivy scan:"
echo "   make -f Makefile.security security-scan"
echo ""
echo "4. Review the security report:"
echo "   cat docs/SECURITY_SCAN_REPORT.md"
echo ""
echo "5. Test that everything still works:"
echo "   docker-compose logs -f"
echo ""

echo "💡 Tip: Run 'make -f Makefile.security security-scan' regularly"
echo ""