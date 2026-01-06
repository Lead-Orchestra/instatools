# PowerShell script for setting up virtual environment on Windows using uv
# This isolates instatools dependencies from your system Python packages

Write-Host "🔧 Setting up virtual environment for instatools using uv..." -ForegroundColor Cyan

# Check if uv is installed
try {
    $uvVersion = uv --version 2>&1
    Write-Host "✅ Found uv: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: uv is not installed or not in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install uv first:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
    Write-Host "  # Or visit: https://github.com/astral-sh/uv"
    exit 1
}

# Create virtual environment using uv (creates .venv by default)
Write-Host "📦 Creating virtual environment..." -ForegroundColor Cyan
uv venv

# Install dependencies using uv
Write-Host "📥 Installing dependencies..." -ForegroundColor Cyan
uv pip install -e .

Write-Host "✅ Virtual environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "The virtual environment is located at: .venv\" -ForegroundColor Yellow
Write-Host ""
Write-Host "To use the virtual environment:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Or use uv run to execute commands in the venv:" -ForegroundColor Yellow
Write-Host "  uv run python followers_extractor.py ..."
Write-Host ""
Write-Host "To deactivate:" -ForegroundColor Yellow
Write-Host "  deactivate"
