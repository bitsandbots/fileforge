#!/usr/bin/env bash
# FileForge — Pre-commit / CI Check Script
# Usage: bash scripts/check.sh
# Runs tests, formatting check, and linting. Exits 1 if any check fails.
# Note: chmod +x scripts/check.sh to make executable
set -uo pipefail

BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RESET='\033[0m'

PASS="${GREEN}PASS${RESET}"
FAIL="${RED}FAIL${RESET}"

overall=0
declare -A results

run_check() {
    local name="$1"
    shift
    printf "${BOLD}[check]${RESET} Running %s...\n" "$name"
    if "$@"; then
        results["$name"]="$PASS"
    else
        results["$name"]="$FAIL"
        overall=1
    fi
    printf "\n"
}

# ── Locate project root ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

# ── Checks ────────────────────────────────────────────────────────────────────
run_check "pytest"        python -m pytest -q
run_check "black"         python -m black --check src/ tests/
run_check "ruff"          python -m ruff check src/ tests/

# ── Summary ───────────────────────────────────────────────────────────────────
printf "${BOLD}──────────────────────────────${RESET}\n"
printf "${BOLD}Check Summary${RESET}\n"
printf "${BOLD}──────────────────────────────${RESET}\n"
for name in pytest black ruff; do
    printf "  %-12s %b\n" "$name" "${results[$name]:-${YELLOW}SKIP${RESET}}"
done
printf "${BOLD}──────────────────────────────${RESET}\n"

if [[ "$overall" -ne 0 ]]; then
    printf "${RED}One or more checks failed.${RESET}\n"
    exit 1
else
    printf "${GREEN}All checks passed.${RESET}\n"
fi
