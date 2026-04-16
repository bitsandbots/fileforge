import tempfile
import time
from pathlib import Path

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
