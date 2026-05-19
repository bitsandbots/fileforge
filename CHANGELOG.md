# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2025-04-15

### Added

**Phase 1 — Core Scanning**
- Recursive directory scanning with depth limits and `.forgeignore` patterns
- Content extraction from 30+ file formats (text, PDF, DOCX, XLSX, HTML, images)
- SHA-256 exact duplicate detection with chunked hashing
- AI classification via local Ollama (qwen3:4b model)
- Rich terminal reports with category grouping and space estimates
- SQLite session persistence for scan history

**Phase 2 — Advanced Analysis**
- Near-duplicate detection via embeddings (nomic-embed-text + cosine similarity)
- Stale file detection based on modification age and junk patterns
- Version supersession detection (e.g., `report_v1.docx` → `report_v2.docx`)
- `--phase-2` flag to enable advanced features

**Phase 3 — Interactive Actions**
- Interactive HTML reports with per-file action buttons
- `fileforge organize` command for automatic file organization
- `fileforge dupes` command for duplicate management
- Dry-run mode for previewing actions
- Trash staging with date-based organization
- Action logging for undo support

**Phase 4 — Background Automation**
- `fileforge watch` for continuous filesystem monitoring
- `fileforge schedule` for cron-based automated scans
- Systemd integration with service and timer units
- Job audit trail for scheduled executions

### Fixed
- NameError bug in organize command (record.id scope issue)
- Silent exception handling in extract_snippet (now logs specific errors)
- Missing forgeignore error handling in organize and dupes commands
- Broad exception catches replaced with specific handlers

### Security
- All file operations use safe path handling
- No credentials or secrets in code
- Graceful degradation when AI services unavailable

### Documentation
- Comprehensive docs/ folder with overview, architecture, setup, API reference
- Tech stack documentation with dependencies and requirements
- Updated README with quick start guide

## [0.1.4] — 2026-05-17

### Added
- `fileforge-server.service` systemd unit for the long-running web UI
- `install.sh --scan|--server|--all` modes in the systemd installer
- Top-level `scripts/install.sh` now offers to register systemd services
- `scripts/release.sh` verifies systemd templates are present before packaging

## [0.1.5] — 2026-05-18

### Added
- `CLAUDE.md` — repository guidance for Claude Code sessions

### Fixed
- `scanner.py`: replace `Path.is_dir/is_file(follow_symlinks=False)` (Python 3.13+) with `os.path` equivalents for Python 3.11/3.12 compatibility

### Changed
- `scripts/release.sh`: stages `CHANGELOG.md` in the release commit and fails fast if the version entry is missing
- `scripts/install.sh`: fixes missing blank line before the Development quick-start block

## [0.1.6] — 2026-05-18

### Fixed
- `api/server.py`: `/api/health` endpoint returned hardcoded `"version":"0.1.0"`; now reflects `__version__` from the package
- `systemd/fileforge-scan.timer`: duplicate `OnCalendar=` directives caused the daily scan to fire at midnight AND 02:00; consolidated to `OnCalendar=*-*-* 02:00:00`

### Changed
- `scripts/install.sh`: systemd installer lookup now falls back to pip-installed package location when the dev-tree path is absent

## [0.1.7] — 2026-05-19

### Fixed
- `api/server.py`: `POST /api/scan` rejected paths containing `~` (e.g. `~/Documents`) with HTTP 400; now calls `.expanduser()` before validation and subprocess invocation
- `frontend/index.html`: category filter dropdown compared raw LLM category paths (e.g. `"Documents/Reports"`) against hardcoded keys (`"document"`) — always false, hiding all rows; added `normalizeCategoryKey()` to map free-text paths to filter keys
- `frontend/index.html`: category colour dot never rendered because `getCategoryColor()` was a literal string inside a CSS `style` attribute; now evaluated in JS before HTML injection
- `frontend/index.html`: switching tabs did not sync the status `<select>` dropdown, leaving it showing a stale value

### Added
- `frontend/index.html`: "Quick scan (skip AI classification)" checkbox (checked by default) so web UI scans complete in seconds rather than hours on large directories
- `db.py`: `complete_session()` sets `completed_at` timestamp on scan/organise/dupes finish; included in `list_sessions()` response

### Changed
- `api/server.py`: `POST /api/scan` is now non-blocking — returns immediately with a `job_id`; clients poll `GET /api/job/{job_id}` for status
- `api/server.py`: added `GET /api/browse?path=` directory browser endpoint for the path-picker widget
- `packaging`: upgraded `packaging` library to 26.2 to support Metadata-Version 2.4 (`License-File` field) in twine checks

## [0.1.8] — 2026-05-19

### Fixed
- `api/server.py` + `db.py`: `GET /api/session/{id}` returned all records with no limit; sessions with millions of files sent a multi-GB JSON payload that froze the browser. Endpoint now accepts `?limit=500&offset=0` query params (default: first 500). Response includes `total`, `limit`, `offset` fields for pagination awareness.
- `frontend/index.html`: page load fetches only first 500 records on large sessions; shows warning toast when session is truncated (e.g. "Showing first 500 of 2,417,064 files"). `stat-total` counter reflects session total, not truncated slice.

### Added
- `db.get_session_file_count(session_id)` — COUNT query returning total records without fetching rows
- `db.get_session_records()` now accepts `limit` (default: 500) and `offset` (default: 0) parameters
- Tests for `get_session_records` pagination and `get_session_file_count` in `tests/test_db.py`

### Documentation
- Comprehensive docs overhaul: all files updated to v0.1.7 (were stuck at 0.1.0)
- `docs/Blueprint_Overview.html`: branded single-page HTML reference (open in browser)
- `docs/gap-analysis.md`: tracks code vs. documentation discrepancies and planned features
- `docs/api.md`: removed fictional `actions/logger.py` section; added complete REST API reference
- `docs/architecture.md`: corrected module table (removed `xlsx.py`, `html.py`, `image.py` that don't exist); added web server diagram and async scan data flow
- `docs/tech-stack.md`: added `fastapi`, `uvicorn`, `Jinja2`, `packaging` entries; clarified which formats have extractors vs. installed dependencies only
- `docs/setup.md`: corrected `fileforge[ui]` → `fileforge[web]`; added `fileforge server` command reference
- Removed stale `docs/superpowers/plans/` planning docs (phases 2–4 are implemented)
- `src/fileforge/api/__init__.py`: added missing package init file
- `scripts/install.sh`: added `Blueprint_Overview.html` and `gap-analysis.md` to docs output

## [Unreleased]

### Planned
- Phase 5: React PWA GUI
- Phase 6: Cross-device sync
- Additional extractor formats (RTF, EPUB, xlsx, OCR)
- Custom classification models via config