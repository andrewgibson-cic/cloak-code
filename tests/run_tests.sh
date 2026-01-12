#!/bin/bash
set -e

echo "=========================================="
echo "Universal Injector Integration Tests"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to project root
cd "$(dirname "$0")/.."

echo "📋 Pre-flight checks..."
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found. Please install docker-compose.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} docker-compose is available"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python 3 is available"

echo ""
echo "🏗️  Starting containers..."
docker-compose up -d
echo ""

echo "⏳ Waiting for containers to be healthy (15 seconds)..."
sleep 15
echo ""

echo "🧪 Running integration tests..."
echo ""

# Run the tests
if python3 tests/integration/test_agent_container.py; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo -e "✅ All tests passed!"
    echo -e "==========================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}=========================================="
    echo -e "❌ Some tests failed"
    echo -e "==========================================${NC}"
    echo ""
    echo "💡 Troubleshooting tips:"
    echo "  - Check container logs: docker-compose logs"
    echo "  - Verify containers are running: docker-compose ps"
    echo "  - Restart containers: docker-compose restart"
    exit 1
fi
