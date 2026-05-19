# FileForge — AGENTS.md

## Commands

```bash
pip install -e ".[dev]"          # editable install + dev deps
pip install -e ".[dev,ann,ocr,web]"  # all extras
bash scripts/check.sh            # pytest → black --check → ruff (pre-commit gate)
python -m pytest -q              # fast test run
python -m pytest tests/test_dedup.py::test_find_exact_duplicates -q  # single test
fileforge scan ~/Documents       # CLI entry
fileforge server                 # web UI at http://localhost:8082
```

## Architecture (what matters)

- **CLI entry**: `src/fileforge/cli.py` — Typer app, all commands are subcommands.
- **DB**: `db.py` — SQLite via stdlib `sqlite3`. Five tables: `sessions`, `file_records`, `action_logs`, `trash`, `job_history`. **All writes go through SessionDB** — never bypass with raw SQL elsewhere.
- **Extractor**: `extractor/__init__.py` dispatches by extension; returns `None` on error (never raises).
- **Classifier**: `ai/classifier.py` calls Ollama at `http://localhost:11434` (configurable). Gracefully degrades to rule-based when Ollama is unavailable.
- **Phase 2** (embeddings, staleness, versions): only runs when explicitly invoked from `organize` or `dupes` commands, not during plain `scan`. Requires `ann` extra (`hnswlib`).
- **OCR**: `extractor/image.py` requires `ocr` extra (`pytesseract`).
- **Web UI**: FastAPI in `api/server.py` serves static `frontend/index.html`.
- **Systemd**: templates in `systemd/` — must be present at build time (`scripts/release.sh` verifies).

## Config

`fileforge.toml` searched at project root → `~/.config/fileforge/` (XDG) → `~/.fileforge/` (legacy). Default model: `qwen3:4b`. Embedding model: `nomic-embed-text`.

## Testing conventions

- All fixture files use `HARNESS_` prefix.
- `conftest.py` provides `tmp_dir`, `sample_txt`, `fixtures_dir`.
- CLI integration tests use `CliRunner` with real SQLite in tmp dir — do **not** mock `SessionDB`.
- Systemd tests test template rendering only, no running systemd required.

## Code style (enforced by `scripts/check.sh`)

- Black 88, target `py311`.
- Ruff: select `E, F, I, UP`.
- Type hints on all signatures; `from __future__ import annotations`.
- All SQL parameterized — no f-strings, no concatenation.

## Release

`scripts/release.sh <version> [--dry-run]` updates `__init__.py` + `pyproject.toml`, builds wheel, creates annotated tag. Run `scripts/check.sh` clean first.
