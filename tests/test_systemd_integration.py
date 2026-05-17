"""Tests for systemd integration templates and installation."""

import subprocess
import tempfile
from pathlib import Path


def test_service_template_exists() -> None:
    """Service template file exists and has correct structure."""
    service_file = (
        Path(__file__).parent.parent / "src/fileforge/systemd/fileforge-scan.service"
    )

    assert service_file.exists()
    content = service_file.read_text()

    # Check required sections
    assert "[Unit]" in content
    assert "[Service]" in content
    assert "[Install]" in content

    # Check required fields
    assert "Description=" in content
    assert "ExecStart=" in content
    assert "Type=oneshot" in content


def test_timer_template_exists() -> None:
    """Timer template file exists and has correct structure."""
    timer_file = (
        Path(__file__).parent.parent / "src/fileforge/systemd/fileforge-scan.timer"
    )

    assert timer_file.exists()
    content = timer_file.read_text()

    # Check required sections
    assert "[Unit]" in content
    assert "[Timer]" in content
    assert "[Install]" in content

    # Check required fields
    assert "OnCalendar=" in content
    assert "Persistent=" in content


def test_server_service_template_exists() -> None:
    """Server service template file exists and has correct structure."""
    service_file = (
        Path(__file__).parent.parent / "src/fileforge/systemd/fileforge-server.service"
    )

    assert service_file.exists()
    content = service_file.read_text()

    assert "[Unit]" in content
    assert "[Service]" in content
    assert "[Install]" in content

    assert "Description=" in content
    assert "ExecStart=" in content
    assert "Type=simple" in content
    assert "Restart=" in content
    assert "fileforge server" in content


def test_install_script_exists() -> None:
    """Install script exists and is executable."""
    install_script = Path(__file__).parent.parent / "src/fileforge/systemd/install.sh"

    assert install_script.exists()

    # Check script has shebang
    content = install_script.read_text()
    assert content.startswith("#!/bin/bash")

    # Check script contains key commands
    assert "systemctl --user" in content
    assert "daemon-reload" in content
    assert "enable fileforge-scan.timer" in content
    assert "enable fileforge-server.service" in content
    # Mode flags
    assert "--scan" in content
    assert "--server" in content
    assert "--all" in content


def test_install_script_substitution() -> None:
    """Install script substitutes user paths correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        service_template = (
            Path(__file__).parent.parent
            / "src/fileforge/systemd/fileforge-scan.service"
        )

        # Create a test service file with substitution
        test_service = Path(tmpdir) / "test.service"

        # Run the substitution command from install.sh (matches current install.sh)
        sed_cmd = f'sed "s|%h|/home/testuser|g" "{service_template}" > "{test_service}"'
        subprocess.run(sed_cmd, shell=True, check=True)

        # Verify substitution worked
        content = test_service.read_text()
        assert "/home/testuser/.local/bin/fileforge" in content
        assert "/home/testuser/Documents" in content
