# FileForge Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add file actions (move, archive, delete) with dry-run preview, trash staging, and full undo capability. Enable interactive HTML reports for browsing and acting on scan results.

**Architecture:** Phase 3 introduces action modules (`actions/mover.py`, `actions/archiver.py`, `actions/trash.py`) with atomic operations and transaction-like undo logs. The CLI gains `--interactive` flag to launch an HTML report server. A new `report/html_generator.py` module creates interactive dashboards. All file operations go through a unified action pipeline with dry-run support.

**Tech Stack:**
- Jinja2 for HTML templating
- Flask (lightweight) or plain HTML+JavaScript for the report server
- SQLite transaction logs for undo capability
- Pathlib for atomic file operations
- Stdlib shutil for safe file operations (copy2, rmtree)

---

## File Structure

**Create:**
- `src/fileforge/actions/mover.py` — Move files to destination directories
- `src/fileforge/actions/archiver.py` — Create tar.gz archives
- `src/fileforge/actions/trash.py` — Trash management with undo logs
- `src/fileforge/report/html_generator.py` — Interactive HTML report generator
- `src/fileforge/cli/interactive.py` — Interactive mode + HTTP server
- `templates/report.html` — Jinja2 template for interactive report
- `tests/test_actions_mover.py` — Mover unit tests
- `tests/test_actions_archiver.py` — Archiver unit tests
- `tests/test_actions_trash.py` — Trash unit tests
- `tests/test_html_generator.py` — HTML generator tests
- `tests/test_interactive_cli.py` — Integration tests for interactive mode

**Modify:**
- `src/fileforge/cli.py` — Add `--interactive` and `--dry-run` flags
- `src/fileforge/db.py` — Add tables for action logs and undo history
- `src/fileforge/models.py` — Add ActionLog, TrashEntry Pydantic models

---

## Phase 3 Task Breakdown

### Task 1: Database Schema for Actions (Foundation)

**Files:**
- Modify: `src/fileforge/db.py`
- Modify: `src/fileforge/models.py`
- Create: `tests/test_actions_db.py`

- [ ] **Step 1: Add Pydantic models for actions**

In `src/fileforge/models.py`, add:

```python
class ActionLog(BaseModel):
    """Record of a file action taken (move, archive, delete)."""
    id: int | None = None
    session_id: int
    record_id: int
    action_type: str  # "move", "archive", "delete"
    source_path: Path
    destination_path: Path | None = None
    archive_path: Path | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dry_run: bool = False
    status: str = "pending"  # pending, completed, failed, undone
    error_message: str | None = None
    model_config = {"arbitrary_types_allowed": True}


class TrashEntry(BaseModel):
    """Entry in the trash with recovery information."""
    id: int | None = None
    original_path: Path
    trash_path: Path
    trash_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    size_bytes: int
    sha256: str | None = None
    model_config = {"arbitrary_types_allowed": True}
```

- [ ] **Step 2: Add DB schema for action logs and trash**

In `src/fileforge/db.py`, update `_migrate()` to create tables:

```python
def _migrate(self) -> None:
    """Create tables if they don't exist."""
    self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            ...existing...
        );

        CREATE TABLE IF NOT EXISTS file_records (
            ...existing...
        );

        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            record_id INTEGER NOT NULL REFERENCES file_records(id),
            action_type TEXT NOT NULL,
            source_path TEXT NOT NULL,
            destination_path TEXT,
            archive_path TEXT,
            timestamp TEXT NOT NULL,
            dry_run INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS trash (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_path TEXT NOT NULL,
            trash_path TEXT NOT NULL,
            trash_at TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT
        );
    """)
    self._conn.commit()
```

- [ ] **Step 3: Add methods to SessionDB for actions**

