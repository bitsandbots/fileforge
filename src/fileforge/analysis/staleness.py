"""Stale and outdated file detection."""

from __future__ import annotations

import fnmatch
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fileforge.models import FileRecord


def is_stale(record: FileRecord, stale_days: int) -> bool:
    """Check if a file is older than the stale threshold.

    Args:
        record: FileRecord to check.
        stale_days: Threshold in days. -1 means never stale.

    Returns:
        True if file is older than stale_days, False otherwise.
    """
    if stale_days < 0:
        return False

    age = (datetime.now(UTC) - record.modified_at).days
    return age > stale_days


def matches_junk_pattern(filename: str, junk_patterns: list[str]) -> bool:
    """Check if filename matches any junk pattern.

    Args:
        filename: Name to check.
        junk_patterns: fnmatch-style patterns.

    Returns:
        True if filename matches any pattern.
    """
    return any(fnmatch.fnmatch(filename, p) for p in junk_patterns)
