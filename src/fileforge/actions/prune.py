"""Remove empty directories after file operations."""

from __future__ import annotations

import os
from pathlib import Path


def prune_empty_dirs(roots: list[Path], dry_run: bool = False) -> list[Path]:
    """Remove empty subdirectories under each root.

    Traverses bottom-up so nested empty directories are cleaned in a single
    pass without requiring multiple calls. Root directories themselves are
    never removed.

    Args:
        roots: Directories to prune under (the roots themselves are kept).
        dry_run: Return what would be removed without deleting anything.

    Returns:
        Paths removed, or that would be removed in dry_run mode.
    """
    removed: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, _dirnames, _filenames in os.walk(str(root), topdown=False):
            candidate = Path(dirpath)
            if candidate == root:
                continue
            try:
                if not os.listdir(dirpath):
                    if not dry_run:
                        candidate.rmdir()
                    removed.append(candidate)
            except PermissionError:
                pass
            except OSError:
                pass
    return removed
