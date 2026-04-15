"""Tests for the scanner module."""

from __future__ import annotations

from pathlib import Path

from fileforge.scanner import Scanner


def test_scan_finds_files(tmp_dir: Path) -> None:
    """Scanner discovers all files in a directory tree."""
    (tmp_dir / "HARNESS_a.txt").write_text("hello")
    sub = tmp_dir / "subdir"
    sub.mkdir()
    (sub / "HARNESS_b.md").write_text("world")

    scanner = Scanner(ignore_patterns=[])
    records = list(scanner.scan([tmp_dir]))
    paths = {r.path for r in records}
    assert tmp_dir / "HARNESS_a.txt" in paths
    assert sub / "HARNESS_b.md" in paths


def test_scan_ignores_patterns(tmp_dir: Path) -> None:
    """Scanner skips paths matching ignore patterns."""
    (tmp_dir / "HARNESS_keep.txt").write_text("keep")
    (tmp_dir / "HARNESS_skip.tmp").write_text("skip")

    scanner = Scanner(ignore_patterns=["*.tmp"])
    records = list(scanner.scan([tmp_dir]))
    names = {r.name for r in records}
    assert "HARNESS_keep.txt" in names
    assert "HARNESS_skip.tmp" not in names


def test_scan_respects_depth_limit(tmp_dir: Path) -> None:
    """Scanner stops at max_depth levels deep."""
    deep = tmp_dir / "level1" / "level2"
    deep.mkdir(parents=True)
    (tmp_dir / "HARNESS_root.txt").write_text("root")
    (tmp_dir / "level1" / "HARNESS_l1.txt").write_text("l1")
    (deep / "HARNESS_l2.txt").write_text("l2")

    scanner = Scanner(ignore_patterns=[], max_depth=1)
    records = list(scanner.scan([tmp_dir]))
    names = {r.name for r in records}
    assert "HARNESS_root.txt" in names
    assert "HARNESS_l1.txt" in names
    assert "HARNESS_l2.txt" not in names


def test_scan_collects_metadata(tmp_dir: Path) -> None:
    """FileRecord metadata (size, extension) is populated correctly."""
    content = "consulting proposal content here"
    f = tmp_dir / "HARNESS_proposal.txt"
    f.write_text(content)

    scanner = Scanner(ignore_patterns=[])
    records = list(scanner.scan([tmp_dir]))
    record = next(r for r in records if r.name == "HARNESS_proposal.txt")
    assert record.extension == ".txt"
    assert record.size_bytes == len(content.encode())


def test_forgeignore_respected(tmp_dir: Path) -> None:
    """Files matching .forgeignore patterns are excluded."""
    (tmp_dir / ".forgeignore").write_text("Videos/\n*.iso\n")
    vids = tmp_dir / "Videos"
    vids.mkdir()
    (vids / "HARNESS_movie.mp4").write_text("video data")
    (tmp_dir / "HARNESS_disk.iso").write_text("iso data")
    (tmp_dir / "HARNESS_doc.txt").write_text("real doc")

    scanner = Scanner.from_directory(tmp_dir, ignore_patterns=[])
    records = list(scanner.scan([tmp_dir]))
    names = {r.name for r in records}
    assert "HARNESS_doc.txt" in names
    assert "HARNESS_movie.mp4" not in names
    assert "HARNESS_disk.iso" not in names
