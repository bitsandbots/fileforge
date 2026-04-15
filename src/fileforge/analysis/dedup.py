"""SHA-256-based exact duplicate detection."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from fileforge.models import FileRecord

_CHUNK = 65536  # 64 KB read chunks


def hash_file(path: Path) -> str:
    """Compute the SHA-256 hash of a file.

    Reads in chunks to handle large files without loading into memory.

    Args:
        path: Path to the file to hash.

    Returns:
        Lowercase hex SHA-256 digest string (64 chars).
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def find_exact_duplicates(records: list[FileRecord]) -> list[list[FileRecord]]:
    """Group FileRecords that are byte-for-byte identical.

    Files with the same SHA-256 hash are considered exact duplicates.
    Records without a sha256 value (failed hashing) are silently skipped.

    Args:
        records: List of FileRecords to analyze.

    Returns:
        List of groups. Each group is a list of 2+ FileRecords with
        identical content. Records with no duplicates are excluded.
    """
    by_hash: dict[str, list[FileRecord]] = defaultdict(list)

    for record in records:
        if record.sha256 is None:
            continue  # failed to hash earlier; exclude from dedup
        by_hash[record.sha256].append(record)

    return [group for group in by_hash.values() if len(group) > 1]
