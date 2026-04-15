# FileForge — API Reference

This document covers the public Python API for each FileForge module. All modules are importable directly if FileForge is installed as a package.

---

## `config.py`

### `FileForgeConfig`

Pydantic v2 settings model. Represents the full configuration for a FileForge run. All fields have defaults; a config file is not required.

```python
class FileForgeConfig(BaseModel):
    # [general]
    scan_dirs: list[Path] = []
    output_dir: Path = Path("~/.fileforge")
    max_depth: int = 0
    max_extract_size: int = 1_048_576

    # [ai]
    classification_model: str = "qwen3:4b"
    embedding_model: str = "nomic-embed-text"
    ollama_url: str = "http://localhost:11434"
    snippet_length: int = 2000
    category_hints: list[str] = []

    # [duplicates]
    similarity_threshold: float = 0.92
    semantic_dedup: bool = False

    # [staleness]
    stale_days: int = 365
    junk_patterns: list[str] = [...]
    temp_patterns: list[str] = [...]
    detect_versions: bool = True

    # [ignore]
    patterns: list[str] = [...]
```

### `load_config()`

```python
def load_config(path: Path | None = None) -> FileForgeConfig
```

Loads configuration from a TOML file and returns a validated `FileForgeConfig` instance.

**Args:**

- `path`: Path to a `fileforge.toml` file. If `None`, looks for `fileforge.toml` in the current working directory. If not found, returns defaults.

**Returns:** `FileForgeConfig` — fully validated settings object.

**Raises:**

- `tomllib.TOMLDecodeError` — if the config file exists but contains invalid TOML.
- `pydantic.ValidationError` — if a config value fails type or constraint validation (e.g., `similarity_threshold` outside 0.0–1.0).

**Usage:**

```python
from fileforge.config import load_config

config = load_config()                        # auto-discover
config = load_config(Path("my.toml"))         # explicit path
print(config.classification_model)            # "qwen3:4b"
```

---

## `models.py`

### `FileRecord`

Pydantic v2 dataclass. Central data object. Created by `Scanner`, updated by hashing, classification, and dedup stages, and persisted by `SessionDB`.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `id` | `str` | UUID4 auto | Unique record identifier |
| `session_id` | `str` | — | Foreign key to parent `Session` |
| `path` | `Path` | — | Absolute path to the file |
| `name` | `str` | — | Filename (no directory) |
| `ext` | `str` | — | Lowercase file extension, e.g. `.pdf` |
| `size` | `int` | — | File size in bytes |
| `mtime` | `datetime` | — | Last modified time (UTC) |
| `ctime` | `datetime` | — | Creation / inode change time (UTC) |
| `sha256` | `str \| None` | `None` | SHA-256 hex digest; populated by hashing step |
| `category` | `str \| None` | `None` | LLM-assigned category path, e.g. `code/python` |
| `embedding` | `list[float] \| None` | `None` | Embedding vector; populated in Phase 2 |
| `is_duplicate` | `bool` | `False` | True if another file in the session has the same SHA-256 |
| `is_stale` | `bool` | `False` | True if `mtime` age exceeds `stale_days` (Phase 2) |
| `is_superseded` | `bool` | `False` | True if a newer version file is detected (Phase 2) |
| `snippet` | `str \| None` | `None` | Extracted text snippet used for classification |

**Usage:**

```python
from fileforge.models import FileRecord
from pathlib import Path
from datetime import datetime

record = FileRecord(
    session_id="abc123",
    path=Path("/home/user/docs/report.pdf"),
    name="report.pdf",
    ext=".pdf",
    size=204800,
    mtime=datetime.utcnow(),
    ctime=datetime.utcnow(),
)
```

---

## `db.py`

### `SessionDB`

SQLite-backed session store. Manages `sessions` and `file_records` tables. Creates the database and schema on first instantiation if they do not exist.

```python
class SessionDB:
    def __init__(self, db_path: Path) -> None
```

**Args:**

- `db_path`: Path to the SQLite file. Created (including parent directories) if it does not exist.

---

#### `SessionDB.create_session()`

```python
def create_session(self, root_paths: list[Path]) -> str
```

Creates a new scan session row and returns its ID.

**Args:**

- `root_paths`: The directories being scanned in this session.

**Returns:** `str` — session UUID.

---

#### `SessionDB.save_record()`

```python
def save_record(self, record: FileRecord) -> None
```

Inserts or replaces a single `FileRecord` in `file_records`.

**Args:**

- `record`: The `FileRecord` to persist.

---

#### `SessionDB.save_records()`

```python
def save_records(self, records: list[FileRecord]) -> None
```

Bulk-inserts a list of `FileRecord` objects using a single transaction.

**Args:**

