#!/usr/bin/env python3
"""
Integration tests for the agent container.

Tests verify:
- Container starts without pre-installed tools
- UID handling works correctly
- Certificates are properly installed
- Runtime tool installation works
- Proxy connectivity is functional
"""

import subprocess
import time
import unittest


class TestAgentContainer(unittest.TestCase):
    """Test the agent container functionality."""

    @classmethod
    def setUpClass(cls):
        """Ensure containers are running before tests."""
        print("\n=== Setting up test environment ===")
        subprocess.run(["docker-compose", "up", "-d"], check=True, cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude")
        # Wait for containers to be healthy
        time.sleep(15)
        print("Containers started\n")

    def test_01_containers_are_running(self):
        """Verify both containers are running."""
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0, "docker-compose ps should succeed")
        self.assertIn("universal_injector_proxy", result.stdout)
        self.assertIn("universal_injector_agent", result.stdout)

    def test_02_agent_starts_clean_no_claude_code(self):
        """Verify Claude Code CLI is NOT pre-installed."""
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "which", "claude-code"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        # Should exit with non-zero (command not found)
        self.assertNotEqual(result.returncode, 0, "claude-code should not be pre-installed")

    def test_03_agent_starts_clean_no_gemini(self):
        """Verify Gemini CLI is NOT pre-installed."""
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "which", "gemini"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        # Should exit with non-zero (command not found)
        self.assertNotEqual(result.returncode, 0, "gemini should not be pre-installed")

    def test_04_agent_has_node_and_npm(self):
        """Verify Node.js and npm are available for runtime installation."""
        # Test node
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "node", "--version"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0, "node should be available")
        self.assertTrue(result.stdout.startswith("v"), "node version should start with 'v'")
        
        # Test npm
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "npm", "--version"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0, "npm should be available")

    def test_05_agent_has_python_and_pip(self):
        """Verify Python and pip are available for runtime installation."""
        # Test python
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "python3", "--version"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0, "python3 should be available")
        self.assertIn("Python", result.stdout, "python version should contain 'Python'")
        
        # Test pip
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "pip3", "--version"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0, "pip3 should be available")

    def test_06_agent_has_sudo_access(self):
        """Verify agent user has sudo access for installations."""
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "sudo", "-n", "echo", "test"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0, "sudo should work without password")
        self.assertIn("test", result.stdout)

    def test_07_certificate_files_exist(self):
        """Verify SSL certificates are properly installed."""
        # Check .crt file (system)
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "test", "-f", "/usr/local/share/ca-certificates/mitmproxy-ca-cert.crt"],
            capture_output=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0, "System certificate (.crt) should exist")
        
        # Check .pem file (Node.js)
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "test", "-f", "/usr/local/share/ca-certificates/mitmproxy-ca-cert.pem"],
            capture_output=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0, "Node.js certificate (.pem) should exist")

    def test_08_proxy_environment_variables_set(self):
        """Verify proxy environment variables are configured."""
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "env"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("HTTP_PROXY=http://proxy:8080", result.stdout)
        self.assertIn("HTTPS_PROXY=http://proxy:8080", result.stdout)

    def test_09_proxy_is_reachable(self):
        """Verify agent can reach the proxy."""
        # Use nc (netcat) to check if proxy port is reachable
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "nc", "-z", "-w5", "proxy", "8080"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertEqual(result.returncode, 0, "Proxy port should be reachable")

    def test_10_runtime_npm_install_works(self):
        """Verify npm can install packages at runtime (test with a tiny package)."""
        # Install a small test package with sudo (required for global install)
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "sudo", "npm", "install", "-g", "is-even"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude",
            timeout=60
        )
        self.assertEqual(result.returncode, 0, "npm install should succeed with sudo")
        self.assertNotIn("certificate", result.stderr.lower(), "Should not have certificate errors")
        
        # Verify it was installed
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "agent", "npm", "list", "-g", "is-even"],
            capture_output=True,
            text=True,
            cwd="/Users/andrewgibson/Documents/NodeProjects/safe-claude"
        )
        self.assertIn("is-even", result.stdout, "Package should be installed")


class TestProxyContainer(unittest.TestCase):
    """Test the proxy container functionality."""

    def test_01_proxy_is_healthy(self):
        """Verify proxy container is healthy."""
        result = subprocess.run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", "universal_injector_proxy"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("healthy", result.stdout.strip())

    def test_02_no_connection_loop(self):
        """Verify proxy is not stuck in a connection loop."""
        # Get recent logs
        result = subprocess.run(
            ["docker", "logs", "--tail", "100", "universal_injector_proxy"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Count disconnect messages - should not be excessive
        disconnect_count = result.stdout.count("client disconnect")
        
        # In regular mode, we shouldn't see massive disconnect loops
        # Allow some disconnects but not hundreds
        self.assertLess(disconnect_count, 50, 
                       f"Too many disconnects ({disconnect_count}), possible connection loop")

    def test_03_proxy_loads_strategies(self):
        """Verify proxy successfully loads credential strategies."""
        result = subprocess.run(
            ["docker", "logs", "universal_injector_proxy"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Loading v2 configuration", result.stdout)
        self.assertIn("Configuration loaded", result.stdout)

    def test_04_proxy_handles_warnings_not_errors(self):
        """Verify proxy logs warnings (not errors) for missing optional strategies."""
        result = subprocess.run(
            ["docker", "logs", "universal_injector_proxy"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        
        # Should have warnings about missing strategies
        self.assertIn("Failed to load strategy", result.stdout)
        
        # But proxy should still be running (not exited)
        ps_result = subprocess.run(
            ["docker", "ps", "--filter", "name=universal_injector_proxy", "--format", "{{.Status}}"],
            capture_output=True,
            text=True
        )
        self.assertIn("Up", ps_result.stdout, "Proxy should still be running despite warnings")


class TestNetworkConfiguration(unittest.TestCase):
    """Test network configuration and separation."""

    def test_01_containers_on_same_network(self):
        """Verify agent and proxy are on the same Docker network."""
        result = subprocess.run(
            ["docker", "network", "inspect", "safe-claude_injector_internal", "--format", "{{range .Containers}}{{.Name}} {{end}}"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("universal_injector_proxy", result.stdout)
        self.assertIn("universal_injector_agent", result.stdout)

    def test_02_containers_have_separate_network_namespaces(self):
        """Verify containers have separate network namespaces (not network_mode: service)."""
        # Check agent doesn't have network_mode: container
        result = subprocess.run(
            ["docker", "inspect", "--format={{.HostConfig.NetworkMode}}", "universal_injector_agent"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        # Should be on a network, not sharing namespace
        self.assertNotIn("container:", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
