"""Version pattern detection and supersession analysis."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from fileforge.models import FileRecord


def extract_version(filename: str) -> tuple[int, int, int] | None:
    """Extract semantic version from filename.

    Looks for patterns like: name_v1, name_v1.2, name_v1.2.3, or just vX.Y.Z.

    Args:
        filename: The filename to parse.

    Returns:
        (major, minor, patch) tuple, or None if no version found.
    """
    name = Path(filename).stem  # Remove extension

    # Pattern: _vX or _vX.Y or _vX.Y.Z (with word boundary after)
    match = re.search(r"_v(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:_|$)", name)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2) or 0)
        patch = int(match.group(3) or 0)
        return (major, minor, patch)

    return None


def find_superseded_versions(records: list[FileRecord]) -> list[FileRecord]:
    """Find records that are superseded by higher versions of the same file.

    Args:
        records: List of FileRecords to analyze.

    Returns:
        List of records that have a newer version in the same group.
    """
    by_stem: dict[str, list[tuple[FileRecord, tuple[int, int, int]]]] = defaultdict(
        list
    )

    for record in records:
        stem = Path(record.path).stem
        # Remove _vX suffix to get base name
        base_stem = re.sub(r"_v\d+(?:\.\d+)*$", "", stem)
        version = extract_version(record.name) or (0, 0, 0)
        by_stem[base_stem].append((record, version))

    superseded = []
    for base_stem, candidates in by_stem.items():
        if len(candidates) > 1:
            # Sort by version, descending
            candidates.sort(key=lambda x: x[1], reverse=True)
            # All except the latest are superseded
            for record, _ in candidates[1:]:
                superseded.append(record)

    return superseded
