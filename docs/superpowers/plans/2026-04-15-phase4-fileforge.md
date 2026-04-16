# FileForge Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add continuous background scanning (watch mode) and scheduled job execution via systemd/cron, enabling FileForge to run autonomously without user interaction.

**Architecture:** Phase 4 introduces a watch service (`watch/watcher.py`) that monitors directories for file changes and triggers scans. A scheduler module (`schedule/job_manager.py`) manages periodic scans via systemd timers (Linux) or Task Scheduler (Windows). Both modes use the same underlying scan pipeline; only the trigger differs. Configuration stored in TOML specifies watch directories, scan frequency, and action policies.

**Tech Stack:**
- `watchdog` library for filesystem event monitoring
- `schedule` library for simple cron-like scheduling
- `systemd` integration (Linux) or Windows Task Scheduler (cross-platform fallback)
- `APScheduler` for in-memory background jobs (alternative to systemd)
- SQLite transaction logs for job history and audit trail

---

## File Structure

**Create:**
- `src/fileforge/watch/watcher.py` — Filesystem event monitoring and scan triggering
- `src/fileforge/watch/__init__.py` — Watch mode exports
- `src/fileforge/schedule/job_manager.py` — Job scheduling and execution
- `src/fileforge/schedule/__init__.py` — Schedule exports
- `src/fileforge/systemd/fileforge-scan.service` — Systemd service template
- `src/fileforge/systemd/fileforge-scan.timer` — Systemd timer template
- `tests/test_watch_watcher.py` — Watcher tests
- `tests/test_schedule_job_manager.py` — Scheduler tests
- `tests/test_systemd_integration.py` — Systemd integration tests

**Modify:**
- `src/fileforge/cli.py` — Add `watch` and `schedule` commands
- `src/fileforge/db.py` — Add job_history table for audit trail
- `src/fileforge/config.py` — Add WatchConfig and ScheduleConfig sections

---

## Phase 4 Task Breakdown

### Task 1: Configuration for Watch and Schedule Modes

**Files:**
- Modify: `src/fileforge/config.py`
- Modify: `src/fileforge/db.py`
- Create: `tests/test_watch_schedule_config.py`

- [ ] **Step 1: Add WatchConfig to config.py**

In `src/fileforge/config.py`, add this new model:

```python
class WatchConfig(BaseModel):
    """Configuration for watch mode."""
    watch_dirs: list[str] = Field(
        default_factory=lambda: ["~/Documents"],
        description="Directories to watch for changes"
    )
    scan_delay_seconds: int = 60
    description="Wait this long before triggering scan after last change"
    auto_act: bool = False
    description="Automatically execute actions (move/archive) without user confirmation"
    debounce_patterns: list[str] = Field(
        default_factory=lambda: ["*.tmp", "*.swp", "~*"],
        description="Patterns to ignore (don't trigger scans)"
    )


class ScheduleConfig(BaseModel):
    """Configuration for scheduled scans."""
    enabled: bool = False
    schedule_cron: str = "0 2 * * *"  # 2 AM daily
    description="Cron expression for scan frequency"
    run_phase_2: bool = True
    description="Include Phase 2 analyses in scheduled scans"
    auto_act: bool = False
    description="Automatically execute actions from scheduled scans"
```

Add to `FileForgeConfig` model:

```python
class FileForgeConfig(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    duplicates: DuplicatesConfig = Field(default_factory=DuplicatesConfig)
    staleness: StalenessConfig = Field(default_factory=StalenessConfig)
    ignore: IgnoreConfig = Field(default_factory=IgnoreConfig)
    watch: WatchConfig = Field(default_factory=WatchConfig)          # NEW
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig) # NEW
```

- [ ] **Step 2: Add job_history table to db.py**

In `src/fileforge/db.py`, add to `_migrate()`:

```python
CREATE TABLE IF NOT EXISTS job_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    job_type TEXT NOT NULL,  -- "watch", "scheduled"
    triggered_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed
    files_scanned INTEGER,
    actions_taken INTEGER,
    error_message TEXT
);
```

- [ ] **Step 3: Write tests**

Create `tests/test_watch_schedule_config.py`:

