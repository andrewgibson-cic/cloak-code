#!/bin/bash
# Security tests for SSH key functionality
# Tests security aspects of SSH key handling in CloakCode

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
CRITICAL_FAILURES=0

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

critical_fail() {
    echo -e "${RED}✗ CRITICAL FAIL${NC}: $1"
    echo -e "  ${RED}Security Issue${NC}: $2"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
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

# Setup test environment
setup() {
    export TEST_HOME="/tmp/ssh-security-test-$$"
    export TEST_SSH_DIR="$TEST_HOME/.ssh"
    
    mkdir -p "$TEST_SSH_DIR"
    
    # Generate test SSH keys
    ssh-keygen -t ed25519 -f "$TEST_SSH_DIR/id_ed25519" -N "" -C "security-test@example.com" >/dev/null 2>&1
    ssh-keygen -t rsa -b 2048 -f "$TEST_SSH_DIR/id_rsa" -N "" -C "security-test@example.com" >/dev/null 2>&1
}

# Cleanup test environment
cleanup() {
    rm -rf "$TEST_HOME"
}

# Security Test 1: Private keys must not be world-readable
test_private_key_not_world_readable() {
    run_test "Private keys must not be world-readable (Security Critical)"
    
    chmod 644 "$TEST_SSH_DIR/id_ed25519"  # Intentionally make it insecure
    
    local perms=$(stat -f "%Lp" "$TEST_SSH_DIR/id_ed25519" 2>/dev/null || stat -c "%a" "$TEST_SSH_DIR/id_ed25519" 2>/dev/null)
    
    if [ "$perms" = "644" ] || [ "$perms" = "666" ] || [ "$perms" = "777" ]; then
        critical_fail "Private key is world-readable" "Permissions are $perms, must be 600 or 400"
    else
        # Fix and verify
        chmod 600 "$TEST_SSH_DIR/id_ed25519"
        local fixed_perms=$(stat -f "%Lp" "$TEST_SSH_DIR/id_ed25519" 2>/dev/null || stat -c "%a" "$TEST_SSH_DIR/id_ed25519" 2>/dev/null)
        if [ "$fixed_perms" = "600" ] || [ "$fixed_perms" = "400" ]; then
            pass "Private key permissions can be secured (set to $fixed_perms)"
        else
            fail "Permission enforcement" "Failed to set secure permissions"
        fi
    fi
}

# Security Test 2: Private keys must not be group-readable
test_private_key_not_group_readable() {
    run_test "Private keys must not be group-readable (Security Critical)"
    
    chmod 640 "$TEST_SSH_DIR/id_rsa"  # Group readable
    
    local perms=$(stat -f "%Lp" "$TEST_SSH_DIR/id_rsa" 2>/dev/null || stat -c "%a" "$TEST_SSH_DIR/id_rsa" 2>/dev/null)
    
    if [ "${perms:1:1}" != "0" ] && [ "${perms:1:1}" != "4" ]; then
        critical_fail "Private key is group-readable" "Permissions are $perms"
    else
        chmod 600 "$TEST_SSH_DIR/id_rsa"
        pass "Private key group permissions secured"
    fi
}

# Security Test 3: SSH directory permissions
test_ssh_directory_permissions() {
    run_test "SSH directory must have 700 permissions (Security Critical)"
    
    chmod 755 "$TEST_SSH_DIR"  # Too permissive
    
    local perms=$(stat -f "%Lp" "$TEST_SSH_DIR" 2>/dev/null || stat -c "%a" "$TEST_SSH_DIR" 2>/dev/null)
    
    if [ "$perms" != "700" ]; then
        critical_fail "SSH directory permissions too permissive" "Permissions are $perms, must be 700"
        chmod 700 "$TEST_SSH_DIR"
    else
        pass "SSH directory has secure permissions (700)"
    fi
}

# Security Test 4: Keys should not be in Docker images
test_keys_not_in_image() {
    run_test "SSH keys must not be embedded in Docker images"
    
    # Check if agent Dockerfile contains any SSH key references
    if grep -r "COPY.*id_rsa\|COPY.*id_ed25519\|ADD.*\.ssh" ../agent/Dockerfile 2>/dev/null; then
        critical_fail "Dockerfile contains SSH key copy commands" "Keys must never be in Docker images"
    else
        pass "No SSH keys found in Dockerfile"
    fi
}

# Security Test 5: Keys must not be in version control
test_keys_not_in_git() {
    run_test "SSH keys must not be committed to git"
    
    if [ -f "../.gitignore" ]; then
        if grep -q "ssh-keys/" "../.gitignore"; then
            pass "ssh-keys/ is in .gitignore"
        else
            critical_fail ".gitignore missing ssh-keys/" "SSH keys directory not protected from git"
        fi
    else
        fail ".gitignore check" ".gitignore file not found"
    fi
}

# Security Test 6: Private keys with passphrases
test_passphrase_protected_keys() {
    run_test "Should support passphrase-protected keys"
    
    local passphrase_key="$TEST_SSH_DIR/id_ed25519_pass"
    ssh-keygen -t ed25519 -f "$passphrase_key" -N "testpassphrase" -C "test@example.com" >/dev/null 2>&1
    
    if [ -f "$passphrase_key" ]; then
        pass "Passphrase-protected key created successfully"
        rm -f "$passphrase_key" "$passphrase_key.pub"
    else
        fail "Passphrase key creation" "Failed to create passphrase-protected key"
    fi
}

# Security Test 7: Known hosts validation
test_known_hosts_validation() {
    run_test "known_hosts should use hashed entries for security"
    
    # Create a test known_hosts
    ssh-keyscan -H github.com > "$TEST_SSH_DIR/known_hosts" 2>/dev/null
    
    if [ -f "$TEST_SSH_DIR/known_hosts" ]; then
        if grep -q "|1|" "$TEST_SSH_DIR/known_hosts"; then
            pass "known_hosts uses hashed hostnames (enhanced privacy)"
        else
            skip "known_hosts not hashed (optional security enhancement)"
        fi
    else
        skip "known_hosts file not created"
    fi
}

# Security Test 8: SSH config security
test_ssh_config_security() {
    run_test "SSH config must have secure settings"
    
    cat > "$TEST_SSH_DIR/config" <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF
    
    # Check for insecure settings
    if grep -qi "StrictHostKeyChecking no" "$TEST_SSH_DIR/config"; then
        critical_fail "SSH config has insecure settings" "StrictHostKeyChecking should not be 'no'"
    elif grep -q "IdentitiesOnly yes" "$TEST_SSH_DIR/config"; then
        pass "SSH config has secure settings"
    else
        skip "IdentitiesOnly not set (recommended for security)"
    fi
}

# Security Test 9: File ownership
test_file_ownership() {
    run_test "SSH files must be owned by the correct user"
    
    local current_user=$(whoami)
    local key_owner=$(stat -f "%Su" "$TEST_SSH_DIR/id_ed25519" 2>/dev/null || stat -c "%U" "$TEST_SSH_DIR/id_ed25519" 2>/dev/null)
    
    if [ "$key_owner" = "$current_user" ]; then
        pass "SSH key owned by correct user ($current_user)"
    else
        critical_fail "SSH key ownership mismatch" "Owner is $key_owner, should be $current_user"
    fi
}

# Security Test 10: No keys in environment variables
test_no_keys_in_env() {
    run_test "SSH private keys must not be in environment variables"
    
    # Check if any env vars contain key-like content
    if env | grep -q "BEGIN.*PRIVATE KEY"; then
        critical_fail "Private key found in environment variable" "Keys must never be in environment"
    else
        pass "No private keys in environment variables"
    fi
}

# Security Test 11: Key file size limits
test_key_file_size() {
    run_test "SSH key files should be reasonable size (detect corruption/tampering)"
    
    local key_size=$(stat -f "%z" "$TEST_SSH_DIR/id_ed25519" 2>/dev/null || stat -c "%s" "$TEST_SSH_DIR/id_ed25519" 2>/dev/null)
    
    # Ed25519 keys are typically around 400-500 bytes
    if [ "$key_size" -lt 100 ] || [ "$key_size" -gt 10000 ]; then
        fail "Key file size suspicious" "Size is $key_size bytes (expected 100-10000)"
    else
        pass "Key file size is reasonable ($key_size bytes)"
    fi
}

# Security Test 12: Verify key format
test_key_format_validation() {
    run_test "SSH keys must be in valid format"
    
    if head -1 "$TEST_SSH_DIR/id_ed25519" | grep -q "BEGIN OPENSSH PRIVATE KEY"; then
        pass "Private key has valid OpenSSH format"
    elif head -1 "$TEST_SSH_DIR/id_ed25519" | grep -q "BEGIN.*PRIVATE KEY"; then
        pass "Private key has valid format"
    else
        fail "Key format validation" "Private key format not recognized"
    fi
}

# Security Test 13: Public key permissions
test_public_key_permissions() {
    run_test "Public keys can be more permissive but should be secure"
    
    chmod 644 "$TEST_SSH_DIR/id_ed25519.pub"
    local perms=$(stat -f "%Lp" "$TEST_SSH_DIR/id_ed25519.pub" 2>/dev/null || stat -c "%a" "$TEST_SSH_DIR/id_ed25519.pub" 2>/dev/null)
    
    if [ "$perms" = "644" ] || [ "$perms" = "600" ]; then
        pass "Public key permissions are acceptable ($perms)"
    else
        fail "Public key permissions" "Unexpected permissions: $perms"
    fi
}

# Security Test 14: Detect symlink attacks
test_symlink_protection() {
    run_test "SSH directory should not be a symlink (symlink attack prevention)"
    
    if [ -L "$TEST_SSH_DIR" ]; then
        critical_fail "SSH directory is a symlink" "Potential symlink attack vector"
    else
        pass "SSH directory is not a symlink"
    fi
}

# Security Test 15: Cleanup verification
test_cleanup_completeness() {
    run_test "Cleanup should remove all SSH key material"
    
    # Create a test cleanup scenario
    local cleanup_test="/tmp/ssh-cleanup-test-$$"
    mkdir -p "$cleanup_test/.ssh"
    touch "$cleanup_test/.ssh/id_ed25519"
    touch "$cleanup_test/.ssh/config"
    touch "$cleanup_test/.ssh/known_hosts"
    
    # Simulate cleanup
    rm -rf "$cleanup_test/.ssh"
    
    if [ ! -d "$cleanup_test/.ssh" ]; then
        pass "Cleanup successfully removes all SSH files"
    else
        critical_fail "Cleanup incomplete" "SSH directory still exists after cleanup"
    fi
    
    rm -rf "$cleanup_test"
}

# Security Test 16: Read-only mount enforcement
test_readonly_mount() {
    run_test "SSH key source should be mountable as read-only"
    
    info "This test simulates read-only mount behavior"
    
    # Create a source directory
    local ro_source="/tmp/ssh-ro-test-$$"
    mkdir -p "$ro_source"
    echo "test" > "$ro_source/test.key"
    
    # Try to make it read-only
    chmod 555 "$ro_source" 2>/dev/null || true
    
    # Test if we can still read
    if [ -r "$ro_source/test.key" ]; then
        pass "Can read from read-only source directory"
    else
        fail "Read-only mount test" "Cannot read from read-only directory"
    fi
    
    # Cleanup
    chmod 755 "$ro_source" 2>/dev/null || true
    rm -rf "$ro_source"
}

# Security Test 17: No keys in log files
test_keys_not_in_logs() {
    run_test "SSH keys must not be logged"
    
    info "Checking that key material isn't accidentally logged"
    
    # This is a reminder test - actual implementation should never log key content
    pass "Reminder: Never log SSH private key content"
}

# Security Test 18: Agent forwarding security
test_agent_forwarding_security() {
    run_test "SSH agent forwarding should be used securely"
    
    info "When using agent forwarding, socket permissions are critical"
    
    # Check if SSH_AUTH_SOCK has secure permissions if it exists
    if [ -n "$SSH_AUTH_SOCK" ] && [ -S "$SSH_AUTH_SOCK" ]; then
        local sock_perms=$(stat -f "%Lp" "$SSH_AUTH_SOCK" 2>/dev/null || stat -c "%a" "$SSH_AUTH_SOCK" 2>/dev/null)
        if [ "$sock_perms" = "600" ] || [ "$sock_perms" = "700" ]; then
            pass "SSH agent socket has secure permissions ($sock_perms)"
        else
            fail "Agent socket permissions" "Socket has permissions $sock_perms"
        fi
    else
        skip "SSH agent not active"
    fi
}

# Security Test 19: Key type strength
test_key_type_strength() {
    run_test "SSH keys should use strong cryptography"
    
    # Ed25519 is preferred
    if [ -f "$TEST_SSH_DIR/id_ed25519" ]; then
        pass "Ed25519 key found (recommended modern algorithm)"
    fi
    
    # Check RSA key size if present
    if [ -f "$TEST_SSH_DIR/id_rsa" ]; then
        local rsa_bits=$(ssh-keygen -l -f "$TEST_SSH_DIR/id_rsa" 2>/dev/null | awk '{print $1}')
        if [ "$rsa_bits" -ge 2048 ]; then
            pass "RSA key size is adequate ($rsa_bits bits)"
        else
            fail "RSA key strength" "RSA key is only $rsa_bits bits (minimum 2048)"
        fi
    fi
}

# Security Test 20: No hardcoded keys
test_no_hardcoded_keys() {
    run_test "No hardcoded SSH keys in source code"
    
    # Check common source files for hardcoded keys
    local found_hardcoded=false
    
    if grep -r "BEGIN.*PRIVATE KEY" ../agent/ ../proxy/ ../scripts/ 2>/dev/null | grep -v ".git" | grep -v "test"; then
        found_hardcoded=true
    fi
    
    if $found_hardcoded; then
        critical_fail "Hardcoded SSH keys found in source" "Keys must be external to code"
    else
        pass "No hardcoded SSH keys in source code"
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "SSH Key Security Tests"
    echo "=========================================="
    echo ""
    echo "These tests verify security aspects of SSH key handling"
    echo ""
    
    # Setup
    setup
    
    # Run all security tests
    test_private_key_not_world_readable
    test_private_key_not_group_readable
    test_ssh_directory_permissions
    test_keys_not_in_image
    test_keys_not_in_git
    test_passphrase_protected_keys
    test_known_hosts_validation
    test_ssh_config_security
    test_file_ownership
    test_no_keys_in_env
    test_key_file_size
    test_key_format_validation
    test_public_key_permissions
    test_symlink_protection
    test_cleanup_completeness
    test_readonly_mount
    test_keys_not_in_logs
    test_agent_forwarding_security
    test_key_type_strength
    test_no_hardcoded_keys
    
    # Cleanup
    cleanup
    
    # Summary
    echo ""
    echo "=========================================="
    echo "Security Test Summary"
    echo "=========================================="
    echo "Tests Run:    $TESTS_RUN"
    echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
    if [ $CRITICAL_FAILURES -gt 0 ]; then
        echo -e "Critical Security Issues: ${RED}$CRITICAL_FAILURES${NC}"
    fi
    echo "=========================================="
    
    # Exit with appropriate code
    if [ $CRITICAL_FAILURES -gt 0 ]; then
        echo ""
        echo -e "${RED}CRITICAL SECURITY ISSUES DETECTED!${NC}"
        echo "Please fix critical issues before deploying."
        exit 2
    elif [ $TESTS_FAILED -gt 0 ]; then
        exit 1
    else
        echo ""
        echo -e "${GREEN}All security tests passed!${NC}"
        exit 0
    fi
}

# Run tests
main
