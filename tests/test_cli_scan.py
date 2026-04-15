"""Integration tests for the scan CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from fileforge.cli import app

runner = CliRunner()


def test_scan_command_runs_on_directory(tmp_dir: Path) -> None:
    """scan command runs without error on a test directory."""
    (tmp_dir / "HARNESS_a.txt").write_text("consulting proposal content")
    (tmp_dir / "HARNESS_b.txt").write_text("hydroponics project notes")

    result = runner.invoke(app, ["scan", str(tmp_dir), "--no-classify"])
    assert result.exit_code == 0, result.output
    assert "Scan complete" in result.output


def test_scan_reports_duplicate(tmp_dir: Path) -> None:
    """scan command identifies exact duplicates."""
    content = "duplicate file content for testing"
    (tmp_dir / "HARNESS_orig.txt").write_text(content)
    (tmp_dir / "HARNESS_copy.txt").write_text(content)

    result = runner.invoke(app, ["scan", str(tmp_dir), "--no-classify"])
    assert result.exit_code == 0
    assert "duplicate" in result.output.lower()


def test_scan_nonexistent_directory_exits_with_error() -> None:
    """scan command exits 1 with a clear message for a non-existent path."""
    result = runner.invoke(app, ["scan", "/tmp/fileforge_harness_nonexistent_12345"])
    assert result.exit_code == 1
    assert "not a directory" in result.output
