# FileForge — Architecture

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI (cli.py)                               │
│              Typer — scan / organize / dupes / watch / schedule         │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
          ┌─────────▼──────┐  ┌───────▼────────┐  ┌─────▼──────────┐
          │ Scanner        │  │ Watcher        │  │ JobManager    │
          │ (scanner.py)   │  │ (watch/watcher)│  │ (schedule/)   │
          │ recursive walk │  │ watchdog events│  │ APScheduler   │
          └────────┬───────┘  └───────┬────────┘  └─────┬──────────┘
                   │                  │                  │
                   └──────────────────┼──────────────────┘
                                      │
                        ┌─────────────▼─────────────┐
                        │      SessionDB (db.py)     │
                        │   SQLite — persist scan   │
                        └──┬──────────┬─────────────┘
                           │          │
             ┌─────────────▼──┐  ┌─────▼──────────────────┐
             │  Dedup         │  │  Extractor             │
             │  (analysis/)   │  │  (extractor/__init__) │
             │  SHA-256       │  │  30+ format handlers  │
             └────────────┬──┘  └─────┬──────────────────┘
                          │          │
             ┌─────────────▼──────────▼─────────────┐
             │  Analysis (Phase 2)                  │
             │  • embeddings.py — near-dedup       │
             │  • staleness.py — age detection     │
             │  • versions.py — supersession       │
             └─────────────┬────────────────────────┘
                           │
             ┌─────────────▼────────────────────────┐
             │  Classifier (ai/classifier.py)       │
             │  Ollama qwen3:4b → category path     │
             └─────────────┬────────────────────────┘
                           │
             ┌─────────────▼────────────────────────┐
             │  Actions (Phase 3)                   │
             │  • mover.py — file organization      │
             │  • archiver.py — create/extract      │
             │  • trash.py — staging + recovery     │
             └─────────────┬────────────────────────┘
                           │
             ┌─────────────▼────────────────────────┐
             │  Report (report/)                    │
             │  • generator.py — Rich terminal      │
             │  • html_generator.py — Interactive   │
             └───────────────────────────────────────┘
