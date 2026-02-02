# CloakCode Testing Guide

**Last Updated:** 2025-02-02  
**Test Coverage:** 90%+ for new code  
**Total Tests:** 90+  

## 📋 Overview

CloakCode has a comprehensive test suite covering unit tests, integration tests, security tests, and performance tests. This guide explains how to run tests, interpret results, and add new tests.

## 🧪 Test Categories

### 1. Unit Tests
**Location:** `tests/unit/`  
**Purpose:** Test individual components in isolation  
**Coverage:** 90%+ for new code  

#### Health Check Tests (`test_health_check.py`)
- **23 test cases** covering:
  - Basic health check functionality
  - Readiness probe (with/without injector)
  - Liveness probe
  - Statistics endpoint
  - Configuration validation
  - Credential checking (without exposing secrets)
  - Error handling
  - Concurrent health checks (50 simultaneous)

**Run:**
```bash
python3 tests/unit/test_health_check.py -v
```

#### Health Addon Tests (`test_health_addon.py`)
- **18 test cases** covering:
  - Addon initialization
  - Health endpoint routing
  - Request interception
  - Response generation (JSON format)
  - Error handling (404, 500)
  - Unknown endpoints
  - Concurrent requests (40 simultaneous)
  - Edge cases (empty data, large responses, special characters)

**Run:**
```bash
python3 tests/unit/test_health_addon.py -v
```

#### Strategy Tests (`test_v2_strategies.py`, `test_mistral_strategy.py`)
- Strategy pattern testing
- Credential injection verification
- Protocol-specific testing

**Run:**
```bash
python3 tests/unit/test_v2_strategies.py -v
python3 tests/unit/test_mistral_strategy.py -v
```

### 2. Integration Tests
**Location:** `tests/integration/`  
**Purpose:** Test component interactions and system behavior  

#### Control Script Tests (`test_control_script.sh`)
- **6 test cases** covering:
  - File existence and permissions
  - Help command functionality
  - Command listing verification
  - Invalid command handling
  - Validate command execution

**Run:**
```bash
bash tests/integration/test_control_script.sh
```

#### Agent Container Tests (`test_agent_container.py`)
- Container lifecycle testing
- Volume mounting verification
- Environment variable handling

**Run:**
```bash
python3 tests/integration/test_agent_container.py
```

### 3. Security Tests
**Location:** `tests/security/`  
**Purpose:** Verify security properties and attack resistance  

#### Attack Scenario Tests (`test_attack_scenarios.py`)
- Credential leakage prevention
- Telemetry blocking
- Injection attack resistance
- Authorization bypass prevention

**Run:**
```bash
python3 tests/security/test_attack_scenarios.py
```

### 4. Performance Tests
**Purpose:** Validate performance characteristics  

- Health check response time (< 100ms)
- Concurrent request handling (50+ simultaneous)
- Large payload handling (10KB+)
- Memory leak detection

## 🚀 Running Tests

### Quick Test (All Unit Tests)
```bash
# Run all unit tests
python3 -m pytest tests/unit/ -v

# Or with unittest
python3 tests/unit/test_health_check.py
python3 tests/unit/test_health_addon.py
```

### Run Specific Test Suite
```bash
# Health check tests only
python3 tests/unit/test_health_check.py -v

# Health addon tests only
python3 tests/unit/test_health_addon.py -v

# Integration tests
bash tests/integration/test_control_script.sh
```

### Run with Coverage
```bash
# Install pytest-cov if needed
pip install pytest pytest-cov

# Run with coverage report
pytest tests/unit/ --cov=proxy --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

### Run All Tests
```bash
# Use the test runner script
bash tests/run_tests.sh

# Or manually run all test suites
python3 tests/unit/test_health_check.py
python3 tests/unit/test_health_addon.py
python3 tests/unit/test_v2_strategies.py
bash tests/integration/test_control_script.sh
python3 tests/security/test_attack_scenarios.py
```

## 📊 Test Results Interpretation

### Successful Test Run
```
test_check_basic (test_health_check.TestHealthChecker) ... ok
test_check_live (test_health_check.TestHealthChecker) ... ok
test_check_ready_with_injector (test_health_check.TestHealthChecker) ... ok
...
----------------------------------------------------------------------
Ran 23 tests in 0.234s

OK
```

### Failed Test Example
```
FAIL: test_check_ready_without_injector (test_health_check.TestHealthChecker)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "test_health_check.py", line 67, in test_check_ready_without_injector
    self.assertEqual(status, 503)
AssertionError: 200 != 503
```

### Coverage Report
```
Name                    Stmts   Miss  Cover
-------------------------------------------
proxy/health_check.py     120      8    93%
proxy/health_addon.py      56      3    95%
-------------------------------------------
TOTAL                     176     11    94%
```

## 🔧 Writing New Tests

### Unit Test Template
```python
import unittest
from unittest.mock import Mock, patch

