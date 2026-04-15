"""Typer CLI definitions."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from fileforge.analysis.dedup import find_exact_duplicates, hash_file
from fileforge.config import load_config
from fileforge.db import SessionDB
from fileforge.report.generator import print_scan_summary
from fileforge.scanner import Scanner

app = typer.Typer(
    name="fileforge",
    help="AI-powered file organizer using local Ollama inference.",
    no_args_is_help=True,
)


@app.command()
def scan(
    dirs: list[str] = typer.Argument(help="Directories to scan"),
    config: Path = typer.Option(None, help="Config file path"),
    no_classify: bool = typer.Option(
        False, "--no-classify", help="Skip AI classification (hash + dedup only)"
    ),
) -> None:
    """Scan directories, hash files, detect duplicates, and optionally classify."""
    # Console created inside function so CliRunner captures output in tests
    console = Console(force_terminal=False, highlight=False)

    cfg = load_config(config)
    scan_paths = [Path(d).expanduser() for d in dirs]

    # Accumulate ignore patterns from config + .forgeignore in each root
    all_patterns = list(cfg.ignore.patterns)
    for root in scan_paths:
        forgeignore = root / ".forgeignore"
        if forgeignore.exists():
            for line in forgeignore.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    all_patterns.append(line)
    scanner = Scanner(ignore_patterns=all_patterns, max_depth=cfg.general.max_depth)

    # Set up session DB
    db_dir = Path(cfg.general.output_dir).expanduser()
    db_dir.mkdir(parents=True, exist_ok=True)
    db = SessionDB(db_dir / "sessions.db")
    session_id = db.create_session(scan_paths)

    try:
        # Scan and collect records
        records = []
        for record in scanner.scan(scan_paths):
            inserted = db.insert_record(session_id, record)
            records.append(inserted)

        # Hash all records for dedup
        console.print(f"Hashing {len(records)} files...")
        hashed_records = []
        for record in records:
            if record.id is not None:
                try:
                    digest = hash_file(record.path)
                    db.update_sha256(record.id, digest)
                    record = record.model_copy(update={"sha256": digest})
                except (PermissionError, OSError):
                    pass
            hashed_records.append(record)

        # Detect exact duplicates
        dup_groups = find_exact_duplicates(hashed_records)

        # Print report
        print_scan_summary(console, hashed_records, dup_groups)
    finally:
        db.close()


@app.command()
def status() -> None:
    """Show current session info and stats."""
    console = Console(force_terminal=False, highlight=False)
    console.print("No active session.")