```

## Module Responsibilities

### Core (Phase 1)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Entry point. Typer CLI with scan, organize, dupes, watch, schedule, status commands. |
| `config.py` | Loads `fileforge.toml` into validated Pydantic settings. Applies `.forgeignore` patterns. |
| `models.py` | Defines `FileRecord` — central data object passed through pipeline stages. |
| `db.py` | SQLite session store. Persists scan results; provides CRUD and iterator access. |
| `scanner.py` | Recursive directory walk with depth limits and ignore patterns. |
| `extractor/__init__.py` | Dispatcher: maps file extension to correct extractor module. |
| `extractor/text.py` | Plain text extraction for 33 extensions with encoding detection. |
| `extractor/pdf.py` | PDF extraction via pdfplumber, page-by-page. |
| `extractor/docx.py` | DOCX extraction via python-docx. |
| `extractor/xlsx.py` | Excel extraction via openpyxl. |
| `extractor/html.py` | HTML extraction via BeautifulSoup. |
| `extractor/image.py` | Image OCR via pytesseract (optional dependency). |
| `analysis/dedup.py` | SHA-256 file hashing (chunked 64KB) and exact-duplicate grouping. |
| `ai/classifier.py` | Sends content snippet to local Ollama for LLM classification. |
| `report/generator.py` | Rich terminal table with category groups, file counts, sizes. |

### Advanced Analysis (Phase 2)

| Module | Responsibility |
|--------|----------------|
| `analysis/embeddings.py` | Near-duplicate detection via `nomic-embed-text` embeddings + cosine similarity. |
| `analysis/staleness.py` | Age-based stale detection + junk pattern matching. |
| `analysis/versions.py` | Version supersession detection via pattern matching. |

### Actions (Phase 3)

| Module | Responsibility |
|--------|----------------|
| `actions/mover.py` | Move files to organized folder structure. |
| `actions/archiver.py` | Create and extract archives (zip, tar, etc.). |
| `actions/trash.py` | Move to trash staging with date-based organization and recovery. |
| `report/html_generator.py` | Interactive HTML reports with per-file action buttons. |

### Background Automation (Phase 4)

| Module | Responsibility |
|--------|----------------|
| `watch/watcher.py` | Filesystem event monitoring via watchdog with debouncing. |
| `schedule/job_manager.py` | APScheduler-based cron job management for scheduled scans. |
| `systemd/fileforge-scan.service` | Systemd service unit for unattended operation. |
| `systemd/fileforge-scan.timer` | Systemd timer for scheduled execution. |

## Data Flow — Scan Pipeline

The `fileforge scan` command executes these steps:

**Step 1 — Scanner**

`Scanner` walks each target directory recursively, respecting `max_depth` and `.forgeignore` patterns. Creates `FileRecord` with path, name, extension, size, and timestamps.

**Step 2 — Session DB**

`FileRecord` list written to SQLite via `SessionDB`. Session row created with scan metadata.

**Step 3 — Hashing**

`hash_file()` reads each file in 64KB chunks, produces SHA-256 digest. Stored to `FileRecord.sha256`.

**Step 4 — Exact Deduplication**

`find_exact_duplicates()` groups records by hash. Groups with >1 member flagged as duplicates.

**Step 5 — Extraction**

`extract_snippet()` dispatches to appropriate extractor based on extension. Returns text snippet up to `max_chars`.

**Step 6 — Classification**

`classify_file()` sends snippet to Ollama. Model returns category string (e.g., `documents/finance/receipts`). Stored to `FileRecord.category`.

**Step 7 — Phase 2 Analysis** (if `--phase-2`)

- `compute_embeddings()` generates vectors for near-duplicate detection
- `is_stale()` checks age and junk patterns
- `find_superseded()` identifies outdated versions

**Step 8 — Report**

`print_scan_summary()` renders Rich table grouped by category with counts and sizes.

## Data Flow — Organize Pipeline

The `fileforge organize` command:

1. **Scan** — Runs scan pipeline (Steps 1-6 above)
2. **Classify** — Assigns categories to all files
3. **Plan** — Creates action plan: `(FileRecord, destination_path, action)`
4. **Execute** — Moves files to `~/Organized/<category>/` (dry-run shows preview only)
5. **Handle Duplicates** — Duplicates moved to `~/Organized/Duplicates/<category>/`
6. **Handle Stale** — Stale files moved to `--trash-dir` (default: `~/.trash`)

## Data Model — FileRecord

`FileRecord` is a Pydantic v2 dataclass passed through every pipeline stage.

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `str` (UUID) | Unique record identifier |
| `session_id` | `str` | Foreign key to parent scan session |
| `path` | `Path` | Absolute path to the file |
| `name` | `str` | Filename without directory |
| `ext` | `str` | Lowercase file extension (e.g., `.pdf`) |
| `size` | `int` | File size in bytes |
| `mtime` | `datetime` | Last modified timestamp |
| `ctime` | `datetime` | Created/changed timestamp |
| `sha256` | `str \| None` | SHA-256 hex digest |
| `category` | `str \| None` | LLM-assigned category path |
| `embedding` | `list[float] \| None` | Embedding vector (Phase 2) |
| `is_duplicate` | `bool` | True if another file has same SHA-256 |
| `is_stale` | `bool` | True if age exceeds `stale_days` |
| `is_superseded` | `bool` | True if a newer version exists |
| `snippet` | `str \| None` | Extracted text snippet |

## SQLite Schema

```sql
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    root_paths  TEXT NOT NULL,   -- JSON array of scanned dirs
    file_count  INTEGER,
    status      TEXT             -- 'scanning', 'complete', 'error'
);

