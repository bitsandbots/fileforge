#!/usr/bin/env bash
# FileForge — Release Automation Script
# Usage: ./scripts/release.sh <version>  [--dry-run]
# Example: ./scripts/release.sh 0.2.0
# Note: chmod +x scripts/release.sh to make executable
set -euo pipefail

BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

info()    { printf "${BOLD}[release]${RESET} %s\n" "$*"; }
success() { printf "${GREEN}[ok]${RESET} %s\n" "$*"; }
warn()    { printf "${YELLOW}[warn]${RESET} %s\n" "$*"; }
fail()    { printf "${RED}[error]${RESET} %s\n" "$*" >&2; exit 1; }
step()    { printf "${CYAN}──>${RESET} %s\n" "$*"; }
dryrun()  { printf "${YELLOW}[dry-run]${RESET} would run: %s\n" "$*"; }

DRY_RUN=false
VERSION=""

# ── Argument parsing ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        -*) fail "Unknown flag: $arg" ;;
        *) VERSION="$arg" ;;
    esac
done

if [[ -z "$VERSION" ]]; then
    printf "Usage: %s <version> [--dry-run]\n" "$0" >&2
    printf "Example: %s 0.2.0\n" "$0" >&2
    exit 1
fi

# ── Semver validation ─────────────────────────────────────────────────────────
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    fail "Version '$VERSION' is not valid semver (expected X.Y.Z, e.g. 0.2.0)"
fi

info "Preparing release v${VERSION}${DRY_RUN:+ (dry-run)}"

# ── Locate project root ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

INIT_FILE="src/fileforge/__init__.py"
PYPROJECT_FILE="pyproject.toml"

# ── Check files exist ─────────────────────────────────────────────────────────
[[ -f "$INIT_FILE" ]]     || fail "Not found: $INIT_FILE"
[[ -f "$PYPROJECT_FILE" ]] || fail "Not found: $PYPROJECT_FILE"

# ── Check for uncommitted changes ─────────────────────────────────────────────
step "Checking for uncommitted changes..."
if [[ -n "$(git status --porcelain)" ]]; then
    fail "Uncommitted changes detected. Commit or stash them before releasing.\n$(git status --short)"
fi
success "Working tree is clean"

# ── Run tests ─────────────────────────────────────────────────────────────────
step "Running test suite..."
if [[ "$DRY_RUN" == "true" ]]; then
    dryrun "python -m pytest -q"
else
    if ! python -m pytest -q; then
        fail "Tests failed. Fix failing tests before releasing."
    fi
    success "All tests passed"
fi

# ── Show current version ──────────────────────────────────────────────────────
CURRENT_VERSION=$(grep -E '^__version__ = ' "$INIT_FILE" | sed 's/__version__ = "//;s/"//')
info "Current version: ${CURRENT_VERSION}  ->  ${VERSION}"

# ── Update __init__.py ────────────────────────────────────────────────────────
step "Updating $INIT_FILE..."
if [[ "$DRY_RUN" == "true" ]]; then
    dryrun "sed -i 's/__version__ = \"${CURRENT_VERSION}\"/__version__ = \"${VERSION}\"/' $INIT_FILE"
else
    if ! grep -q '__version__' "$INIT_FILE"; then
        fail "__version__ not found in $INIT_FILE"
    fi
    sed -i "s/__version__ = \"${CURRENT_VERSION}\"/__version__ = \"${VERSION}\"/" "$INIT_FILE"
    success "Updated $INIT_FILE"
fi

# ── Update pyproject.toml ─────────────────────────────────────────────────────
step "Updating $PYPROJECT_FILE..."
if [[ "$DRY_RUN" == "true" ]]; then
    dryrun "sed -i 's/^version = \"${CURRENT_VERSION}\"/version = \"${VERSION}\"/' $PYPROJECT_FILE"
else
    if ! grep -q "^version = \"${CURRENT_VERSION}\"" "$PYPROJECT_FILE"; then
        fail "version = \"${CURRENT_VERSION}\" not found in $PYPROJECT_FILE. Check file manually."
    fi
    sed -i "s/^version = \"${CURRENT_VERSION}\"/version = \"${VERSION}\"/" "$PYPROJECT_FILE"
    success "Updated $PYPROJECT_FILE"
fi

# ── Build package ─────────────────────────────────────────────────────────────
step "Building package..."
if [[ "$DRY_RUN" == "true" ]]; then
    dryrun "python -m build"
else
    if ! python -m build --version &>/dev/null 2>&1; then
        warn "build package not found. Installing..."
        pip install build -q
    fi
    python -m build
    success "Package built in dist/"
fi

# ── Git commit ────────────────────────────────────────────────────────────────
step "Creating release commit..."
COMMIT_MSG="chore: bump version to ${VERSION}"
if [[ "$DRY_RUN" == "true" ]]; then
    dryrun "git add ${INIT_FILE} ${PYPROJECT_FILE}"
    dryrun "git commit -m \"${COMMIT_MSG}\""
else
    git add "${INIT_FILE}" "${PYPROJECT_FILE}"
    git commit -m "${COMMIT_MSG}"
    success "Committed: ${COMMIT_MSG}"
fi

# ── Git tag ───────────────────────────────────────────────────────────────────
step "Creating git tag v${VERSION}..."
TAG_MSG="Release v${VERSION}"
if [[ "$DRY_RUN" == "true" ]]; then
    dryrun "git tag -a v${VERSION} -m \"${TAG_MSG}\""
else
    if git rev-parse "v${VERSION}" &>/dev/null 2>&1; then
        fail "Tag v${VERSION} already exists. Delete it first: git tag -d v${VERSION}"
    fi
    git tag -a "v${VERSION}" -m "${TAG_MSG}"
    success "Tagged v${VERSION}"
fi

# ── Next steps ────────────────────────────────────────────────────────────────
printf "\n"
if [[ "$DRY_RUN" == "true" ]]; then
    info "Dry-run complete. No changes were made."
else
    success "Release v${VERSION} prepared."
fi
printf "\n"
printf "${BOLD}Next steps:${RESET}\n"
printf "  Push branch and tag:\n"
printf "    git push origin main\n"
printf "    git push origin v${VERSION}\n"
printf "\n"
printf "  Publish to PyPI (when ready):\n"
printf "    python -m twine upload dist/fileforge-${VERSION}*\n"
printf "\n"
printf "  Or use trusted publishing via GitHub Actions.\n"
printf "\n"
