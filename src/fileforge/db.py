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

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
