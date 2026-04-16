# FileForge — Project Overview

## What It Is

FileForge is an AI-powered file organizer that runs entirely on your local machine. It scans directories, reads file contents, and uses a locally hosted LLM to classify files into meaningful folder taxonomies — no cloud services, no data leaving your system.

The core problem it solves: file systems accumulate noise over time. Duplicate downloads, stale drafts, misnamed exports, and forgotten temp files pile up in ways that are expensive to clean manually but too risky to automate blindly. FileForge gives you an intelligent, auditable, and reversible process for reclaiming that space and restoring order.

## Key Capabilities

### Phase 1 — Current

- **Recursive scanning**: Walk one or more root directories, respecting depth limits and `.forgeignore` patterns.
- **Content extraction**: Extract text snippets from `.txt`, `.md`, `.py`, `.pdf`, `.docx`, and 30+ additional formats. Used as context for AI classification.
- **Exact deduplication**: SHA-256 hash comparison identifies identical files regardless of filename or location.
- **AI classification**: Local Ollama LLM (`qwen3:4b`) reads a content snippet and assigns each file a nested category (e.g., `documents/finance/receipts`). Skippable with `--no-classify` for fast runs.
- **Rich terminal report**: Scan summary with file counts, group sizes, and estimated reclaimable space.
- **Session persistence**: SQLite database stores scan results so you can query and act on them later.

### Phase 2 — Complete

- **Near-duplicate detection** via `nomic-embed-text` embeddings + hnswlib + cosine similarity (configurable threshold, default 0.92)
- **Stale file flagging** based on modification age (configurable stale_days, default 365) and junk patterns (Thumbs.db, *.tmp, *.swp, etc.)
- **Version supersession detection** via pattern matching (e.g., `report_v1.docx` superseded by `report_v2.docx`)
- Enabled with `--phase-2` flag; opt-in to avoid performance impact on first scan
- All Phase 2 data persisted to database for later querying

### Phase 3 — Complete

- **Interactive HTML reports** with per-file action buttons (move, archive, delete)
- **Dry-run mode** with action preview showing affected files before execution
- **Trash staging** with date-based organization and permanent cleanup after 30 days
- **Undo support** via action logs persisted in database
- Enabled with `--interactive` flag (launches report in browser) and `--dry-run` (preview-only)

### Phase 4 — Complete

- **Watch mode** with filesystem event monitoring (continuous background scanning)
- **Scheduled scans** via cron or systemd timers (Linux) / Task Scheduler (Windows)
- **Job audit trail** tracking all scheduled executions, file counts, and actions
- **Auto-act mode** for unattended organization (with safety checks)
- Enabled with `fileforge watch` and `fileforge schedule` commands

### Phase 5 — Planned

- GUI front-end (React PWA)
- Cross-device sync for multi-machine households

## Design Philosophy

**Offline-first, data-sovereign.** Classification runs via Ollama on your local machine. File contents never leave your system. This is not negotiable — cloud LLM APIs are explicitly excluded from the design.

**Safe by default.** Phase 1 reads and reports only. No files are moved, renamed, or deleted. When Phase 3 actions land, they will default to dry-run mode, and all moves will go through a recoverable trash stage before permanent action.

**Transparent and auditable.** Every scan is recorded to SQLite with full metadata. Every classification decision includes the category returned by the model. Nothing happens silently.

**Graceful degradation.** If Ollama is unavailable, classification falls back gracefully and scan continues. If a file can't be read, it's recorded with an empty snippet rather than aborting the run.

## CoreConduit Context

FileForge is developed and maintained by CoreConduit Consulting Services. It is MIT-licensed and open-source — a demonstration of the technical capability CoreConduit brings to client engagements, particularly for organizations with strict data-handling requirements (legal, nonprofit, healthcare-adjacent) where cloud processing of documents is not acceptable.

The reference deployment target is a Raspberry Pi 5 (8GB RAM). FileForge is intentionally designed to run well on modest hardware: chunked SHA-256 hashing, iterator-based DB access, and configurable extraction limits keep memory pressure low even on large directories.

## Quick Start

```bash
pip install fileforge

# Pull required Ollama models
ollama pull qwen3:4b
ollama pull nomic-embed-text

# Scan your Documents folder
fileforge scan ~/Documents
```

Output: a Rich terminal table showing file counts by category, duplicate groups, and estimated reclaimable space.

To skip AI classification (faster, no Ollama required):

```bash
fileforge scan ~/Documents --no-classify
```
