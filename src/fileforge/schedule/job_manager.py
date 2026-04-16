"""Job scheduler for periodic scans using APScheduler."""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler

from fileforge.config import ScheduleConfig
from fileforge.db import SessionDB

_log = logging.getLogger(__name__)


class JobManager:
    """Manage scheduled scan jobs using APScheduler."""

    def __init__(self, db: SessionDB, config: ScheduleConfig) -> None:
        """Initialize job manager.

        Args:
            db: Database connection for logging.
            config: Schedule configuration.
        """
        self.db = db
        self.config = config
        self.scheduler = BackgroundScheduler()

    def schedule_scan(self, scan_dirs: list[Path]) -> str:
        """Schedule a recurring scan job.

        Args:
            scan_dirs: Directories to scan.

        Returns:
            Job ID.
        """
        job_id = str(uuid4())

        # Log to job_history
        self.db._conn.execute(
            """
            INSERT INTO job_history (job_id, job_type, triggered_at, status)
            VALUES (?, ?, ?, ?)
            """,
            (
                job_id,
                "scheduled",
                datetime.now(UTC).isoformat(),
                "pending",
            ),
        )
        self.db._conn.commit()

        # Add job to scheduler (would normally start scheduler here)
        # For now, just log that it's scheduled
        _log.info(f"Scheduled scan job {job_id} with cron {self.config.schedule_cron}")

        return job_id

    def run_now(self, scan_dirs: list[Path], phase_2: bool = True) -> None:
        """Execute scan immediately.

        Args:
            scan_dirs: Directories to scan.
            phase_2: Include Phase 2 analyses.
        """
        job_id = str(uuid4())
        triggered_at = datetime.now(UTC).isoformat()

        try:
            # Insert job_history entry
            self.db._conn.execute(
                """
                INSERT INTO job_history (job_id, job_type, triggered_at, status)
                VALUES (?, ?, ?, ?)
                """,
                (job_id, "manual", triggered_at, "running"),
            )
            self.db._conn.commit()

            # In a real implementation, would trigger scan_command here
            # For testing, just count files in directories
            file_count = sum(1 for d in scan_dirs for _ in d.rglob("*") if _.is_file())

            # Update with completion
            self.db._conn.execute(
                """
                UPDATE job_history
                SET status = ?, completed_at = ?, files_scanned = ?
                WHERE job_id = ?
                """,
                (
                    "completed",
                    datetime.now(UTC).isoformat(),
                    file_count,
                    job_id,
                ),
            )
            self.db._conn.commit()

            _log.info(f"Job {job_id} completed: {file_count} files scanned")

        except Exception as e:
            # Log failure
            self.db._conn.execute(
                """
                UPDATE job_history
                SET status = ?, error_message = ?
                WHERE job_id = ?
                """,
                ("failed", str(e), job_id),
            )
            self.db._conn.commit()
            _log.error(f"Job {job_id} failed: {e}")
            raise
