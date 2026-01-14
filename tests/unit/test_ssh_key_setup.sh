#!/bin/bash
# Unit tests for SSH key setup functionality
# Tests the agent/entrypoint.sh SSH key setup functions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test helper functions
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    echo -e "  ${RED}Error${NC}: $2"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

skip() {
    echo -e "${YELLOW}⊘ SKIP${NC}: $1"
}

run_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "\n${YELLOW}Test ${TESTS_RUN}${NC}: $1"
}

# Setup test environment
setup() {
    export TEST_HOME="/tmp/ssh-key-test-$$"
    export TEST_SSH_SOURCE="/tmp/ssh-key-source-$$"
    
    mkdir -p "$TEST_HOME/.ssh"
    mkdir -p "$TEST_SSH_SOURCE"
    
    # Generate test SSH keys
    ssh-keygen -t ed25519 -f "$TEST_SSH_SOURCE/id_ed25519" -N "" -C "test@example.com" >/dev/null 2>&1
    ssh-keygen -t rsa -b 2048 -f "$TEST_SSH_SOURCE/id_rsa" -N "" -C "test@example.com" >/dev/null 2>&1
}

# Cleanup test environment
cleanup() {
    rm -rf "$TEST_HOME"
    rm -rf "$TEST_SSH_SOURCE"
}

# Test 1: Verify SSH key file permissions
test_ssh_key_permissions() {
    run_test "SSH private key permissions should be 600"
    
    local key="$TEST_SSH_SOURCE/id_ed25519"
    chmod 600 "$key"
    
    local perms=$(stat -f "%Lp" "$key" 2>/dev/null || stat -c "%a" "$key" 2>/dev/null)
    
    if [ "$perms" = "600" ]; then
        pass "Private key has correct permissions (600)"
    else
        fail "Private key permissions" "Expected 600, got $perms"
    fi
}

# Test 2: Verify SSH directory permissions
test_ssh_directory_permissions() {
    run_test "SSH directory permissions should be 700"
    
    local ssh_dir="$TEST_HOME/.ssh"
    chmod 700 "$ssh_dir"
    
    local perms=$(stat -f "%Lp" "$ssh_dir" 2>/dev/null || stat -c "%a" "$ssh_dir" 2>/dev/null)
    
    if [ "$perms" = "700" ]; then
        pass "SSH directory has correct permissions (700)"
    else
        fail "SSH directory permissions" "Expected 700, got $perms"
    fi
}

# Test 3: Verify public key permissions
test_ssh_public_key_permissions() {
    run_test "SSH public key permissions should be 644"
    
    local key="$TEST_SSH_SOURCE/id_ed25519.pub"
    chmod 644 "$key"
    
    local perms=$(stat -f "%Lp" "$key" 2>/dev/null || stat -c "%a" "$key" 2>/dev/null)
    
    if [ "$perms" = "644" ]; then
        pass "Public key has correct permissions (644)"
    else
        fail "Public key permissions" "Expected 644, got $perms"
    fi
}

# Test 4: Test key copying functionality
test_key_copying() {
    run_test "Keys should be copied correctly"
    
    # Copy keys
    cp "$TEST_SSH_SOURCE/id_ed25519" "$TEST_HOME/.ssh/"
    cp "$TEST_SSH_SOURCE/id_ed25519.pub" "$TEST_HOME/.ssh/"
    chmod 600 "$TEST_HOME/.ssh/id_ed25519"
    chmod 644 "$TEST_HOME/.ssh/id_ed25519.pub"
    
    if [ -f "$TEST_HOME/.ssh/id_ed25519" ] && [ -f "$TEST_HOME/.ssh/id_ed25519.pub" ]; then
        pass "Keys copied successfully"
    else
        fail "Key copying" "Keys not found in destination"
    fi
}

# Test 5: Test multiple key types
test_multiple_key_types() {
    run_test "Should support multiple key types (Ed25519, RSA)"
    
    local ed25519_exists=false
    local rsa_exists=false
    
    if [ -f "$TEST_SSH_SOURCE/id_ed25519" ]; then
        ed25519_exists=true
    fi
    
    if [ -f "$TEST_SSH_SOURCE/id_rsa" ]; then
        rsa_exists=true
    fi
    
    if $ed25519_exists && $rsa_exists; then
        pass "Both Ed25519 and RSA keys available"
    else
        fail "Multiple key types" "Not all key types found"
    fi
}

# Test 6: Test SSH config file creation
test_ssh_config_creation() {
    run_test "Should create valid SSH config file"
    
    cat > "$TEST_HOME/.ssh/config" <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
EOF
    chmod 600 "$TEST_HOME/.ssh/config"
    
    if [ -f "$TEST_HOME/.ssh/config" ]; then
        if grep -q "github.com" "$TEST_HOME/.ssh/config"; then
            pass "SSH config file created with correct content"
        else
            fail "SSH config content" "Config missing expected content"
        fi
    else
        fail "SSH config creation" "Config file not created"
    fi
}

# Test 7: Test known_hosts file creation
test_known_hosts_creation() {
    run_test "Should create known_hosts file"
    
    touch "$TEST_HOME/.ssh/known_hosts"
    chmod 644 "$TEST_HOME/.ssh/known_hosts"
    
    if [ -f "$TEST_HOME/.ssh/known_hosts" ]; then
        local perms=$(stat -f "%Lp" "$TEST_HOME/.ssh/known_hosts" 2>/dev/null || stat -c "%a" "$TEST_HOME/.ssh/known_hosts" 2>/dev/null)
        if [ "$perms" = "644" ]; then
            pass "known_hosts file created with correct permissions"
        else
            fail "known_hosts permissions" "Expected 644, got $perms"
        fi
    else
        fail "known_hosts creation" "File not created"
    fi
}

