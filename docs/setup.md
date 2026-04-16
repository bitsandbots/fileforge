# FileForge — Setup and Usage

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required. 3.12+ recommended. |
| Ollama | Latest | Required for AI classification. Not required for `--no-classify` runs. |
| Tesseract | Any | Optional. Not used in Phase 1; reserved for OCR extraction (Phase 2). |

Ollama must be running and accessible at `http://localhost:11434` (default) before running `fileforge scan` without `--no-classify`.

## Installation

### From PyPI (when published)

```bash
pip install fileforge
```

### From source (development)

```bash
git clone https://github.com/coreconduit/fileforge.git
cd fileforge
pip install -e ".[dev]"
```

The `[dev]` extra installs pytest, black, and ruff for local development.

### Phase 2 Setup (Optional)

If using Phase 2 features (near-duplicate detection via embeddings, stale file flagging, version detection):

```bash
# Pull the embedding model for Phase 2
ollama pull nomic-embed-text

# Install optional hnswlib dependency for similarity indexing
pip install "fileforge[ann]"
```

Usage:

```bash
fileforge scan ~/Documents --phase-2
# Shows stale files, version patterns, and near-duplicates
```

### Phase 3 Setup (Optional)

If using interactive HTML reports and file actions:

```bash
pip install "fileforge[ui]"  # Installs Jinja2 for HTML templating
```

Usage:

```bash
# Interactive mode with HTML report
fileforge scan ~/Documents --phase-2 --interactive

# Preview actions without executing
fileforge scan ~/Documents --phase-2 --dry-run

# All three phases together
fileforge scan ~/Documents --interactive
```

### Phase 4 Setup (Optional)

Enable continuous background organization:

**Watch mode (immediate scans on file changes):**
```bash
fileforge watch ~/Documents ~/Downloads --phase-2
```

**Scheduled scans (daily at 2 AM):**
```bash
fileforge schedule ~/Documents --cron "0 2 * * *"

# Or use systemd timer (Linux)
bash src/fileforge/systemd/install.sh
```

**Systemd integration (Linux):**

For automatic daily scans at 2 AM, install the systemd timer:

```bash
cd /path/to/fileforge
bash src/fileforge/systemd/install.sh

# Check status
systemctl --user status fileforge-scan.timer

# View logs
journalctl --user -u fileforge-scan.service
```

### Verify installation

```bash
fileforge --version
fileforge status
```

## Ollama Setup

FileForge requires two models:

```bash
# Classification model (~2.5GB)
ollama pull qwen3:4b

# Embedding model (~270MB) — used in Phase 2
ollama pull nomic-embed-text
```

Confirm both are available:

```bash
ollama list
```

Expected output includes `qwen3:4b` and `nomic-embed-text`.

If Ollama is not running, start it:

```bash
# Linux (systemd)
sudo systemctl start ollama

# macOS / Linux (manual)
ollama serve
```

## Quick Start

```bash
# Scan with classification
fileforge scan ~/Documents

# Scan multiple directories
fileforge scan ~/Documents ~/Downloads ~/Desktop

# Scan without classification (fast, no Ollama required)
fileforge scan ~/Documents --no-classify

# Check session info
fileforge status
```

## CLI Reference

### `fileforge scan`

Scans one or more directories. Runs the full pipeline: walk, hash, dedup, classify, report.

```
fileforge scan <dirs>... [OPTIONS]
```

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `dirs` | paths (1+) | — | One or more directories to scan. Recursive. |
| `--no-classify` | flag | off | Skip AI classification. Faster; Ollama not required. |
| `--phase-2` | flag | off | Enable near-duplicate detection, stale file detection, version supersession. |
| `--interactive` | flag | off | Open HTML report in browser after scan. |
| `--dry-run` | flag | off | Preview actions without executing. |
| `--config` | path | `./fileforge.toml` | Path to a custom config file. |
| `--depth` | int | from config | Override `max_depth` for this run. |

**Examples:**

```bash
# Basic scan with classification
fileforge scan ~/Documents

# Fast scan without classification
fileforge scan ~/Downloads ~/Desktop --no-classify

# Full analysis with Phase 2
fileforge scan ~/Documents --phase-2

# Interactive HTML report
fileforge scan ~/Documents --phase-2 --interactive

# Preview actions without executing
fileforge scan ~/Documents --dry-run
```

