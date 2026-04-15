"""Shared test fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir() -> Path:
    """Provide a temporary directory cleaned up after each test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_txt(tmp_dir: Path) -> Path:
    """Write a sample test text file using the HARNESS_ prefix.

    Args:
        tmp_dir: Temporary directory fixture.

    Returns:
        Path to the created test file.
    """
    p = tmp_dir / "HARNESS_sample.txt"
    p.write_text("This is a consulting proposal for a nonprofit client.\n")
    return p


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory.

    Returns:
        Path to tests/fixtures/.
    """
    return Path(__file__).parent / "fixtures"
