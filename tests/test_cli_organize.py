"""Tests for the organize CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from fileforge.cli import app

runner = CliRunner()


def test_organize_dry_run_previews_only(tmp_path: Path) -> None:
    """organize --dry-run previews actions without moving files."""
    # Create files in different categories
    (tmp_path / "HARNESS_proposal.txt").write_text("consulting proposal for nonprofit")
    (tmp_path / "HARNESS_notes.txt").write_text("project meeting notes")

    # Mock home directory to use tmp_path
    with patch.object(Path, "home", return_value=tmp_path):
        result = runner.invoke(app, ["organize", str(tmp_path), "--dry-run"])

    assert result.exit_code == 0, result.output
    # Should show preview, not execute
    assert "DRY RUN" in result.output or "dry-run" in result.output.lower()
    # Files should still exist in original location (dry-run doesn't move)
    assert (tmp_path / "HARNESS_proposal.txt").exists()
    assert (tmp_path / "HARNESS_notes.txt").exists()


def test_organize_moves_files_to_category_folders(tmp_path: Path) -> None:
    """organize moves files to ~/Organized/<category>/ folders."""
    # Create a file that will be classified
    (tmp_path / "HARNESS_proposal.txt").write_text("consulting proposal for nonprofit")

    # Organized folder will be under tmp_path (simulating home)
    organized_base = tmp_path / "Organized"

    # Mock home directory and classify_file
    with (
        patch.object(Path, "home", return_value=tmp_path),
        patch("fileforge.cli.classify_file", return_value="Work/Proposals"),
    ):
        result = runner.invoke(app, ["organize", str(tmp_path)])

    assert result.exit_code == 0, result.output
    # Original file should be moved (no longer in source)
    assert not (tmp_path / "HARNESS_proposal.txt").exists()
    # File should exist in category folder
    assert (organized_base / "Work" / "Proposals" / "HARNESS_proposal.txt").exists()


def test_organize_moves_duplicates_to_duplicates_folder(tmp_path: Path) -> None:
    """organize handles duplicates by moving to duplicates folder."""
    # Create duplicate files (same content)
    content = "duplicate content for testing"
    (tmp_path / "HARNESS_file1.txt").write_text(content)
    (tmp_path / "HARNESS_file2.txt").write_text(content)

    organized_base = tmp_path / "Organized"
    duplicates_dir = organized_base / "Duplicates"

    # Mock home directory and classify_file
    with (
        patch.object(Path, "home", return_value=tmp_path),
        patch("fileforge.cli.classify_file", return_value="Documents"),
    ):
        result = runner.invoke(app, ["organize", str(tmp_path)])

    assert result.exit_code == 0, result.output
    # One file should be in Documents folder, one in Duplicates/Documents
    docs_files = list((organized_base / "Documents").glob("HARNESS_*.txt"))
    dup_files = list((duplicates_dir / "Documents").glob("HARNESS_*.txt"))
    # Exactly one file in Documents and one in Duplicates
    assert len(docs_files) == 1, f"Expected 1 file in Documents, got {len(docs_files)}"
    assert len(dup_files) == 1, f"Expected 1 file in Duplicates, got {len(dup_files)}"


def test_organize_moves_stale_to_trash(tmp_path: Path) -> None:
    """organize moves stale files to trash directory."""
    # Create an old file (simulating stale)
    (tmp_path / "HARNESS_old.txt").write_text("old content from years ago")

    trash_dir = tmp_path / ".trash"

    # Mock home directory, classify_file, and staleness detection
    with (
        patch.object(Path, "home", return_value=tmp_path),
        patch("fileforge.cli.classify_file", return_value="Documents"),
        patch("fileforge.analysis.staleness.is_stale", return_value=True),
        patch("fileforge.analysis.staleness.matches_junk_pattern", return_value=False),
    ):
        result = runner.invoke(
            app, ["organize", str(tmp_path), "--trash-dir", str(trash_dir)]
        )

    assert result.exit_code == 0, result.output
    # File should be moved to trash
    assert (trash_dir / "HARNESS_old.txt").exists() or "stale" in result.output.lower()


def test_organize_validates_paths(tmp_path: Path) -> None:
    """organize validates directory paths before starting."""
    nonexistent = tmp_path / "HARNESS_nonexistent"

    # Mock home directory
    with patch.object(Path, "home", return_value=tmp_path):
        result = runner.invoke(app, ["organize", str(nonexistent)])

    assert result.exit_code == 1
    assert (
        "not a directory" in result.output.lower() or "error" in result.output.lower()
    )
