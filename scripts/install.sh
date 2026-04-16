#!/usr/bin/env bash
# FileForge — Development Install Script
# Run from the project root: bash scripts/install.sh
# Note: chmod +x scripts/install.sh to make executable
set -euo pipefail

BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RESET='\033[0m'

info()    { printf "${BOLD}[install]${RESET} %s\n" "$*"; }
success() { printf "${GREEN}[ok]${RESET} %s\n" "$*"; }
warn()    { printf "${YELLOW}[warn]${RESET} %s\n" "$*"; }
fail()    { printf "${RED}[error]${RESET} %s\n" "$*" >&2; exit 1; }

# ── Python version check ──────────────────────────────────────────────────────
info "Checking Python version..."

PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        major=$("$candidate" -c 'import sys; print(sys.version_info.major)')
        minor=$("$candidate" -c 'import sys; print(sys.version_info.minor)')
        if [[ "$major" -ge 3 && "$minor" -ge 11 ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    fail "Python 3.11 or newer is required. Found: $(python3 --version 2>/dev/null || echo 'none'). Install from https://python.org"
fi

PYTHON_VERSION=$("$PYTHON" --version)
success "Found $PYTHON_VERSION ($PYTHON)"

# ── pip check ─────────────────────────────────────────────────────────────────
info "Checking pip..."

if ! "$PYTHON" -m pip --version &>/dev/null; then
    fail "pip is not available for $PYTHON. Install it with: $PYTHON -m ensurepip --upgrade"
fi

PIP_VERSION=$("$PYTHON" -m pip version | awk '{print $1, $2}')
success "Found $PIP_VERSION"

# ── Install in editable mode with dev deps ────────────────────────────────────
info "Installing FileForge in editable mode..."

"$PYTHON" -m pip install -e ".[dev]"

success "Core package installed"

# ── Optional extras ────────────────────────────────────────────────────────────
info "Checking optional extras..."

# ANN (approximate nearest neighbor for large datasets)
if "$PYTHON" -c "import hnswlib" 2>/dev/null; then
    success "hnswlib already installed (ANN support)"
else
    read -p "Install hnswlib for large-scale similarity search? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "$PYTHON" -m pip install "hnswlib>=0.8"
        success "hnswlib installed"
    fi
fi

# OCR support
if "$PYTHON" -c "import pytesseract" 2>/dev/null; then
    success "pytesseract already installed (OCR support)"
else
    read -p "Install pytesseract for image OCR? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "$PYTHON" -m pip install "pytesseract>=0.3"
        warn "Note: Tesseract binary must be installed separately"
        success "pytesseract installed"
    fi
fi

# ── Ollama check ──────────────────────────────────────────────────────────────
info "Checking Ollama..."

OLLAMA_RUNNING=false
if command -v ollama &>/dev/null; then
    if ollama list &>/dev/null 2>&1; then
        OLLAMA_RUNNING=true
        success "Ollama is running"

        # Check for required models
        if ! ollama list | grep -q "qwen3:4b"; then
            warn "qwen3:4b model not found"
            read -p "Pull qwen3:4b for classification? [Y/n] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                ollama pull qwen3:4b
            fi
        fi

        if ! ollama list | grep -q "nomic-embed-text"; then
            warn "nomic-embed-text model not found"
            read -p "Pull nomic-embed-text for embeddings? [Y/n] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                ollama pull nomic-embed-text
            fi
        fi
    else
        warn "Ollama is installed but not running"
    fi
else
    warn "Ollama is not installed"
fi

if [[ "$OLLAMA_RUNNING" == "false" ]]; then
    printf "\n"
    printf "${YELLOW}Ollama setup required:${RESET}\n"
    printf "  1. Install Ollama:  https://ollama.com/download\n"
    printf "  2. Start service:   ollama serve\n"
    printf "  3. Pull models:     ollama pull qwen3:4b\n"
    printf "                     ollama pull nomic-embed-text\n"
    printf "\n"
    printf "  FileForge will work without Ollama for non-AI operations,\n"
    printf "  but AI-assisted classification requires a running Ollama instance.\n"
    printf "\n"
fi

# ── Verify installation ───────────────────────────────────────────────────────
info "Verifying installation..."

if ! "$PYTHON" -c "import fileforge" 2>/dev/null; then
    fail "Import test failed. Check the installation."
fi

if ! "$PYTHON" -m fileforge --version &>/dev/null; then
    warn "CLI entry point not found in PATH"
fi

success "Import test passed"

# ── Run tests ─────────────────────────────────────────────────────────────────
read -p "Run test suite to verify? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    info "Running tests..."
    if "$PYTHON" -m pytest -q; then
        success "All tests passed"
    else
        warn "Some tests failed. Check the output above."
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
printf "\n"
success "Installation complete."
printf "\n"
printf "  ${BOLD}Quick start:${RESET}\n"
printf "    fileforge --help\n"
printf "    fileforge scan ~/Downloads --dry-run\n"
printf "\n"
printf "  ${BOLD}Documentation:${RESET}\n"
printf "    docs/overview.md    — Project overview\n"
printf "    docs/setup.md       — Detailed usage guide\n"
printf "    docs/architecture.md — System design\n"
printf "\n"
printf "  ${BOLD}Development:${RESET}\n"
printf "    python -m pytest -q    — Run tests\n"
printf "    bash scripts/check.sh  — Lint + format\n"
printf "\n"