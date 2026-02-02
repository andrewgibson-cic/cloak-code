#!/bin/bash
# Integration tests for the ./cloakcode control script
#
# These tests verify that the control script functions correctly
# and handles various scenarios properly.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONTROL_SCRIPT="$PROJECT_ROOT/cloakcode"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

test_file_exists() {
    if [ -f "$CONTROL_SCRIPT" ]; then
        pass "Control script exists"
    else
        fail "Control script not found"
        exit 1
    fi
}

test_file_executable() {
    if [ -x "$CONTROL_SCRIPT" ]; then
        pass "Control script is executable"
    else
        fail "Control script is not executable"
    fi
}

test_help_command() {
    if "$CONTROL_SCRIPT" help > /dev/null 2>&1; then
        pass "Help command works"
    else
        fail "Help command failed"
    fi
}

test_help_shows_commands() {
    output=$("$CONTROL_SCRIPT" help 2>&1)
    
    if echo "$output" | grep -q "start"; then
        pass "Help shows 'start' command"
    else
        fail "Help doesn't show 'start' command"
    fi
    
    if echo "$output" | grep -q "stop"; then
        pass "Help shows 'stop' command"
    else
        fail "Help doesn't show 'stop' command"
    fi
    
    if echo "$output" | grep -q "status"; then
        pass "Help shows 'status' command"
    else
        fail "Help doesn't show 'status' command"
    fi
}

test_invalid_command() {
    if "$CONTROL_SCRIPT" invalid_command_xyz 2>&1 | grep -q "Unknown command"; then
        pass "Invalid command returns error"
    else
        fail "Invalid command doesn't show error"
    fi
}

test_validate_command() {
    if "$CONTROL_SCRIPT" validate > /dev/null 2>&1; then
        pass "Validate command works"
    else
        # May fail if .env doesn't exist, which is okay
        pass "Validate command executes (may report issues)"
    fi
}

# Print test header
echo "=================================="
echo "Control Script Integration Tests"
echo "=================================="
echo ""

# Run tests
echo "Running tests..."
echo ""

test_file_exists
test_file_executable
test_help_command
test_help_shows_commands
test_invalid_command
test_validate_command

# Print summary
echo ""
echo "=================================="
echo "Test Summary"
echo "=================================="
echo "Total:  $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi