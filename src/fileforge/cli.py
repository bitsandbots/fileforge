"""Typer CLI definitions."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import typer
from rich.console import Console

from fileforge.ai.classifier import classify_file
from fileforge.analysis.dedup import find_exact_duplicates, hash_file
from fileforge.config import load_config
from fileforge.db import SessionDB
from fileforge.extractor import extract_snippet
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
    phase_2: bool = typer.Option(
        False, "--phase-2", help="Enable Phase 2 analyses (stale, versions, near-dupes)"
    ),
) -> None:
    """Scan directories, hash files, detect duplicates, and optionally classify."""
    # Console created inside function so CliRunner captures output in tests
    console = Console(force_terminal=False, highlight=False)

    cfg = load_config(config)
    scan_paths = [Path(d).expanduser() for d in dirs]

    # Validate all paths before touching the filesystem
    invalid = [p for p in scan_paths if not p.is_dir()]
    if invalid:
        for p in invalid:
            console.print(f"[red]Error:[/red] not a directory: {p}")
        raise typer.Exit(code=1)

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
    try:
        db = SessionDB(db_dir / "sessions.db")
        session_id = db.create_session(scan_paths)
    except sqlite3.OperationalError as exc:
        console.print(f"[red]Error:[/red] cannot open database: {exc}")
        raise typer.Exit(code=1)

    try:
        # Scan and collect records
        records = []
        for record in scanner.scan(scan_paths):
            inserted = db.insert_record(session_id, record)
            records.append(inserted)

        # Hash all records for dedup
        console.print(f"Hashing {len(records)} files...")
        hashed_records = []
        hash_skipped = 0
        for record in records:
            if record.id is not None:
                try:
                    digest = hash_file(record.path)
                    db.update_sha256(record.id, digest)
                    record = record.model_copy(update={"sha256": digest})
                except (PermissionError, OSError):
                    hash_skipped += 1
            hashed_records.append(record)
        if hash_skipped:
            console.print(
                f"[yellow]Warning:[/yellow] {hash_skipped} file(s) skipped (permission denied)"
            )

        # Detect exact duplicates
        dup_groups = find_exact_duplicates(hashed_records)

        # AI classification (unless --no-classify)
        if not no_classify:
            console.print(f"Classifying {len(hashed_records)} files...")
            classified_records = []
            for record in hashed_records:
                snippet = extract_snippet(record.path, max_chars=2000)
                category = classify_file(
                    path=record.path,
                    snippet=snippet,
                    model=cfg.ai.classification_model,
                    hints=cfg.ai.category_hints,
                )
                if record.id is not None:
                    db.update_category(record.id, category)
                record = record.model_copy(update={"category": category})
                classified_records.append(record)
            hashed_records = classified_records

        # Phase 2: Staleness detection
        stale_records = []
        if phase_2:
            from fileforge.analysis.staleness import is_stale, matches_junk_pattern

            console.print("Detecting stale files...")
            for i, record in enumerate(hashed_records):
                is_stale_age = is_stale(record, cfg.staleness.stale_days)
                is_junk = matches_junk_pattern(record.name, cfg.staleness.junk_patterns)

                if is_stale_age or is_junk:
                    reason = (
                        "older than threshold"
                        if is_stale_age
                        else "matches junk pattern"
                    )
                    if record.id is not None:
                        db.update_stale(record.id, reason)
                    hashed_records[i] = record.model_copy(
                        update={"is_stale": True, "stale_reason": reason}
                    )
                    stale_records.append(hashed_records[i])

        # Phase 2: Version supersession detection
        if phase_2:
            from fileforge.analysis.versions import find_superseded_versions

            console.print("Detecting version patterns...")
            superseded = find_superseded_versions(hashed_records)
            for record in superseded:
                if record.id is not None:
                    db.update_stale(record.id, "superseded by newer version")
                hashed_records = [
                    (
                        r.model_copy(
                            update={"is_stale": True, "stale_reason": "superseded"}
                        )
                        if r.id == record.id
                        else r
                    )
                    for r in hashed_records
                ]
                stale_records.append(
                    record.model_copy(
                        update={"is_stale": True, "stale_reason": "superseded"}
                    )
                )

        # Phase 2: Near-duplicate detection via embeddings
        near_dup_groups = []
        if phase_2:
            from fileforge.analysis.embeddings import (
                find_near_duplicates,
                generate_embedding,
            )

            console.print("Generating embeddings for near-duplicate detection...")
            embedding_count = 0
            for i, record in enumerate(hashed_records):
                if record.embedding is None:
                    snippet = extract_snippet(record.path, max_chars=500)
                    if snippet:
                        embedding = generate_embedding(snippet)
                        if embedding and record.id is not None:
                            db.update_embedding(record.id, embedding)
                            hashed_records[i] = record.model_copy(
                                update={"embedding": embedding}
                            )
                            embedding_count += 1

            console.print(f"Generated {embedding_count} embeddings")

            near_dup_groups = find_near_duplicates(
                hashed_records,
                threshold=cfg.duplicates.similarity_threshold,
            )

        # Print report
        print_scan_summary(
            console,
            hashed_records,
            dup_groups,
            stale_records=stale_records if phase_2 else None,
            near_dup_groups=near_dup_groups if phase_2 else None,
        )
    finally:
        db.close()


@app.command()
def status() -> None:
    """Show current session info and stats."""
    console = Console(force_terminal=False, highlight=False)
    console.print("No active session.")
