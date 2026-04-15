"""Tests for the config module."""

from __future__ import annotations

from pathlib import Path

import pytest

from fileforge.config import FileForgeConfig, load_config


def test_load_config_defaults(tmp_dir: Path) -> None:
    """Config with no file returns all defaults."""
    cfg = load_config(None)
    assert cfg.ai.classification_model == "qwen3:4b"
    assert cfg.staleness.stale_days == 365
    assert cfg.duplicates.similarity_threshold == 0.92


def test_load_config_from_toml(tmp_dir: Path) -> None:
    """TOML file values override defaults."""
    toml = tmp_dir / "fileforge.toml"
    toml.write_text("[staleness]\nstale_days = 180\n")
    cfg = load_config(toml)
    assert cfg.staleness.stale_days == 180
    assert cfg.ai.classification_model == "qwen3:4b"  # still default


def test_load_config_missing_file_raises(tmp_dir: Path) -> None:
    """Non-existent config path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config(tmp_dir / "nonexistent.toml")
