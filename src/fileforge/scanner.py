"""Recursive directory scanner with ignore-pattern support."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterator

from rich.progress import Progress, SpinnerColumn, TextColumn

from fileforge.models import FileRecord


class Scanner:
    """Walks directories, collecting FileRecord metadata.

    Args:
        ignore_patterns: Glob patterns (gitignore-style) to skip.
        max_depth: Maximum directory depth. -1 means unlimited.
    """

    def __init__(self, ignore_patterns: list[str], max_depth: int = -1) -> None:
        self._patterns = ignore_patterns
        self._max_depth = max_depth

    @classmethod
    def from_directory(cls, root: Path, ignore_patterns: list[str]) -> "Scanner":
        """Create a Scanner, merging .forgeignore from root into patterns.

        Args:
            root: Directory to look for .forgeignore.
            ignore_patterns: Base patterns from config.

        Returns:
            Scanner with merged patterns.
        """
        forgeignore = root / ".forgeignore"
        extra: list[str] = []
        if forgeignore.exists():
            for line in forgeignore.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    extra.append(line)
        return cls(ignore_patterns + extra)

    def scan(self, dirs: list[Path]) -> Iterator[FileRecord]:
        """Yield FileRecord for each file found under all dirs.

        Args:
            dirs: Root directories to scan.

        Yields:
            FileRecord for each non-ignored file.
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Scanning...", total=None)
            for root in dirs:
                yield from self._walk(root, root, depth=0, progress=progress, task=task)

    def _walk(
        self,
        root: Path,
        current: Path,
        depth: int,
        progress: Progress,
        task: int,
    ) -> Iterator[FileRecord]:
        """Recursive walk helper.

        Args:
            root: Original scan root (for depth calculation).
            current: Current directory being walked.
            depth: Current depth from root.
            progress: Rich progress instance.
            task: Rich task ID for updates.
        """
        if self._max_depth != -1 and depth > self._max_depth:
            return

        try:
            entries = list(current.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if self._should_ignore(entry):
                continue

            if entry.is_dir(follow_symlinks=False):
                yield from self._walk(root, entry, depth + 1, progress, task)
            elif entry.is_file(follow_symlinks=False):
                try:
                    record = self._make_record(entry)
                except (FileNotFoundError, PermissionError, OSError):
                    continue
                progress.update(task, description=f"Scanning {entry.name}")
                yield record

    def _should_ignore(self, path: Path) -> bool:
        """Return True if path matches any ignore pattern.

        Args:
            path: The filesystem path to check.

        Returns:
            True if the path should be excluded from scanning.
        """
        name = path.name
        # Check trailing slash patterns (directory indicators)
        dir_pattern = f"{name}/" if path.is_dir() else None
        for pattern in self._patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
            if dir_pattern and fnmatch.fnmatch(dir_pattern, pattern):
                return True
        return False

    @staticmethod
    def _make_record(path: Path) -> FileRecord:
        """Build a FileRecord from a file's stat metadata.

        Args:
            path: Path to the file.

        Returns:
            A FileRecord populated with filesystem metadata.
        """
        from datetime import UTC, datetime

        stat = path.stat()
        return FileRecord(
            path=path,
            name=path.name,
            extension=path.suffix.lower(),
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
        )
