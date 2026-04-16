# FileForge

AI-powered file organizer using local Ollama inference — no cloud, no subscriptions.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)

## What it does

- **Scans** directories and classifies files using local AI (Ollama) or rule-based heuristics
- **Detects** duplicates by content hash and semantic similarity
- **Organizes** files into category folders automatically
- **Automates** with watch mode and scheduled scans
- **Runs offline** — no data leaves your machine

## Install

### From PyPI (coming soon)

```bash
pip install fileforge
```

### From source

```bash
git clone https://github.com/coreconduit/fileforge.git
cd fileforge
bash scripts/install.sh
```

**Requirements:** Python 3.11+, [Ollama](https://ollama.com) (optional, for AI classification).

## Quick start

```bash
# Pull required Ollama models
ollama pull qwen3:4b
ollama pull nomic-embed-text

# Scan a directory
fileforge scan ~/Documents

# Preview organization (dry-run)
fileforge organize ~/Downloads --dry-run

# Find duplicates
fileforge dupes ~/Documents
```

## Commands

| Command | Description |
|---------|-------------|
| `fileforge scan <dirs>` | Scan and classify files |
| `fileforge organize <dirs>` | Move files to categorized folders |
| `fileforge dupes <dirs>` | Find and manage duplicates |
| `fileforge watch <dirs>` | Monitor for changes |
| `fileforge schedule <dirs>` | Schedule automated scans |
| `fileforge status` | Show session info |

Run `fileforge --help` for full options.

## Background Automation

### Watch mode

Monitor directories and scan on changes:

```bash
fileforge watch ~/Documents ~/Downloads --phase-2
```

### Scheduled scans

Run daily scans automatically:

```bash
# Daily at 2 AM
fileforge schedule ~/Documents --cron "0 2 * * *"

# Or use systemd (Linux)
bash src/fileforge/systemd/install.sh
```

## Configuration

Copy the example config and edit to suit:

```bash
cp fileforge.toml.example fileforge.toml
```

Create `.forgeignore` files in any directory to exclude patterns:

```
*.log
node_modules/
*.tmp
```

## Development

```bash
bash scripts/install.sh       # editable install + dev deps
bash scripts/check.sh         # tests + lint + formatting
python -m pytest -q           # run tests
```

## Documentation

- [Overview](docs/overview.md) — Project goals and capabilities
- [Architecture](docs/architecture.md) — Design and data flow
- [Setup Guide](docs/setup.md) — Detailed installation and usage
- [Tech Stack](docs/tech-stack.md) — Dependencies and requirements

## License

MIT — see [LICENSE](LICENSE).

---

A [CoreConduit Consulting Services](https://coreconduit.com) open-source tool.
Issues and contributions welcome.