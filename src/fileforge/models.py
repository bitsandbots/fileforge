"""Core data models for FileForge."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class FileRecord(BaseModel):
    """Represents a scanned file with all metadata and analysis results."""

    id: int | None = None
    path: Path
    name: str
    extension: str
    size_bytes: int
    modified_at: datetime
    created_at: datetime
    sha256: str | None = None
    content_snippet: str | None = None
    category: str | None = None
    embedding: list[float] | None = None
    is_duplicate: bool = False
    duplicate_of: Path | None = None
    is_stale: bool = False
    stale_reason: str | None = None

    model_config = {"arbitrary_types_allowed": True}
