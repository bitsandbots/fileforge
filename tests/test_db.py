"""Tests for the DB session management module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fileforge.db import SessionDB
from fileforge.models import FileRecord


def test_create_session(tmp_dir: Path) -> None:
    """SessionDB creates SQLite file and returns a session ID."""
    db = SessionDB(tmp_dir / "test.db")
    session_id = db.create_session(scan_dirs=[tmp_dir])
    assert isinstance(session_id, int)
    assert session_id > 0


def test_insert_and_fetch_record(tmp_dir: Path) -> None:
    """Inserting a FileRecord and fetching it returns matching data."""
    db = SessionDB(tmp_dir / "test.db")
    session_id = db.create_session(scan_dirs=[tmp_dir])

    record = FileRecord(
        path=tmp_dir / "HARNESS_test.txt",
        name="HARNESS_test.txt",
        extension=".txt",
        size_bytes=42,
        modified_at=datetime(2024, 1, 15, 12, 0),
        created_at=datetime(2024, 1, 15, 10, 0),
    )
    inserted = db.insert_record(session_id, record)
    assert inserted.id is not None

    fetched = db.get_record(inserted.id)
    assert fetched is not None
    assert fetched.name == "HARNESS_test.txt"
    assert fetched.size_bytes == 42


def test_update_record_sha256(tmp_dir: Path) -> None:
    """Updating sha256 on a record persists the change."""
    db = SessionDB(tmp_dir / "test.db")
    session_id = db.create_session(scan_dirs=[tmp_dir])
    record = FileRecord(
        path=tmp_dir / "HARNESS_doc.txt",
        name="HARNESS_doc.txt",
        extension=".txt",
        size_bytes=10,
        modified_at=datetime(2024, 6, 1),
        created_at=datetime(2024, 6, 1),
    )
    inserted = db.insert_record(session_id, record)
    db.update_sha256(inserted.id, "abc123hash")

    fetched = db.get_record(inserted.id)
    assert fetched.sha256 == "abc123hash"


def test_update_category(tmp_dir: Path) -> None:
    """Updating category on a record persists the change."""
    db = SessionDB(tmp_dir / "test.db")
    session_id = db.create_session(scan_dirs=[tmp_dir])
    record = FileRecord(
        path=tmp_dir / "HARNESS_proposal.txt",
        name="HARNESS_proposal.txt",
        extension=".txt",
        size_bytes=20,
        modified_at=datetime(2024, 6, 1),
        created_at=datetime(2024, 6, 1),
    )
    inserted = db.insert_record(session_id, record)
    db.update_category(inserted.id, "Work/Consulting/Proposals")

    fetched = db.get_record(inserted.id)
    assert fetched.category == "Work/Consulting/Proposals"


def test_list_records_for_session(tmp_dir: Path) -> None:
    """list_records returns all records for a session."""
    db = SessionDB(tmp_dir / "test.db")
    session_id = db.create_session(scan_dirs=[tmp_dir])
    for i in range(3):
        db.insert_record(
            session_id,
            FileRecord(
                path=tmp_dir / f"HARNESS_file{i}.txt",
                name=f"HARNESS_file{i}.txt",
                extension=".txt",
                size_bytes=i * 10,
                modified_at=datetime(2024, 1, i + 1),
                created_at=datetime(2024, 1, i + 1),
            ),
        )
    records = list(db.list_records(session_id))
    assert len(records) == 3