- `records`: List of `FileRecord` objects to persist.

---

#### `SessionDB.get_session()`

```python
def get_session(self, session_id: str) -> dict | None
```

Retrieves session metadata by ID.

**Returns:** `dict` with session fields, or `None` if not found.

---

#### `SessionDB.iter_records()`

```python
def iter_records(self, session_id: str) -> Iterator[FileRecord]
```

Yields `FileRecord` objects for a session one at a time. Use this for large sessions to avoid loading all records into memory.

**Args:**

- `session_id`: The session to iterate.

**Yields:** `FileRecord` instances.

---

#### `SessionDB.get_latest_session()`

```python
def get_latest_session(self) -> dict | None
```

Returns the most recently created session row, or `None` if no sessions exist.

---

#### `SessionDB.update_record()`

```python
def update_record(self, record: FileRecord) -> None
```

Updates an existing `FileRecord` in place (identified by `record.id`). Used by the hashing and classification steps to write results back without re-inserting.

---

## `scanner.py`

### `Scanner`

Walks one or more directories recursively, respects ignore patterns and depth limits, and returns a list of `FileRecord` objects with path and stat metadata populated.

```python
class Scanner:
    def __init__(
        self,
        ignore_patterns: list[str],
        max_depth: int = 0,
    ) -> None
```

**Args:**

- `ignore_patterns`: Glob patterns (from config `[ignore]` + `.forgeignore`). Files or directories matching any pattern are skipped.
- `max_depth`: Maximum recursion depth. `0` = unlimited.

---

#### `Scanner.from_directory()`

```python
@classmethod
def from_directory(cls, config: FileForgeConfig) -> Scanner
```

Convenience constructor. Builds a `Scanner` from a `FileForgeConfig`, merging config patterns with any `.forgeignore` files found under the scan roots.

---

#### `Scanner.scan()`

```python
def scan(
    self,
    directories: list[Path],
    session_id: str,
) -> list[FileRecord]
```

Recursively walks `directories` and returns a `FileRecord` for every non-ignored file.

**Args:**

- `directories`: Root directories to scan.
- `session_id`: Session ID to attach to each `FileRecord`.

**Returns:** `list[FileRecord]` — one record per file found. `sha256`, `category`, `embedding`, and `snippet` are all `None` at this stage.

**Behavior:**

- Symlinks are not followed.
- Files that cannot be stat'd (permission error, broken link) are logged and skipped.
- A Rich progress bar is displayed to stderr during scanning.

---

## `extractor/__init__.py`

### `extract_snippet()`

```python
def extract_snippet(path: Path, max_chars: int = 2000) -> str
```

Dispatches to the appropriate extractor based on `path.suffix` and returns a text snippet.

**Args:**

- `path`: File to extract from.
- `max_chars`: Maximum characters to return. Extractors truncate at this limit.

**Returns:** Extracted text string, or empty string `""` if:
- No extractor is registered for the extension.
- The extractor raises any exception (logged silently).

**Registered extensions (Phase 1):**

| Extractor | Extensions |
|---|---|
| `text.py` | `.txt`, `.md`, `.rst`, `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.html`, `.htm`, `.css`, `.scss`, `.less`, `.json`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.sh`, `.bash`, `.zsh`, `.fish`, `.ps1`, `.bat`, `.cmd`, `.c`, `.cpp`, `.h`, `.hpp`, `.java`, `.go`, `.rs`, `.rb`, `.php`, `.swift`, `.kt`, `.cs`, `.sql`, `.r` |
| `pdf.py` | `.pdf` |
| `docx.py` | `.docx` |

**Adding a new extractor:**

```python
# extractor/myformat.py
from pathlib import Path

def extract(path: Path, max_chars: int) -> str:
    # Read file, return text up to max_chars
    ...
```

```python
# extractor/__init__.py — add to EXTRACTORS dict
from . import myformat
EXTRACTORS[".myext"] = myformat.extract
```

---

## `analysis/dedup.py`

### `hash_file()`

```python
def hash_file(path: Path, chunk_size: int = 65536) -> str
```

Computes the SHA-256 digest of a file using chunked reads.

**Args:**

- `path`: File to hash.
- `chunk_size`: Read chunk size in bytes. Default 64KB. Adjust for memory-constrained environments.

**Returns:** Lowercase hex string of the SHA-256 digest (64 characters).

**Raises:**

- `OSError` — if the file cannot be opened or read.

**Algorithm:** Opens the file in binary mode, reads `chunk_size` bytes at a time, feeds each chunk to `hashlib.sha256().update()`, returns the final hexdigest. This approach keeps memory usage constant regardless of file size.

---

### `find_exact_duplicates()`

```python
def find_exact_duplicates(
    records: list[FileRecord],
) -> dict[str, list[FileRecord]]
```

Groups `FileRecord` objects by SHA-256 hash and returns only groups with more than one member.

**Args:**

- `records`: List of `FileRecord` objects with `sha256` populated. Records where `sha256 is None` are skipped.

**Returns:** `dict[str, list[FileRecord]]` — maps each hash to the list of duplicate records. Single-instance files are excluded. The first element of each list is considered the canonical copy by convention (not enforced here).

**Usage:**

```python
from fileforge.analysis.dedup import find_exact_duplicates