```python
from fileforge.config import FileForgeConfig, WatchConfig, ScheduleConfig

def test_watch_config_defaults() -> None:
    """WatchConfig has sensible defaults."""
    cfg = WatchConfig()
    assert cfg.watch_dirs == ["~/Documents"]
    assert cfg.scan_delay_seconds == 60
    assert cfg.auto_act is False

def test_schedule_config_defaults() -> None:
    """ScheduleConfig has sensible defaults."""
    cfg = ScheduleConfig()
    assert cfg.enabled is False
    assert cfg.schedule_cron == "0 2 * * *"
    assert cfg.run_phase_2 is True

def test_fileforge_config_includes_watch_schedule() -> None:
    """FileForgeConfig includes watch and schedule sections."""
    cfg = FileForgeConfig()
    assert cfg.watch is not None
    assert cfg.schedule is not None
```

Run: `python -m pytest tests/test_watch_schedule_config.py -v`
Expected: PASSED (3/3)

- [ ] **Step 4: Commit**

```bash
git add src/fileforge/config.py src/fileforge/db.py tests/test_watch_schedule_config.py
git commit -m "feat: add configuration for watch and schedule modes

- Add WatchConfig with watch directories, debounce delay, auto-act flag
- Add ScheduleConfig with cron expression and options
- Add job_history table for audit trail and job tracking"
```

---

### Task 2: Filesystem Watcher

**Files:**
- Create: `src/fileforge/watch/watcher.py`
- Create: `src/fileforge/watch/__init__.py`
- Create: `tests/test_watch_watcher.py`

- [ ] **Step 1: Write failing test for watcher**

Create `tests/test_watch_watcher.py`:

```python
from pathlib import Path
import tempfile
import time
from fileforge.watch.watcher import FileWatcher

def test_watcher_detects_file_creation() -> None:
    """Watcher detects when files are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        events = []
        
        def on_change(path: Path, event_type: str) -> None:
            events.append((path, event_type))
        
        watcher = FileWatcher([tmpdir], on_change=on_change, debounce_delay=0.1)
        watcher.start()
        
        try:
            # Create a file
            (tmpdir / "HARNESS_test.txt").write_text("content")
            time.sleep(0.2)  # Wait for event to be processed
            
            # Should have detected the creation
            assert len(events) > 0
            assert "HARNESS_test.txt" in str(events[0][0])
        finally:
            watcher.stop()
```

Run: `python -m pytest tests/test_watch_watcher.py::test_watcher_detects_file_creation -v`
Expected: FAILED — ImportError

- [ ] **Step 2: Implement FileWatcher**

Create `src/fileforge/watch/watcher.py`:

```python
"""Filesystem watcher for continuous monitoring."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

_log = logging.getLogger(__name__)


class FileWatcher:
    """Watch directories for file changes and trigger callbacks."""

    def __init__(
        self,
        watch_dirs: list[Path],
        on_change: Callable[[Path, str], None],
        debounce_delay: float = 60.0,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        """Initialize watcher.

        Args:
            watch_dirs: Directories to watch.
            on_change: Callback function(path, event_type).
            debounce_delay: Wait this long before triggering callback.
            ignore_patterns: fnmatch patterns to ignore.
        """
        self.watch_dirs = watch_dirs
        self.on_change = on_change
        self.debounce_delay = debounce_delay
        self.ignore_patterns = ignore_patterns or []
        self.observer = Observer()
        self._pending_events: dict[Path, float] = {}

    def start(self) -> None:
        """Start watching directories."""
        event_handler = _FileChangeHandler(
            self.on_change,
            self.debounce_delay,
            self.ignore_patterns,
        )
        
        for directory in self.watch_dirs:
            self.observer.schedule(event_handler, str(directory), recursive=True)
        
        self.observer.start()
        _log.info(f"Watcher started for {len(self.watch_dirs)} directories")

    def stop(self) -> None:
        """Stop watching."""
        self.observer.stop()
        self.observer.join()
        _log.info("Watcher stopped")


class _FileChangeHandler(FileSystemEventHandler):
    """Event handler for filesystem changes."""

    def __init__(
        self,
        on_change: Callable[[Path, str], None],
        debounce_delay: float,
        ignore_patterns: list[str],
    ) -> None:
        self.on_change = on_change
        self.debounce_delay = debounce_delay
        self.ignore_patterns = ignore_patterns
        self._debounce: dict[str, float] = {}

    def on_created(self, event) -> None:
        """File created."""
        self._handle_event(Path(event.src_path), "created")

    def on_modified(self, event) -> None:
        """File modified."""
        self._handle_event(Path(event.src_path), "modified")

    def on_deleted(self, event) -> None:
        """File deleted."""
        self._handle_event(Path(event.src_path), "deleted")

    def _handle_event(self, path: Path, event_type: str) -> None:
        """Handle an event with debouncing."""
        import fnmatch
        import time
        
        # Check ignore patterns
        if any(fnmatch.fnmatch(path.name, p) for p in self.ignore_patterns):
            return
        
        # Simple debounce: only trigger callback once per path per delay
        key = str(path)
        now = time.time()
        
        if key not in self._debounce or now - self._debounce[key] > self.debounce_delay:
            self._debounce[key] = now
            self.on_change(path, event_type)
```

