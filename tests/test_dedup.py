"""Tests for SHA-256 duplicate detection."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fileforge.analysis.dedup import hash_file, find_exact_duplicates
from fileforge.models import FileRecord


def _make_record(path: Path) -> FileRecord:
    """Create a FileRecord with sha256 pre-computed for dedup tests."""
    stat = path.stat()
    return FileRecord(
        path=path,
        name=path.name,
        extension=path.suffix,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        created_at=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
        sha256=hash_file(path),
    )


def test_hash_file_deterministic(tmp_dir: Path) -> None:
    """Same content always produces same hash."""
    f = tmp_dir / "HARNESS_a.txt"
    f.write_text("hello world")
    h1 = hash_file(f)
    h2 = hash_file(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest is 64 chars


def test_hash_file_different_content(tmp_dir: Path) -> None:
    """Different content produces different hashes."""
    a = tmp_dir / "HARNESS_a.txt"
    b = tmp_dir / "HARNESS_b.txt"
    a.write_text("hello")
    b.write_text("world")
    assert hash_file(a) != hash_file(b)


def test_find_exact_duplicates_identifies_copies(tmp_dir: Path) -> None:
    """Files with identical content are grouped as duplicates."""
    content = "duplicate content here"
    original = tmp_dir / "HARNESS_original.txt"
    copy1 = tmp_dir / "HARNESS_copy1.txt"
    copy2 = tmp_dir / "HARNESS_copy2.txt"
    unique = tmp_dir / "HARNESS_unique.txt"

    original.write_text(content)
    copy1.write_text(content)
    copy2.write_text(content)
    unique.write_text("something else entirely")

    records = [_make_record(f) for f in [original, copy1, copy2, unique]]
    groups = find_exact_duplicates(records)

    assert len(groups) == 1  # one duplicate group
    group_paths = {r.path for r in groups[0]}
    assert original in group_paths
    assert copy1 in group_paths
    assert copy2 in group_paths
    assert unique not in group_paths


def test_find_exact_duplicates_no_duplicates(tmp_dir: Path) -> None:
    """Returns empty list when all files are unique."""
    for i in range(3):
        (tmp_dir / f"HARNESS_file{i}.txt").write_text(f"unique content {i}")

    records = [_make_record(f) for f in tmp_dir.iterdir()]
    groups = find_exact_duplicates(records)
    assert groups == []