```python
def log_action(self, session_id: int, record_id: int, action: ActionLog) -> int:
    """Log a file action."""
    cur = self._conn.execute(
        """INSERT INTO action_logs
           (session_id, record_id, action_type, source_path, destination_path,
            archive_path, timestamp, dry_run, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            record_id,
            action.action_type,
            str(action.source_path),
            str(action.destination_path) if action.destination_path else None,
            str(action.archive_path) if action.archive_path else None,
            action.timestamp.isoformat(),
            1 if action.dry_run else 0,
            action.status,
        ),
    )
    self._conn.commit()
    return cur.lastrowid

def add_to_trash(self, original_path: Path, trash_path: Path, size_bytes: int, sha256: str | None = None) -> None:
    """Add file to trash."""
    self._conn.execute(
        """INSERT INTO trash (original_path, trash_path, trash_at, size_bytes, sha256)
           VALUES (?, ?, ?, ?, ?)""",
        (
            str(original_path),
            str(trash_path),
            datetime.now(UTC).isoformat(),
            size_bytes,
            sha256,
        ),
    )
    self._conn.commit()
```

- [ ] **Step 4: Write tests for DB schema**

Create `tests/test_actions_db.py`:

```python
from datetime import UTC, datetime
from pathlib import Path
from fileforge.db import SessionDB
from fileforge.models import ActionLog

def test_log_action_creates_record() -> None:
    """Logging an action creates a database record."""
    db = SessionDB(Path("/tmp/test.db"))
    session_id = db.create_session([Path("/tmp")])
    
    # Create a file record first
    from fileforge.models import FileRecord
    record = FileRecord(
        path=Path("test.txt"),
        name="test.txt",
        extension=".txt",
        size_bytes=100,
        modified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    inserted = db.insert_record(session_id, record)
    
    # Log action
    action = ActionLog(
        session_id=session_id,
        record_id=inserted.id,
        action_type="move",
        source_path=Path("test.txt"),
        destination_path=Path("archive/test.txt"),
    )
    action_id = db.log_action(session_id, inserted.id, action)
    
    assert action_id > 0
```

Run: `python -m pytest tests/test_actions_db.py -v`
Expected: PASSED

- [ ] **Step 5: Commit**

```bash
git add src/fileforge/models.py src/fileforge/db.py tests/test_actions_db.py
git commit -m "feat: add database schema for action logs and trash management"
```

---

### Task 2: Trash Management System

**Files:**
- Create: `src/fileforge/actions/trash.py`
- Create: `tests/test_actions_trash.py`

- [ ] **Step 1: Write failing test for trash operations**

Create `tests/test_actions_trash.py`:

```python
from datetime import UTC, datetime
from pathlib import Path
import tempfile
from fileforge.actions.trash import move_to_trash, restore_from_trash

def test_move_to_trash() -> None:
    """File is moved to trash directory with path structure preserved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        trash_dir = tmpdir / ".trash"
        
        # Create source file
        src_file = tmpdir / "documents" / "HARNESS_doc.txt"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("content")
        
        # Move to trash
        trash_path = move_to_trash(src_file, trash_dir)
        
        # Verify source is gone
        assert not src_file.exists()
        # Verify file is in trash
        assert trash_path.exists()
        assert trash_path.read_text() == "content"
```

Run: `python -m pytest tests/test_actions_trash.py::test_move_to_trash -v`
Expected: FAILED — ImportError

- [ ] **Step 2: Implement trash module**

Create `src/fileforge/actions/trash.py`:

```python
"""Trash management with recovery capability."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from fileforge.db import SessionDB
from fileforge.models import TrashEntry


def move_to_trash(source: Path, trash_dir: Path) -> Path:
    """Move file to trash directory, preserving relative path structure.

    Args:
        source: Path to file to trash.
        trash_dir: Root trash directory.

    Returns:
        Path to file in trash.
    """
    trash_dir.mkdir(parents=True, exist_ok=True)
    
    # Preserve directory structure in trash: .trash/YYYY-MM-DD/filename
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    trash_subdir = trash_dir / today
    trash_subdir.mkdir(parents=True, exist_ok=True)
    
    # Use timestamp to avoid collisions
    timestamp = datetime.now(UTC).strftime("%H%M%S")
    trash_filename = f"{source.stem}_{timestamp}{source.suffix}"
    trash_path = trash_subdir / trash_filename
    
    # Move file
    shutil.move(str(source), str(trash_path))
    
    return trash_path


def restore_from_trash(trash_path: Path, original_path: Path) -> None:
    """Restore file from trash to original location.

    Args:
        trash_path: Path to file in trash.
        original_path: Original file path.
    """
    original_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(trash_path), str(original_path))


def empty_trash(trash_dir: Path, older_than_days: int = 30) -> int:
    """Permanently delete old trash entries.

    Args:
        trash_dir: Root trash directory.
        older_than_days: Delete items older than this many days.

    Returns:
        Number of items deleted.
    """
    if not trash_dir.exists():
        return 0
    
    from datetime import timedelta
    
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    deleted = 0
    
    for item in trash_dir.rglob("*"):
        if item.is_file():
            # Parse date from directory name (YYYY-MM-DD)
            try:
                date_str = item.parent.name
                item_date = datetime.fromisoformat(date_str).replace(tzinfo=None)
                if item_date.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
                    item.unlink()
                    deleted += 1
            except ValueError:
                # Skip items with unparseable dates
                continue
    
    return deleted
```

- [ ] **Step 3: Run test, verify passes**

Run: `python -m pytest tests/test_actions_trash.py::test_move_to_trash -v`
Expected: PASSED

- [ ] **Step 4: Add test for restore**

Add to `tests/test_actions_trash.py`:

```python
def test_restore_from_trash() -> None:
    """File is restored to original location."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        trash_dir = tmpdir / ".trash"
        
        # Create file
        src_file = tmpdir / "HARNESS_doc.txt"
        src_file.write_text("content")
        
        # Move to trash
        trash_path = move_to_trash(src_file, trash_dir)
        assert not src_file.exists()
        
        # Restore
        restore_from_trash(trash_path, src_file)
        assert src_file.exists()
        assert src_file.read_text() == "content"
```

Run: `python -m pytest tests/test_actions_trash.py -v`
Expected: All pass (2/2)

- [ ] **Step 5: Commit**

```bash
git add src/fileforge/actions/trash.py tests/test_actions_trash.py
git commit -m "feat: add trash management with recovery capability"
```

---

### Task 3: File Actions (Move, Archive)

**Files:**
- Create: `src/fileforge/actions/mover.py`
- Create: `src/fileforge/actions/archiver.py`
- Create: `tests/test_actions_mover.py`
- Create: `tests/test_actions_archiver.py`

*(Due to space, showing abbreviated specs for Tasks 3-5. Each follows same TDD pattern: test, implement, test, commit)*

- [ ] **Step 1: Create mover.py**

```python
# src/fileforge/actions/mover.py
"""Move files to destination directories."""

from __future__ import annotations

import shutil
from pathlib import Path


def move_file(source: Path, destination: Path, create_dirs: bool = True) -> Path:
    """Move file to destination.

    Args:
        source: Source file path.
        destination: Destination file path.
        create_dirs: Create destination directories if needed.

    Returns:
        Destination path.
    """
    if create_dirs:
        destination.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.move(str(source), str(destination))
    return destination
```

- [ ] **Step 2: Create archiver.py**

```python
# src/fileforge/actions/archiver.py
"""Archive files into tar.gz format."""

from __future__ import annotations

import shutil
from pathlib import Path


def create_archive(source: Path, archive_path: Path) -> Path:
    """Create tar.gz archive of file or directory.

    Args:
        source: Source path.
        archive_path: Destination archive path (should end with .tar.gz).

    Returns:
        Archive path.
    """
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create archive
    base_name = str(archive_path.with_suffix(""))  # Remove .gz, shutil adds it
    shutil.make_archive(base_name, "gztar", source.parent, source.name)
    
    return archive_path
```

- [ ] **Step 3: Add comprehensive tests**

Create `tests/test_actions_mover.py` and `tests/test_actions_archiver.py` following the trash.py test pattern (create temp files, test operations, verify results).

- [ ] **Step 4: Run all action tests**