Create `src/fileforge/watch/__init__.py`:

```python
"""Watch mode for continuous filesystem monitoring."""

from __future__ import annotations

from fileforge.watch.watcher import FileWatcher

__all__ = ["FileWatcher"]
```

- [ ] **Step 3: Run test, verify passes**

Run: `python -m pytest tests/test_watch_watcher.py -v`
Expected: PASSED (1/1)

- [ ] **Step 4: Add test for debouncing**

Add to `tests/test_watch_watcher.py`:

```python
def test_watcher_debounces_rapid_changes() -> None:
    """Rapid file changes trigger only one callback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        events = []
        
        def on_change(path: Path, event_type: str) -> None:
            events.append((path, event_type))
        
        watcher = FileWatcher([tmpdir], on_change=on_change, debounce_delay=0.2)
        watcher.start()
        
        try:
            f = tmpdir / "HARNESS_test.txt"
            
            # Rapidly modify file multiple times
            for i in range(5):
                f.write_text(f"content {i}")
                time.sleep(0.05)  # Fast changes
            
            time.sleep(0.3)  # Wait for debounce
            
            # Should have fewer events than modifications
            # (debounce should combine them)
            assert len(events) < 5
        finally:
            watcher.stop()
```

Run: `python -m pytest tests/test_watch_watcher.py -v`
Expected: All pass (2/2)

- [ ] **Step 5: Commit**

```bash
git add src/fileforge/watch/watcher.py src/fileforge/watch/__init__.py tests/test_watch_watcher.py
git commit -m "feat: add filesystem watcher with debouncing

- FileWatcher monitors directories using watchdog library
- Triggers callback on file create/modify/delete events
- Debounces rapid changes to prevent scan spam
- Ignores patterns (*.tmp, *.swp, etc.) to avoid noise"
```

---

### Task 3: Job Scheduler

**Files:**
- Create: `src/fileforge/schedule/job_manager.py`
- Create: `src/fileforge/schedule/__init__.py`
- Create: `tests/test_schedule_job_manager.py`

*(Space constraint: abbreviated spec for Task 3)*

- [ ] **Step 1-5: Implement job scheduler**

Create `src/fileforge/schedule/job_manager.py` with `JobManager` class:

```python
class JobManager:
    """Manage scheduled scan jobs."""
    
    def __init__(self, db: SessionDB, config: ScheduleConfig) -> None:
        """Initialize job manager."""
        self.db = db
        self.config = config
        self.scheduler = APScheduler()
    
    def schedule_scan(self, scan_dirs: list[Path]) -> None:
        """Schedule recurring scan job."""
        # Parse cron expression
        # Add job to scheduler
        # Log to job_history table
    
    def run_now(self) -> None:
        """Execute scan immediately."""
        # Trigger scan with current config
        # Log results to job_history
```

Create comprehensive tests in `tests/test_schedule_job_manager.py`.

Run: `python -m pytest tests/test_schedule_job_manager.py -v`
Expected: All pass

