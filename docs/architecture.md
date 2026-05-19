# FileForge — Architecture

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                                        │
│         Typer — scan / organize / dupes / watch / schedule / server         │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
           ┌───────────────────┼────────────────────────────┐
           │                   │                            │
 ┌─────────▼──────┐  ┌─────────▼──────┐  ┌────────────────▼────────────────┐
 │ Scanner        │  │ Watcher        │  │ JobManager / FastAPI Server     │
 │ (scanner.py)   │  │ (watch/watcher)│  │ (schedule/,  api/server.py)    │
 │ recursive walk │  │ watchdog events│  │ APScheduler + REST API          │
 └────────┬───────┘  └───────┬────────┘  └────────────────┬────────────────┘
          │                  │                             │
          └──────────────────┼─────────────────────────────┘
                             │
                 ┌───────────▼───────────┐
                 │   SessionDB (db.py)   │
                 │   SQLite persistence  │
                 └───┬───────────────────┘
                     │
     ┌───────────────┼─────────────────────┐
     │               │                     │
┌────▼─────┐  ┌──────▼──────┐  ┌──────────▼──────────┐
│ Dedup    │  │ Extractor   │  │ Classifier           │
│(analysis)│  │(extractor/) │  │(ai/classifier.py)   │
│ SHA-256  │  │ text/pdf/doc│  │ Ollama → category   │
└────┬─────┘  └──────┬──────┘  └──────────┬──────────┘
     │               │                     │
     └───────────────┼─────────────────────┘
                     │
         ┌───────────▼───────────────────────┐
         │  Phase 2 Analysis (analysis/)     │
         │  • embeddings.py — near-dedup     │
         │  • staleness.py — age detection   │
         │  • versions.py — supersession     │
         └───────────┬───────────────────────┘
                     │
         ┌───────────▼───────────────────────┐
         │  Actions (actions/)               │
         │  • mover.py — file organization   │
         │  • archiver.py — create archives  │
         │  • trash.py — staging + recovery  │
         │  • prune.py — empty dir removal   │
         └───────────┬───────────────────────┘
                     │
         ┌───────────▼───────────────────────┐
         │  Report (report/)                 │
         │  • generator.py — Rich terminal   │
         │  • html_generator.py — Jinja2 HTML│
         └───────────────────────────────────┘
```

## Module Responsibilities

### Core (Phase 1)

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Typer CLI: scan, organize, dupes, watch, schedule, status, server commands. |
| `config.py` | Loads `fileforge.toml` into a validated Pydantic `FileForgeConfig`. Handles XDG and legacy config paths. |
| `models.py` | Defines `FileRecord` — the central data object passed through every pipeline stage. |
| `db.py` | SQLite session store. Manages 5 tables: sessions, file_records, action_logs, trash, job_history. All writes go through `SessionDB`. |
| `scanner.py` | Recursive directory walk respecting depth limits and `.forgeignore` patterns. Uses `os.path` for 3.11/3.12 compatibility. |
| `extractor/__init__.py` | Dispatcher: maps file extension to the correct extractor function. Returns `None` on any error (never raises). |
| `extractor/text.py` | Plain text extraction for 33+ extensions with `chardet` encoding detection and BeautifulSoup HTML tag-stripping. |
| `extractor/pdf.py` | PDF extraction via `pdfplumber`, page-by-page with configurable limit. |
| `extractor/docx.py` | DOCX extraction via `python-docx`. |
| `analysis/dedup.py` | SHA-256 file hashing (chunked 64KB) and exact-duplicate grouping. |
| `ai/classifier.py` | Sends content snippet to local Ollama for LLM classification. Degrades to `"uncategorized"` on any error. |
| `report/generator.py` | Rich terminal table with category groups, file counts, and sizes. |

### Advanced Analysis (Phase 2)

| Module | Responsibility |
|--------|----------------|
| `analysis/embeddings.py` | Near-duplicate detection via `nomic-embed-text` embeddings + cosine similarity. Requires `[ann]` extra for hnswlib. |
| `analysis/staleness.py` | Age-based stale detection + junk pattern matching. |
| `analysis/versions.py` | Version supersession detection via regex pattern matching. |

### Actions (Phase 3)

| Module | Responsibility |
|--------|----------------|
| `actions/mover.py` | Move files to organized folder structure with directory creation. |
| `actions/archiver.py` | Create and extract `.tar.gz` archives. |
| `actions/trash.py` | Move files to date-organized trash staging with recovery support. |
| `actions/prune.py` | Remove empty directories after organization runs. |
| `report/html_generator.py` | Interactive HTML report generation via Jinja2 (`templates/report.html`). |

### Background Automation (Phase 4)

| Module | Responsibility |
|--------|----------------|
| `watch/watcher.py` | Filesystem event monitoring via `watchdog` with configurable debouncing. |
| `schedule/job_manager.py` | APScheduler-based cron job management, execution tracking in `job_history`. |
| `systemd/fileforge-scan.service` | Systemd oneshot service for the daily scan. |
| `systemd/fileforge-scan.timer` | Systemd timer: fires daily at 02:00, persistent across reboots. |
| `systemd/fileforge-server.service` | Systemd long-running service for the web UI server. Restarts on failure. |
| `systemd/install.sh` | Installer for the above units into `~/.config/systemd/user/`. |

### Web UI / API (Phase 4+)

| Module | Responsibility |
|--------|----------------|
| `api/server.py` | FastAPI application: REST endpoints, async scan jobs, config management, directory browser. |
| `frontend/index.html` | Vanilla JS single-page application served by the FastAPI server. |
| `templates/report.html` | Jinja2 template for static HTML scan reports. |

## Data Flow — Scan Pipeline

The `fileforge scan` command executes these steps:

**Step 1 — Scanner**

`Scanner.scan()` walks each target directory recursively, respecting `max_depth` and `.forgeignore` patterns. Creates `FileRecord` with path, name, extension, size, and timestamps. Symlinks are not followed.

**Step 2 — Hashing**

`hash_file()` reads each file in 64KB chunks and produces a SHA-256 digest stored in `FileRecord.sha256`.

**Step 3 — Exact Deduplication**

`find_exact_duplicates()` groups records by hash. Groups with >1 member are flagged.

**Step 4 — Extraction**

`extract_snippet()` dispatches to the appropriate extractor based on extension. Returns `None` rather than raising for unreadable files.

**Step 5 — Classification** (unless `--no-classify`)

`classify_file()` sends the snippet to Ollama. Returns a category string (e.g., `code/python`). Stored to `FileRecord.category`.

**Step 6 — Session DB**

`SessionDB.save_records()` bulk-inserts all `FileRecord` objects. `complete_session()` stamps the `completed_at` timestamp.

**Step 7 — Phase 2 Analysis** (if `--phase-2`)

- `compute_embeddings()` generates vectors for near-duplicate detection
- `is_stale()` checks age and junk patterns
- `find_superseded()` identifies outdated versions

**Step 8 — Report**

`print_scan_summary()` renders a Rich table grouped by category with counts and sizes.

## Data Flow — Web UI / Async Scan

The `fileforge server` command starts FastAPI. When a user initiates a scan from the browser:

1. `POST /api/scan` validates directories, builds a `fileforge scan ...` subprocess command, launches it in a thread pool via `asyncio.get_running_loop().run_in_executor()`, and returns a `job_id` immediately.
2. The browser polls `GET /api/job/{job_id}` at intervals until `status` is `"complete"` or `"error"`.
3. On completion, the UI calls `GET /api/session/{session_id}` to load the full file records.

## Data Model — FileRecord

`FileRecord` is a Pydantic v2 model passed through every pipeline stage.

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

Database location: `~/.fileforge/sessions.db` (configurable via `output_dir` in config).

```sql
CREATE TABLE sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    completed_at TEXT,                    -- populated by complete_session()
    root_paths   TEXT NOT NULL,           -- JSON array of scanned dirs
    file_count   INTEGER DEFAULT 0,
    status       TEXT DEFAULT 'scanning'  -- 'scanning', 'complete', 'error'
);

