# InstaTools Setup Guide

## Dependency Conflict Resolution

InstaTools requires `pydantic==1.10.2`, which conflicts with packages that need `pydantic>=2.0`. 

**Solution: Use `uv` with a virtual environment** to isolate instatools dependencies.

## Why UV?

- ⚡ **Much faster** than pip (written in Rust)
- 🔒 **Automatic venv management** - no manual activation needed
- 📦 **Better dependency resolution** - handles conflicts automatically
- 🎯 **Modern standard** - uses `pyproject.toml` instead of `requirements.txt`

## Prerequisites

Install `uv` if you haven't already:

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/Mac:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or visit: https://github.com/astral-sh/uv

## Quick Setup

### Windows (PowerShell)

```powershell
# Navigate to instatools directory
cd submodules/instatools

# Run setup script (checks for uv and creates .venv)
.\setup-venv.ps1
```

### Linux/Mac

```bash
# Navigate to instatools directory
cd submodules/instatools

# Make setup script executable
chmod +x setup-venv.sh

# Run setup script (checks for uv and creates .venv)
./setup-venv.sh
```

### Manual Setup

```bash
cd submodules/instatools

# Create virtual environment (creates .venv by default)
uv venv

# Install dependencies from pyproject.toml
uv pip install -e .
```

## Create Session File

After setting up the virtual environment:

**Using UV (Recommended - no activation needed):**
```bash
cd submodules/instatools
uv run python cookies.py
```

**Or activate manually:**
```bash
cd submodules/instatools

# Activate virtual environment
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# Create session file (make sure you're logged into Instagram in Firefox)
python cookies.py
```

## Using the Scraper

The TypeScript wrapper (`src/scraper-instagram-followers.ts`) will automatically detect and use the virtual environment if it exists. It checks in this order:
1. `.venv/` (uv's default)
2. `venv/` (traditional)
3. System Python

You don't need to manually activate it when using the npm script:

```bash
# From project root
pnpm scrape:instagram:followers -u target_user -s session_file
```

## Running Python Scripts Directly

**With UV (Recommended):**
```bash
cd submodules/instatools
uv run python FollowersExtractor/followers_extractor.py -u target_user -s session_file
```

**With Manual Activation:**
```bash
cd submodules/instatools
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
python FollowersExtractor/followers_extractor.py -u target_user -s session_file
```

## Troubleshooting

### UV Not Found

If you get "uv is not installed" error:

1. Install uv (see Prerequisites above)
2. Make sure uv is in your PATH
3. Restart your terminal/PowerShell

### Virtual Environment Not Detected

If the TypeScript wrapper doesn't find the virtual environment, make sure:
1. The `.venv` folder exists in `submodules/instatools/`
2. The Python executable exists at:
   - Windows: `submodules/instatools/.venv/Scripts/python.exe`
   - Linux/Mac: `submodules/instatools/.venv/bin/python3`

### Still Getting Dependency Conflicts

If you installed packages system-wide and are getting conflicts:

1. **Option 1:** Use UV's isolated environment (recommended):
   ```bash
   cd submodules/instatools
   uv venv
   uv pip install -e .
   ```

2. **Option 2:** Uninstall conflicting packages:
   ```bash
   pip uninstall instagrapi instaloader pydantic
   # Then set up with uv as above
   ```

### Session File Issues

If you get "Login required" errors:
1. Make sure you're logged into Instagram in Firefox
2. Regenerate the session file:
   ```bash
   cd submodules/instatools
   uv run python cookies.py
   ```

## Notes

- The virtual environment (`.venv/`) is gitignored (see `.gitignore`)
- Session files (`*.session`) are also gitignored for security
- You only need to set up the virtual environment once
- The TypeScript wrapper handles activation automatically
- UV uses `pyproject.toml` instead of `requirements.txt` for dependency management

## Benefits of UV

- **Speed**: 10-100x faster than pip for package installation
- **Reliability**: Better dependency resolution and conflict handling
- **Simplicity**: No need to manually activate virtual environments when using `uv run`
- **Modern**: Uses `pyproject.toml` (PEP 517/518 standard)