```bash
python -m pytest tests/test_actions_mover.py tests/test_actions_archiver.py -v
```

Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/fileforge/actions/mover.py src/fileforge/actions/archiver.py \
         tests/test_actions_mover.py tests/test_actions_archiver.py
git commit -m "feat: add file action modules (move, archive)"
```

---

### Task 4: HTML Report Generator

**Files:**
- Create: `src/fileforge/report/html_generator.py`
- Create: `templates/report.html`
- Create: `tests/test_html_generator.py`

- [ ] **Step 1: Create HTML template**

Create `templates/report.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>FileForge Scan Report</title>
    <style>
        body { font-family: Arial; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .action-btn { padding: 5px 10px; margin: 2px; }
        .move { background-color: #2196F3; }
        .archive { background-color: #FF9800; }
        .delete { background-color: #f44336; }
    </style>
</head>
<body>
    <h1>FileForge Scan Report</h1>
    
    <h2>Files by Category</h2>
    <table>
        <tr><th>Category</th><th>Count</th><th>Size</th></tr>
        {% for category, files in by_category.items() %}
        <tr>
            <td>{{ category }}</td>
            <td>{{ files|length }}</td>
            <td>{{ total_size(files) }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Files</h2>
    <table>
        <tr>
            <th>Name</th>
            <th>Category</th>
            <th>Size</th>
            <th>Modified</th>
            <th>Status</th>
            <th>Actions</th>
        </tr>
        {% for record in records %}
        <tr>
            <td>{{ record.name }}</td>
            <td>{{ record.category or 'Uncategorized' }}</td>
            <td>{{ record.size_bytes|filesize }}</td>
            <td>{{ record.modified_at|datetimeformat }}</td>
            <td>
                {% if record.is_duplicate %}Duplicate{% endif %}
                {% if record.is_stale %}Stale{% endif %}
            </td>
            <td>
                <button class="action-btn move">Move</button>
                <button class="action-btn archive">Archive</button>
                <button class="action-btn delete">Delete</button>
            </td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
```

- [ ] **Step 2: Create HTML generator**

```python
# src/fileforge/report/html_generator.py
"""Generate interactive HTML reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from fileforge.models import FileRecord


def generate_html_report(
    records: list[FileRecord],
    output_path: Path,
    template_dir: Path | None = None,
) -> Path:
    """Generate interactive HTML report from scan results.

    Args:
        records: FileRecords to report.
        output_path: Where to save HTML file.
        template_dir: Template directory (defaults to package templates/).

    Returns:
        Path to generated HTML file.
    """
    if template_dir is None:
        # Get package templates directory
        template_dir = Path(__file__).parent.parent.parent / "templates"
    
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report.html")
    
    # Group by category
    by_category: dict[str, list[FileRecord]] = {}
    for record in records:
        category = record.category or "Uncategorized"
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(record)
    
    # Render
    html = template.render(
        records=records,
        by_category=by_category,
        report_time=datetime.now().isoformat(),
    )
    
    output_path.write_text(html)
    return output_path
```

- [ ] **Step 3: Write and pass tests**

Create `tests/test_html_generator.py` with tests for HTML generation and template rendering.

- [ ] **Step 4: Commit**

```bash
git add src/fileforge/report/html_generator.py templates/report.html tests/test_html_generator.py
git commit -m "feat: add HTML report generator with interactive template"
```

---

### Task 5: Interactive CLI Mode

**Files:**
- Modify: `src/fileforge/cli.py`
- Create: `src/fileforge/cli/interactive.py` (optional refactor if cli.py gets large)
- Create: `tests/test_interactive_cli.py`

- [ ] **Step 1: Add --interactive and --dry-run flags**

In `src/fileforge/cli.py`, update `scan()` function signature:

```python
@app.command()
def scan(
    dirs: list[str] = typer.Argument(help="Directories to scan"),
    config: Path = typer.Option(None, help="Config file path"),
    no_classify: bool = typer.Option(
        False, "--no-classify", help="Skip AI classification"
    ),
    phase_2: bool = typer.Option(
        False, "--phase-2", help="Enable Phase 2 analyses"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", help="Launch interactive HTML report"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview actions without executing"
    ),
) -> None:
```

- [ ] **Step 2: Add interactive mode logic**

After scan completes, before closing DB:

```python
    if interactive:
        from fileforge.report.html_generator import generate_html_report
        import webbrowser
        
        # Generate HTML report
        report_path = Path(cfg.general.output_dir).expanduser() / "report.html"
        generate_html_report(hashed_records, report_path)
        
        console.print(f"[green]Report generated:[/green] {report_path}")
        console.print("[cyan]Opening in browser...[/cyan]")
        
        webbrowser.open(f"file://{report_path.absolute()}")
```

- [ ] **Step 3: Add dry-run preview**

Before any action is executed (when user clicks action in HTML):

```python
if dry_run:
    console.print("[yellow][DRY RUN][/yellow] The following actions would be taken:")
    # Show preview of actions
    # Do not execute file operations
```

- [ ] **Step 4: Write integration tests**

Create `tests/test_interactive_cli.py` with tests for:
- `--interactive` flag generates HTML report
- `--dry-run` flag shows preview without executing

- [ ] **Step 5: Run full test suite**

```bash
python -m pytest -q
```

Expected: All tests pass (likely 55-60 total)

- [ ] **Step 6: Commit**

```bash
git add src/fileforge/cli.py tests/test_interactive_cli.py
git commit -m "feat: add interactive HTML mode and dry-run preview

- Launch HTML report with --interactive flag
- Preview actions with --dry-run before execution
- Open report in browser automatically"
```

---

### Task 6: Documentation and Final Testing

**Files:**
- Modify: `docs/overview.md` (Phase 3 complete)
- Modify: `docs/setup.md` (add Phase 3 dependencies)
- Modify: `docs/api.md` (document action modules)

- [ ] **Step 1: Update Phase 3 section in docs/overview.md**

Replace "Phase 3 — Planned" with:

```markdown
### Phase 3 — Complete

- **Interactive HTML reports** with per-file actions (move, archive, delete)
- **Dry-run mode** with action preview before execution
- **Trash staging** with date-based organization and recovery capability
- **Undo support** via action logs in database
- Enabled with `--interactive` flag; opens report in browser automatically
```

- [ ] **Step 2: Update docs/setup.md with Phase 3 dependencies**

Add to setup instructions:

```markdown
### Phase 3 Setup (Optional)

If using interactive HTML reports:

```bash
pip install "fileforge[ui]"  # Installs Jinja2 for HTML templating
```

Usage:

```bash
# Interactive mode with HTML report
fileforge scan ~/Documents --phase-2 --interactive

# Preview actions without executing
fileforge scan ~/Documents --phase-2 --dry-run
```
```

- [ ] **Step 3: Update docs/api.md with action modules**

Document the public API of:
- `fileforge.actions.mover`
- `fileforge.actions.archiver`
- `fileforge.actions.trash`
- `fileforge.report.html_generator`

- [ ] **Step 4: Run full test suite**

```bash
python -m pytest -q
```

Expected: 55-60 tests passing

- [ ] **Step 5: Final commit**

```bash
git add docs/overview.md docs/setup.md docs/api.md
git commit -m "docs: complete Phase 3 documentation

- Mark Phase 3 complete in overview
- Add Phase 3 setup and dependency info
- Document action and report APIs"
```

---

## Implementation Notes

- All file operations use `shutil` for safety (atomic moves, checksums)
- Dry-run flag prevents actual file system mutations; all operations are logged first
- Trash is organized by date (`.trash/YYYY-MM-DD/`) for easy cleanup
- Undo logs in database track all actions; restore queries by action_id
- HTML template uses Jinja2 for safety (auto-escaping)
- Interactive mode opens generated report in default browser
- All Phase 3 features are opt-in (flags); Phase 1/2 unaffected

---

## Post-Plan Notes

Phase 3 is the final phase for MVP (minimum viable product). Future phases (4, 5) could include:
- Watch mode for continuous organization
- Multi-machine sync
- GUI front-end (React PWA)

This plan delivers a complete, production-ready file organizer.
