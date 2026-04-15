"""Tests for stale and outdated file detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fileforge.analysis.staleness import is_stale
from fileforge.models import FileRecord


def test_is_stale_by_age() -> None:
    """File older than stale_days threshold is marked stale."""
    old_date = datetime.now(UTC) - timedelta(days=400)
    record = FileRecord(
        path=Path("HARNESS_old.txt"),
        name="HARNESS_old.txt",
        extension=".txt",
        size_bytes=100,
        modified_at=old_date,
        created_at=old_date,
    )
    assert is_stale(record, stale_days=365) is True


def test_is_stale_by_pattern() -> None:
    """File matching junk pattern is marked stale."""
    from fileforge.analysis.staleness import matches_junk_pattern

    assert matches_junk_pattern("Thumbs.db", junk_patterns=["Thumbs.db"]) is True
    assert matches_junk_pattern("file.txt", junk_patterns=["Thumbs.db"]) is False
    assert matches_junk_pattern("backup~", junk_patterns=["*~"]) is True
