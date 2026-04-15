"""SQLite session management for FileForge scan state."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from fileforge.models import FileRecord


class SessionDB:
    """Manages a SQLite database for scan sessions and file records.

    Args:
        db_path: Path to the SQLite file. Created if it does not exist.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_dirs TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS file_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                path TEXT NOT NULL,
                name TEXT NOT NULL,
                extension TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sha256 TEXT,
                content_snippet TEXT,
                category TEXT,
                embedding TEXT,
                is_duplicate INTEGER NOT NULL DEFAULT 0,
                duplicate_of TEXT,
                is_stale INTEGER NOT NULL DEFAULT 0,
                stale_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                record_id INTEGER NOT NULL REFERENCES file_records(id),
                action_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                destination_path TEXT,
                archive_path TEXT,
                timestamp TEXT NOT NULL,
                dry_run INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS trash (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                trash_path TEXT NOT NULL,
                trash_at TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT
            );
        """)
        self._conn.commit()

    def create_session(self, scan_dirs: list[Path]) -> int:
        """Create a new scan session and return its ID.

        Args:
            scan_dirs: Root directories being scanned.

        Returns:
            The new session's integer ID.
        """
        cur = self._conn.execute(
            "INSERT INTO sessions (scan_dirs, created_at) VALUES (?, ?)",
            (json.dumps([str(d) for d in scan_dirs]), datetime.now(UTC).isoformat()),
        )
        self._conn.commit()
        return cur.lastrowid

    def insert_record(self, session_id: int, record: FileRecord) -> FileRecord:
        """Insert a FileRecord into the DB and return it with its ID set.

        Args:
            session_id: Session this record belongs to.
            record: The FileRecord to insert.

        Returns:
            A copy of the record with `id` populated.
        """
        cur = self._conn.execute(
            """INSERT INTO file_records
               (session_id, path, name, extension, size_bytes,
                modified_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                str(record.path),
                record.name,
                record.extension,
                record.size_bytes,
                record.modified_at.isoformat(),
                record.created_at.isoformat(),
            ),
        )
        self._conn.commit()
        return record.model_copy(update={"id": cur.lastrowid})

    def update_sha256(self, record_id: int, sha256: str) -> None:
        """Update the SHA-256 hash for a record.

        Args:
            record_id: The record's integer ID.
            sha256: The computed hash string.
        """
        self._conn.execute(
            "UPDATE file_records SET sha256 = ? WHERE id = ?",
            (sha256, record_id),
        )
        self._conn.commit()

    def update_category(self, record_id: int, category: str) -> None:
        """Update the AI-assigned category for a record.

        Args:
            record_id: The record's integer ID.
            category: The assigned category path string.
        """
        self._conn.execute(
            "UPDATE file_records SET category = ? WHERE id = ?",
            (category, record_id),
        )
        self._conn.commit()

    def get_record(self, record_id: int) -> FileRecord | None:
        """Fetch a single record by ID.

        Args:
            record_id: The record's integer ID.

        Returns:
            The FileRecord, or None if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM file_records WHERE id = ?", (record_id,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def list_records(self, session_id: int) -> Iterator[FileRecord]:
        """Yield all FileRecords for a session (memory-efficient).

        Args:
            session_id: The session to query.
        """
        cur = self._conn.execute(
            "SELECT * FROM file_records WHERE session_id = ?", (session_id,)
        )
        for row in cur:
            yield self._row_to_record(row)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> FileRecord:
        """Convert a SQLite row to a FileRecord.

        Args:
            row: A sqlite3.Row from the file_records table.

        Returns:
            A populated FileRecord instance.
        """
        return FileRecord(
            id=row["id"],
            path=Path(row["path"]),
            name=row["name"],
            extension=row["extension"],
            size_bytes=row["size_bytes"],
            modified_at=datetime.fromisoformat(row["modified_at"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            sha256=row["sha256"],
            content_snippet=row["content_snippet"],
            category=row["category"],
            is_duplicate=bool(row["is_duplicate"]),
            duplicate_of=Path(row["duplicate_of"]) if row["duplicate_of"] else None,
            is_stale=bool(row["is_stale"]),
            stale_reason=row["stale_reason"],
        )

    def update_stale(self, record_id: int, reason: str) -> None:
        """Mark a record as stale with a reason.

        Args:
            record_id: The record's integer ID.
            reason: The stale reason (e.g., "older than threshold", "superseded").
        """
        self._conn.execute(
            "UPDATE file_records SET is_stale = 1, stale_reason = ? WHERE id = ?",
            (reason, record_id),
        )
        self._conn.commit()

    def update_embedding(self, record_id: int, embedding: list[float]) -> None:
        """Store embedding for a record.

        Args:
            record_id: The record's integer ID.
            embedding: List of float values.
        """
        embedding_json = json.dumps(embedding)
        self._conn.execute(
            "UPDATE file_records SET embedding = ? WHERE id = ?",
            (embedding_json, record_id),
        )
        self._conn.commit()

    def query_records_without_embeddings(self, session_id: int) -> Iterator[FileRecord]:
        """Yield all records for a session that don't have embeddings yet.

        Args:
            session_id: The session to query.
        """
        cur = self._conn.execute(
            "SELECT * FROM file_records WHERE session_id = ? AND embedding IS NULL",
            (session_id,),
        )
        for row in cur:
            yield self._row_to_record(row)

    def log_action(
        self,
        session_id: int,
        record_id: int,
        action_type: str,
        source_path: Path,
        destination_path: Path | None = None,
        archive_path: Path | None = None,
        dry_run: bool = False,
        status: str = "pending",
        error_message: str | None = None,
    ) -> int:
        """Log a file action.

        Args:
            session_id: Session this action belongs to.
            record_id: Record being acted upon.
            action_type: Type of action ("move", "archive", "delete").
            source_path: Source file path.
            destination_path: Destination (for move/archive).
            archive_path: Archive path (for archive action).
            dry_run: Whether this was a dry-run preview.
            status: Action status ("pending", "completed", "failed", "undone").
            error_message: Error message if status is "failed".

        Returns:
            The new action log's ID.
        """
        cur = self._conn.execute(
            """INSERT INTO action_logs
               (session_id, record_id, action_type, source_path, destination_path,
                archive_path, timestamp, dry_run, status, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                record_id,
                action_type,
                str(source_path),
                str(destination_path) if destination_path else None,
                str(archive_path) if archive_path else None,
                datetime.now(UTC).isoformat(),
                1 if dry_run else 0,
                status,
                error_message,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def add_to_trash(
        self,
        original_path: Path,
        trash_path: Path,
        size_bytes: int,
        sha256: str | None = None,
    ) -> int:
        """Add file to trash.

        Args:
            original_path: Original file location.
            trash_path: Where file was moved in trash.
            size_bytes: File size.
            sha256: SHA-256 hash for recovery verification.

        Returns:
            The new trash entry's ID.
        """
        cur = self._conn.execute(
            """INSERT INTO trash (original_path, trash_path, trash_at, size_bytes, sha256)
               VALUES (?, ?, ?, ?, ?)""",
            (
                str(original_path),
                str(trash_path),
                datetime.now(UTC).isoformat(),
                size_bytes,
                sha256,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
