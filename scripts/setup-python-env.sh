#!/bin/bash
# Setup Python environment for CloakCode

set -e

echo "🔍 Detecting Python installations..."

# Check for Python 3.12 or 3.13
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    PYTHON_VERSION="3.12"
elif command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
    PYTHON_VERSION="3.13"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    PYTHON_VERSION="3.11"
else
    echo "❌ No compatible Python version found (need 3.11, 3.12, or 3.13)"
    echo ""
    echo "Install Python 3.12 with:"
    echo "  brew install python@3.12"
    exit 1
fi

echo "✅ Found compatible Python: $PYTHON_VERSION"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo ""
    echo "📦 Creating virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv venv
    
    echo ""
    echo "✅ Virtual environment created!"
    echo ""
    echo "To activate it, run:"
    echo "  source venv/bin/activate"
    echo ""
    echo "Then install dependencies with:"
    echo "  make install"
else
    echo ""
    echo "✅ Already in virtual environment: $VIRTUAL_ENV"
    echo ""
    echo "Installing dependencies..."
    make install
fi