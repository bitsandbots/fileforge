# FileForge — API Reference

This document covers the public Python API and REST API for FileForge. All Python modules are importable directly when FileForge is installed as a package.

---

## REST API (`api/server.py`)

Start the server with `fileforge server` (default: `http://localhost:8082`).

### `GET /api/health`

Health check. Returns server version.

```json
{ "status": "ok", "version": "0.1.7" }
```

---

### `POST /api/scan`

Start an asynchronous scan job. Returns immediately with a `job_id`.

**Request body:**

```json
{
  "directories": ["~/Documents", "/home/user/Downloads"],
  "no_classify": false,
  "phase_2": false,
  "dry_run": false
}
```

**Response:**

```json
{
  "success": true,
  "message": "Scan started",
  "job_id": "a1b2c3d4e5"
}
```

**Errors:**

- `400` — one or more directories do not exist
- `409` — a scan is already running

**Notes:** Directories with `~` are expanded server-side. Only one concurrent scan is permitted.

---

### `GET /api/job/{job_id}`

Poll for scan job status.

**Response (running):**

```json
{ "status": "running", "session_id": null, "error": null }
```

**Response (complete):**

```json
{ "status": "complete", "session_id": 42 }
```

**Response (error):**

```json
{ "status": "error", "error": "Scan exited with non-zero status: ..." }
```

---

### `GET /api/stats`

Returns aggregate statistics from the most recent scan. Includes up to 100 file records.

```json
{
  "total_files": 1247,
  "total_size": 2147483648,
  "duplicates": 47,
  "duplicates_size": 524288000,
  "stale": 23,
  "categories": 12,
  "records": [ /* up to 100 FileRecord objects */ ]
}
```

---

### `GET /api/sessions`

Lists all scan sessions ordered by creation time (newest first).

```json
{
  "sessions": [
    {
      "id": 42,
      "created_at": "2026-05-19T14:30:00",
      "completed_at": "2026-05-19T14:31:15",
      "root_paths": "[\"~/Documents\"]",
      "file_count": 1247,
      "status": "complete"
    }
  ]
}
```

---

### `GET /api/session/{session_id}`

Returns all file records for a specific session.

```json
{
  "session_id": 42,
  "records": [ /* FileRecord objects */ ]
}
```

---

### `GET /api/config`

Returns the current configuration as JSON (mirrors `FileForgeConfig` fields).

---

### `POST /api/config`

Validates and persists a new configuration. Body must be a `FileForgeConfig`-shaped JSON object.

**Response:**

```json
{ "status": "saved", "path": "/home/user/.config/fileforge/fileforge.toml" }
```

---

### `GET /api/browse?path=`

Directory browser for the path-picker widget. Lists non-hidden subdirectories.

**Response:**

```json
{
  "path": "/home/user/Documents",
  "parent": "/home/user",
  "entries": [
    { "name": "Projects", "path": "/home/user/Documents/Projects" },
    { "name": "Reports", "path": "/home/user/Documents/Reports" }
  ]
}
```

**Errors:**

- `404` — path does not exist or is not a directory
- `403` — permission denied

---

---

## Python API

### `config.py`

#### `FileForgeConfig`

Pydantic v2 settings model. All fields have defaults; a config file is not required.

```python
class FileForgeConfig(BaseModel):
    # [general]
    scan_dirs: list[Path] = []
    output_dir: Path = Path("~/.fileforge")
    max_depth: int = 0
    max_extract_size: int = 52_428_800  # 50 MB

    # [ai]
    classification_model: str = "qwen3:4b"
    embedding_model: str = "nomic-embed-text"
    ollama_url: str = "http://localhost:11434"
    snippet_length: int = 2000
    category_hints: str = ""

    # [duplicates]
    similarity_threshold: float = 0.92
    semantic_dedup: bool = True

    # [staleness]
    stale_days: int = 365
    junk_patterns: list[str] = [...]
    temp_patterns: list[str] = [...]
    detect_versions: bool = True

    # [ignore]
    patterns: list[str] = [...]
```

#### `load_config()`

```python
def load_config(path: Path | None = None) -> FileForgeConfig
```

Loads configuration from a TOML file. Searches XDG path → legacy path → defaults if `path` is `None`.

**Raises:** `tomllib.TOMLDecodeError`, `pydantic.ValidationError`

---

### `models.py`

#### `FileRecord`

Pydantic v2 model. Central data object created by `Scanner` and enriched through the pipeline.

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `id` | `str` | UUID4 auto | Unique record identifier |
| `session_id` | `str` | — | Foreign key to parent session |
| `path` | `Path` | — | Absolute path to the file |
| `name` | `str` | — | Filename (no directory) |
| `ext` | `str` | — | Lowercase file extension, e.g. `.pdf` |
| `size` | `int` | — | File size in bytes |
| `mtime` | `datetime` | — | Last modified time |
| `ctime` | `datetime` | — | Creation / inode change time |
| `sha256` | `str \| None` | `None` | SHA-256 hex digest |
| `category` | `str \| None` | `None` | LLM-assigned category path |
| `embedding` | `list[float] \| None` | `None` | Embedding vector (Phase 2) |
| `is_duplicate` | `bool` | `False` | Same SHA-256 as another file in session |
| `is_stale` | `bool` | `False` | Age exceeds `stale_days` (Phase 2) |
| `is_superseded` | `bool` | `False` | Newer version detected (Phase 2) |
| `snippet` | `str \| None` | `None` | Extracted text snippet |

---

### `db.py`

#### `SessionDB`

SQLite-backed session store. Creates the database schema on first instantiation.

