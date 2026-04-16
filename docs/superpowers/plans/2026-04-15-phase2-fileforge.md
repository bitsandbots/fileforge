# FileForge Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three advanced analysis capabilities — near-duplicate detection via embeddings, stale file flagging, and version supersession detection — integrated into the scan report.

**Architecture:** Phase 2 adds three independent analysis modules (`analysis/embeddings.py`, `analysis/staleness.py`, `analysis/versions.py`), each with its own test suite. The scan command gains a `--phase-2` flag to enable these analyses. Embeddings are cached in the database to avoid recomputation.

**Tech Stack:** 
- `nomic-embed-text` Ollama model for embeddings
- `hnswlib` for HNSW similarity indexing
- Scipy's cosine similarity for threshold filtering
- Pydantic validators for version patterns
- SQLite for embedding storage

---

## File Structure

**Create:**
- `src/fileforge/analysis/embeddings.py` — Generate and cache embeddings, query similarity
- `src/fileforge/analysis/staleness.py` — Detect stale files by age and pattern
- `src/fileforge/analysis/versions.py` — Detect version patterns and supersession
- `tests/test_embeddings.py` — Embedding generation and similarity
- `tests/test_staleness.py` — Staleness detection logic
- `tests/test_versions.py` — Version pattern matching and ordering

**Modify:**
- `src/fileforge/cli.py` — Add `--phase-2` flag to scan command
- `src/fileforge/db.py` — Add `update_embedding` and `query_records_without_embeddings` methods
- `src/fileforge/models.py` — Ensure `embedding` field is present (already is)
- `src/fileforge/report/generator.py` — Add sections for near-dupes, stale files, superseded versions

---

## Phase 2 Task Breakdown

### Task 1: Staleness Detection (Simplest, No Dependencies)

**Files:**
- Create: `src/fileforge/analysis/staleness.py`
- Create: `tests/test_staleness.py`
- Modify: `src/fileforge/cli.py` (add phase-2 flag and integration at end)

- [ ] **Step 1: Write failing test for stale detection by age**

```python
# tests/test_staleness.py
from datetime import UTC, datetime, timedelta
from fileforge.analysis.staleness import is_stale
from fileforge.models import FileRecord

def test_is_stale_by_age() -> None:
    """File older than stale_days threshold is marked stale."""
    old_date = datetime.now(UTC) - timedelta(days=400)
    record = FileRecord(
        path=Path("HARNESS_old.txt"),
        name="HARNESS_old.txt",
        extension=".txt",
        size_bytes=100,
        modified_at=old_date,
        created_at=old_date,
    )
    assert is_stale(record, stale_days=365) is True
```

- [ ] **Step 2: Run test, verify it fails**

```bash
python -m pytest tests/test_staleness.py::test_is_stale_by_age -v
```

Expected: `FAILED — ImportError: cannot import name 'is_stale'`

- [ ] **Step 3: Write minimal `is_stale` function**

```python
# src/fileforge/analysis/staleness.py
"""Stale and outdated file detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fileforge.models import FileRecord


def is_stale(record: FileRecord, stale_days: int) -> bool:
    """Check if a file is older than the stale threshold.

    Args:
        record: FileRecord to check.
        stale_days: Threshold in days. -1 means never stale.

    Returns:
        True if file is older than stale_days, False otherwise.
    """
    if stale_days < 0:
        return False
    
    age = (datetime.now(UTC) - record.modified_at).days
    return age > stale_days
```

- [ ] **Step 4: Run test, verify it passes**

```bash
python -m pytest tests/test_staleness.py::test_is_stale_by_age -v
```

Expected: `PASSED`

- [ ] **Step 5: Add test for pattern matching**

```python
def test_is_stale_by_pattern() -> None:
    """File matching junk pattern is marked stale."""
    from fileforge.analysis.staleness import matches_junk_pattern
    
    assert matches_junk_pattern("Thumbs.db", junk_patterns=["Thumbs.db"]) is True
    assert matches_junk_pattern("file.txt", junk_patterns=["Thumbs.db"]) is False
    assert matches_junk_pattern("backup~", junk_patterns=["~$*"]) is True
```

- [ ] **Step 6: Implement `matches_junk_pattern`**

