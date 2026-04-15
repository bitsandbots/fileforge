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
