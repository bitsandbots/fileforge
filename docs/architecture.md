# FileForge — Architecture

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (cli.py)                         │
│                  Typer — scan / status                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │      Scanner (scanner.py) │
              │  recursive walk + ignore  │
              └─────────────┬─────────────┘
                            │ FileRecord list
              ┌─────────────▼─────────────┐
              │      SessionDB (db.py)    │
              │   SQLite — persist scan   │
              └──┬──────────┬─────────────┘
                 │          │
    ┌────────────▼──┐  ┌────▼────────────────────┐
    │  Dedup        │  │  Extractor              │
    │  (dedup.py)   │  │  (extractor/__init__.py)│
    │  SHA-256      │  │  text / pdf / docx      │
    └────────────┬──┘  └────┬────────────────────┘
                 │          │ snippets
                 │    ┌─────▼────────────────┐
                 │    │  Classifier          │
                 │    │  (ai/classifier.py)  │
                 │    │  Ollama qwen3:4b     │
                 │    └─────┬────────────────┘
                 │          │ categories
              ┌──▼──────────▼──────────────────┐
              │   Report (report/generator.py)  │
              │   Rich terminal summary table   │
              └─────────────────────────────────┘
```

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `cli.py` | Entry point. Typer CLI. Orchestrates the full scan pipeline. |
| `config.py` | Loads `fileforge.toml` into a validated Pydantic settings model. Applies `.forgeignore` patterns. |
| `models.py` | Defines `FileRecord` — the central data object passed through every pipeline stage. |
| `db.py` | SQLite session store. Persists scan results; provides CRUD and iterator access. |
| `scanner.py` | Recursive directory walk. Applies depth limits, ignore patterns, and collects `FileRecord` metadata. |
| `extractor/__init__.py` | Dispatcher: maps file extension to the correct extractor module. |
| `extractor/text.py` | Plain text and source code extraction for 33 extensions. Handles encoding detection via chardet. |
| `extractor/pdf.py` | PDF extraction via pdfplumber. Page-by-page up to `max_chars`. |
| `extractor/docx.py` | DOCX extraction via python-docx. Joins paragraphs up to `max_chars`. |
| `analysis/dedup.py` | SHA-256 file hashing (chunked 64KB reads) and exact-duplicate grouping. |
| `ai/classifier.py` | Sends content snippet to local Ollama instance for LLM classification. Parses and normalizes the category response. |
| `report/generator.py` | Renders the post-scan Rich table: category groups, file counts, sizes, reclaimable space. |

## Data Flow — Scan Pipeline

The `fileforge scan` command executes these steps in sequence:

**Step 1 — Scanner**

`Scanner` walks each target directory recursively, subject to `max_depth` and `.forgeignore` patterns. For each file it creates a `FileRecord` with path, name, extension, size, and `mtime`/`ctime`. No content is read at this stage.

**Step 2 — Session DB**

The list of `FileRecord` objects is written to SQLite via `SessionDB`. A session row is created first with scan metadata (timestamp, root paths). File records reference this session ID.

**Step 3 — Hashing**

`hash_file()` reads each file in 64KB chunks and produces a SHA-256 digest. The digest is stored back to `FileRecord.sha256` and updated in the DB.

**Step 4 — Exact Deduplication**

`find_exact_duplicates()` groups the session's file records by hash. Groups with more than one member are flagged as duplicates. The first occurrence in each group is designated the canonical copy.

**Step 5 — Extraction (conditional)**

If `--no-classify` is not set, `extract_snippet()` is called for each file. It dispatches to the appropriate extractor based on extension and returns a text snippet up to `snippet_length` characters.

**Step 6 — Classification (conditional)**

If `--no-classify` is not set, `classify_file()` sends the snippet to Ollama via the chat API. The model returns a category string (e.g., `code/python/scripts`). `parse_category()` normalizes this to a clean path. Results are stored to `FileRecord.category`.

**Step 7 — Report**

`print_scan_summary()` queries the session from SQLite and renders a Rich table grouped by category, with file counts, total sizes, and duplicate space reclaim estimates.

## Data Model — FileRecord

`FileRecord` is a Pydantic v2 dataclass. It is the unit of data passed through every pipeline stage and persisted to SQLite.

| Field | Type | Purpose |
|---|---|---|
| `id` | `str` (UUID) | Unique record identifier |
| `session_id` | `str` | Foreign key to parent scan session |
| `path` | `Path` | Absolute path to the file |
| `name` | `str` | Filename without directory |
| `ext` | `str` | Lowercase file extension (e.g., `.pdf`) |
| `size` | `int` | File size in bytes |
| `mtime` | `datetime` | Last modified timestamp |
| `ctime` | `datetime` | Created/changed timestamp |
| `sha256` | `str \| None` | SHA-256 hex digest; `None` until hashing step |
| `category` | `str \| None` | LLM-assigned category path; `None` if unclassified |
| `embedding` | `list[float] \| None` | Embedding vector; `None` until Phase 2 |
| `is_duplicate` | `bool` | True if another file has the same SHA-256 |
| `is_stale` | `bool` | True if age exceeds `stale_days` (Phase 2) |
| `is_superseded` | `bool` | True if a newer version exists (Phase 2) |
| `snippet` | `str \| None` | Extracted text snippet used for classification |

## SQLite Schema

FileForge uses two tables. Both are created automatically on first run.

```sql
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    root_paths  TEXT NOT NULL,   -- JSON array of scanned dirs
    file_count  INTEGER,
    status      TEXT             -- 'scanning', 'complete', 'error'
);

