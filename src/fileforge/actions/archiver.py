"""Archive files into tar.gz format."""

from __future__ import annotations

import shutil
from pathlib import Path


def create_archive(source: Path, archive_path: Path) -> Path:
    """Create tar.gz archive of file or directory.

    Args:
        source: Source file or directory path.
        archive_path: Destination archive path (should end with .tar.gz).

    Returns:
        Archive path (for chaining operations).

    Raises:
        FileNotFoundError: If source does not exist.
    """
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    archive_path.parent.mkdir(parents=True, exist_ok=True)

    # Create archive: shutil.make_archive adds the compression suffix
    base_name = str(archive_path.with_suffix(""))  # Remove .gz
    base_name = base_name.rsplit(".tar", 1)[0]  # Remove .tar too

    shutil.make_archive(base_name, "gztar", source.parent, source.name)

    return archive_path


def extract_archive(archive_path: Path, destination: Path) -> Path:
    """Extract tar.gz archive to destination.

    Args:
        archive_path: Path to .tar.gz archive.
        destination: Where to extract.

    Returns:
        Destination path.

    Raises:
        FileNotFoundError: If archive does not exist.
    """
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    destination.mkdir(parents=True, exist_ok=True)

    shutil.unpack_archive(str(archive_path), str(destination), format="gztar")

    return destination
