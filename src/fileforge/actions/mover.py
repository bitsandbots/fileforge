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
        Destination path (for chaining operations).

    Raises:
        FileNotFoundError: If source does not exist.
        IsADirectoryError: If source is a directory.
    """
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    if source.is_dir():
        raise IsADirectoryError(f"Source is a directory, not a file: {source}")

    if create_dirs:
        destination.parent.mkdir(parents=True, exist_ok=True)

    shutil.move(str(source), str(destination))
    return destination
