#!/bin/bash
# Setup script for creating a virtual environment for instatools using uv
# This isolates instatools dependencies from your system Python packages

echo "🔧 Setting up virtual environment for instatools using uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed or not in PATH"
    echo ""
    echo "Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  # Or visit: https://github.com/astral-sh/uv"
    exit 1
fi

echo "✅ Found uv: $(uv --version)"

# Create virtual environment using uv (creates .venv by default)
echo "📦 Creating virtual environment..."
uv venv

# Install dependencies using uv
echo "📥 Installing dependencies..."
uv pip install -e .

echo "✅ Virtual environment setup complete!"
echo ""
echo "The virtual environment is located at: .venv/"
echo ""
echo "To use the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "Or use uv run to execute commands in the venv:"
echo "  uv run python followers_extractor.py ..."
echo ""
echo "To deactivate:"
echo "  deactivate"