CREATE TABLE file_records (
    id            TEXT PRIMARY KEY,
    session_id    INTEGER NOT NULL REFERENCES sessions(id),
    path          TEXT NOT NULL,
    name          TEXT NOT NULL,
    ext           TEXT NOT NULL,
    size          INTEGER NOT NULL,
    mtime         TEXT NOT NULL,
    ctime         TEXT NOT NULL,
    sha256        TEXT,
    category      TEXT,
    embedding     TEXT,                   -- JSON-serialized float array
    is_duplicate  INTEGER NOT NULL DEFAULT 0,
    is_stale      INTEGER NOT NULL DEFAULT 0,
    is_superseded INTEGER NOT NULL DEFAULT 0,
    snippet       TEXT
);

CREATE TABLE action_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER REFERENCES sessions(id),
    file_id     TEXT,
    action      TEXT NOT NULL,            -- 'move', 'archive', 'trash', 'delete'
    source      TEXT NOT NULL,
    destination TEXT,
    timestamp   TEXT NOT NULL,
    status      TEXT DEFAULT 'success'
);

CREATE TABLE trash (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path TEXT NOT NULL,
    trash_path    TEXT NOT NULL,
    moved_at      TEXT NOT NULL
);

CREATE TABLE job_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    cron_expr  TEXT,
    started_at TEXT NOT NULL,
    ended_at   TEXT,
    status     TEXT,
    file_count INTEGER DEFAULT 0
);
```

## Extractor Dispatch Pattern

`extractor/__init__.py` maintains a `_DISPATCH` dict mapping file extensions to extractor callables. The dispatcher pattern ensures no extractor can crash the scan:

```python
def extract_snippet(path: Path, max_chars: int = 2000) -> str | None:
    ext = path.suffix.lower()
    fn = _DISPATCH.get(ext)
    if fn is None:
        return None
    try:
        return fn(path, max_chars=max_chars)
    except PermissionError:
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
| `PermissionError` (scan) | Log warning, skip file | File excluded from scan |
| `PermissionError` (extract) | Return `None` snippet | Classification uses filename only |
| `UnicodeDecodeError` | Return `None` snippet | Classification uses filename only |
| `OSError` (scan) | Log warning, skip file | File excluded from scan |
| Ollama `ConnectionError` | Log warning, use `"uncategorized"` | No AI classification |
| Generic `Exception` (extract) | Log error, return `None` | File processed with empty snippet |

## Configuration

Config is searched in order:
1. `--config <path>` CLI argument
2. `~/.config/fileforge/fileforge.toml` (XDG)
3. `~/.fileforge/fileforge.toml` (legacy)
4. Built-in defaults (`FileForgeConfig()`)

Override on a per-directory basis with `.forgeignore` files (gitignore syntax).

## Phase Roadmap

| Phase | Status | Scope |
|-------|--------|-------|
| **1** | Complete | Scan, hash, exact dedup, AI classify, Rich report, SQLite |
| **2** | Complete | Near-dedup via embeddings, stale detection, version supersession |
| **3** | Complete | HTML reports, dry-run, trash staging, file actions, action logs |
| **4** | Complete | Watch mode, scheduled scans, systemd, web UI (FastAPI + JS SPA) |
| **5** | Planned | React PWA GUI replacing the vanilla JS SPA |
| **6** | Planned | Cross-device sync for NEXUS multi-Pi platform |