```python
def matches_junk_pattern(filename: str, junk_patterns: list[str]) -> bool:
    """Check if filename matches any junk pattern.

    Args:
        filename: Name to check.
        junk_patterns: fnmatch-style patterns.

    Returns:
        True if filename matches any pattern.
    """
    import fnmatch
    return any(fnmatch.fnmatch(filename, p) for p in junk_patterns)
```

- [ ] **Step 7: Commit**

```bash
git add src/fileforge/analysis/staleness.py tests/test_staleness.py
git commit -m "feat: add stale file detection (age + pattern matching)"
```

---

### Task 2: Version Pattern Detection

**Files:**
- Create: `src/fileforge/analysis/versions.py`
- Create: `tests/test_versions.py`

- [ ] **Step 1: Write failing test for version extraction**

```python
# tests/test_versions.py
from fileforge.analysis.versions import extract_version

def test_extract_version_simple() -> None:
    """Extract version from simple pattern: name_v1.ext, name_v2.ext."""
    assert extract_version("report_v1.docx") == (1, 0, 0)
    assert extract_version("report_v2.docx") == (2, 0, 0)
    assert extract_version("project_final.pdf") is None
    assert extract_version("file_v1.2.3.txt") == (1, 2, 3)
    assert extract_version("v2024_01_15.txt") is None  # date pattern, not version
```

- [ ] **Step 2: Run test, verify fails**

```bash
python -m pytest tests/test_versions.py::test_extract_version_simple -v
```

Expected: `FAILED — ImportError`

- [ ] **Step 3: Implement version extraction**

```python
# src/fileforge/analysis/versions.py
"""Version pattern detection and supersession analysis."""

from __future__ import annotations

import re
from pathlib import Path


def extract_version(filename: str) -> tuple[int, int, int] | None:
    """Extract semantic version from filename.

    Looks for patterns like: name_v1, name_v1.2, name_v1.2.3, or just vX.Y.Z.

    Args:
        filename: The filename to parse.

    Returns:
        (major, minor, patch) tuple, or None if no version found.
    """
    name = Path(filename).stem  # Remove extension
    
    # Pattern: _vX or _vX.Y or _vX.Y.Z
    match = re.search(r'_v(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:_|$)', name)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2) or 0)
        patch = int(match.group(3) or 0)
        return (major, minor, patch)
    
    return None
```

- [ ] **Step 4: Run test, verify passes**

```bash
python -m pytest tests/test_versions.py::test_extract_version_simple -v
```

Expected: `PASSED`

- [ ] **Step 5: Add test for supersession detection**

```python
def test_find_superseded_versions() -> None:
    """Older versions are marked as superseded by newer ones."""
    from fileforge.analysis.versions import find_superseded_versions
    from fileforge.models import FileRecord
    from datetime import UTC, datetime
    from pathlib import Path
    
    v1 = FileRecord(
        path=Path("report_v1.docx"),
        name="report_v1.docx",
        extension=".docx",
        size_bytes=100,
        modified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    v2 = FileRecord(
        path=Path("report_v2.docx"),
        name="report_v2.docx",
        extension=".docx",
        size_bytes=120,
        modified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    
    superseded = find_superseded_versions([v1, v2])
    # v1 is superseded by v2 (same stem, higher version)
    assert v1 in superseded
    assert v2 not in superseded
```

- [ ] **Step 6: Implement supersession detection**

```python
def find_superseded_versions(records: list[FileRecord]) -> list[FileRecord]:
    """Find records that are superseded by higher versions of the same file.

    Args:
        records: List of FileRecords to analyze.

    Returns:
        List of records that have a newer version in the same group.
    """
    from collections import defaultdict
    from pathlib import Path
    
    by_stem: dict[str, list[tuple[FileRecord, tuple[int, int, int]]]] = defaultdict(list)
    
    for record in records:
        stem = Path(record.path).stem
        # Remove _vX suffix to get base name
        base_stem = re.sub(r'_v\d+(?:\.\d+)*$', '', stem)
        version = extract_version(record.name) or (0, 0, 0)
        by_stem[base_stem].append((record, version))
    
    superseded = []
    for base_stem, candidates in by_stem.items():
        if len(candidates) > 1:
            # Sort by version, descending
            candidates.sort(key=lambda x: x[1], reverse=True)
            # All except the latest are superseded
            for record, _ in candidates[1:]:
                superseded.append(record)
    
    return superseded
```

- [ ] **Step 7: Commit**

