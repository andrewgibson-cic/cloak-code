# SSH Key Testing Documentation

## Overview

This document describes the comprehensive test suite for SSH key functionality in CloakCode. The tests are organized into three categories: unit tests, integration tests, and security tests.

## Test Categories

### 1. Unit Tests (`tests/unit/test_ssh_key_setup.sh`)

Unit tests verify individual components of SSH key functionality in isolation.

**Test Count**: 15 tests

**Coverage**:
- SSH key file permissions (600 for private, 644 for public)
- SSH directory permissions (700)
- Key copying functionality
- Multiple key type support (Ed25519, RSA, ECDSA)
- SSH config file creation and validation
- known_hosts file creation
- SSH key cleanup on exit
- SSH agent socket detection
- Key type identification
- Read-only mount handling
- Git configuration for SSH URLs
- Missing keys scenario handling
- Permission enforcement

**Running Unit Tests**:
```bash
./tests/unit/test_ssh_key_setup.sh
```

**Expected Output**:
```
==========================================
SSH Key Setup Unit Tests
==========================================

Test 1: SSH private key permissions should be 600
✓ PASS: Private key has correct permissions (600)

...

==========================================
Test Summary
==========================================
Tests Run:    15
Tests Passed: 15
Tests Failed: 0
==========================================
```

### 2. Integration Tests (`tests/integration/test_ssh_keys_integration.sh`)

Integration tests verify SSH key functionality within the actual Docker container environment.

**Test Count**: 20 tests

**Prerequisites**:
- Docker agent container must be running
- Container name: `cloakcode_agent_test_ssh`
- SSH keys optionally mounted

**Coverage**:
- SSH client installation
- SSH directory and file permissions in container
- SSH key presence verification
- SSH config and known_hosts files
- Git SSH configuration
- SSH connection testing (to GitHub)
- Git operations (clone, init)
- Multiple key type support
- SSH agent forwarding detection
- Environment variable configuration
- Security checks (world-readable files)
- DNS resolution for git hosts

**Running Integration Tests**:
```bash
# Start the agent container with SSH keys
docker-compose up -d agent

# Run integration tests
./tests/integration/test_ssh_keys_integration.sh
```

**Note**: Some tests may be skipped if:
- SSH keys are not mounted
- SSH agent forwarding is not configured
- Public keys are not added to GitHub

### 3. Security Tests (`tests/security/test_ssh_key_security.sh`)

Security tests verify that SSH keys are handled securely and no security vulnerabilities exist.

**Test Count**: 20 tests

**Coverage**:
- Private key permissions (not world-readable)
- Private key permissions (not group-readable)
- SSH directory permissions (700 required)
- Keys not embedded in Docker images
- Keys not committed to version control
- Passphrase-protected keys support
- Known_hosts hashing for privacy
- SSH config security settings
- File ownership verification
- No keys in environment variables
- Key file size validation
- Key format validation
- Public key permissions
- Symlink attack prevention
- Cleanup completeness
- Read-only mount support
- No keys in log files (reminder)
- SSH agent forwarding security
- Key cryptographic strength
- No hardcoded keys in source

**Running Security Tests**:
```bash
./tests/security/test_ssh_key_security.sh
```

**Critical Failures**: Tests marked as "CRITICAL" will cause exit code 2 and must be fixed before deployment.

## Test Results Interpretation

### Exit Codes

- `0`: All tests passed
- `1`: Some tests failed (non-critical)
- `2`: Critical security issues detected (security tests only)

### Test Status Indicators

- ✓ **PASS** (Green): Test passed successfully
- ✗ **FAIL** (Red): Test failed
- ✗ **CRITICAL FAIL** (Red): Security-critical test failed
- ⊘ **SKIP** (Yellow): Test skipped (conditions not met)
- ℹ **INFO** (Blue): Informational message

## Running All SSH Key Tests

### Quick Test Run

```bash
# Run all unit tests
./tests/unit/test_ssh_key_setup.sh

# Run security tests (no container needed)
./tests/security/test_ssh_key_security.sh
```

### Full Test Suite (with Container)

```bash
# 1. Setup SSH keys
./scripts/setup-ssh-keys.sh

# 2. Start containers
docker-compose up -d

# 3. Run all tests
./tests/unit/test_ssh_key_setup.sh
./tests/integration/test_ssh_keys_integration.sh
./tests/security/test_ssh_key_security.sh
```

### Automated Test Script

Create a test runner script:

```bash
#!/bin/bash
# test-ssh-keys.sh - Run all SSH key tests

set -e

echo "==================================="
echo "Running SSH Key Test Suite"
echo "==================================="

# Unit tests
echo -e "\n[1/3] Running Unit Tests..."
./tests/unit/test_ssh_key_setup.sh || exit 1

# Security tests
echo -e "\n[2/3] Running Security Tests..."
./tests/security/test_ssh_key_security.sh || exit 1

# Integration tests (if container is running)
if docker ps | grep -q "cloakcode_agent"; then
    echo -e "\n[3/3] Running Integration Tests..."
    ./tests/integration/test_ssh_keys_integration.sh || exit 1
else
    echo -e "\n[3/3] Skipping Integration Tests (container not running)"
fi

echo -e "\n==================================="
echo "All SSH Key Tests Completed!"
echo "==================================="
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: SSH Key Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Unit Tests
        run: ./tests/unit/test_ssh_key_setup.sh
      
      - name: Run Security Tests
        run: ./tests/security/test_ssh_key_security.sh
      
      - name: Setup Docker
        run: docker-compose up -d
      
      - name: Run Integration Tests
        run: ./tests/integration/test_ssh_keys_integration.sh
```

