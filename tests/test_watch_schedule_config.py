"""Tests for watch and schedule configuration models."""

from fileforge.config import FileForgeConfig, ScheduleConfig, WatchConfig


def test_watch_config_defaults() -> None:
    """WatchConfig has sensible defaults."""
    cfg = WatchConfig()
    assert cfg.watch_dirs == ["~/Documents"]
    assert cfg.scan_delay_seconds == 60
    assert cfg.auto_act is False


def test_schedule_config_defaults() -> None:
    """ScheduleConfig has sensible defaults."""
    cfg = ScheduleConfig()
    assert cfg.enabled is False
    assert cfg.schedule_cron == "0 2 * * *"
    assert cfg.run_phase_2 is True


def test_fileforge_config_includes_watch_schedule() -> None:
    """FileForgeConfig includes watch and schedule sections."""
    cfg = FileForgeConfig()
    assert cfg.watch is not None
    assert cfg.schedule is not None