```bash
git add src/fileforge/analysis/versions.py tests/test_versions.py
git commit -m "feat: add version pattern detection and supersession analysis"
```

---

### Task 3: Embedding Generation and Caching

**Files:**
- Create: `src/fileforge/analysis/embeddings.py`
- Create: `tests/test_embeddings.py`
- Modify: `src/fileforge/db.py` (add methods to store/retrieve embeddings)

- [ ] **Step 1: Add DB methods for embeddings**

In `src/fileforge/db.py`, add:

```python
def update_embedding(self, record_id: int, embedding: list[float]) -> None:
    """Store embedding for a record.

    Args:
        record_id: The record's integer ID.
        embedding: List of float values.
    """
    embedding_json = json.dumps(embedding)
    self._conn.execute(
        "UPDATE file_records SET embedding = ? WHERE id = ?",
        (embedding_json, record_id),
    )
    self._conn.commit()

def query_records_without_embeddings(
    self, session_id: int
) -> Iterator[FileRecord]:
    """Yield all records for a session that don't have embeddings yet.

    Args:
        session_id: The session to query.
    """
    cur = self._conn.execute(
        "SELECT * FROM file_records WHERE session_id = ? AND embedding IS NULL",
        (session_id,),
    )
    for row in cur:
        yield self._row_to_record(row)
```

- [ ] **Step 2: Verify DB changes don't break tests**

```bash
python -m pytest tests/test_db.py -v
```

Expected: All pass

- [ ] **Step 3: Write failing test for embedding generation**

```python
# tests/test_embeddings.py
from fileforge.analysis.embeddings import generate_embedding

def test_generate_embedding_returns_vector() -> None:
    """generate_embedding returns a list of floats."""
    # Use a short, deterministic text
    embedding = generate_embedding("consulting proposal", model="nomic-embed-text")
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)
```

- [ ] **Step 4: Implement minimal embedding generation**

```python
# src/fileforge/analysis/embeddings.py
"""Embedding-based similarity detection for near-duplicates."""

from __future__ import annotations

import logging
from pathlib import Path

import ollama

_log = logging.getLogger(__name__)


def generate_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    """Generate an embedding for text using Ollama.

    Args:
        text: Text to embed.
        model: Ollama model name.

    Returns:
        List of floats representing the embedding.
        Returns empty list on error (graceful degradation).
    """
    if not text or not text.strip():
        return []
    
    try:
        response = ollama.embeddings(
            model=model,
            prompt=text,
        )
        return response.get("embedding", [])
    except (ollama.ResponseError, ollama.RequestError, ConnectionError, TimeoutError):
        _log.warning("Ollama unavailable for embedding; skipping")
        return []
```

- [ ] **Step 5: Run test, verify passes (may need mock if Ollama unavailable)**

```bash
python -m pytest tests/test_embeddings.py::test_generate_embedding_returns_vector -v
```

If it fails due to Ollama unavailable, update test to mock:

```python
from unittest.mock import patch

def test_generate_embedding_returns_vector() -> None:
    """generate_embedding returns a list of floats."""
    mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    with patch("fileforge.analysis.embeddings.ollama.embeddings") as mock_emb:
        mock_emb.return_value = {"embedding": mock_embedding}
        embedding = generate_embedding("test text", model="nomic-embed-text")
        assert embedding == mock_embedding
```

- [ ] **Step 6: Add test for similarity search**

```python
def test_find_near_duplicates() -> None:
    """Near-duplicate detection finds similar content."""
    from fileforge.analysis.embeddings import find_near_duplicates
    from fileforge.models import FileRecord
    from datetime import UTC, datetime
    from pathlib import Path
    
    # Two similar records with embeddings
    similar_embedding = [0.9, 0.85, 0.8, 0.75, 0.7]
    
    record1 = FileRecord(
        path=Path("doc1.txt"),
        name="doc1.txt",
        extension=".txt",
        size_bytes=100,
        modified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        embedding=[0.9, 0.85, 0.8, 0.75, 0.7],
    )
    record2 = FileRecord(
        path=Path("doc2.txt"),
        name="doc2.txt",
        extension=".txt",
        size_bytes=105,
        modified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        embedding=[0.89, 0.84, 0.79, 0.74, 0.69],  # Very similar
    )
    
    groups = find_near_duplicates([record1, record2], threshold=0.85)
    assert len(groups) == 1
    assert len(groups[0]) == 2
```

