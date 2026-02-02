# Installation Troubleshooting Guide

## Quick Fix: Python 3.14 Compatibility Issue

### The Problem
If you see this error when running `make install`:

```
ERROR: Failed building wheel for cffi
error: command '/usr/bin/clang' failed with exit code 1
```

**Cause:** Python 3.14 is too new for the `cffi` package (used by mitmproxy).

### The Solution

#### Option 1: Automated Setup (Easiest)

```bash
./scripts/setup-python-env.sh
source venv/bin/activate
make install
```

This script will:
1. Find a compatible Python version (3.11, 3.12, or 3.13)
2. Create a virtual environment
3. Guide you through activation

#### Option 2: Manual Setup with Python 3.12

```bash
# Install Python 3.12 if not already installed
brew install python@3.12

# Create virtual environment
python3.12 -m venv venv

# Activate it
source venv/bin/activate

# Verify version
python --version  # Should show 3.12.x

# Install dependencies
make install
```

#### Option 3: Use Docker (Recommended for Development)

Skip Python version issues entirely:

```bash
docker-compose up -d --build
```

All development happens inside the container with the correct Python version.

### Verification

After installation, verify everything works:

```bash
# Check mitmproxy installed correctly
python -c "import mitmproxy; print(mitmproxy.__version__)"

# Run tests
make test
```

### Platform-Specific Notes

#### macOS (Homebrew)
```bash
# List available Python versions
brew search python

# Install specific version
brew install python@3.12

# Use that version
python3.12 -m venv venv
```

####