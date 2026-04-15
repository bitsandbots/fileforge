"""Tests for --interactive and --dry-run CLI flags."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from fileforge.cli import app

runner = CliRunner()


def test_interactive_flag_generates_html_report(tmp_dir: Path) -> None:
    """--interactive flag generates an HTML report."""
    (tmp_dir / "HARNESS_a.txt").write_text("content a")
    (tmp_dir / "HARNESS_b.txt").write_text("content b")

    result = runner.invoke(
        app,
        ["scan", str(tmp_dir), "--no-classify", "--interactive"],
    )

    assert result.exit_code == 0
    assert "Report generated:" in result.output or "Opening in browser" in result.output


def test_dry_run_flag_shows_preview(tmp_dir: Path) -> None:
    """--dry-run flag shows action preview without executing."""
    content = "duplicate"
    (tmp_dir / "HARNESS_a.txt").write_text(content)
    (tmp_dir / "HARNESS_b.txt").write_text(content)

    result = runner.invoke(
        app,
        ["scan", str(tmp_dir), "--no-classify", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "[DRY RUN]" in result.output or "dry" in result.output.lower()


def test_interactive_without_browser_handles_error(tmp_dir: Path) -> None:
    """Interactive mode handles missing browser gracefully."""
    (tmp_dir / "HARNESS_file.txt").write_text("content")

    with patch("fileforge.cli.webbrowser.open", side_effect=Exception("No browser")):
        result = runner.invoke(
            app,
            ["scan", str(tmp_dir), "--no-classify", "--interactive"],
        )

    assert result.exit_code == 0
    assert "report.html" in result.output or "Open manually" in result.output