### `fileforge organize`

Moves files to organized folder structure by category.

```
fileforge organize <dirs>... [OPTIONS]
```

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `dirs` | paths (1+) | — | One or more directories to organize. |
| `--dry-run` | flag | off | Preview moves without executing. |
| `--trash-dir` | path | `~/.trash` | Directory for stale files. |
| `--config` | path | `./fileforge.toml` | Custom config file. |

**Examples:**

```bash
# Preview organization plan
fileforge organize ~/Downloads --dry-run

# Organize files (moves to ~/Organized/<category>/)
fileforge organize ~/Downloads

# Custom destination for stale files
fileforge organize ~/Downloads --trash-dir ~/Archive/old
```

### `fileforge dupes`

Find and manage duplicate files.

```
fileforge dupes <dirs>... [OPTIONS]
```

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `dirs` | paths (1+) | — | One or more directories to scan. |
| `--delete` | flag | off | Delete duplicate files. |
| `--move` | flag | off | Move duplicates to `~/Organized/Duplicates/`. |
| `--dry-run` | flag | off | Preview actions without executing. |

**Examples:**

```bash
# Show duplicate report
fileforge dupes ~/Documents

# Preview deletion
fileforge dupes ~/Downloads --delete --dry-run

# Move duplicates to organized folder
fileforge dupes ~/Downloads --move
```

### `fileforge watch`

Monitor directories for changes and scan automatically.

```
fileforge watch <dirs>... [OPTIONS]
```

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `dirs` | paths (1+) | — | One or more directories to monitor. |
| `--phase-2` | flag | off | Enable Phase 2 analysis on each scan. |
| `--debounce` | int | 5 | Seconds to wait after last change before scanning. |

**Examples:**

```bash
# Watch Documents for changes
fileforge watch ~/Documents

# Watch multiple dirs with Phase 2
fileforge watch ~/Documents ~/Downloads --phase-2

# Custom debounce interval (wait for changes to settle)
fileforge watch ~/Documents --debounce 10
```

### `fileforge schedule`

Schedule automated scans via cron syntax.

```
fileforge schedule <dirs>... --cron <expr> [OPTIONS]
```

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `dirs` | paths (1+) | — | One or more directories to scan. |
| `--cron` | string | — | Cron expression (e.g., `"0 2 * * *"` for 2 AM daily). |
| `--phase-2` | flag | off | Enable Phase 2 analysis. |

**Examples:**

```bash
# Daily 2 AM scan
fileforge schedule ~/Documents --cron "0 2 * * *"

# Every Monday at 9 AM
fileforge schedule ~/Documents --cron "0 9 * * 1"

# With Phase 2 analysis
fileforge schedule ~/Documents ~/Downloads --cron "0 2 * * *" --phase-2
```

### `fileforge status`

Displays information about the current session: last scan time, root paths, file count, and session ID.

```
fileforge status
```

No options. Reads from the SQLite database at `output_dir`.

## Configuration File

FileForge looks for `fileforge.toml` in the current working directory by default. You can override this with `--config`.

Full reference with defaults:

```toml
[general]
# Directories to scan if none are provided on the command line
scan_dirs = []

# Directory for the SQLite database and future output files
# Supports ~ expansion
output_dir = "~/.fileforge"

# Maximum recursion depth. 0 = unlimited.
max_depth = 0

# Maximum bytes to read from a file for extraction
max_extract_size = 1_048_576  # 1MB


[ai]
# Ollama model used for classification
classification_model = "qwen3:4b"

# Ollama model used for embeddings (Phase 2)
embedding_model = "nomic-embed-text"

# Ollama API base URL
ollama_url = "http://localhost:11434"

# Maximum characters from extracted text sent to the classifier
snippet_length = 2000

# Optional hints to steer classification toward your taxonomy
# Example: ["invoices", "meeting notes", "source code"]
category_hints = []


[duplicates]
# Cosine similarity threshold for near-duplicate detection (Phase 2)
similarity_threshold = 0.92

# Enable semantic deduplication via embeddings (Phase 2)
semantic_dedup = false


[staleness]
# Files not modified in this many days are flagged as stale (Phase 2)
stale_days = 365

# Glob patterns that identify junk files (Phase 2)
junk_patterns = ["*.tmp", "*.bak", "~$*", "Thumbs.db", ".DS_Store"]

# Glob patterns that identify temp files (Phase 2)
temp_patterns = ["*.temp", "tmp_*"]

# Detect versioned file pairs (e.g., report_v1 / report_v2) (Phase 2)
detect_versions = true


[ignore]
# Glob patterns to skip during scanning
# Matched against the full path
patterns = [
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    "*.pyc",
    ".venv",
    "venv",
    ".env",
]
```