CREATE TABLE file_records (
    id            TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES sessions(id),
    path          TEXT NOT NULL,
    name          TEXT NOT NULL,
    ext           TEXT NOT NULL,
    size          INTEGER NOT NULL,
    mtime         TEXT NOT NULL,
    ctime         TEXT NOT NULL,
    sha256        TEXT,
    category      TEXT,
    embedding     TEXT,           -- JSON-serialized float array
    is_duplicate  INTEGER NOT NULL DEFAULT 0,
    is_stale      INTEGER NOT NULL DEFAULT 0,
    is_superseded INTEGER NOT NULL DEFAULT 0,
    snippet       TEXT
);

CREATE TABLE action_log (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    file_id     TEXT NOT NULL REFERENCES file_records(id),
    action      TEXT NOT NULL,     -- 'move', 'archive', 'trash', 'delete'
    source      TEXT NOT NULL,
    destination TEXT,
    timestamp   TEXT NOT NULL
);
```

Database location: `~/.fileforge/fileforge.db` (configurable via `output_dir`).

## Extractor Dispatch Pattern

```python
_DISPATCH: dict[str, object] = {}

# Text extensions registered in extractor/text.py
for ext in TEXT_EXTENSIONS:
    _DISPATCH[ext] = _text

_DISPATCH[".pdf"] = _pdf
_DISPATCH[".docx"] = _docx
# ... additional format handlers

def extract_snippet(path: Path, max_chars: int = 2000) -> str | None:
    ext = path.suffix.lower()
    module = _DISPATCH.get(ext)
    if module is None:
        return None
    try:
        return module.extract(path, max_chars=max_chars)
    except PermissionError:
        _log.warning("Permission denied reading %s", path)
        return None
    except UnicodeDecodeError:
        _log.debug("Cannot decode %s as text (binary file?)", path)
        return None
    except OSError as e:
        _log.warning("OS error reading %s: %s", path, e)
        return None
    except Exception:
        _log.error("Unexpected error extracting %s", path, exc_info=True)
        return None
```

**Adding a new extractor:**

1. Create `extractor/myformat.py` with `extract(path: Path, max_chars: int) -> str | None`
2. Register extension(s) in `extractor/__init__.py`
3. No other changes required — classifier consumes snippets uniformly

## Error Handling Strategy

FileForge uses graceful degradation throughout:

| Error Type | Handling | User Impact |
|------------|----------|-------------|
| `PermissionError` | Log warning, skip file | File excluded from scan |
| `UnicodeDecodeError` | Log debug, return empty snippet | Classification falls back to filename |
| `OSError` | Log warning, skip file | File excluded from scan |
| `ConnectionError` | Log warning, assign "Uncategorized" | Classification unavailable |
| Generic `Exception` | Log error with traceback, continue | File processed with defaults |

This ensures the scan completes even when individual files fail.

## Configuration

Configuration loaded from `fileforge.toml` (created on first run):

```toml
[general]
output_dir = "~/.fileforge"
max_depth = 10

[ignore]
patterns = [
    ".git",
    "__pycache__",
    "node_modules",
    "*.pyc",
]

[ai]
classification_model = "qwen3:4b"
embedding_model = "nomic-embed-text"
category_hints = [
    "Documents → contracts, reports, invoices",
    "Code → projects, scripts, snippets",
]

[phase_2]
stale_days = 365
similarity_threshold = 0.92
```

Override with `.forgeignore` files in any scanned directory.

## Phase Roadmap

| Phase | Status | Scope |
|-------|--------|-------|
| **1** | ✅ Complete | Scan, hash, exact dedup, AI classify, Rich report, SQLite persistence |
| **2** | ✅ Complete | Near-dedup via embeddings, stale detection, version supersession |
| **3** | ✅ Complete | Interactive HTML reports, dry-run, trash staging, undo |
| **4** | ✅ Complete | Watch mode, scheduled scans, systemd integration |
| **5** | 📋 Planned | React PWA GUI |
| **6** | 📋 Planned | Cross-device sync |