CREATE TABLE file_records (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES sessions(id),
    path         TEXT NOT NULL,
    name         TEXT NOT NULL,
    ext          TEXT NOT NULL,
    size         INTEGER NOT NULL,
    mtime        TEXT NOT NULL,
    ctime        TEXT NOT NULL,
    sha256       TEXT,
    category     TEXT,
    embedding    TEXT,           -- JSON-serialized float array
    is_duplicate INTEGER NOT NULL DEFAULT 0,
    is_stale     INTEGER NOT NULL DEFAULT 0,
    is_superseded INTEGER NOT NULL DEFAULT 0,
    snippet      TEXT
);
```

The database file lives at `~/.fileforge/fileforge.db` by default (`output_dir` in config).

## Extractor Dispatch Pattern

`extractor/__init__.py` maintains a registry mapping file extensions to extractor callables:

```python
EXTRACTORS: dict[str, Callable[[Path, int], str]] = {
    ".txt":  text.extract,
    ".md":   text.extract,
    ".py":   text.extract,
    # ... 30+ more text/code extensions
    ".pdf":  pdf.extract,
    ".docx": docx.extract,
}

def extract_snippet(path: Path, max_chars: int = 2000) -> str:
    extractor = EXTRACTORS.get(path.suffix.lower())
    if extractor is None:
        return ""
    try:
        return extractor(path, max_chars)
    except Exception:
        return ""
```

**Adding a new extractor:**

1. Create `extractor/myformat.py` with a function `extract(path: Path, max_chars: int) -> str`.
2. Register the extension(s) in the `EXTRACTORS` dict in `extractor/__init__.py`.

No other changes are required. The classifier and pipeline consume snippets uniformly regardless of source format.

## Phase Roadmap

| Phase | Status | Scope |
|---|---|---|
| **1** | Complete | Scan, hash, exact dedup, AI classify, Rich report, SQLite persistence |
| **2** | Planned | Near-dedup via embeddings, stale file detection, superseded version detection |
| **3** | Planned | HTML report with actions, dry-run mode, trash staging, undo |
| **4** | Planned | Watch mode, scheduled scans (systemd / Task Scheduler) |
| **5** | Planned | React PWA GUI, cross-device sync |