### Category Hints

`category_hints` is a list of strings that are injected into the classification prompt. Use them to bias the LLM toward your preferred taxonomy:

```toml
[ai]
category_hints = ["receipts", "contracts", "meeting notes", "design mockups"]
```

The classifier will favor these terms when they are semantically relevant to the file content.

## `.forgeignore` Syntax

FileForge also reads `.forgeignore` from the scanned directory (and any parent up to the filesystem root). It uses the same glob syntax as `.gitignore`:

```
# Skip all log files
*.log

# Skip a specific folder
archive/2018/

# Skip files matching a pattern in any subdirectory
**/node_modules/

# Skip files starting with a dot (hidden files on Unix)
.*
```

`.forgeignore` patterns are merged with the `[ignore]` patterns from `fileforge.toml`. Either source can trigger exclusion.

## Cross-Platform Notes

### Windows

- Paths use backslashes internally but FileForge normalizes them via `pathlib.Path`. You can use forward slashes in config files and CLI arguments.
- Hidden file detection uses `FILE_ATTRIBUTE_HIDDEN` on Windows, not the leading-dot convention. Both are respected.
- The default `output_dir` resolves to `%LOCALAPPDATA%\fileforge` via `platformdirs`.
- If Ollama is installed via the Windows installer, it runs as a system service and is available at the default URL without manual startup.

### Linux / Raspberry Pi

- Default `output_dir` resolves to `~/.fileforge`.
- Ollama typically runs via systemd: `sudo systemctl enable --now ollama`.
- On Raspberry Pi 5 with 8GB RAM, `qwen3:4b` runs comfortably. On 4GB models, consider a smaller classification model and adjust `snippet_length` downward (e.g., 500) to reduce prompt memory pressure.

### macOS

- Default `output_dir` resolves to `~/Library/Application Support/fileforge` via `platformdirs`.
- Ollama desktop app starts automatically on login. No manual `ollama serve` needed.

## Troubleshooting

### Ollama not running

**Symptom:** `fileforge scan` reports classification errors for every file, or fails immediately.

**Fix:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start it if not
ollama serve        # foreground
# or
sudo systemctl start ollama   # systemd
```

If you want to scan without classification while Ollama is unavailable:
```bash
fileforge scan ~/Documents --no-classify
```

### Model not found

**Symptom:** Ollama responds but classification fails with a model-not-found error.

**Fix:**
```bash
ollama pull qwen3:4b
```

### Encoding errors on text files

**Symptom:** Some files produce empty snippets or garbled text.

**Cause:** FileForge uses `chardet` to detect encoding, but confidence may be low on binary-looking text files.

**Fix:** This is handled gracefully — files with undetectable encoding produce an empty snippet and are still scanned and hashed. Classification falls back to `uncategorized`. No action required unless you need accurate classification of those files specifically.

### Permission denied

**Symptom:** Some files are skipped with a permission error during scanning.

**Cause:** The user running FileForge does not have read access to those files.

**Fix:** FileForge logs skipped files and continues. To include them, run with elevated permissions or adjust file ACLs. On Linux:
```bash
sudo fileforge scan /var/log --no-classify
```

### Database locked

**Symptom:** `fileforge status` or a second concurrent scan reports a SQLite lock error.

**Cause:** SQLite allows only one writer at a time. Running two `fileforge scan` commands simultaneously will cause one to fail.

**Fix:** Run scans sequentially. FileForge does not support concurrent scan sessions.

### Scan is slow

**Cause:** Classification via Ollama is the bottleneck on large directories. Each file requires a round-trip to the local LLM.

**Options:**

1. Use `--no-classify` for a fast initial pass: hashing and dedup still run.
2. Reduce `snippet_length` in config (e.g., `500`) to shorten prompts and speed up inference.
3. Use a smaller/faster model: set `classification_model = "qwen2.5:1.5b"` in `fileforge.toml`.