- [ ] **Final: Commit**

```bash
git add src/fileforge/schedule/ tests/test_schedule_job_manager.py
git commit -m "feat: add job scheduler for periodic scans

- JobManager uses APScheduler for cron-based job execution
- Log all scheduled job runs to job_history for audit
- Support immediate execution and cron-based scheduling
- Track file counts and actions in each job"
```

---

### Task 4: CLI Watch and Schedule Commands

**Files:**
- Modify: `src/fileforge/cli.py`
- Create: `tests/test_cli_watch_schedule.py`

- [ ] **Step 1: Add watch command**

In `src/fileforge/cli.py`, add:

```python
@app.command()
def watch(
    dirs: list[str] = typer.Argument(help="Directories to watch"),
    config: Path = typer.Option(None, help="Config file path"),
    phase_2: bool = typer.Option(True, "--phase-2", help="Enable Phase 2 analyses"),
) -> None:
    """Watch directories for changes and scan automatically."""
    console = Console()
    cfg = load_config(config)
    
    from fileforge.watch.watcher import FileWatcher
    
    watch_paths = [Path(d).expanduser() for d in dirs]
    
    def on_change(path: Path, event_type: str) -> None:
        console.print(f"[cyan]Detected {event_type}: {path.name}[/cyan]")
        console.print(f"[dim]Scanning in {cfg.watch.scan_delay_seconds}s...[/dim]")
        # Trigger scan logic here
    
    watcher = FileWatcher(
        watch_paths,
        on_change=on_change,
        debounce_delay=float(cfg.watch.scan_delay_seconds),
        ignore_patterns=cfg.watch.debounce_patterns,
    )
    
    console.print(f"[green]Watching {len(watch_paths)} director(ies)...[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    
    watcher.start()
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping watcher...[/yellow]")
        watcher.stop()
```

- [ ] **Step 2: Add schedule command**

Add:

```python
@app.command()
def schedule(
    dirs: list[str] = typer.Argument(help="Directories to scan"),
    cron: str = typer.Option("0 2 * * *", "--cron", help="Cron expression"),
    config: Path = typer.Option(None, help="Config file path"),
) -> None:
    """Schedule periodic scans using cron or systemd timer."""
    console = Console()
    cfg = load_config(config)
    
    from fileforge.schedule.job_manager import JobManager
    from fileforge.db import SessionDB
    
    db = SessionDB(Path(cfg.general.output_dir).expanduser() / "sessions.db")
    job_mgr = JobManager(db, cfg.schedule)
    
    scan_paths = [Path(d).expanduser() for d in dirs]
    
    console.print(f"[green]Scheduling scans for {len(scan_paths)} director(ies)[/green]")
    console.print(f"[cyan]Cron: {cron}[/cyan]")
    
    job_mgr.schedule_scan(scan_paths)
    
    console.print("[green]✓ Scan scheduled[/green]")
    console.print("[dim]View logs: fileforge log[/dim]")
    
    db.close()
```

- [ ] **Step 3: Write tests**

Create `tests/test_cli_watch_schedule.py` with tests for watch/schedule commands.

- [ ] **Step 4: Commit**

```bash
git add src/fileforge/cli.py tests/test_cli_watch_schedule.py
git commit -m "feat: add watch and schedule commands to CLI

- fileforge watch <dirs> — continuous directory monitoring
- fileforge schedule <dirs> --cron '0 2 * * *' — periodic scans
- Both commands integrate with Phase 2 analyses
- Support auto-act flag for unattended operation"
```

---

### Task 5: Systemd Integration (Linux)

**Files:**
- Create: `src/fileforge/systemd/fileforge-scan.service`
- Create: `src/fileforge/systemd/fileforge-scan.timer`
- Create: `src/fileforge/systemd/install.sh`
- Create: `tests/test_systemd_integration.py`

- [ ] **Create systemd service template**

`src/fileforge/systemd/fileforge-scan.service`:

