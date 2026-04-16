"""Tests for the dupes CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from fileforge.cli import app

runner = CliRunner()


def test_dupes_shows_duplicate_report(tmp_path: Path) -> None:
    """dupes shows duplicate report without taking actions by default."""
    # Create duplicate files (same content)
    content = "duplicate content for testing"
    (tmp_path / "HARNESS_file1.txt").write_text(content)
    (tmp_path / "HARNESS_file2.txt").write_text(content)
    (tmp_path / "HARNESS_unique.txt").write_text("unique content")

    # Mock home directory
    with patch.object(Path, "home", return_value=tmp_path):
        result = runner.invoke(app, ["dupes", str(tmp_path)])

    assert result.exit_code == 0, result.output
    # Should report duplicates found
    assert "duplicate" in result.output.lower() or "2 file" in result.output
    # Files should still exist (no deletion by default)
    assert (tmp_path / "HARNESS_file1.txt").exists()
    assert (tmp_path / "HARNESS_file2.txt").exists()
    assert (tmp_path / "HARNESS_unique.txt").exists()


def test_dupes_dry_run_previews_only(tmp_path: Path) -> None:
    """dupes --dry-run previews actions without executing."""
    # Create duplicate files
    content = "duplicate content for testing"
    (tmp_path / "HARNESS_file1.txt").write_text(content)
    (tmp_path / "HARNESS_file2.txt").write_text(content)

    # Mock home directory
    with patch.object(Path, "home", return_value=tmp_path):
        result = runner.invoke(app, ["dupes", str(tmp_path), "--delete", "--dry-run"])

    assert result.exit_code == 0, result.output
    # Should show preview, not execute
    assert "DRY RUN" in result.output or "dry-run" in result.output.lower()
    # Files should still exist (dry-run doesn't delete)
    assert (tmp_path / "HARNESS_file1.txt").exists()
    assert (tmp_path / "HARNESS_file2.txt").exists()


def test_dupes_delete_removes_duplicates(tmp_path: Path) -> None:
    """dupes --delete permanently removes duplicate files, keeping one."""
    # Create duplicate files (same content)
    content = "duplicate content for testing"
    (tmp_path / "HARNESS_original.txt").write_text(content)
    (tmp_path / "HARNESS_duplicate.txt").write_text(content)
    (tmp_path / "HARNESS_unique.txt").write_text("unique content")

    # Mock home directory
    with patch.object(Path, "home", return_value=tmp_path):
        result = runner.invoke(app, ["dupes", str(tmp_path), "--delete"])

    assert result.exit_code == 0, result.output
    # One of the duplicates should be deleted
    remaining_dupes = sum(
        1
        for f in ["HARNESS_original.txt", "HARNESS_duplicate.txt"]
        if (tmp_path / f).exists()
    )
    assert (
        remaining_dupes == 1
    ), f"Expected 1 duplicate to remain, got {remaining_dupes}"
    # Unique file should still exist
    assert (tmp_path / "HARNESS_unique.txt").exists()


def test_dupes_move_moves_duplicates(tmp_path: Path) -> None:
    """dupes --move moves duplicates to duplicates folder."""
    # Create duplicate files
    content = "duplicate content for testing"
    (tmp_path / "HARNESS_file1.txt").write_text(content)
    (tmp_path / "HARNESS_file2.txt").write_text(content)

    duplicates_dir = tmp_path / "Duplicates"

    # Mock home directory
    with patch.object(Path, "home", return_value=tmp_path):
        result = runner.invoke(
            app,
            ["dupes", str(tmp_path), "--move", "--duplicates-dir", str(duplicates_dir)],
        )

    assert result.exit_code == 0, result.output
    # One duplicate should be moved to duplicates folder
    moved_files = list(duplicates_dir.glob("HARNESS_*.txt"))
    assert (
        len(moved_files) == 1
    ), f"Expected 1 file in duplicates folder, got {len(moved_files)}"


def test_dupes_validates_paths(tmp_path: Path) -> None:
    """dupes validates directory paths before starting."""
    nonexistent = tmp_path / "HARNESS_nonexistent"

    # Mock home directory
    with patch.object(Path, "home", return_value=tmp_path):
        result = runner.invoke(app, ["dupes", str(nonexistent)])

    assert result.exit_code == 1
    assert (
        "not a directory" in result.output.lower() or "error" in result.output.lower()
    )


def test_dupes_conflicting_flags_error(tmp_path: Path) -> None:
    """dupes errors when both --delete and --move are specified."""
    # Create a file
    (tmp_path / "HARNESS_file.txt").write_text("test content")

    # Mock home directory
    with patch.object(Path, "home", return_value=tmp_path):
        result = runner.invoke(app, ["dupes", str(tmp_path), "--delete", "--move"])

    assert result.exit_code == 1
    assert (
        "error" in result.output.lower() or "cannot use both" in result.output.lower()
    )