- [ ] **Step 7: Implement similarity search**

```python
def find_near_duplicates(
    records: list[FileRecord],
    threshold: float = 0.92,
) -> list[list[FileRecord]]:
    """Group records with similar embeddings.

    Uses cosine similarity. Records without embeddings are excluded.

    Args:
        records: FileRecords with embeddings.
        threshold: Similarity threshold (0-1). 1.0 = identical, 0.5 = moderate.

    Returns:
        List of groups. Each group has 2+ similar records.
    """
    from scipy.spatial.distance import cosine
    from collections import defaultdict
    
    # Filter to records with embeddings
    with_embeddings = [r for r in records if r.embedding]
    if len(with_embeddings) < 2:
        return []
    
    groups: dict[int, list[FileRecord]] = defaultdict(list)
    used = set()
    
    for i, record_a in enumerate(with_embeddings):
        if i in used:
            continue
        
        group = [record_a]
        used.add(i)
        
        for j in range(i + 1, len(with_embeddings)):
            if j in used:
                continue
            record_b = with_embeddings[j]
            
            # Cosine similarity = 1 - cosine distance
            similarity = 1 - cosine(record_a.embedding, record_b.embedding)
            if similarity >= threshold:
                group.append(record_b)
                used.add(j)
        
        if len(group) > 1:
            groups[i] = group
    
    return list(groups.values())
```

- [ ] **Step 8: Commit**

```bash
git add src/fileforge/analysis/embeddings.py tests/test_embeddings.py src/fileforge/db.py
git commit -m "feat: add embedding generation and near-duplicate detection"
```

---

### Task 4: Integrate Phase 2 Analyses into Scan Command

**Files:**
- Modify: `src/fileforge/cli.py` (add `--phase-2` flag and orchestration)
- Modify: `src/fileforge/report/generator.py` (add output sections)

- [ ] **Step 1: Add `--phase-2` flag to scan command**

In `src/fileforge/cli.py`, modify the `scan` function signature:

```python
@app.command()
def scan(
    dirs: list[str] = typer.Argument(help="Directories to scan"),
    config: Path = typer.Option(None, help="Config file path"),
    no_classify: bool = typer.Option(
        False, "--no-classify", help="Skip AI classification (hash + dedup only)"
    ),
    phase_2: bool = typer.Option(
        False, "--phase-2", help="Enable Phase 2 analyses (stale, versions, near-dupes)"
    ),
) -> None:
```

- [ ] **Step 2: Add staleness detection after classification**

In the `scan` function, after the classification block and before `print_scan_summary`:

```python
        # Phase 2: Staleness detection
        if phase_2:
            from fileforge.analysis.staleness import is_stale, matches_junk_pattern
            
            console.print("Detecting stale files...")
            for i, record in enumerate(hashed_records):
                is_stale_age = is_stale(record, cfg.staleness.stale_days)
                is_junk = matches_junk_pattern(record.name, cfg.staleness.junk_patterns)
                
                if is_stale_age or is_junk:
                    reason = "older than threshold" if is_stale_age else "matches junk pattern"
                    if record.id is not None:
                        db.update_stale(record.id, reason)
                    hashed_records[i] = record.model_copy(
                        update={"is_stale": True, "stale_reason": reason}
                    )
```