groups = find_exact_duplicates(records)
for sha256, dupes in groups.items():
    print(f"{sha256[:8]}... — {len(dupes)} copies")
    for r in dupes:
        print(f"  {r.path}")
```

---

## `ai/classifier.py`

### `classify_file()`

```python
def classify_file(
    snippet: str,
    config: FileForgeConfig,
) -> str
```

Sends a text snippet to the local Ollama instance and returns a category string.

**Args:**

- `snippet`: Extracted text content of the file (up to `config.snippet_length` chars).
- `config`: `FileForgeConfig` supplying `ollama_url`, `classification_model`, `snippet_length`, and `category_hints`.

**Returns:** Category string as returned by the model (before normalization). Empty string `""` on failure.

**Prompt strategy:** The system prompt instructs the model to act as a file classification assistant and return only a category path in the form `major/minor/detail` with no explanation. If `category_hints` is non-empty, they are listed in the prompt as preferred taxonomy terms. Temperature is set low (0.1) to reduce variability.

**Error handling:** Any exception from the Ollama HTTP call (connection refused, timeout, model error) is caught and logged. The function returns `""` rather than propagating, allowing the pipeline to continue with unclassified records.

---

### `parse_category()`

```python
def parse_category(raw: str) -> str
```

Normalizes a raw category string returned by the LLM.

**Args:**

- `raw`: Raw string from `classify_file()`, e.g. `"  Documents/Finance/Receipts\n"`.

**Returns:** Cleaned, lowercase, slash-separated category path, e.g. `"documents/finance/receipts"`. Returns `"uncategorized"` if `raw` is empty or cannot be parsed.

**Normalization steps:**

1. Strip leading/trailing whitespace and newlines.
2. Lowercase the entire string.
3. Replace backslashes with forward slashes.
4. Collapse consecutive slashes.
5. Strip leading/trailing slashes.
6. Return `"uncategorized"` if the result is empty.

---

## `report/generator.py`

### `print_scan_summary()`

```python
def print_scan_summary(
    session_id: str,
    db: SessionDB,
    duplicate_groups: dict[str, list[FileRecord]],
) -> None
```

Renders a Rich terminal report summarizing the scan results.

**Args:**

- `session_id`: The session to report on.
- `db`: Open `SessionDB` instance to read records from.
- `duplicate_groups`: Output of `find_exact_duplicates()`.

**Returns:** `None`. Output goes to stdout via Rich's `Console`.

**Output format:**

The report renders two sections:

1. **Category breakdown table** — one row per unique category. Columns: Category, File Count, Total Size. Sorted by total size descending.

2. **Duplicate summary** — count of duplicate groups, total files involved, and estimated reclaimable space (sum of non-canonical copies).

Example output:

```
Scan Summary — 1,247 files in 3 directories

 Category                    Files     Size
 ─────────────────────────── ─────── ──────
 documents/finance            142    890 MB
 code/python                   98    124 MB
 images/photos                 87    2.1 GB
 uncategorized                 44     18 MB
 ...

 Duplicates: 23 groups, 47 files — 1.2 GB reclaimable
