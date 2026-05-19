# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run full check suite (pytest + black + ruff) — use before every commit
bash scripts/check.sh

# Run tests only
python -m pytest -q

# Run a single test file
python -m pytest tests/test_scanner.py -q

# Run a single test by name
python -m pytest tests/test_dedup.py::test_find_exact_duplicates -q

# Format check (non-destructive)
black --check src/ tests/

# Auto-format
black src/ tests/

# Lint
ruff check src/ tests/

# Install in editable mode with dev deps
pip install -e ".[dev]"

# Install with optional extras
pip install -e ".[dev,ann,ocr,web]"

# Run the CLI
fileforge scan ~/Documents
fileforge server  # starts on http://localhost:8082
```

## Architecture

FileForge is a **6-phase AI-powered file organizer** (Phases 1–4 implemented). The CLI entry point is `src/fileforge/cli.py`; all commands are Typer subcommands.

### Data flow (scan pipeline)

```
Scanner.scan()          → recursive walk → List[FileRecord]
SessionDB.insert()      → persist to SQLite (sessions.db in ~/.fileforge/)
hash_file()             → SHA-256 in 64 KB chunks
find_exact_duplicates() → group by hash
extract_snippet()       → dispatch to extractor/ (text, PDF, DOCX, HTML, image)
classify_file()         → Ollama LLM → category string
(Phase 2) embeddings / staleness / versions analysis
print_scan_summary()    → Rich terminal table or HTML report
```

### Key layers

| Layer | Path | Purpose |
|---|---|---|
| CLI | `cli.py` | Typer commands: scan, organize, dupes, watch, schedule, status, server |
| Config | `config.py` | Loads `fileforge.toml`; dataclass `FileForgeConfig` |
| Models | `models.py` | Pydantic v2: `FileRecord`, `ActionLog`, `TrashEntry` |
| DB | `db.py` | SQLite via stdlib `sqlite3`; `SessionDB` manages sessions, file_records, action_logs, trash, job_history |
| Scanner | `scanner.py` | Recursive walk, respects `.forgeignore` and `max_depth` |
| Extractor | `extractor/` | `extract_snippet()` dispatches to format-specific modules (30+ types) |
| AI | `ai/classifier.py` | `classify_file()` → Ollama REST → category path string |
| Analysis | `analysis/` | `dedup.py` (SHA-256), `embeddings.py` (nomic-embed-text + cosine), `staleness.py`, `versions.py` |
| Actions | `actions/` | `mover.py`, `trash.py`, `archiver.py` — all write to `action_logs` |
| Report | `report/` | `generator.py` (Rich), `html_generator.py` (Jinja2 → report.html template) |
| Automation | `watch/watcher.py`, `schedule/job_manager.py` | watchdog + APScheduler |
| API | `api/server.py` | FastAPI; static frontend in `frontend/index.html` |
| Systemd | `systemd/` | `fileforge-scan.service/.timer` + `fileforge-server.service` |

### SQLite schema (db.py)

Five tables: `sessions`, `file_records`, `action_logs`, `trash`, `job_history`. All writes go through `SessionDB` — never bypass it with raw SQL outside `db.py`.

### Classifier / Ollama

`ai/classifier.py` calls Ollama at the URL from config (default `http://localhost:11434`). It gracefully degrades to rule-based category inference when Ollama is unavailable. The default model is `qwen3:4b`; override with `[ai] classification_model` in `fileforge.toml`.

### Extractor dispatch

`extractor/__init__.py` inspects extension and MIME type, then calls the matching module. Unreadable files return `None` rather than raising. Note: `extractor/image.py` (OCR via pytesseract) and `extractor/xlsx.py` are planned but not yet implemented — see `docs/gap-analysis.md`.

### Phase 2 analyses (embeddings, staleness, versions)

These run only when explicitly invoked from `organize` or `dupes` commands, not during a plain `scan`. They require the `ann` extra (`hnswlib`) for ANN-accelerated nearest-neighbour search.

## Configuration

Copy `fileforge.toml.example` → `fileforge.toml` (project root or `~/.config/fileforge/`). Key knobs:

- `[ai].classification_model` — Ollama model name
- `[duplicates].similarity_threshold` — cosine threshold (0–1) for near-dup detection
- `[staleness].stale_days` — age threshold for staleness flag
- `[ignore].patterns` — glob list; `.git`, `node_modules`, `__pycache__` are defaults

## Tests

- All test fixtures use the `HARNESS_` prefix per project convention.
- `conftest.py` provides `tmp_dir`, `sample_txt`, `fixtures_dir`.
- Integration tests that exercise the CLI (`test_cli_*.py`) spin up real SQLite sessions in a tmp directory — do not mock the DB layer.
- Systemd tests (`test_systemd_integration.py`) require no running systemd; they test template rendering and installer logic only.

## Release

`scripts/release.sh` handles version bump, tagging, and PyPI publish. It verifies systemd templates are present before building. Run `scripts/check.sh` clean first.