(Note: You'll need to add `update_stale` method to `db.py` similar to `update_category`)

- [ ] **Step 3: Add version detection**

After staleness block:

```python
        # Phase 2: Version supersession detection
        if phase_2:
            from fileforge.analysis.versions import find_superseded_versions
            
            console.print("Detecting version patterns...")
            superseded = find_superseded_versions(hashed_records)
            for record in superseded:
                if record.id is not None:
                    db.update_stale(record.id, "superseded by newer version")
                hashed_records = [
                    r.model_copy(update={"is_stale": True, "stale_reason": "superseded"})
                    if r.id == record.id else r
                    for r in hashed_records
                ]
```

- [ ] **Step 4: Add embedding generation and similarity**

After version block:

```python
        # Phase 2: Near-duplicate detection via embeddings
        if phase_2:
            from fileforge.analysis.embeddings import generate_embedding, find_near_duplicates
            
            console.print("Generating embeddings for near-duplicate detection...")
            embedding_count = 0
            for record in hashed_records:
                if record.embedding is None:
                    snippet = extract_snippet(record.path, max_chars=500)
                    if snippet:
                        record.embedding = generate_embedding(snippet)
                        if record.embedding and record.id is not None:
                            db.update_embedding(record.id, record.embedding)
                            embedding_count += 1
            
            console.print(f"Generated {embedding_count} embeddings")
            
            near_dupes = find_near_duplicates(
                hashed_records,
                threshold=cfg.duplicates.similarity_threshold,
            )
```

- [ ] **Step 5: Update report generator to show Phase 2 results**

In `src/fileforge/report/generator.py`, modify `print_scan_summary` to accept Phase 2 data:

```python
def print_scan_summary(
    console: Console,
    records: list[FileRecord],
    dup_groups: list[list[FileRecord]],
    stale_records: list[FileRecord] | None = None,
    near_dup_groups: list[list[FileRecord]] | None = None,
) -> None:
    """Print scan summary with optional Phase 2 results."""
    # ... existing code ...
    
    if stale_records:
        console.print("\n[bold]Stale Files[/bold]")
        for record in stale_records:
            console.print(f"  {record.name} ({record.stale_reason})")
    
    if near_dup_groups:
        console.print("\n[bold]Near-Duplicates[/bold]")
        for i, group in enumerate(near_dup_groups, 1):
            console.print(f"  Group {i}: {len(group)} similar files")
            for record in group:
                console.print(f"    - {record.path}")
```

- [ ] **Step 6: Update scan command to pass Phase 2 data to reporter**

Before `print_scan_summary` call:

```python
        stale = [r for r in hashed_records if r.is_stale]
        near_dupes = [] if not phase_2 else near_dupes
        
        print_scan_summary(
            console,
            hashed_records,
            dup_groups,
            stale_records=stale if phase_2 else None,
            near_dup_groups=near_dupes if phase_2 else None,
        )
```

- [ ] **Step 7: Run all tests to ensure integration works**

```bash
python -m pytest -q
```

Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add src/fileforge/cli.py src/fileforge/db.py src/fileforge/report/generator.py
git commit -m "feat: integrate Phase 2 analyses into scan pipeline

- Add --phase-2 flag to enable advanced analyses
- Wire up staleness, version, and embedding detection
- Update report output with Phase 2 findings"
```

---

### Task 5: Documentation and Final Testing

**Files:**
- Modify: `docs/overview.md`
- Modify: `docs/setup.md`

- [ ] **Step 1: Update Phase documentation in overview.md**

Replace the Phase 2 section:

```markdown
### Phase 2 — Complete

- Near-duplicate detection via `nomic-embed-text` embeddings + hnswlib + cosine similarity (threshold: 0.92 by default)
- Stale/outdated file flagging based on modification age (configurable stale_days, default 365) and junk patterns (Thumbs.db, *.tmp, etc.)
- Superseded version detection via pattern matching (e.g., `report_v1.docx` vs `report_v2.docx`)
- Enabled with `--phase-2` flag; opt-in to avoid performance impact on first scan
```

- [ ] **Step 2: Update setup.md with Phase 2 requirements**

Add Ollama model pull for embeddings:

```markdown
### Phase 2 Setup

If using Phase 2 features (near-duplicate detection, stale file flagging):

```bash
ollama pull nomic-embed-text  # For embeddings
pip install "fileforge[ann]"  # Install hnswlib
```
```

- [ ] **Step 3: Run full test suite and verify docs build**

```bash
python -m pytest -q
```

Expected: All tests pass

- [ ] **Step 4: Test Phase 2 manually (if Ollama available)**

```bash
fileforge scan ~/Documents --phase-2 --no-classify
# Should show stale files, version patterns, and near-duplicates
```

- [ ] **Step 5: Final commit**

```bash
git add docs/overview.md docs/setup.md
git commit -m "docs: update Phase 2 documentation and requirements"
```

---

## Post-Plan Notes

- Embedding generation gracefully degrades if Ollama is unavailable (returns empty list, skips similarity matching)
- Stale detection is separate from classification — can run independently with `--phase-2 --no-classify`
- Version detection is pattern-based, not ML-based, so it's fast and deterministic
- Near-duplicate threshold is configurable via `duplicates.similarity_threshold` in config
- All Phase 2 data is persisted to database for later querying