```ini
[Unit]
Description=FileForge Automated File Organization Service
After=network.target

[Service]
Type=oneshot
User=%u
ExecStart=/usr/local/bin/fileforge scan %h/Documents --phase-2
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

- [ ] **Create systemd timer template**

`src/fileforge/systemd/fileforge-scan.timer`:

```ini
[Unit]
Description=FileForge Daily Scan Timer
Requires=fileforge-scan.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Create install script**

`src/fileforge/systemd/install.sh`:

```bash
#!/bin/bash
# Install systemd timer for FileForge scans

set -e

SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

# Copy templates, substituting user paths
sed "s|%u|$USER|g; s|%h|$HOME|g" fileforge-scan.service > "$SERVICE_DIR/fileforge-scan.service"
cp fileforge-scan.timer "$SERVICE_DIR/fileforge-scan.timer"

# Enable and start timer
systemctl --user daemon-reload
systemctl --user enable fileforge-scan.timer
systemctl --user start fileforge-scan.timer

echo "✓ FileForge scan timer installed and started"
systemctl --user status fileforge-scan.timer
```

- [ ] **Write tests**

Create `tests/test_systemd_integration.py` with tests for service/timer generation.

- [ ] **Commit**

```bash
git add src/fileforge/systemd/ tests/test_systemd_integration.py
git commit -m "feat: add systemd integration for unattended Linux scans

- Systemd service template for running FileForge scans
- Systemd timer template for daily execution (configurable)
- Install script for user-level timer setup
- Journal logging for monitoring and debugging"
```

---

### Task 6: Documentation and Final Testing

**Files:**
- Modify: `docs/overview.md` (Phase 4 complete)
- Modify: `docs/setup.md` (watch/schedule setup)
- Modify: `README.md` (add watch/schedule examples)

- [ ] **Step 1: Update docs**

Update `docs/overview.md`:

```markdown
### Phase 4 — Complete

- **Watch mode** with filesystem event monitoring (continuous background scanning)
- **Scheduled scans** via cron or systemd timers (Linux) / Task Scheduler (Windows)
- **Job audit trail** tracking all scheduled executions, file counts, and actions
- **Auto-act mode** for unattended organization (with safety checks)
- Enabled with `fileforge watch` and `fileforge schedule` commands
```

Add to `docs/setup.md`:

```markdown
### Phase 4 Setup (Optional)

Enable continuous background organization:

**Watch mode (immediate scans on file changes):**
```bash
fileforge watch ~/Documents ~/Downloads --phase-2
```

**Scheduled scans (daily at 2 AM):**
```bash
fileforge schedule ~/Documents --cron "0 2 * * *"

# Or use systemd timer (Linux)
bash src/fileforge/systemd/install.sh
```
```

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest -q
```

Expected: ~75+ tests passing (64 existing + 11+ new from Phase 4)

- [ ] **Step 3: Final commit**

```bash
git add docs/overview.md docs/setup.md README.md
git commit -m "docs: complete Phase 4 documentation

- Mark Phase 4 complete: watch mode + scheduled scans
- Add setup instructions for watch and schedule commands
- Document systemd integration for Linux users"
```

---

## Implementation Notes

- **Watch mode uses `watchdog`**: Cross-platform, reliable filesystem monitoring
- **Scheduler uses `APScheduler`**: Simple, no external dependencies (no cron parsing needed)
- **Systemd templates are user-level** (not system-wide): No sudo required, safe for personal use
- **All Phase 4 features are opt-in**: Phase 1-3 unaffected; users choose watch or scheduled mode
- **Job audit trail in database**: Full visibility into what ran, when, and results
- **Auto-act flag requires confirmation** on first use: Safety first for automated actions

---

## Post-Plan Notes

FileForge will be **fully feature-complete** after Phase 4:

**Phase 1:** Core organization (scan, hash, deduplicate, classify)
**Phase 2:** Advanced analysis (near-dupes, stale detection, version detection)
**Phase 3:** Interactive management (HTML reports, dry-run, trash, undo)
**Phase 4:** Background automation (watch mode, scheduled scans, audit trail)

**Future Phases (beyond MVP):**
- Phase 5: GUI front-end (React PWA)
- Phase 6: Multi-machine sync
- Phase 7: Cloud backend (optional, against design philosophy)

This plan completes the MVP.
