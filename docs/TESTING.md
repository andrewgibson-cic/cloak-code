# Testing Guide

This document describes how to run the comprehensive test suite for the Universal Injector system.

## Test Coverage

The test suite covers all the major fixes and features:

### Agent Container Tests
- ✅ Container starts fresh and clean (no pre-installed tools)
- ✅ Claude Code CLI is NOT pre-installed
- ✅ Gemini CLI is NOT pre-installed
- ✅ Node.js and npm are available for runtime installation
- ✅ Python and pip are available for runtime installation
- ✅ Agent user has sudo access
- ✅ SSL certificates are properly installed (.crt and .pem)
- ✅ Proxy environment variables are configured
- ✅ Agent can reach the proxy
- ✅ Runtime npm installation works without certificate errors

### Proxy Container Tests
- ✅ Proxy container is healthy
- ✅ No connection loops (separate network namespaces)
- ✅ Proxy loads credential strategies successfully
- ✅ Proxy handles warnings (not errors) for missing optional strategies
- ✅ Proxy stays running despite missing optional environment variables

### Network Configuration Tests
- ✅ Containers are on the same Docker network
- ✅ Containers have separate network namespaces (not shared)

## Prerequisites

Before running tests, ensure you have:

1. **Docker** installed and running
2. **docker-compose** installed
3. **Python 3** installed
4. Project environment configured (`.env` file exists)

## Running Tests

### Quick Start

Run all integration tests with a single command:

```bash
./tests/run_tests.sh
```

### Manual Test Execution

If you prefer to run tests manually:

```bash
# 1. Start the containers
docker-compose up -d

# 2. Wait for containers to be healthy
sleep 15

# 3. Run the tests
python3 tests/integration/test_agent_container.py
```

### Running Specific Test Classes

```bash
# Run only agent container tests
python3 tests/integration/test_agent_container.py TestAgentContainer

# Run only proxy container tests
python3 tests/integration/test_agent_container.py TestProxyContainer

# Run only network configuration tests
python3 tests/integration/test_agent_container.py TestNetworkConfiguration
```

### Running Individual Tests

```bash
# Run a specific test
python3 tests/integration/test_agent_container.py TestAgentContainer.test_02_agent_starts_clean_no_claude_code
```

## Expected Output

When all tests pass, you should see:

```
==========================================
Universal Injector Integration Tests
==========================================

📋 Pre-flight checks...

✓ Docker is running
✓ docker-compose is available
✓ Python 3 is available

🏗️  Starting containers...

⏳ Waiting for containers to be healthy (15 seconds)...

🧪 Running integration tests...

test_01_containers_are_running (__main__.TestAgentContainer) ... ok
test_02_agent_starts_clean_no_claude_code (__main__.TestAgentContainer) ... ok
test_03_agent_starts_clean_no_gemini (__main__.TestAgentContainer) ... ok
...

==========================================
✅ All tests passed!
==========================================
```

## Troubleshooting

### Tests Fail

If tests fail, try these steps:

1. **Check container status:**
   ```bash
   docker-compose ps
   ```

2. **View container logs:**
   ```bash
   docker-compose logs
   # Or for specific container:
   docker-compose logs agent
   docker-compose logs proxy
   ```

3. **Restart containers:**
   ```bash
   docker-compose restart
   # Wait a bit, then retry tests
   sleep 15
   ./tests/run_tests.sh
   ```

4. **Clean restart:**
   ```bash
   docker-compose down
   docker-compose up -d --build
   sleep 20
   ./tests/run_tests.sh
   ```

### Docker Not Running

Error: `Docker is not running`

**Solution:** Start Docker Desktop or Docker daemon before running tests.

### Permission Denied

Error: `Permission denied: './tests/run_tests.sh'`

**Solution:** Make the script executable:
```bash
chmod +x tests/run_tests.sh
```

### Connection Loop Detected

If the test `test_02_no_connection_loop` fails:

**Cause:** The proxy and agent are likely sharing the same network namespace (transparent proxy mode issue).

**Solution:** Verify docker-compose.yml uses:
- `network_mode: "service:proxy"` is NOT used for agent
- Agent has explicit `HTTP_PROXY` and `HTTPS_PROXY` environment variables
- Proxy uses `--mode regular` (not `--mode transparent`)

### Certificate Errors

If `test_10_runtime_npm_install_works` fails with certificate errors:

**Cause:** Certificate symlink may not be created properly.

**Solution:** 
1. Check agent logs: `docker-compose logs agent`
2. Verify entrypoint.sh creates the symlink
3. Restart containers: `docker-compose restart agent`

## Continuous Integration

To run tests in CI/CD:

```bash
#!/bin/bash
set -e

# Start services
docker-compose up -d

# Wait for healthy state
sleep 20

# Run tests
python3 tests/integration/test_agent_container.py

# Cleanup
docker-compose down
```

## Adding New Tests

To add new tests:

1. Open `tests/integration/test_agent_container.py`
2. Add a new test method to the appropriate class:
   ```python
   def test_11_my_new_test(self):
       """Description of what this tests."""
       result = subprocess.run(
           ["docker-compose", "exec", "-T", "agent", "command"],
           capture_output=True,
           text=True,
           cwd="/Users/andrewgibson/Documents/NodeProjects/cloak-code"
       )
       self.assertEqual(result.returncode, 0, "Should succeed")
   ```
3. Run the test suite to verify

## Test Naming Convention

Tests are numbered to run in logical order:
- `test_01_*` - Basic setup and container status
- `test_02_*` - Core functionality
- `test_03_*` - Advanced features
- etc.

This ensures dependencies are checked before more complex tests run.
