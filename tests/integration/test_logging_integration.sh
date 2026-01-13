#!/bin/bash
# Integration Tests for Logging Functionality
# Requires containers to be running

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test helper functions
test_start() {
    echo -e "${YELLOW}TEST: $1${NC}"
    TESTS_RUN=$((TESTS_RUN + 1))
}

test_pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo ""
}

test_fail() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo ""
}

echo "=============================================="
echo "Integration Tests for Logging"
echo "=============================================="
echo ""

# Check if containers are running
if ! docker ps | grep -q cloakcode_agent; then
    echo -e "${RED}ERROR: Containers not running${NC}"
    echo "Please start containers with: docker-compose up -d"
    exit 1
fi

# Test 1: Log directory exists and is writable in agent container
test_start "Log directory exists in agent container"
if docker exec cloakcode_agent test -d /home/agent/logs && \
   docker exec cloakcode_agent test -w /home/agent/logs; then
    test_pass
else
    test_fail "Log directory not found or not writable"
fi

# Test 2: Logging utilities are available in agent container
test_start "Logging utilities loaded in agent container"
if docker exec cloakcode_agent bash -c 'type log_event' >/dev/null 2>&1; then
    test_pass
else
    test_fail "Logging functions not available"
fi

# Test 3: Test log_event creates log on host
test_start "log_event creates log file on host"
# Clear any existing test messages
rm -f "$PROJECT_ROOT/logs/agent_activity.log" 2>/dev/null || true
# Create a test log entry
docker exec cloakcode_agent bash -c 'source /usr/local/bin/logging_utils.sh && log_event "TEST_INTEGRATION_MESSAGE"' >/dev/null 2>&1
sleep 1
if [ -f "$PROJECT_ROOT/logs/agent_activity.log" ] && \
   grep -q "TEST_INTEGRATION_MESSAGE" "$PROJECT_ROOT/logs/agent_activity.log"; then
    test_pass
else
    test_fail "Log file not created or message not found on host"
fi

# Test 4: Test npm logging wrapper
test_start "npm commands are logged"
docker exec cloakcode_agent bash -c 'npm --version' >/dev/null 2>&1
sleep 1
if grep -q "NPM:" "$PROJECT_ROOT/logs/agent_activity.log" 2>/dev/null; then
    test_pass
else
    test_fail "npm command not logged"
fi

# Test 5: Test git logging wrapper
test_start "git commands are logged"
docker exec cloakcode_agent bash -c 'git --version' >/dev/null 2>&1
sleep 1
if grep -q "GIT:" "$PROJECT_ROOT/logs/agent_activity.log" 2>/dev/null; then
    test_pass
else
    test_fail "git command not logged"
fi

# Test 6: Test JSON audit log creation
test_start "JSON audit log is created"
docker exec cloakcode_agent bash -c 'source /usr/local/bin/logging_utils.sh && log_json_event "test_integration" "integration test message"' >/dev/null 2>&1
sleep 1
if [ -f "$PROJECT_ROOT/logs/audit.json" ]; then
    test_pass
else
    test_fail "audit.json not created"
fi

# Test 7: Validate JSON structure
test_start "JSON audit log has valid structure"
if [ -f "$PROJECT_ROOT/logs/audit.json" ] && \
   cat "$PROJECT_ROOT/logs/audit.json" | tail -1 | jq empty 2>/dev/null; then
    test_pass
else
    test_fail "Invalid JSON structure"
fi

# Test 8: Test proxy log directory
test_start "Proxy can write to log directory"
if docker exec cloakcode_proxy test -d /logs && \
   docker exec cloakcode_proxy test -w /logs; then
    test_pass
else
    test_fail "Proxy cannot access log directory"
fi

# Test 9: Test bash history persistence
test_start "Bash history is persistent"
docker exec cloakcode_agent bash -c 'echo "test_history_command" >> ~/.bash_history'
sleep 1
if [ -f "$PROJECT_ROOT/logs/.bash_history" ]; then
    test_pass
else
    test_fail "Bash history not persisted to host"
fi

# Test 10: Test container restart persistence
test_start "Logs persist after container restart"
TEST_MSG="PERSIST_TEST_$(date +%s)"
docker exec cloakcode_agent bash -c "source /usr/local/bin/logging_utils.sh && log_event '$TEST_MSG'" >/dev/null 2>&1
sleep 1
docker-compose restart agent >/dev/null 2>&1
sleep 3
if grep -q "$TEST_MSG" "$PROJECT_ROOT/logs/agent_activity.log" 2>/dev/null; then
    test_pass
else
    test_fail "Logs not persisted after restart"
fi

# Test 11: Test log file permissions
test_start "Log files have correct permissions"
if [ -f "$PROJECT_ROOT/logs/agent_activity.log" ] && \
   [ -r "$PROJECT_ROOT/logs/agent_activity.log" ] && \
   [ -w "$PROJECT_ROOT/logs/agent_activity.log" ]; then
    test_pass
else
    test_fail "Incorrect log file permissions"
fi

# Test 12: Test container stop logging
test_start "Container stop is logged"
STOP_TIME=$(date -Iseconds)
docker-compose restart agent >/dev/null 2>&1
sleep 3
if grep -q "Container Stopping\|Container Started" "$PROJECT_ROOT/logs/agent_activity.log" 2>/dev/null; then
    test_pass
else
    test_fail "Container lifecycle not logged"
fi

# Summary
echo "=============================================="
echo "Integration Test Summary"
echo "=============================================="
echo "Tests Run:    $TESTS_RUN"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
else
    echo -e "Tests Failed: ${GREEN}$TESTS_FAILED${NC}"
fi
echo "=============================================="

if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
else
    echo -e "${GREEN}All integration tests passed!${NC}"
    exit 0
fi
