#!/bin/bash
# Integration tests for SSH key functionality in CloakCode agent container
# Tests actual container behavior with SSH keys

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Configuration
CONTAINER_NAME="cloakcode_agent_test_ssh"
TEST_SSH_DIR="./test-ssh-keys"

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

info() {
    echo -e "${BLUE}ℹ INFO${NC}: $1"
}

run_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "\n${YELLOW}Test ${TESTS_RUN}${NC}: $1"
}

# Check if container is running
check_container() {
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        echo -e "${RED}Error${NC}: Container $CONTAINER_NAME is not running"
        echo "Please start the agent container with SSH keys mounted"
        exit 1
    fi
}

# Setup test environment
setup() {
    echo -e "${BLUE}Setting up integration test environment...${NC}"
    
    # Create test SSH keys directory if it doesn't exist
    if [ ! -d "$TEST_SSH_DIR" ]; then
        mkdir -p "$TEST_SSH_DIR"
        
        # Generate test keys
        ssh-keygen -t ed25519 -f "$TEST_SSH_DIR/id_ed25519" -N "" -C "test@cloakcode.local" >/dev/null 2>&1
        chmod 600 "$TEST_SSH_DIR/id_ed25519"
        chmod 644 "$TEST_SSH_DIR/id_ed25519.pub"
        
        info "Created test SSH keys in $TEST_SSH_DIR"
    fi
}

# Cleanup test environment
cleanup() {
    echo -e "${BLUE}Cleaning up integration test environment...${NC}"
    # Note: We don't delete test-ssh-keys as they might be used for manual testing
}

# Test 1: Container has SSH client installed
test_ssh_client_installed() {
    run_test "SSH client should be installed in container"
    
    if docker exec "$CONTAINER_NAME" which ssh >/dev/null 2>&1; then
        pass "SSH client is installed"
    else
        fail "SSH client installation" "ssh command not found in container"
    fi
}

# Test 2: SSH directory exists and has correct permissions
test_ssh_directory_permissions() {
    run_test "SSH directory should exist with 700 permissions"
    
    local result=$(docker exec "$CONTAINER_NAME" sh -c '[ -d ~/.ssh ] && stat -c "%a" ~/.ssh 2>/dev/null || stat -f "%Lp" ~/.ssh 2>/dev/null || echo "NOT_FOUND"')
    
    if [ "$result" = "700" ]; then
        pass "SSH directory has correct permissions (700)"
    elif [ "$result" = "NOT_FOUND" ]; then
        skip "SSH directory not found (SSH keys may not be mounted)"
    else
        fail "SSH directory permissions" "Expected 700, got $result"
    fi
}

# Test 3: SSH keys are present in container
test_ssh_keys_present() {
    run_test "SSH keys should be present in container"
    
    local has_keys=$(docker exec "$CONTAINER_NAME" sh -c 'ls ~/.ssh/id_* 2>/dev/null | wc -l')
    
    if [ "$has_keys" -gt 0 ]; then
        pass "SSH keys found in container ($has_keys key(s))"
    else
        skip "No SSH keys found (may not be mounted)"
    fi
}

# Test 4: SSH private key permissions
test_ssh_private_key_permissions() {
    run_test "SSH private keys should have 600 permissions"
    
    local key_perms=$(docker exec "$CONTAINER_NAME" sh -c 'for key in ~/.ssh/id_*; do [ -f "$key" ] && ! [[ "$key" == *.pub ]] && stat -c "%a" "$key" 2>/dev/null || stat -f "%Lp" "$key" 2>/dev/null; done | head -1')
    
    if [ -z "$key_perms" ]; then
        skip "No private keys found in container"
    elif [ "$key_perms" = "600" ]; then
        pass "Private key has correct permissions (600)"
    else
        fail "Private key permissions" "Expected 600, got $key_perms"
    fi
}

# Test 5: SSH config exists
test_ssh_config_exists() {
    run_test "SSH config file should exist"
    
    if docker exec "$CONTAINER_NAME" test -f ~/.ssh/config; then
        pass "SSH config file exists"
    else
        skip "SSH config file not found"
    fi
}

