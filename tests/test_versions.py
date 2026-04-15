"""Tests for version pattern detection and supersession analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from fileforge.analysis.versions import extract_version, find_superseded_versions
from fileforge.models import FileRecord


def test_extract_version_simple() -> None:
    """Extract version from simple pattern: name_v1.ext, name_v2.ext."""
    assert extract_version("report_v1.docx") == (1, 0, 0)
    assert extract_version("report_v2.docx") == (2, 0, 0)
    assert extract_version("project_final.pdf") is None
    assert extract_version("file_v1.2.3.txt") == (1, 2, 3)
    assert extract_version("v2024_01_15.txt") is None  # date pattern, not version


def test_find_superseded_versions() -> None:
    """Older versions are marked as superseded by newer ones."""
    now = datetime.now(UTC)

    v1 = FileRecord(
        path=Path("report_v1.docx"),
        name="report_v1.docx",
        extension=".docx",
        size_bytes=100,
        modified_at=now,
        created_at=now,
    )
    v2 = FileRecord(
        path=Path("report_v2.docx"),
        name="report_v2.docx",
        extension=".docx",
        size_bytes=120,
        modified_at=now,
        created_at=now,
    )

    superseded = find_superseded_versions([v1, v2])
    # v1 is superseded by v2 (same stem, higher version)
    assert v1 in superseded
    assert v2 not in superseded
