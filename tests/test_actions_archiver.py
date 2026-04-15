"""Tests for archiver action module."""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from fileforge.actions.archiver import create_archive, extract_archive


def test_create_archive_from_file() -> None:
    """File is compressed into tar.gz archive."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create source file
        src = tmpdir / "HARNESS_file.txt"
        src.write_text("content")

        # Create archive
        archive = tmpdir / "archive.tar.gz"
        result = create_archive(src, archive)

        # Verify archive exists
        assert archive.exists()
        assert result == archive
        # Archive should have positive size
        assert archive.stat().st_size > 0


def test_extract_archive() -> None:
    """Archive is extracted to destination."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create source file
        src = tmpdir / "HARNESS_file.txt"
        src.write_text("content")

        # Create and extract archive
        archive = tmpdir / "archive.tar.gz"
        create_archive(src, archive)

        # Extract to new location
        extract_dir = tmpdir / "extracted"
        extract_archive(archive, extract_dir)

        # Verify extracted file
        extracted_file = extract_dir / "HARNESS_file.txt"
        assert extracted_file.exists()
        assert extracted_file.read_text() == "content"


def test_create_archive_raises_on_missing_source() -> None:
    """Creating archive from nonexistent source raises FileNotFoundError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        with pytest.raises(FileNotFoundError):
            create_archive(tmpdir / "nonexistent.txt", tmpdir / "archive.tar.gz")