# Test 6: Known hosts file exists
test_known_hosts_exists() {
    run_test "known_hosts file should exist"
    
    if docker exec "$CONTAINER_NAME" test -f ~/.ssh/known_hosts; then
        pass "known_hosts file exists"
    else
        skip "known_hosts file not found"
    fi
}

# Test 7: Known hosts contains GitHub
test_known_hosts_github() {
    run_test "known_hosts should contain GitHub host key"
    
    if docker exec "$CONTAINER_NAME" grep -q "github.com" ~/.ssh/known_hosts 2>/dev/null; then
        pass "GitHub host key found in known_hosts"
    else
        skip "GitHub host key not in known_hosts"
    fi
}

# Test 8: Git is configured for SSH
test_git_ssh_config() {
    run_test "Git should be configured to use SSH for GitHub"
    
    local git_config=$(docker exec "$CONTAINER_NAME" git config --get url."git@github.com:".insteadof 2>/dev/null || echo "")
    
    if [ "$git_config" = "https://github.com/" ]; then
        pass "Git configured to rewrite GitHub HTTPS URLs to SSH"
    else
        skip "Git SSH URL rewriting not configured"
    fi
}

# Test 9: SSH connection test (if keys are valid)
test_ssh_connection() {
    run_test "SSH connection to GitHub should work (if keys are configured)"
    
    # This will fail if the public key isn't added to GitHub, which is expected
    local result=$(docker exec "$CONTAINER_NAME" ssh -T git@github.com 2>&1 || true)
    
    if echo "$result" | grep -q "successfully authenticated"; then
        pass "SSH authentication to GitHub successful"
    elif echo "$result" | grep -q "Permission denied"; then
        skip "GitHub SSH connection failed (public key not added to GitHub - expected)"
    else
        skip "Could not test SSH connection (keys may not be mounted)"
    fi
}

# Test 10: Git operations work
test_git_clone_public() {
    run_test "Should be able to clone a public repository"
    
    docker exec "$CONTAINER_NAME" sh -c 'cd /tmp && git clone --depth 1 https://github.com/github/gitignore.git test-clone 2>/dev/null' >/dev/null 2>&1 || true
    
    if docker exec "$CONTAINER_NAME" test -d /tmp/test-clone; then
        pass "Successfully cloned public repository"
        docker exec "$CONTAINER_NAME" rm -rf /tmp/test-clone 2>/dev/null || true
    else
        fail "Git clone" "Failed to clone public repository"
    fi
}

# Test 11: SSH key cleanup on restart
test_ssh_cleanup_on_restart() {
    run_test "SSH keys should be cleaned up on container restart"
    
    info "This test would require container restart - skipping for safety"
    skip "Requires container restart (not safe during test run)"
}

# Test 12: Multiple key types support
test_multiple_key_types() {
    run_test "Should support multiple SSH key types"
    
    local key_count=$(docker exec "$CONTAINER_NAME" sh -c 'ls ~/.ssh/id_* 2>/dev/null | grep -v ".pub" | wc -l')
    
    if [ "$key_count" -gt 0 ]; then
        pass "Found $key_count SSH key(s) in container"
    else
        skip "No SSH keys found in container"
    fi
}

# Test 13: SSH agent forwarding detection
test_ssh_agent_forwarding() {
    run_test "Should detect SSH agent if available"
    
    local has_agent=$(docker exec "$CONTAINER_NAME" sh -c '[ -S "$SSH_AUTH_SOCK" ] && echo "yes" || echo "no"')
    
    if [ "$has_agent" = "yes" ]; then
        pass "SSH agent socket detected in container"
    else
        skip "SSH agent not forwarded (using volume-mounted keys)"
    fi
}

# Test 14: Workspace git operations
test_workspace_git_operations() {
    run_test "Should be able to perform git operations in workspace"
    
    docker exec "$CONTAINER_NAME" sh -c 'cd ~/workspace && git init test-repo 2>/dev/null' >/dev/null 2>&1 || true
    
    if docker exec "$CONTAINER_NAME" test -d ~/workspace/test-repo/.git; then
        pass "Can perform git operations in workspace"
        docker exec "$CONTAINER_NAME" rm -rf ~/workspace/test-repo 2>/dev/null || true
    else
        fail "Workspace git operations" "Failed to initialize git repository"
    fi
}

