"""Filesystem watcher for continuous monitoring."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

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

    def on_created(self, event) -> None:  # type: ignore
        """File created."""
        self._handle_event(Path(event.src_path), "created")

    def on_modified(self, event) -> None:  # type: ignore
        """File modified."""
        self._handle_event(Path(event.src_path), "modified")

    def on_deleted(self, event) -> None:  # type: ignore
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
