"""Core data models for FileForge."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


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


class ActionLog(BaseModel):
    """Record of a file action taken (move, archive, delete)."""

    id: int | None = None
    session_id: int
    record_id: int
    action_type: str  # "move", "archive", "delete"
    source_path: Path
    destination_path: Path | None = None
    archive_path: Path | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dry_run: bool = False
    status: str = "pending"  # pending, completed, failed, undone
    error_message: str | None = None
    model_config = {"arbitrary_types_allowed": True}


class TrashEntry(BaseModel):
    """Entry in the trash with recovery information."""

    id: int | None = None
    original_path: Path
    trash_path: Path
    trash_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    size_bytes: int
    sha256: str | None = None
    model_config = {"arbitrary_types_allowed": True}
