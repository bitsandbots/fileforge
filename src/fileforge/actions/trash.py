"""Trash management with recovery capability."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path


def move_to_trash(source: Path, trash_dir: Path) -> Path:
    """Move file to trash directory, organizing by date.

    Args:
        source: Path to file to trash.
        trash_dir: Root trash directory.

    Returns:
        Path to file in trash.
    """
    trash_dir.mkdir(parents=True, exist_ok=True)

    # Preserve directory structure: .trash/YYYY-MM-DD/filename_timestamp
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
        older_than_days: Delete items older than this many days (default 30).

    Returns:
        Number of items deleted.
    """
    if not trash_dir.exists():
        return 0

    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    deleted = 0

    for item in trash_dir.rglob("*"):
        if item.is_file():
            # Parse date from directory name (YYYY-MM-DD)
            try:
                date_str = item.parent.name
                item_date = datetime.fromisoformat(date_str).replace(tzinfo=None)
                if item_date < cutoff.replace(tzinfo=None):
                    item.unlink()
                    deleted += 1
            except ValueError:
                # Skip items with unparseable dates
                continue

    return deleted