```python
class SessionDB:
    def __init__(self, db_path: Path) -> None
```

---

#### `SessionDB.create_session()`

```python
def create_session(self, root_paths: list[Path]) -> int
```

Creates a new scan session row. Returns the integer session ID.

---

#### `SessionDB.save_records()`

```python
def save_records(self, records: list[FileRecord]) -> None
```

Bulk-inserts a list of `FileRecord` objects in a single transaction.

---

#### `SessionDB.complete_session()`

```python
def complete_session(self, session_id: int) -> None
```

Stamps `completed_at` on the session row and sets `status = "complete"`.

---

#### `SessionDB.get_session_records()`

```python
def get_session_records(self, session_id: int) -> list[FileRecord]
```

Returns all `FileRecord` objects for a session.

---

#### `SessionDB.list_sessions()`

```python
def list_sessions(self) -> list[dict]
```

Returns all sessions ordered by creation time, newest first. Each dict includes `id`, `created_at`, `completed_at`, `root_paths`, `file_count`, and `status`.

---

#### `SessionDB.get_stats()`

```python
def get_stats(self) -> dict
```

Returns aggregate statistics across all sessions: `total_files`, `total_size`, `duplicates`, `duplicates_size`, `stale`, `categories`.

---

#### `SessionDB.get_all_records()`

```python
def get_all_records(self, limit: int = 100) -> list[FileRecord]
```

Returns the most recent file records across all sessions, up to `limit`.

---

#### `SessionDB.close()`

```python
def close(self) -> None
```

Closes the underlying SQLite connection. Always call in a `finally` block.

---

### `scanner.py`

#### `Scanner`

```python
class Scanner:
    def __init__(
        self,
        ignore_patterns: list[str],
        max_depth: int = 0,
    ) -> None
```

#### `Scanner.scan()`

```python
def scan(
    self,
    directories: list[Path],
    session_id: str,
) -> list[FileRecord]
```

Recursively walks `directories`. Returns one `FileRecord` per file found. `sha256`, `category`, `embedding`, and `snippet` are all `None` at this stage. Symlinks are not followed. Files that cannot be stat'd are logged and skipped.

---

### `extractor/__init__.py`

#### `extract_snippet()`

```python
def extract_snippet(path: Path, max_chars: int = 2000) -> str | None
```

Dispatches to the appropriate extractor based on file extension. Returns `None` if no extractor is registered or any error occurs (never raises).

**Registered extensions:**

| Extractor | Extensions |
|-----------|------------|
| `text.py` | `.txt .md .rst .log .csv .json .xml .yaml .yml .py .pyw .js .ts .jsx .tsx .html .htm .css .scss .less .sh .bash .zsh .fish .ps1 .bat .cmd .c .cpp .h .hpp .rs .go .java .kt .swift .rb .php .lua .r .sql .toml .ini .cfg .conf .env` |
| `pdf.py` | `.pdf` |
| `docx.py` | `.docx` |

---

### `analysis/dedup.py`

#### `hash_file()`

```python
def hash_file(path: Path, chunk_size: int = 65536) -> str
```

Computes SHA-256 of a file using chunked reads. Returns lowercase hex string (64 chars). Raises `OSError` if the file cannot be read.

---

#### `find_exact_duplicates()`

```python
def find_exact_duplicates(
    records: list[FileRecord],
) -> dict[str, list[FileRecord]]
```

Groups records by `sha256`. Returns only groups with more than one member. Records with `sha256 = None` are skipped.

---

### `ai/classifier.py`

#### `classify_file()`

```python
def classify_file(
    snippet: str,
    config: FileForgeConfig,
) -> str
```

Sends a snippet to Ollama and returns a raw category string. Returns `""` on any error.

---

#### `parse_category()`

```python
def parse_category(raw: str) -> str
```

Normalizes a raw LLM category string: strips whitespace, lowercases, normalizes slashes. Returns `"uncategorized"` if empty.

---

### `report/generator.py`

#### `print_scan_summary()`

```python
def print_scan_summary(
    session_id: int,
    db: SessionDB,
    duplicate_groups: dict[str, list[FileRecord]],
) -> None
```

Renders a Rich terminal report grouped by category.

---

### `actions/mover.py`

#### `move_file()`

```python
def move_file(source: Path, destination: Path, create_dirs: bool = True) -> None
```

Moves a file, creating parent directories if `create_dirs=True`.

---

### `actions/archiver.py`

#### `create_archive()`

```python
def create_archive(source: Path, archive_path: Path) -> None
```

Creates a `.tar.gz` archive of a file or directory.

---

#### `extract_archive()`

```python
def extract_archive(archive_path: Path, destination: Path) -> None
```

Extracts a `.tar.gz` to `destination`.

---

### `actions/trash.py`

#### `move_to_trash()`

```python
def move_to_trash(source: Path, trash_dir: Path) -> Path
```

Moves a file to `trash_dir/YYYY/MM/DD/filename`. Returns the trash path.

---

#### `restore_from_trash()`

```python
def restore_from_trash(trash_path: Path, original_path: Path) -> None
```

Restores a file from trash to its original location.

---

#### `empty_trash()`

```python
def empty_trash(trash_dir: Path, older_than_days: int = 30) -> int
```

Deletes files in trash older than `older_than_days`. Returns count deleted.

---

### `report/html_generator.py`

#### `generate_html_report()`

```python
def generate_html_report(
    records: list[FileRecord],
    output_path: Path,
    config: FileForgeConfig | None = None,
) -> None
```

Generates a static HTML report from `templates/report.html` (Jinja2). Written to `output_path`.