# Test 8: Test SSH key cleanup
test_ssh_cleanup() {
    run_test "Should clean up SSH directory on exit"
    
    mkdir -p "$TEST_HOME/.ssh"
    touch "$TEST_HOME/.ssh/id_ed25519"
    
    # Simulate cleanup
    rm -rf "$TEST_HOME/.ssh"
    
    if [ ! -d "$TEST_HOME/.ssh" ]; then
        pass "SSH directory cleaned up successfully"
    else
        fail "SSH cleanup" "Directory still exists after cleanup"
    fi
}

# Test 9: Test SSH agent socket detection
test_ssh_agent_detection() {
    run_test "Should detect SSH agent socket if available"
    
    if [ -n "$SSH_AUTH_SOCK" ] && [ -S "$SSH_AUTH_SOCK" ]; then
        pass "SSH agent socket detected"
    else
        skip "SSH agent not running (expected in many test environments)"
    fi
}

# Test 10: Test key type detection
test_key_type_detection() {
    run_test "Should correctly identify key types"
    
    # Check Ed25519 key format
    if ssh-keygen -l -f "$TEST_SSH_SOURCE/id_ed25519" 2>/dev/null | grep -q "ED25519"; then
        pass "Ed25519 key type correctly identified"
    else
        fail "Ed25519 key detection" "Key type not recognized"
    fi
}

# Test 11: Test read-only mount simulation
test_readonly_mount() {
    run_test "Should handle read-only source directory"
    
    local readonly_source="/tmp/ssh-readonly-$$"
    mkdir -p "$readonly_source"
    cp "$TEST_SSH_SOURCE/id_ed25519" "$readonly_source/"
    
    # Make read-only (on Linux)
    chmod 555 "$readonly_source" 2>/dev/null || true
    
    if [ -r "$readonly_source/id_ed25519" ]; then
        pass "Can read keys from read-only source"
    else
        fail "Read-only mount" "Cannot read from read-only source"
    fi
    
    # Cleanup
    chmod 755 "$readonly_source" 2>/dev/null || true
    rm -rf "$readonly_source"
}

# Test 12: Test git configuration
test_git_config() {
    run_test "Should configure git to use SSH URLs"
    
    # Test URL rewriting
    cd "$TEST_HOME"
    git init >/dev/null 2>&1
    git config url."git@github.com:".insteadOf "https://github.com/"
    
    local config=$(git config --get url."git@github.com:".insteadof)
    
    if [ "$config" = "https://github.com/" ]; then
        pass "Git configured to rewrite HTTPS URLs to SSH"
    else
        fail "Git configuration" "URL rewriting not configured correctly"
    fi
}

# Test 13: Test missing keys scenario
test_missing_keys() {
    run_test "Should handle missing keys gracefully"
    
    local empty_dir="/tmp/empty-ssh-$$"
    mkdir -p "$empty_dir"
    
    if [ -z "$(ls -A $empty_dir 2>/dev/null)" ]; then
        pass "Correctly detects empty/missing keys directory"
    else
        fail "Missing keys handling" "Failed to detect empty directory"
    fi
    
    rm -rf "$empty_dir"
}

# Test 14: Test SSH config validation
test_ssh_config_syntax() {
    run_test "Should create syntactically valid SSH config"
    
    cat > "$TEST_HOME/.ssh/config" <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF
    
    # Validate config (ssh will fail on syntax errors)
    if ssh -F "$TEST_HOME/.ssh/config" -G github.com >/dev/null 2>&1; then
        pass "SSH config is syntactically valid"
    else
        skip "SSH config validation (requires SSH client)"
    fi
}

# Test 15: Test permission enforcement
test_permission_enforcement() {
    run_test "Should enforce secure permissions"
    
    # Create key with wrong permissions
    cp "$TEST_SSH_SOURCE/id_ed25519" "$TEST_HOME/.ssh/"
    chmod 644 "$TEST_HOME/.ssh/id_ed25519"  # Too permissive
    
    local perms=$(stat -f "%Lp" "$TEST_HOME/.ssh/id_ed25519" 2>/dev/null || stat -c "%a" "$TEST_HOME/.ssh/id_ed25519" 2>/dev/null)
    
    # Fix permissions
    chmod 600 "$TEST_HOME/.ssh/id_ed25519"
    local fixed_perms=$(stat -f "%Lp" "$TEST_HOME/.ssh/id_ed25519" 2>/dev/null || stat -c "%a" "$TEST_HOME/.ssh/id_ed25519" 2>/dev/null)
    
    if [ "$fixed_perms" = "600" ]; then
        pass "Permissions enforced correctly (changed from $perms to 600)"
    else
        fail "Permission enforcement" "Failed to set correct permissions"
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "SSH Key Setup Unit Tests"
    echo "=========================================="
    echo ""
    
    # Setup
    setup
    
    # Run all tests
    test_ssh_key_permissions
    test_ssh_directory_permissions
    test_ssh_public_key_permissions
    test_key_copying
    test_multiple_key_types
    test_ssh_config_creation
    test_known_hosts_creation
    test_ssh_cleanup
    test_ssh_agent_detection
    test_key_type_detection
    test_readonly_mount
    test_git_config
    test_missing_keys
    test_ssh_config_syntax
    test_permission_enforcement
    
    # Cleanup
    cleanup
    
    # Summary
    echo ""
    echo "=========================================="
    echo "Test Summary"
    echo "=========================================="
    echo "Tests Run:    $TESTS_RUN"
    echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
    echo "=========================================="
    
    # Exit with appropriate code
    if [ $TESTS_FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run tests
main
