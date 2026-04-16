# FileForge

AI-powered file organizer using local Ollama inference — no cloud, no subscriptions.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)

## What it does

- Scans directories and classifies files using local AI (Ollama) or rule-based heuristics
- Detects and reports duplicate files by content hash and semantic similarity
- Moves or renames files according to configurable rules, with a trash-safe undo path
- Runs fully offline — no data leaves your machine

## Install

PyPI release coming soon. For now, install from source:

```bash
git clone https://github.com/coreconduit/fileforge.git
cd fileforge
bash scripts/install.sh
```

Requirements: Python 3.11+, [Ollama](https://ollama.com) (optional, for AI classification).

## Quick start

```bash
# Scan a directory and preview what would change (no files moved)
fileforge scan ~/Downloads --dry-run

# Scan and preview organization interactively
fileforge scan ~/Downloads --interactive

# Find duplicates
fileforge dupes ~/Documents
```

## Background Organization (Phase 4)

FileForge can run continuously in the background:

### Watch Mode
Monitor directories and scan on changes:
```bash
fileforge watch ~/Documents ~/Downloads --phase-2
```

### Scheduled Scans
Run daily scans automatically:
```bash
# Schedule a daily 2 AM scan
fileforge schedule ~/Documents --cron "0 2 * * *"

# Or use systemd (Linux)
bash src/fileforge/systemd/install.sh
```

See `fileforge --help` or the [docs/](docs/) directory for full usage.

## Configuration

Copy the example config and edit to suit:

```bash
cp fileforge.toml.example fileforge.toml
```

## Development

```bash
bash scripts/install.sh       # editable install + dev deps
bash scripts/check.sh         # tests + lint + formatting
```

---

A [CoreConduit Consulting Services](https://coreconduit.com) open-source tool.
MIT licensed. Issues and contributions welcome.
