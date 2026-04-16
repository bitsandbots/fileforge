"""Tests for CLI watch and schedule commands."""

from pathlib import Path
import tempfile
from typer.testing import CliRunner

from fileforge.cli import app

runner = CliRunner()


def test_watch_command_validates_paths() -> None:
    """Watch command validates directory paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["watch", tmpdir, "/nonexistent/path"])

        # Should fail with error about nonexistent path
        assert result.exit_code == 1
        assert "not a directory" in result.output


def test_schedule_command_validates_paths() -> None:
    """Schedule command validates directory paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["schedule", tmpdir, "/nonexistent/path"])

        # Should fail with error about nonexistent path
        assert result.exit_code == 1
        assert "not a directory" in result.output


def test_schedule_command_creates_job() -> None:
    """Schedule command creates a job in the database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create a config file
        config_content = f"""
[general]
output_dir = "{tmpdir_path}"

[schedule]
enabled = true
"""
        config_file = tmpdir_path / "config.toml"
        config_file.write_text(config_content)

        # Create a directory to scan
        scan_dir = tmpdir_path / "scan_me"
        scan_dir.mkdir()

        result = runner.invoke(
            app, ["schedule", str(scan_dir), "--config", str(config_file)]
        )

        # Should succeed
        assert result.exit_code == 0
        assert "scheduled" in result.output.lower() or "job" in result.output.lower()
