"""Trash management tests with recovery capability."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import tempfile

import pytest

from fileforge.actions.trash import empty_trash, move_to_trash, restore_from_trash


def test_move_to_trash() -> None:
    """File is moved to trash directory with date-based organization."""
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
        # Verify it's in a date subdirectory
        assert trash_path.parent.name.count("-") == 2  # YYYY-MM-DD format


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


def test_empty_trash_removes_old_entries() -> None:
    """Trash entries older than threshold are permanently deleted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        trash_dir = tmpdir / ".trash"

        # Create old trash entry (manually, as if from 31 days ago)
        old_date = (datetime.now(UTC) - timedelta(days=31)).strftime("%Y-%m-%d")
        old_dir = trash_dir / old_date
        old_dir.mkdir(parents=True, exist_ok=True)
        old_file = old_dir / "HARNESS_old.txt"
        old_file.write_text("old content")

        # Create recent entry
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        today_dir = trash_dir / today
        today_dir.mkdir(parents=True, exist_ok=True)
        recent_file = today_dir / "HARNESS_recent.txt"
        recent_file.write_text("recent content")

        # Empty trash (older than 30 days)
        deleted = empty_trash(trash_dir, older_than_days=30)

        assert deleted >= 1  # At least the old file
        assert not old_file.exists()
        assert recent_file.exists()
