#!/bin/bash
# Unit Tests for Logging Functionality

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
echo "Testing Logging Utilities"
echo "=============================================="
echo ""

# Test 1: Check if logging utilities script exists
test_start "Logging utilities script exists"
if [ -f "$PROJECT_ROOT/agent/logging_utils.sh" ]; then
    test_pass
else
    test_fail "agent/logging_utils.sh not found"
fi

# Test 2: Check if script is executable or can be sourced
test_start "Logging utilities script is sourceable"
if bash -n "$PROJECT_ROOT/agent/logging_utils.sh" 2>/dev/null; then
    test_pass
else
    test_fail "Script has syntax errors"
fi

# Test 3: Source the script and check for key functions
test_start "Key logging functions are defined"
if source "$PROJECT_ROOT/agent/logging_utils.sh" 2>/dev/null && \
   type log_event >/dev/null 2>&1 && \
   type log_json_event >/dev/null 2>&1 && \
   type log_command >/dev/null 2>&1; then
    test_pass
else
    test_fail "Required functions not defined"
fi

# Test 4: Check log directory structure
test_start "Log directory structure exists"
if [ -d "$PROJECT_ROOT/logs" ] && \
   [ -f "$PROJECT_ROOT/logs/.gitignore" ] && \
   [ -f "$PROJECT_ROOT/logs/.gitkeep" ]; then
    test_pass
else
    test_fail "Log directory structure incomplete"
fi

# Test 5: Check docker-compose.yml has log volume mounts
test_start "Docker compose has log volume mounts"
if grep -q "./logs:/home/agent/logs:rw" "$PROJECT_ROOT/docker-compose.yml" && \
   grep -q "./logs:/logs:rw" "$PROJECT_ROOT/docker-compose.yml"; then
    test_pass
else
    test_fail "Log volume mounts not configured"
fi

# Test 6: Check agent entrypoint sources logging utilities
test_start "Agent entrypoint sources logging utilities"
if grep -q "source /usr/local/bin/logging_utils.sh" "$PROJECT_ROOT/agent/entrypoint.sh" || \
   grep -q ". /usr/local/bin/logging_utils.sh" "$PROJECT_ROOT/agent/entrypoint.sh"; then
    test_pass
else
    test_fail "Entrypoint doesn't source logging utilities"
fi

# Test 7: Check proxy inject.py has logging methods
test_start "Proxy inject.py has logging methods"
if grep -q "_write_injection_log" "$PROJECT_ROOT/proxy/inject.py" && \
   grep -q "_write_security_log" "$PROJECT_ROOT/proxy/inject.py"; then
    test_pass
else
    test_fail "Proxy logging methods not found"
fi

# Test 8: Test log rotation function
test_start "Log rotation function works"
source "$PROJECT_ROOT/agent/logging_utils.sh" 2>/dev/null
export LOG_DIR="/tmp/test_logs_$$"
export ACTIVITY_LOG="$LOG_DIR/test.log"
mkdir -p "$LOG_DIR"
echo "test" > "$ACTIVITY_LOG"

if rotate_log_if_needed "$ACTIVITY_LOG" 2>/dev/null; then
    # Should not rotate small file
    if [ -f "$ACTIVITY_LOG" ] && [ ! -f "${ACTIVITY_LOG}."* ]; then
        test_pass
    else
        test_fail "Rotation triggered incorrectly"
    fi
else
    test_fail "Rotation function failed"
fi
rm -rf "$LOG_DIR"

# Test 9: Test log_event function creates log file
test_start "log_event creates log file"
source "$PROJECT_ROOT/agent/logging_utils.sh" 2>/dev/null
export LOG_DIR="/tmp/test_logs_$$"
export ACTIVITY_LOG="$LOG_DIR/activity.log"
mkdir -p "$LOG_DIR"

if log_event "Test message" >/dev/null 2>&1; then
    if [ -f "$ACTIVITY_LOG" ] && grep -q "Test message" "$ACTIVITY_LOG"; then
        test_pass
    else
        test_fail "Log file not created or message not found"
    fi
else
    test_fail "log_event function failed"
fi
rm -rf "$LOG_DIR"

# Test 10: Test log_json_event creates valid JSON
test_start "log_json_event creates valid JSON"
source "$PROJECT_ROOT/agent/logging_utils.sh" 2>/dev/null
export LOG_DIR="/tmp/test_logs_$$"
export AUDIT_LOG="$LOG_DIR/audit.json"
mkdir -p "$LOG_DIR"

if log_json_event "test_event" "test message" >/dev/null 2>&1; then
    if [ -f "$AUDIT_LOG" ] && cat "$AUDIT_LOG" | jq empty 2>/dev/null; then
        test_pass
    else
        test_fail "Invalid JSON or file not created"
    fi
else
    test_fail "log_json_event function failed"
fi
rm -rf "$LOG_DIR"

# Test 11: Check documentation exists
test_start "Logging documentation exists"
if [ -f "$PROJECT_ROOT/docs/LOGGING.md" ]; then
    test_pass
else
    test_fail "docs/LOGGING.md not found"
fi

# Test 12: Check README mentions logging
test_start "README mentions logging"
if grep -q -i "logging" "$PROJECT_ROOT/README.md" && \
   grep -q "logs/" "$PROJECT_ROOT/README.md"; then
    test_pass
else
    test_fail "README doesn't document logging"
fi

# Summary
echo "=============================================="
echo "Test Summary"
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
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