```

Rich markup and color are applied automatically based on the terminal's color support.

---

## Phase 3: File Actions and Reports

### `fileforge.actions.mover`

#### `move_file()`

```python
def move_file(source: Path, destination: Path, create_dirs: bool = True) -> None
```

Moves a file to a destination path, creating parent directories if needed.

**Args:**

- `source`: Path to the file to move.
- `destination`: Destination path (full path including filename).
- `create_dirs`: If `True` (default), creates parent directories if they don't exist.

**Raises:**

- `FileNotFoundError` — if source does not exist.
- `OSError` — if the move operation fails (permission denied, disk full, etc.).

---

### `fileforge.actions.archiver`

#### `create_archive()`

```python
def create_archive(source: Path, archive_path: Path) -> None
```

Creates a gzip-compressed tar archive of a file or directory.

**Args:**

- `source`: Path to file or directory to archive.
- `archive_path`: Path where the `.tar.gz` archive will be written.

**Raises:**

- `FileNotFoundError` — if source does not exist.
- `OSError` — if archive creation fails.

---

#### `extract_archive()`

```python
def extract_archive(archive_path: Path, destination: Path) -> None
```

Extracts a `.tar.gz` archive to a destination directory.

**Args:**

- `archive_path`: Path to the `.tar.gz` file.
- `destination`: Directory where contents will be extracted.

**Raises:**

- `FileNotFoundError` — if archive does not exist.
- `OSError` — if extraction fails.

---

### `fileforge.actions.trash`

#### `move_to_trash()`

```python
def move_to_trash(source: Path, trash_dir: Path) -> Path
```

Moves a file to a trash directory with date-based organization (YYYY/MM/DD subdirectories).

**Args:**

- `source`: Path to the file to move to trash.
- `trash_dir`: Root trash directory (e.g., `~/.fileforge/trash`).

**Returns:** `Path` — the destination path in trash.

**Behavior:**

Files are organized as `trash_dir/YYYY/MM/DD/filename`. Parent directories are created as needed.

**Raises:**

- `FileNotFoundError` — if source does not exist.
- `OSError` — if the move fails.

---

#### `restore_from_trash()`

```python
def restore_from_trash(trash_path: Path, original_path: Path) -> None
```

Restores a file from trash back to its original location.

**Args:**

- `trash_path`: Path to the file in the trash directory.
- `original_path`: Original file path to restore to.

**Raises:**

- `FileNotFoundError` — if trash_path does not exist.
- `OSError` — if restoration fails.

---

#### `empty_trash()`

```python
def empty_trash(trash_dir: Path, older_than_days: int = 30) -> int
```

Permanently deletes files in trash that are older than a specified number of days.

**Args:**

- `trash_dir`: Root trash directory.
- `older_than_days`: Files with mtime older than this many days are deleted. Default: 30 days.

**Returns:** `int` — number of files deleted.

**Behavior:**

Walks the trash directory tree, checks file mtime, and deletes files older than the threshold. Empty directories are left in place.

---

### `fileforge.report.html_generator`

#### `generate_html_report()`

```python
def generate_html_report(
    records: list[FileRecord],
    output_path: Path,
    config: FileForgeConfig | None = None,
) -> None
```

Generates an interactive HTML report with per-file action buttons (move, archive, delete).

**Args:**

- `records`: List of `FileRecord` objects to include in the report.
- `output_path`: Path where the HTML file will be written.
- `config`: Optional `FileForgeConfig` for templating. If not provided, defaults are used.

**Returns:** `None`. HTML file is written to `output_path`.

**Behavior:**

Renders a single-page HTML report with:
- File list table showing path, size, category, and duplicate/stale/superseded flags
- Action buttons for each file (move, archive, delete, restore from trash)
- Search/filter interface
- Summary statistics

**Raises:**

- `OSError` — if the output file cannot be written.

---

## Phase 3: Dry-Run and Action Logging

### `fileforge.actions.logger`

#### `ActionLog` (dataclass)

```python
@dataclass
class ActionLog:
    id: str
    session_id: str
    timestamp: datetime
    action_type: str  # "move", "archive", "delete", "restore"
    source_path: Path
    destination_path: Path | None
    status: str  # "pending", "success", "failed"
    error_message: str | None = None
```

Represents a single file action (move, archive, delete, restore) with its execution status.

---

#### `log_action()`

```python
def log_action(
    db: SessionDB,
    session_id: str,
    action_type: str,
    source_path: Path,
    destination_path: Path | None = None,
    status: str = "pending",
    error_message: str | None = None,
) -> str
```

Records a file action to the database for undo support and audit trail.

**Args:**

- `db`: Open `SessionDB` instance.
- `session_id`: Session ID to associate with the action.
- `action_type`: Type of action: `"move"`, `"archive"`, `"delete"`, or `"restore"`.
- `source_path`: Original file path.
- `destination_path`: New location (for move/archive) or `None` (for delete/restore).
- `status`: Initial status (`"pending"`, `"success"`, `"failed"`).
- `error_message`: Optional error details if status is `"failed"`.

**Returns:** `str` — action ID (UUID).

**Behavior:**

Inserts a new row into the `action_logs` table. Used by the interactive report to track what the user has requested.

---

#### `undo_action()`

```python
def undo_action(db: SessionDB, action_id: str) -> None
```

Reverses the effect of a previously logged action.

**Args:**

- `db`: Open `SessionDB` instance.
- `action_id`: ID of the action to undo.

**Behavior:**

- For `"move"` or `"archive"` actions: moves the file back to its source.
- For `"delete"` actions: restores from trash if still available.
- For `"restore"` actions: moves back to trash.

**Raises:**

- `ValueError` — if action_id not found.
- `OSError` — if the file can no longer be found or moved.
