from datetime import UTC, datetime
from pathlib import Path

import pytest

from fileforge.db import SessionDB
from fileforge.models import FileRecord


def test_log_action_creates_record(tmp_dir: Path) -> None:
    """Logging an action creates a database record."""
    db = SessionDB(tmp_dir / "test.db")
    session_id = db.create_session([Path("/tmp")])

    # Create a file record first
    record = FileRecord(
        path=Path("test.txt"),
        name="test.txt",
        extension=".txt",
        size_bytes=100,
        modified_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    inserted = db.insert_record(session_id, record)

    # Log action
    action_id = db.log_action(
        session_id=session_id,
        record_id=inserted.id,
        action_type="move",
        source_path=Path("test.txt"),
        destination_path=Path("archive/test.txt"),
    )

    assert action_id > 0
    db.close()


def test_add_to_trash_creates_entry(tmp_dir: Path) -> None:
    """Adding file to trash creates a trash entry."""
    db = SessionDB(tmp_dir / "test.db")

    trash_id = db.add_to_trash(
        original_path=Path("/home/user/doc.txt"),
        trash_path=Path("/home/user/.trash/2026-04-15/doc_123456.txt"),
        size_bytes=1024,
        sha256="abc123",
    )

    assert trash_id > 0
    db.close()
