# FileForge — Tech Stack

## Runtime Requirements

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Runtime environment |
| Ollama | Latest | Local LLM inference (optional) |

## Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `typer[all]` | >=0.12 | CLI framework with completion |
| `rich` | >=13 | Terminal formatting and tables |
| `pydantic` | >=2 | Data validation and settings |
| `platformdirs` | >=4 | Cross-platform paths |

## Content Extraction

| Package | Version | Formats Supported |
|---------|---------|-------------------|
| `pdfplumber` | >=0.11 | PDF |
| `python-docx` | >=1 | DOCX, DOC |
| `openpyxl` | >=3 | XLSX, XLS |
| `beautifulsoup4` | >=4 | HTML, XML |
| `chardet` | >=5 | Encoding detection |
| `Pillow` | >=10 | Image processing |

## AI/ML

| Package | Version | Purpose |
|---------|---------|---------|
| `ollama` | >=0.3 | Local LLM inference client |
| `numpy` | >=1.26 | Numerical operations |
| `scipy` | >=1.13 | Cosine similarity for embeddings |

## Background Automation

| Package | Version | Purpose |
|---------|---------|---------|
| `watchdog` | >=4 | Filesystem event monitoring |
| `apscheduler` | >=3.10 | Cron-based job scheduling |

## Optional Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `hnswlib` | >=0.8 | Approximate nearest neighbor (for large datasets) |
| `pytesseract` | >=0.3 | OCR for images (requires Tesseract binary) |

## Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | >=8 | Test framework |
| `pytest-cov` | Latest | Coverage reporting |
| `black` | Latest | Code formatting |
| `ruff` | Latest | Linting |

## Build System

| Tool | Version | Purpose |
|------|---------|---------|
| `hatchling` | Latest | Build backend |
| `build` | Latest | Package builder |
| `twine` | Latest | PyPI publisher |

## Supported File Formats

### Text and Code (33 extensions)

```
.txt .md .rst .log .csv .json .xml .yaml .yml
.py .pyw .js .ts .jsx .tsx .html .css .scss .less
.sh .bash .zsh .fish .ps1
.c .cpp .h .hpp .rs .go .java .kt .swift .rb .php .lua .r .sql
.toml .ini .cfg .conf .env
```

### Documents

```
.pdf .docx .doc .xlsx .xls .pptx .ppt
```

### Web

```
.html .htm .xhtml .xml
```

### Images (OCR with pytesseract)

```
.png .jpg .jpeg .gif .bmp .tiff .webp
```

## System Requirements

### Minimum

- **CPU**: 2 cores
- **RAM**: 2 GB
- **Disk**: 100 MB for FileForge + database
- **Python**: 3.11 or newer

### Recommended (with Ollama)

- **CPU**: 4+ cores
- **RAM**: 8 GB (for local LLM)
- **Disk**: 5-10 GB (for model weights)

### Target Platform

FileForge is designed for Raspberry Pi 5 (8GB) as the reference deployment target. It runs well on modest hardware due to:

- Chunked file hashing (64KB) for memory efficiency
- Iterator-based database access (no full result sets in memory)
- Configurable extraction limits (`max_chars`)
- Lazy loading of embeddings

## Data Storage

| Location | Purpose |
|----------|---------|
| `~/.fileforge/fileforge.db` | SQLite database (scan sessions, file records) |
| `~/.fileforge/fileforge.toml` | User configuration |
| `~/Organized/` | Default organization destination |
| `~/.trash/` | Default trash staging (date-organized) |

## External Services

### Ollama (Local LLM)

- **Default URL**: `http://localhost:11434`
- **Classification Model**: `qwen3:4b` (default)
- **Embedding Model**: `nomic-embed-text` (Phase 2)
- **Memory**: ~2GB for `qwen3:4b`, ~274MB for `nomic-embed-text`

### Model Installation

```bash
# Pull classification model
ollama pull qwen3:4b

# Pull embedding model (Phase 2)
ollama pull nomic-embed-text

# List installed models
ollama list
```

### Fallback Behavior

When Ollama is unavailable:

1. Classification falls back to "Uncategorized"
2. Embedding-based near-duplicate detection is skipped
3. All other features continue normally
4. Warnings logged to console

## Performance Characteristics

| Operation | Time Complexity | Memory |
|-----------|-----------------|--------|
| Directory scan | O(n files) | O(1) iterator |
| SHA-256 hash | O(file size) | 64KB buffer |
| Exact dedup | O(n) | O(n) for hash table |
| Near-dedup | O(n log n) | O(n) for embeddings |
| Classification | O(n files) | O(snippet) per file |
| SQLite query | O(n) | O(result set) |