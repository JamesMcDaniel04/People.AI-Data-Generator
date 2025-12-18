#!/bin/bash
# Development environment setup script

set -e  # Exit on error

echo "=================================================="
echo "People.ai Demo Generator - Development Setup"
echo "=================================================="

# Check Python version
echo ""
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo "❌ Error: Python 3.9 or higher is required"
    echo "   Found: Python $python_version"
    exit 1
fi
echo "✅ Python $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  venv already exists, skipping creation"
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install package
echo ""
echo "Installing demo-gen in development mode..."
pip install -e . --quiet
echo "✅ Package installed"

# Install dev dependencies
echo ""
read -p "Install development dependencies (pytest, black, ruff)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -e ".[dev]" --quiet
    echo "✅ Development dependencies installed"
fi

# Create config files if they don't exist
echo ""
echo "Setting up configuration files..."

if [ ! -f "demo.yaml" ]; then
    cp demo.example.yaml demo.yaml
    echo "✅ Created demo.yaml from example"
else
    echo "⚠️  demo.yaml already exists, skipping"
fi

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env from example"
    echo "⚠️  Remember to edit .env with your credentials!"
else
    echo "⚠️  .env already exists, skipping"
fi

# Create runs directory
mkdir -p runs
echo "✅ Created runs directory"

# Verify installation
echo ""
echo "Verifying installation..."
python3 verify_install.py

echo ""
echo "=================================================="
echo "Setup complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your Salesforce credentials"
echo "2. Edit demo.yaml with your configuration"
echo "3. Run: source venv/bin/activate"
echo "4. Test: demo-gen --help"
echo "5. Dry run: demo-gen dry-run -c demo.yaml"
echo ""
echo "For more information, see:"
echo "- README.md (full documentation)"
echo "- QUICKSTART.md (5-minute guide)"
echo "=================================================="
