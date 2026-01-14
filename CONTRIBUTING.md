# Contributing to CloakCode

First off, thank you for considering contributing to CloakCode! It's people like you that make CloakCode such a great tool for secure credential management.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Testing](#testing)
- [Adding New Strategies](#adding-new-strategies)

---

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

### Our Standards

- **Be respectful** and considerate in your communication
- **Be collaborative** and help others learn
- **Be patient** with questions and feedback
- **Focus on what is best** for the community
- **Show empathy** towards other community members

---

## Getting Started

### Prerequisites

- Docker 20.0+
- Docker Compose v2+
- Python 3.9+ (for local testing)
- Git

### Quick Setup

```bash
# Fork and clone the repository
git clone git@github.com:YOUR_USERNAME/cloak-code.git
cd cloak-code

# Create a feature branch
git checkout -b feature/your-feature-name

# Install development dependencies
pip install -r requirements-dev.txt

# Setup environment
make setup

# Run tests
make test
```

---

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

**Bug Report Template:**

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Configure '...'
2. Run command '...'
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
 - OS: [e.g. macOS 13.0]
 - Docker version: [e.g. 24.0.0]
 - CloakCode version: [e.g. v2.0.0]

**Logs**
Paste relevant logs here.

**Additional context**
Any other context about the problem.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List any potential drawbacks** or security implications

### Your First Code Contribution

Unsure where to begin? Look for issues labeled:

- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `documentation` - Documentation improvements

---

## Development Setup

### 1. Local Development Environment

```bash
# Install development tools
pip install -r requirements-dev.txt

# Setup pre-commit hooks (optional but recommended)
pre-commit install
```

### 2. Running CloakCode Locally

```bash
# Start services
make dev

# In another terminal, run tests
make test

# View logs
make logs
```

### 3. Project Structure

```
cloakcode/
├── proxy/              # Proxy service
│   ├── strategies/     # Authentication strategies
│   ├── inject.py       # Main injection logic
│   └── config.yaml     # Configuration
├── agent/              # Agent container
├── scripts/            # Helper scripts
├── tests/              # Test suite
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── security/      # Security tests
└── docs/              # Documentation
```

---

## Pull Request Process

### 1. Before Submitting

- [ ] Code follows the style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages are clear

### 2. Submitting a Pull Request

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to your fork: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### 3. PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran.

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where needed
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing unit tests pass locally
```

### 4. Review Process

- Maintainers will review your PR within 1-2 weeks
- Address any requested changes
- Once approved, a maintainer will merge your PR

---

## Style Guidelines

### Python Code Style

We follow [PEP 8](https://pep8.org/) with some modifications:

```python
# Good
class MyStrategy(InjectionStrategy):
    """Strategy for MyAPI authentication.
    
    This strategy handles Bearer token injection
    for MyAPI endpoints.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.token = self._get_credential('token')
    
    def detect(self, flow: http.HTTPFlow) -> bool:
        """Detect if this strategy should handle the request."""
        return 'DUMMY_MYAPI' in flow.request.headers.get('Authorization', '')
    
    def inject(self, flow: http.HTTPFlow) -> None:
        """Inject real credentials into the request."""
        flow.request.headers['Authorization'] = f'Bearer {self.token}'
        self.log_injection(flow)
```

**Key Points:**
- Use type hints
- Write docstrings for classes and public methods
- Maximum line length: 100 characters
- Use meaningful variable names
- Keep functions focused and small

### Shell Script Style

```bash
#!/bin/bash
# Script description

set -e  # Exit on error

# Use long-form flags for readability
docker-compose up --detach

# Quote variables
echo "Starting ${SERVICE_NAME}"

# Use functions for reusability
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "Docker not found"
        return 1
    fi
}
```

### YAML Style

```yaml
# Use 2-space indentation
strategies:
  - name: my-strategy
    type: bearer
    config:
      token: MY_TOKEN
      allowed_hosts:
        - "api.example.com"
        - "*.example.com"

# Use quotes for strings with special characters
rules:
  - name: my-rule
    domain_regex: "^api\\.example\\.com$"
    priority: 100
```

---

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run security tests
pytest tests/security/ -v

# Run with coverage
pytest --cov=proxy --cov-report=html
```

### Writing Tests

#### Unit Test Example

```python
def test_bearer_strategy_detection():
    """Test Bearer strategy detects dummy tokens."""
    strategy = BearerStrategy('test', {
        'token': 'REAL_TOKEN',
        'dummy_pattern': 'DUMMY_.*'
    })
    
    flow = create_mock_flow(
        headers={'Authorization': 'Bearer DUMMY_TOKEN'}
    )
    
    assert strategy.detect(flow) is True
```

#### Integration Test Example

```python
def test_end_to_end_injection():
    """Test complete credential injection flow."""
    # Start containers
    subprocess.run(['docker-compose', 'up', '-d'])
    
    # Make request with dummy credential
    response = requests.get(
        'https://api.example.com/data',
        headers={'Authorization': 'Bearer DUMMY_TOKEN'}
    )
    
    # Verify request succeeded (real token was injected)
    assert response.status_code == 200
```

---

## Adding New Strategies

Want to add support for a new API? Here's how:

### 1. Create Strategy Class

```python
# proxy/strategies/myapi.py
from .base import InjectionStrategy
from mitmproxy import http
from typing import Dict, Any

class MyAPIStrategy(InjectionStrategy):
    """Strategy for MyAPI authentication."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.api_key = self._get_credential('api_key')
        self.allowed_hosts = config.get('allowed_hosts', [])
    
    def detect(self, flow: http.HTTPFlow) -> bool:
        """Detect dummy API key in request."""
        # Check for dummy pattern in headers
        api_key_header = flow.request.headers.get('X-API-Key', '')
        return 'DUMMY_MYAPI' in api_key_header
    
    def inject(self, flow: http.HTTPFlow) -> None:
        """Inject real API key."""
        # Validate destination host
        if not self._validate_host(flow.request.pretty_host):
            raise SecurityError(f"Host not whitelisted: {flow.request.pretty_host}")
        
        # Inject real credential
        flow.request.headers['X-API-Key'] = self.api_key
        
        # Log the injection (without exposing real key)
        self.log_injection(flow)
```

### 2. Register Strategy

```python
# proxy/strategies/__init__.py
from .myapi import MyAPIStrategy

__all__ = [
    'InjectionStrategy',
    'BearerStrategy',
    'MyAPIStrategy',  # Add your strategy
    # ... others
]
```

### 3. Add to Injector

```python
# proxy/inject.py
STRATEGY_CLASSES = {
    "bearer": BearerStrategy,
    "myapi": MyAPIStrategy,  # Register type
    # ... others
}
```

### 4. Add Tests

```python
# tests/unit/test_myapi_strategy.py
def test_myapi_detection():
    """Test MyAPI strategy detects requests correctly."""
    strategy = MyAPIStrategy('myapi', {
        'api_key': 'REAL_API_KEY',
        'allowed_hosts': ['api.myapi.com']
    })
    
    flow = create_mock_flow(
        host='api.myapi.com',
        headers={'X-API-Key': 'DUMMY_MYAPI_KEY'}
    )
    
    assert strategy.detect(flow) is True

def test_myapi_injection():
    """Test MyAPI strategy injects credentials."""
    strategy = MyAPIStrategy('myapi', {
        'api_key': 'REAL_KEY',
        'allowed_hosts': ['api.myapi.com']
    })
    
    flow = create_mock_flow(
        host='api.myapi.com',
        headers={'X-API-Key': 'DUMMY_MYAPI_KEY'}
    })
    
    strategy.inject(flow)
    
    assert flow.request.headers['X-API-Key'] == 'REAL_KEY'
```

### 5. Document the Strategy

Add documentation to `docs/reference/strategies.md`:

```markdown
## MyAPI Strategy

### Configuration

```yaml
strategies:
  - name: myapi
    type: myapi
    config:
      api_key: MYAPI_KEY
      allowed_hosts:
        - "api.myapi.com"
```

### Usage

Use `DUMMY_MYAPI_KEY` in your application code.
```

---

## Documentation

### Writing Documentation

- Use clear, concise language
- Include code examples
- Add diagrams where helpful
- Keep it up-to-date with code changes

### Documentation Structure

```
docs/
├── getting-started/   # Installation and quick start
├── guides/           # How-to guides
├── reference/        # API reference
└── deployment/       # Deployment guides
```

---

## Release Process

Releases are managed by maintainers:

1. Version bump in relevant files
2. Update CHANGELOG.md
3. Create GitHub release with notes
4. Build and push Docker images
5. Announce on community channels

---

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bug reports**: Open a GitHub Issue
- **Security issues**: Email maintainers privately
- **Chat**: Join our community chat (link in README)

---

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project website (when available)

---

**Thank you for contributing to CloakCode! 🛡️**

Every contribution, no matter how small, makes a difference.
