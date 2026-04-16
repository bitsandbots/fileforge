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

## [Unreleased]

### Planned
- Phase 5: React PWA GUI
- Phase 6: Cross-device sync
- Additional extractor formats (RTF, EPUB, etc.)
- Custom classification models via config