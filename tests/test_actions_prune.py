"""Tests for prune action module."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fileforge.actions.prune import prune_empty_dirs


def test_removes_single_empty_dir() -> None:
    """A single empty subdirectory is removed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        empty = root / "HARNESS_empty"
        empty.mkdir()

        removed = prune_empty_dirs([root])

        assert empty not in removed or not empty.exists()
        assert not empty.exists()
        assert len(removed) == 1


def test_keeps_non_empty_dir() -> None:
    """A directory containing a file is not removed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        occupied = root / "HARNESS_occupied"
        occupied.mkdir()
        (occupied / "file.txt").write_text("data")

        removed = prune_empty_dirs([root])

        assert occupied.exists()
        assert len(removed) == 0


def test_cascades_nested_empty_dirs() -> None:
    """Deeply nested empty directories are all removed in one pass."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        deep = root / "HARNESS_a" / "HARNESS_b" / "HARNESS_c"
        deep.mkdir(parents=True)

        removed = prune_empty_dirs([root])

        assert not deep.exists()
        assert not deep.parent.exists()
        assert not deep.parent.parent.exists()
        assert len(removed) == 3


def test_root_is_never_removed() -> None:
    """The root directory itself is never removed even if empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        removed = prune_empty_dirs([root])

        assert root.exists()
        assert len(removed) == 0


def test_partial_cleanup_mixed_tree() -> None:
    """Empty siblings removed; dirs containing files are kept."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        empty = root / "HARNESS_empty"
        empty.mkdir()
        occupied = root / "HARNESS_occupied"
        occupied.mkdir()
        (occupied / "keep.txt").write_text("keep")

        removed = prune_empty_dirs([root])

        assert not empty.exists()
        assert occupied.exists()
        assert len(removed) == 1


def test_dry_run_does_not_delete() -> None:
    """dry_run=True returns would-be removals without touching the filesystem."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        empty = root / "HARNESS_dry"
        empty.mkdir()

        removed = prune_empty_dirs([root], dry_run=True)

        assert empty.exists()
        assert len(removed) == 1
        assert removed[0] == empty


def test_nonexistent_root_is_skipped() -> None:
    """A root that does not exist is silently ignored."""
    removed = prune_empty_dirs([Path("/nonexistent/HARNESS_path")])
    assert removed == []


def test_multiple_roots() -> None:
    """Empty dirs under multiple roots are all cleaned."""
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        root1 = Path(tmp1)
        root2 = Path(tmp2)
        (root1 / "HARNESS_e1").mkdir()
        (root2 / "HARNESS_e2").mkdir()

        removed = prune_empty_dirs([root1, root2])

        assert len(removed) == 2
        assert not (root1 / "HARNESS_e1").exists()
        assert not (root2 / "HARNESS_e2").exists()