class TestNewFeature(unittest.TestCase):
    """Test suite for new feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.instance = NewFeature()
    
    def test_basic_functionality(self):
        """Test basic functionality works."""
        result = self.instance.do_something()
        self.assertEqual(result, expected_value)
    
    def test_error_handling(self):
        """Test error handling."""
        with self.assertRaises(ValueError):
            self.instance.do_something_invalid()
    
    def tearDown(self):
        """Clean up after tests."""
        pass

if __name__ == '__main__':
    unittest.main(verbosity=2)
```

### Integration Test Template
```bash
#!/bin/bash
# Integration test for new feature

set -e

test_feature_works() {
    if ./command_to_test; then
        echo "✓ Feature works"
    else
        echo "✗ Feature failed"
        exit 1
    fi
}

# Run tests
test_feature_works
```

## 📝 Test Best Practices

### 1. Test Naming
- Use descriptive names: `test_check_ready_with_injector`
- Follow pattern: `test_<what>_<when>_<expected>`
- Be specific about what's being tested

### 2. Test Structure
- **Arrange:** Set up test conditions
- **Act:** Execute the code being tested
- **Assert:** Verify expected behavior

### 3. Test Independence
- Tests should not depend on each other
- Use `setUp()` and `tearDown()` for fixtures
- Clean up resources after tests

### 4. Mock External Dependencies
- Use `unittest.mock` for external services
- Mock file I/O, network calls, database access
- Isolate unit under test

### 5. Test Edge Cases
- Empty inputs
- Large inputs
- Invalid inputs
- Boundary conditions
- Concurrent access

## 🐛 Debugging Failed Tests

### 1. Run with Verbose Output
```bash
python3 tests/unit/test_health_check.py -v
```

### 2. Run Single Test
```bash
python3 -m pytest tests/unit/test_health_check.py::TestHealthChecker::test_check_basic -v
```

### 3. Add Debug Output
```python
def test_something(self):
    result = function_under_test()
    print(f"DEBUG: result = {result}")  # Temporary debug
    self.assertEqual(result, expected)
```

### 4. Use Python Debugger
```python
def test_something(self):
    import pdb; pdb.set_trace()  # Breakpoint
    result = function_under_test()
    self.assertEqual(result, expected)
```

## 📈 Test Coverage Goals

### Current Coverage
- **Health Check Module:** 93%
- **Health Addon:** 95%
- **Overall New Code:** 90%+

### Target Coverage
- **Critical Paths:** 100%
- **Error Handlers:** 100%
- **Business Logic:** 95%+
- **Overall:** 80%+

## 🔄 Continuous Integration

### Pre-commit Checks
```bash
# Run before committing
./tests/run_tests.sh

# Or use git pre-commit hook
cp tests/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### CI/CD Pipeline (Future)
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          python3 -m pytest tests/unit/ -v
          bash tests/integration/test_control_script.sh
```

## 📚 Test Resources

### Documentation
- **Unit Tests:** `tests/unit/test_*.py`
- **Integration Tests:** `tests/integration/test_*.sh`
- **Security Tests:** `tests/security/test_*.py`
- **This Guide:** `docs/TESTING.md`

### Tools
- **unittest:** Python built-in testing framework
- **pytest:** Advanced testing framework (optional)
- **mock:** Mocking library (`unittest.mock`)
- **coverage:** Code coverage tool

### References
- [Python unittest docs](https://docs.python.org/3/library/unittest.html)
- [pytest documentation](https://docs.pytest.org/)
- [Mock object library](https://docs.python.org/3/library/unittest.mock.html)

## 🎯 Test Checklist for New Features

When adding a new feature:

- [ ] Write unit tests for new code
- [ ] Test happy path (normal operation)
- [ ] Test error conditions
- [ ] Test edge cases
- [ ] Test concurrent access (if applicable)
- [ ] Add integration test (if needed)
- [ ] Update this TESTING.md document
- [ ] Run all tests before committing
- [ ] Verify coverage meets target (90%+)

## 💡 Tips & Tricks

### Fast Test Development
```bash
# Run specific test class
python3 -m pytest tests/unit/test_health_check.py::TestHealthChecker -v

# Run tests matching pattern
python3 -m pytest tests/unit/ -k "test_check" -v

# Stop on first failure
python3 -m pytest tests/unit/ -x
```

### Test Fixtures
```python
@classmethod
def setUpClass(cls):
    """Run once before all tests in class."""
    cls.shared_resource = expensive_setup()

def setUp(self):
    """Run before each test."""
    self.instance = NewFeature()
```

### Parametrized Tests
```python
import pytest

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert double(input) == expected
```

---

**Questions?** Check `docs/CONTRIBUTING.md` or open an issue on GitHub.

**Last Updated:** 2025-02-02  
**Test Count:** 90+  
**Coverage:** 90%+