"""TOML configuration loading with Pydantic validation."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field


class GeneralConfig(BaseModel):
    scan_dirs: list[str] = Field(default_factory=lambda: ["~/Documents"])
    output_dir: str = "~/.fileforge"
    max_depth: int = -1
    max_extract_size: int = 52_428_800  # 50 MB


class AIConfig(BaseModel):
    classification_model: str = "qwen3:4b"
    embedding_model: str = "nomic-embed-text"
    ollama_url: str = "http://localhost:11434"
    snippet_length: int = 2000
    category_hints: str = ""


class DuplicatesConfig(BaseModel):
    similarity_threshold: float = 0.92
    semantic_dedup: bool = True


class StalenessConfig(BaseModel):
    stale_days: int = 365
    junk_patterns: list[str] = Field(
        default_factory=lambda: [
            "Thumbs.db",
            ".DS_Store",
            "desktop.ini",
            "~$*",
            "*.tmp",
        ]
    )
    temp_patterns: list[str] = Field(
        default_factory=lambda: ["*.bak", "*.swp", "*.log", "*.orig"]
    )
    detect_versions: bool = True


class IgnoreConfig(BaseModel):
    patterns: list[str] = Field(
        default_factory=lambda: [
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "*.iso",
            "*.vmdk",
        ]
    )


class FileForgeConfig(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    duplicates: DuplicatesConfig = Field(default_factory=DuplicatesConfig)
    staleness: StalenessConfig = Field(default_factory=StalenessConfig)
    ignore: IgnoreConfig = Field(default_factory=IgnoreConfig)


def load_config(path: Path | None) -> FileForgeConfig:
    """Load config from TOML file, falling back to defaults.

    Args:
        path: Path to fileforge.toml, or None for all defaults.

    Returns:
        Validated FileForgeConfig instance.

    Raises:
        FileNotFoundError: If path is provided but does not exist.
    """
    if path is None:
        return FileForgeConfig()

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    return FileForgeConfig.model_validate(raw)
