# FileForge — Project Overview

## What It Is

FileForge is an AI-powered file organizer that runs entirely on your local machine. It scans directories, reads file contents, and uses a locally hosted LLM to classify files into meaningful folder taxonomies — no cloud services, no data leaving your system.

The core problem it solves: file systems accumulate noise over time. Duplicate downloads, stale drafts, misnamed exports, and forgotten temp files pile up in ways that are expensive to clean manually but too risky to automate blindly. FileForge gives you an intelligent, auditable, and reversible process for reclaiming that space and restoring order.

## Status

**Version 0.1.0** — Alpha release. All planned phases complete and tested (91/91 tests passing).

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Core scanning, extraction, classification |
| Phase 2 | ✅ Complete | Near-duplicates, stale files, versions |
| Phase 3 | ✅ Complete | Interactive reports, actions, trash |
| Phase 4 | ✅ Complete | Watch mode, scheduled scans, systemd |
| Phase 5 | 📋 Planned | GUI front-end (React PWA) |
| Phase 6 | 📋 Planned | Cross-device sync |

## Key Capabilities

### Phase 1 — Core Scanning

- **Recursive scanning**: Walk one or more root directories, respecting depth limits and `.forgeignore` patterns.
- **Content extraction**: Extract text snippets from 30+ formats (`.txt`, `.md`, `.py`, `.pdf`, `.docx`, `.xlsx`, `.html`, images via OCR, and more).
- **Exact deduplication**: SHA-256 hash comparison identifies identical files regardless of filename or location.
- **AI classification**: Local Ollama LLM (`qwen3:4b`) reads a content snippet and assigns each file a nested category (e.g., `documents/finance/receipts`).
- **Rich terminal report**: Scan summary with file counts, group sizes, and estimated reclaimable space.
- **Session persistence**: SQLite database stores scan results for querying and auditing.

### Phase 2 — Advanced Analysis

- **Near-duplicate detection**: `nomic-embed-text` embeddings + cosine similarity (threshold 0.92) finds semantically similar files.
- **Stale file flagging**: Age-based detection (default 365 days) + junk pattern matching (`Thumbs.db`, `*.tmp`, `*.swp`).
- **Version supersession**: Pattern matching identifies outdated versions (`report_v1.docx` → `report_v2.docx`).
- **Enabled with**: `fileforge scan <dirs> --phase-2`

### Phase 3 — Interactive Actions

- **Interactive HTML reports**: Per-file action buttons with Rich terminal fallback.
- **Dry-run mode**: Preview actions before execution (`--dry-run`).
- **Trash staging**: Date-based organization with 30-day auto-cleanup.
- **Undo support**: Action logs persisted in database for recovery.
- **File organization**: `fileforge organize <dirs>` moves files to `~/Organized/<category>/`.
- **Duplicate handling**: `fileforge dupes <dirs>` finds and manages duplicates.

### Phase 4 — Background Automation

- **Watch mode**: `fileforge watch <dirs>` monitors filesystem for changes.
- **Scheduled scans**: `fileforge schedule <dirs> --cron "0 2 * * *"` for automated daily scans.
- **Systemd integration**: Linux timer/service for unattended operation.
- **Job audit trail**: All scheduled executions logged with file counts and actions.

## Design Philosophy

**Offline-first, data-sovereign.** Classification runs via Ollama on your local machine. File contents never leave your system. This is not negotiable — cloud LLM APIs are explicitly excluded from the design.

**Safe by default.** Phase 1 reads and reports only. No files are moved, renamed, or deleted without explicit commands. All destructive operations require confirmation or dry-run preview.

**Transparent and auditable.** Every scan is recorded to SQLite with full metadata. Every classification decision includes the category returned by the model. Nothing happens silently.

**Graceful degradation.** If Ollama is unavailable, classification falls back gracefully and scan continues. If a file can't be read, it's recorded with an empty snippet rather than aborting the run.

## CoreConduit Context

FileForge is developed and maintained by CoreConduit Consulting Services. It is MIT-licensed and open-source — a demonstration of the technical capability CoreConduit brings to client engagements, particularly for organizations with strict data-handling requirements (legal, nonprofit, healthcare-adjacent) where cloud processing of documents is not acceptable.

The reference deployment target is a Raspberry Pi 5 (8GB RAM). FileForge is intentionally designed to run well on modest hardware: chunked SHA-256 hashing, iterator-based DB access, and configurable extraction limits keep memory pressure low even on large directories.

## Quick Start

```bash
# Install
pip install fileforge

# Or from source
git clone https://github.com/coreconduit/fileforge.git
cd fileforge
bash scripts/install.sh

# Pull required Ollama models
ollama pull qwen3:4b
ollama pull nomic-embed-text

# Scan your Documents folder (dry-run by default)
fileforge scan ~/Documents --dry-run

# Organize files by category
fileforge organize ~/Downloads --dry-run

# Find duplicates
fileforge dupes ~/Documents
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `fileforge scan <dirs>` | Scan directories and classify files |
| `fileforge organize <dirs>` | Move files to categorized folders |
| `fileforge dupes <dirs>` | Find and manage duplicate files |
| `fileforge watch <dirs>` | Monitor directories for changes |
| `fileforge schedule <dirs>` | Schedule automated scans |
| `fileforge status` | Show current session status |

Run `fileforge --help` or `fileforge <command> --help` for detailed options.