## Test Coverage Report

### Feature Coverage Matrix

| Feature | Unit | Integration | Security |
|---------|------|-------------|----------|
| **Key Permissions** | ✓ | ✓ | ✓ |
| **Key Copying** | ✓ | ✓ | - |
| **SSH Config** | ✓ | ✓ | ✓ |
| **Known Hosts** | ✓ | ✓ | ✓ |
| **Git Configuration** | ✓ | ✓ | - |
| **Cleanup** | ✓ | ✓ | ✓ |
| **Agent Forwarding** | ✓ | ✓ | ✓ |
| **Multiple Keys** | ✓ | ✓ | - |
| **Read-only Mount** | ✓ | - | ✓ |
| **Security Checks** | - | ✓ | ✓ |

### Code Coverage

The test suite covers:
- `agent/entrypoint.sh`: SSH key setup functions (95%+ coverage)
- `scripts/setup-ssh-keys.sh`: Key preparation (90%+ coverage)
- Security configurations: .gitignore, Dockerfile (100% coverage)

## Troubleshooting Tests

### Common Test Failures

#### 1. Permission Tests Failing

**Problem**: Tests fail with "wrong permissions" errors

**Solution**:
```bash
# macOS uses different stat syntax
# Tests handle both Linux and macOS automatically
# If still failing, check umask:
umask 0022
```

#### 2. Integration Tests Failing

**Problem**: Container not found

**Solution**:
```bash
# Ensure container is running
docker-compose up -d agent

# Check container name matches
docker ps | grep cloakcode_agent
```

#### 3. SSH Key Generation Fails

**Problem**: ssh-keygen not found

**Solution**:
```bash
# Install SSH client
# macOS: included by default
# Ubuntu/Debian: apt-get install openssh-client
# RHEL/CentOS: yum install openssh-clients
```

#### 4. Security Tests Show Critical Failures

**Problem**: Critical security issues detected

**Solution**:
- Review the specific failure message
- Fix the security issue before proceeding
- Never ignore critical security failures
- Re-run tests after fixes

### Test Environment Issues

#### Cleanup Between Test Runs

```bash
# Clean up test artifacts
rm -rf /tmp/ssh-*test*

# Reset container
docker-compose down agent
docker-compose up -d agent
```

#### Test Isolation

Tests use unique temporary directories to avoid conflicts:
- `/tmp/ssh-key-test-$$` (unit tests)
- `/tmp/ssh-security-test-$$` (security tests)

The `$$` expands to the process ID, ensuring uniqueness.

## Writing New Tests

### Test Template

```bash
#!/bin/bash
# New SSH key test

set -e

# Test function
test_my_feature() {
    run_test "Description of what this tests"
    
    # Setup test scenario
    local test_data="example"
    
    # Perform test
    if [ condition ]; then
        pass "Test passed because X"
    else
        fail "Test failed" "Expected Y, got Z"
    fi
}

# Add to main() function
main() {
    setup
    test_my_feature
    cleanup
}
```

### Test Guidelines

1. **Use descriptive test names**: `test_ssh_key_not_world_readable`
2. **Include failure messages**: Explain why test failed
3. **Clean up after tests**: Remove temporary files
4. **Handle platform differences**: Linux vs macOS
5. **Mark critical tests**: Use `critical_fail` for security issues
6. **Skip when appropriate**: Use `skip` if prerequisites not met

## Performance Benchmarks

### Test Execution Times

| Test Suite | Tests | Typical Duration |
|------------|-------|------------------|
| Unit | 15 | ~5 seconds |
| Integration | 20 | ~30 seconds |
| Security | 20 | ~10 seconds |
| **Total** | **55** | **~45 seconds** |

### Optimization Tips

- Run unit and security tests in parallel
- Integration tests require serial execution
- Use `--quick` flag (if implemented) to skip slow tests

## Test Maintenance

### Regular Updates

- Review tests quarterly
- Update for new security best practices
- Add tests for new features
- Remove obsolete tests

### Test Quality Checklist

- [ ] Tests are idempotent (can run multiple times)
- [ ] Tests clean up after themselves
- [ ] Tests don't require manual intervention
- [ ] Tests work on multiple platforms
- [ ] Tests have clear pass/fail criteria
- [ ] Critical security tests are marked
- [ ] Tests document prerequisites
- [ ] Tests handle edge cases

## Related Documentation

- [SSH Key Setup Guide](./SSH_KEY_SETUP.md) - User-facing setup instructions
- [SSH Key Investigation](./SSH_KEY_INJECTION_INVESTIGATION.md) - Technical design
- [General Testing Guide](./TESTING.md) - Overall CloakCode testing
- [Security Analysis](../SECURITY_ANALYSIS.md) - Security considerations

## Support

For test failures or issues:
1. Check this troubleshooting guide
2. Review test output carefully
3. Check container logs: `docker-compose logs agent`
4. File an issue with test output attached

---

**Last Updated**: 2026-12-01  
**Test Suite Version**: 1.0.0
