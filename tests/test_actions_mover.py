"""Tests for mover action module."""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from fileforge.actions.mover import move_file


def test_move_file_to_destination() -> None:
    """File is moved to destination directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create source file
        src = tmpdir / "HARNESS_file.txt"
        src.write_text("content")

        # Move to destination
        dst = tmpdir / "subdir" / "HARNESS_file.txt"
        result = move_file(src, dst, create_dirs=True)

        # Verify source is gone
        assert not src.exists()
        # Verify file is at destination
        assert dst.exists()
        assert dst.read_text() == "content"
        assert result == dst


def test_move_file_raises_on_missing_source() -> None:
    """Moving nonexistent file raises FileNotFoundError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        with pytest.raises(FileNotFoundError):
            move_file(tmpdir / "nonexistent.txt", tmpdir / "dest.txt")


def test_move_file_raises_on_directory_source() -> None:
    """Moving a directory raises IsADirectoryError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        src_dir = tmpdir / "HARNESS_dir"
        src_dir.mkdir()

        with pytest.raises(IsADirectoryError):
            move_file(src_dir, tmpdir / "dest_dir")