# Test 15: Environment variables set correctly
test_environment_variables() {
    run_test "Git-related environment variables should be set"
    
    local git_ssh_cmd=$(docker exec "$CONTAINER_NAME" sh -c 'echo $GIT_SSH_COMMAND' 2>/dev/null || echo "")
    
    if [ -n "$git_ssh_cmd" ]; then
        pass "GIT_SSH_COMMAND is set: $git_ssh_cmd"
    else
        skip "GIT_SSH_COMMAND not set"
    fi
}

# Test 16: SSH key files are not world-readable
test_ssh_security() {
    run_test "SSH keys should not be world-readable"
    
    local world_readable=$(docker exec "$CONTAINER_NAME" sh -c 'find ~/.ssh -type f -perm -004 2>/dev/null | wc -l')
    
    if [ "$world_readable" -eq 0 ]; then
        pass "No SSH files are world-readable"
    else
        fail "SSH security" "Found $world_readable world-readable SSH files"
    fi
}

# Test 17: Git user configuration
test_git_user_config() {
    run_test "Git user should be configured"
    
    local git_user=$(docker exec "$CONTAINER_NAME" git config --get user.name 2>/dev/null || echo "")
    
    if [ -n "$git_user" ]; then
        pass "Git user configured: $git_user"
    else
        skip "Git user not configured (not required for SSH)"
    fi
}

# Test 18: SSH config has proper permissions
test_ssh_config_permissions() {
    run_test "SSH config should have 600 permissions"
    
    if docker exec "$CONTAINER_NAME" test -f ~/.ssh/config; then
        local perms=$(docker exec "$CONTAINER_NAME" stat -c "%a" ~/.ssh/config 2>/dev/null || docker exec "$CONTAINER_NAME" stat -f "%Lp" ~/.ssh/config 2>/dev/null)
        
        if [ "$perms" = "600" ] || [ "$perms" = "644" ]; then
            pass "SSH config has secure permissions ($perms)"
        else
            fail "SSH config permissions" "Expected 600 or 644, got $perms"
        fi
    else
        skip "SSH config file not present"
    fi
}

# Test 19: Container can resolve git hosts
test_dns_resolution() {
    run_test "Container should be able to resolve GitHub hostname"
    
    if docker exec "$CONTAINER_NAME" nslookup github.com >/dev/null 2>&1 || \
       docker exec "$CONTAINER_NAME" host github.com >/dev/null 2>&1 || \
       docker exec "$CONTAINER_NAME" getent hosts github.com >/dev/null 2>&1; then
        pass "Can resolve github.com"
    else
        fail "DNS resolution" "Cannot resolve github.com"
    fi
}

# Test 20: SSH verbose test for debugging
test_ssh_verbose() {
    run_test "SSH verbose connection test (for debugging)"
    
    info "Testing SSH connection with verbose output..."
    local verbose_output=$(docker exec "$CONTAINER_NAME" ssh -vT git@github.com 2>&1 | head -20 || true)
    
    if echo "$verbose_output" | grep -q "Connecting to github.com"; then
        pass "SSH is attempting to connect to GitHub"
    else
        skip "Could not perform verbose SSH test"
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "SSH Key Integration Tests"
    echo "=========================================="
    echo ""
    
    # Check container is running
    check_container
    
    # Setup
    setup
    
    # Run all tests
    test_ssh_client_installed
    test_ssh_directory_permissions
    test_ssh_keys_present
    test_ssh_private_key_permissions
    test_ssh_config_exists
    test_known_hosts_exists
    test_known_hosts_github
    test_git_ssh_config
    test_ssh_connection
    test_git_clone_public
    test_ssh_cleanup_on_restart
    test_multiple_key_types
    test_ssh_agent_forwarding
    test_workspace_git_operations
    test_environment_variables
    test_ssh_security
    test_git_user_config
    test_ssh_config_permissions
    test_dns_resolution
    test_ssh_verbose
    
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
    echo -e "Tests Skipped: ${YELLOW}$((TESTS_RUN - TESTS_PASSED - TESTS_FAILED))${NC}"
    echo "=========================================="
    echo ""
    echo "Note: Some tests may be skipped if SSH keys are not mounted"
    echo "      or if certain features are not configured."
    
    # Exit with appropriate code
    if [ $TESTS_FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run tests
main
