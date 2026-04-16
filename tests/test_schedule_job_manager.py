"""Tests for job scheduler using APScheduler."""

from datetime import datetime, UTC
from pathlib import Path
import tempfile
from fileforge.db import SessionDB
from fileforge.config import ScheduleConfig
from fileforge.schedule.job_manager import JobManager


def test_job_manager_schedules_scan() -> None:
    """JobManager schedules a periodic scan job."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create database
        db = SessionDB(tmpdir_path / "sessions.db")

        # Create config
        cfg = ScheduleConfig(
            enabled=True, schedule_cron="0 2 * * *", run_phase_2=True, auto_act=False
        )

        # Create job manager
        mgr = JobManager(db, cfg)

        # Schedule a scan
        scan_paths = [tmpdir_path]
        mgr.schedule_scan(scan_paths)

        # Verify job was added (check job_history table)
        cursor = db._conn.execute(
            "SELECT COUNT(*) FROM job_history WHERE job_type = 'scheduled'"
        )
        count = cursor.fetchone()[0]
        assert count >= 1

        db.close()


def test_job_manager_logs_execution() -> None:
    """JobManager logs execution to job_history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        db = SessionDB(tmpdir_path / "sessions.db")
        cfg = ScheduleConfig(enabled=True)
        mgr = JobManager(db, cfg)

        # Run a scan immediately
        mgr.run_now([tmpdir_path], phase_2=False)

        # Check that it was logged
        cursor = db._conn.execute(
            "SELECT status FROM job_history WHERE job_type = 'manual' ORDER BY triggered_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "completed"

        db.close()


def test_job_manager_tracks_stats() -> None:
    """JobManager logs file counts and actions in job_history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create some test files
        (tmpdir_path / "HARNESS_1.txt").write_text("content")
        (tmpdir_path / "HARNESS_2.txt").write_text("content")

        db = SessionDB(tmpdir_path / "sessions.db")
        cfg = ScheduleConfig(enabled=True, run_phase_2=False)
        mgr = JobManager(db, cfg)

        # Run scan
        mgr.run_now([tmpdir_path], phase_2=False)

        # Check that file count was logged
        cursor = db._conn.execute(
            "SELECT files_scanned FROM job_history ORDER BY triggered_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] >= 2

        db.close()
