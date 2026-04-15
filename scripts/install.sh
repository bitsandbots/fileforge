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
        version=$("$candidate" -c 'import sys; print(sys.version_info[:2])')
        major=$("$candidate" -c 'import sys; print(sys.version_info.major)')
        minor=$("$candidate" -c 'import sys; print(sys.version_info.minor)')
        if [[ "$major" -ge 3 && "$minor" -ge 11 ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    fail "Python 3.11 or newer is required. Found: $("python3" --version 2>/dev/null || echo 'none'). Install from https://python.org"
fi

PYTHON_VERSION=$("$PYTHON" --version)
success "Found $PYTHON_VERSION ($PYTHON)"

# ── pip check ─────────────────────────────────────────────────────────────────
info "Checking pip..."

if ! "$PYTHON" -m pip --version &>/dev/null; then
    fail "pip is not available for $PYTHON. Install it with: $PYTHON -m ensurepip --upgrade"
fi

PIP_VERSION=$("$PYTHON" -m pip --version | awk '{print $1, $2}')
success "Found $PIP_VERSION"

# ── Install in editable mode with dev deps ────────────────────────────────────
info "Installing FileForge in editable mode with dev dependencies..."

"$PYTHON" -m pip install -e ".[dev]"

success "FileForge installed"

# ── Ollama check ──────────────────────────────────────────────────────────────
info "Checking Ollama..."

OLLAMA_RUNNING=false
if command -v ollama &>/dev/null; then
    if ollama list &>/dev/null 2>&1; then
        OLLAMA_RUNNING=true
        success "Ollama is running"
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
    printf "  3. Pull a model:    ollama pull llama3\n"
    printf "  FileForge will work without Ollama for non-AI operations,\n"
    printf "  but AI-assisted classification requires a running Ollama instance.\n"
    printf "\n"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
printf "\n"
success "Installation complete."
printf "\n"
printf "  ${BOLD}Quick start:${RESET}\n"
printf "    fileforge --help\n"
printf "    fileforge scan ~/Downloads --dry-run\n"
printf "\n"
printf "  ${BOLD}Run tests:${RESET}\n"
printf "    python -m pytest -q\n"
printf "\n"
