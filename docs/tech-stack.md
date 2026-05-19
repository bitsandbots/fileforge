# FileForge — Tech Stack

## Runtime Requirements

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Runtime environment |
| Ollama | Latest | Local LLM inference (optional — degrades gracefully) |

## Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `typer[all]` | >=0.12 | CLI framework with shell completion |
| `rich` | >=13 | Terminal formatting and progress display |
| `pydantic` | >=2 | Data validation and settings |
| `platformdirs` | >=4 | Cross-platform data directory resolution |
| `packaging` | >=26.2 | Metadata-Version 2.4 wheel support |

## Content Extraction

| Package | Version | Formats Supported |
|---------|---------|-------------------|
| `pdfplumber` | >=0.11 | PDF |
| `python-docx` | >=1 | DOCX |
| `openpyxl` | >=3 | XLSX (dependency only; extractor planned) |
| `beautifulsoup4` | >=4 | HTML parsing (used in text extractor) |
| `chardet` | >=5 | Encoding detection for text files |
| `Pillow` | >=10 | Image processing (dep only; OCR extractor planned) |
| `Jinja2` | >=3 | HTML report generation |

## Web UI / Server

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | >=0.115 | REST API and web UI server |
| `uvicorn` | >=0.32 | ASGI server for FastAPI |

## AI/ML

| Package | Version | Purpose |
|---------|---------|---------|
| `ollama` | >=0.3 | Local LLM inference client |
| `numpy` | >=1.26 | Numerical operations |
| `scipy` | >=1.13 | Cosine similarity for embedding comparison |

## Background Automation

| Package | Version | Purpose |
|---------|---------|---------|
| `watchdog` | >=4 | Filesystem event monitoring |
| `apscheduler` | >=3.10 | Cron-based job scheduling |

## Optional Dependencies

| Package | Extra | Purpose |
|---------|-------|---------|
| `hnswlib` | `[ann]` | Approximate nearest-neighbor for large embedding sets |
| `pytesseract` | `[ocr]` | OCR for images (requires Tesseract binary; extractor planned) |

Install extras:

```bash
pip install "fileforge[ann]"    # ANN similarity indexing
pip install "fileforge[ocr]"    # OCR extraction
pip install "fileforge[dev]"    # pytest, black, ruff
```

## Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | >=8 | Test framework |
| `pytest-cov` | Latest | Coverage reporting |
| `black` | Latest | Code formatting (88 char line length) |
| `ruff` | Latest | Linting (E, F, I, UP rules) |

## Build System

| Tool | Version | Purpose |
|------|---------|---------|
| `hatchling` | Latest | Build backend |
| `build` | Latest | Package builder |
| `twine` | Latest | PyPI publisher |

## Supported File Formats

### Text and Code (handled by `extractor/text.py`)

```
.txt .md .rst .log .csv .json .xml .yaml .yml
.py .pyw .js .ts .jsx .tsx .css .scss .less
.sh .bash .zsh .fish .ps1 .bat .cmd
.c .cpp .h .hpp .rs .go .java .kt .swift .rb .php .lua .r .sql
.toml .ini .cfg .conf .env
```

HTML files are also handled via text.py with beautifulsoup4 for tag stripping.

### Documents

```
.pdf    — via pdfplumber
.docx   — via python-docx
```

### Planned / Dependency Installed

```
.xlsx .xls  — openpyxl installed; dedicated extractor not yet implemented
.png .jpg .jpeg .bmp .tiff .webp  — Pillow installed; OCR extractor not yet implemented
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
- **Disk**: 5–10 GB (for model weights)

### Target Platform

FileForge is designed for Raspberry Pi 5 (8GB) as the reference deployment target. It runs well on modest hardware due to:

- Chunked file hashing (64KB) for constant memory use
- Iterator-based database access (no full result sets in memory)
- Configurable extraction limits (`max_extract_size`)
- Lazy loading of embeddings

## Data Storage

| Location | Purpose |
|----------|---------|
| `~/.fileforge/sessions.db` | SQLite database (sessions, file records, action logs) |
| `~/.config/fileforge/fileforge.toml` | User configuration (XDG path) |
| `~/.fileforge/fileforge.toml` | Legacy config fallback |
| `~/Organized/` | Default organization destination |
| `~/.fileforge/trash/` | Default trash staging (date-organized) |

## External Services

### Ollama (Local LLM)

- **Default URL**: `http://localhost:11434`
- **Classification Model**: `qwen3:4b` (default; ~2.5 GB)
- **Embedding Model**: `nomic-embed-text` (Phase 2; ~270 MB)

```bash
ollama pull qwen3:4b
ollama pull nomic-embed-text
ollama list
```

When Ollama is unavailable, classification falls back to `"uncategorized"` and embedding-based dedup is skipped. All other features continue normally.

## Performance Characteristics

| Operation | Time Complexity | Memory |
|-----------|-----------------|--------|
| Directory scan | O(n files) | O(1) iterator |
| SHA-256 hash | O(file size) | 64 KB buffer |
| Exact dedup | O(n) | O(n) hash table |
| Near-dedup | O(n log n) | O(n) embeddings |
| AI classification | O(n files) | O(snippet) per file |
| SQLite query | O(n) | O(result set) |
