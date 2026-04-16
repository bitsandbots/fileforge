"""Typer CLI definitions."""

from __future__ import annotations

import sqlite3
import webbrowser
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
    interactive: bool = typer.Option(
        False, "--interactive", help="Launch interactive HTML report"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview actions without executing"
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

        # Dry-run preview: show what actions would be taken
        if dry_run:
            console.print(
                "\n[yellow][DRY RUN][/yellow] The following actions would be taken:"
            )
            console.print("[dim](No files will be modified)[/dim]\n")

            preview_count = 0
            for record in hashed_records:
                if record.is_duplicate or record.is_stale:
                    action = (
                        "SKIP (duplicate)"
                        if record.is_duplicate
                        else f"SKIP ({record.stale_reason})"
                    )
                    console.print(f"  {record.name:40s} → {action}")
                    preview_count += 1

            if preview_count == 0:
                console.print("  (No files marked for action)")

            console.print(
                f"\n[dim]Total files that would be affected: {preview_count}[/dim]"
            )

        # Interactive mode: generate and open HTML report
        if interactive:
            from fileforge.report.html_generator import generate_html_report

            report_path = Path(cfg.general.output_dir).expanduser() / "report.html"
            generate_html_report(hashed_records, report_path)

            console.print(f"[green]Report generated:[/green] {report_path}")
            console.print("[cyan]Opening in browser...[/cyan]")

            try:
                webbrowser.open(f"file://{report_path.absolute()}")
            except Exception as e:
                console.print(f"[yellow]Could not open browser:[/yellow] {e}")
                console.print(f"[cyan]Open manually:[/cyan] {report_path.absolute()}")

    finally:
        db.close()


@app.command()
def organize(
    dirs: list[str] = typer.Argument(help="Directories to organize"),
    config: Path = typer.Option(None, help="Config file path"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without executing"),
    trash_dir: Path = typer.Option(None, help="Trash directory for stale files"),
) -> None:
    """Organize files based on classification, duplicates, and staleness."""
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

    # Set up default trash directory
    if trash_dir is None:
        trash_dir = Path(cfg.general.output_dir).expanduser() / "trash"

    # Import actions inside function for lazy loading
    from fileforge.actions.mover import move_file
    from fileforge.actions.trash import move_to_trash

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
        # Scan and collect records (reuse scan logic)
        all_patterns = list(cfg.ignore.patterns)
        for root in scan_paths:
            forgeignore = root / ".forgeignore"
            if forgeignore.exists():
                for line in forgeignore.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        all_patterns.append(line)
        scanner = Scanner(ignore_patterns=all_patterns, max_depth=cfg.general.max_depth)

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

        # Mark duplicate records
        for group in dup_groups:
            for i, record in enumerate(group):
                if i > 0:  # First file is original, rest are duplicates
                    idx = hashed_records.index(record)
                    hashed_records[idx] = record.model_copy(
                        update={"is_duplicate": True, "duplicate_of": group[0].path}
                    )
                    if record.id is not None:
                        db.update_stale(record.id, "duplicate")

        # AI classification
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

        # Detect stale files (phase 2 analysis)
        from fileforge.analysis.staleness import is_stale, matches_junk_pattern

        console.print("Detecting stale files...")
        stale_records = []
        for i, record in enumerate(hashed_records):
            is_stale_age = is_stale(record, cfg.staleness.stale_days)
            is_junk = matches_junk_pattern(record.name, cfg.staleness.junk_patterns)

            if is_stale_age or is_junk:
                reason = (
                    "older than threshold" if is_stale_age else "matches junk pattern"
                )
                if record.id is not None:
                    db.update_stale(record.id, reason)
                hashed_records[i] = record.model_copy(
                    update={"is_stale": True, "stale_reason": reason}
                )
                stale_records.append(hashed_records[i])

        # Build action plan
        organized_base = Path.home() / "Organized"
        duplicates_base = organized_base / "Duplicates"
        action_plan: list[tuple[Path, Path, str]] = []  # (source, dest, action_type)

        for record in hashed_records:
            # Skip duplicates - they go to duplicates folder
            if record.is_duplicate:
                dest = duplicates_base / record.category / record.name
                action_plan.append((record.path, dest, "duplicate"))
            # Skip stale files - they go to trash
            elif record.is_stale:
                action_plan.append((record.path, trash_dir, "stale"))
            # Regular files - organize by category
            elif record.category:
                dest = organized_base / record.category / record.name
                action_plan.append((record.path, dest, "organize"))

        # Dry-run: just print the plan
        if dry_run:
            console.print(
                "\n[yellow][DRY RUN][/yellow] The following actions would be taken:"
            )
            console.print("[dim](No files will be modified)[/dim]\n")

            for source, dest, action_type in action_plan:
                if action_type == "stale":
                    console.print(f"  {source.name:40s} → [red]TRASH[/red] ({source})")
                elif action_type == "duplicate":
                    console.print(
                        f"  {source.name:40s} → [yellow]DUPLICATE[/yellow] {dest}"
                    )
                else:
                    console.print(f"  {source.name:40s} → [green]{dest}[/green]")

            console.print(f"\n[dim]Total files to process: {len(action_plan)}[/dim]")
            return

        # Execute actions
        console.print(f"\nOrganizing {len(action_plan)} files...")
        organized_count = 0
        duplicate_count = 0
        stale_count = 0
        error_count = 0

        for source, dest, action_type in action_plan:
            try:
                if action_type == "stale":
                    # Move to trash
                    trash_path = move_to_trash(source, trash_dir)
                    db.log_action(
                        session_id=session_id,
                        record_id=record.id or 0,
                        action_type="trash",
                        source_path=source,
                        destination_path=trash_path,
                        status="completed",
                    )
                    stale_count += 1
                elif action_type == "duplicate":
                    # Move to duplicates folder
                    final_dest = move_file(source, dest, create_dirs=True)
                    db.log_action(
                        session_id=session_id,
                        record_id=record.id or 0,
                        action_type="duplicate",
                        source_path=source,
                        destination_path=final_dest,
                        status="completed",
                    )
                    duplicate_count += 1
                else:
                    # Organize by category
                    final_dest = move_file(source, dest, create_dirs=True)
                    db.log_action(
                        session_id=session_id,
                        record_id=record.id or 0,
                        action_type="organize",
                        source_path=source,
                        destination_path=final_dest,
                        status="completed",
                    )
                    organized_count += 1

            except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
                console.print(f"[red]Error moving {source.name}:[/red] {e}")
                db.log_action(
                    session_id=session_id,
                    record_id=record.id or 0,
                    action_type=action_type,
                    source_path=source,
                    destination_path=dest,
                    status="failed",
                    error_message=str(e),
                )
                error_count += 1

        # Print summary
        console.print("\n[green]Organization complete![/green]")
        console.print(f"  Organized: {organized_count}")
        console.print(f"  Duplicates: {duplicate_count}")
        console.print(f"  Stale/Trashed: {stale_count}")
        if error_count:
            console.print(f"  [red]Errors: {error_count}[/red]")

    finally:
        db.close()


@app.command()
def watch(
    dirs: list[str] = typer.Argument(help="Directories to watch"),
    config: Path = typer.Option(None, help="Config file path"),
    phase_2: bool = typer.Option(True, "--phase-2", help="Enable Phase 2 analyses"),
) -> None:
    """Watch directories for changes and scan automatically."""
    console = Console(force_terminal=False, highlight=False)
    cfg = load_config(config)

    from fileforge.watch.watcher import FileWatcher

    watch_paths = [Path(d).expanduser() for d in dirs]

    # Validate paths
    invalid = [p for p in watch_paths if not p.is_dir()]
    if invalid:
        for p in invalid:
            console.print(f"[red]Error:[/red] not a directory: {p}")
        raise typer.Exit(code=1)

    def on_change(path: Path, event_type: str) -> None:
        console.print(f"[cyan]Detected {event_type}: {path.name}[/cyan]")
        console.print(f"[dim]Scanning in {cfg.watch.scan_delay_seconds}s...[/dim]")
        # In production, this would trigger scan_command
        # For now, just log the detection

    watcher = FileWatcher(
        watch_paths,
        on_change=on_change,
        debounce_delay=float(cfg.watch.scan_delay_seconds),
        ignore_patterns=cfg.watch.debounce_patterns,
    )

    console.print(f"[green]Watching {len(watch_paths)} director(ies)...[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    watcher.start()
    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping watcher...[/yellow]")
        watcher.stop()


@app.command()
def schedule(
    dirs: list[str] = typer.Argument(help="Directories to scan"),
    cron: str = typer.Option("0 2 * * *", "--cron", help="Cron expression"),
    config: Path = typer.Option(None, help="Config file path"),
) -> None:
    """Schedule periodic scans using cron or systemd timer."""
    console = Console(force_terminal=False, highlight=False)
    cfg = load_config(config)

    from fileforge.schedule.job_manager import JobManager
    from fileforge.db import SessionDB

    db = SessionDB(Path(cfg.general.output_dir).expanduser() / "sessions.db")
    job_mgr = JobManager(db, cfg.schedule)

    scan_paths = [Path(d).expanduser() for d in dirs]

    # Validate paths
    invalid = [p for p in scan_paths if not p.is_dir()]
    if invalid:
        for p in invalid:
            console.print(f"[red]Error:[/red] not a directory: {p}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]Scheduling scans for {len(scan_paths)} director(ies)[/green]"
    )
    console.print(f"[cyan]Cron: {cron}[/cyan]")

    job_id = job_mgr.schedule_scan(scan_paths)

    console.print(f"[green]✓ Scan scheduled (job ID: {job_id})[/green]")
    console.print("[dim]View logs: fileforge log[/dim]")

    db.close()


@app.command()
def dupes(
    dirs: list[str] = typer.Argument(help="Directories to scan for duplicates"),
    config: Path = typer.Option(None, help="Config file path"),
    delete: bool = typer.Option(
        False, "--delete", help="Permanently delete duplicates"
    ),
    move: bool = typer.Option(
        False, "--move", help="Move duplicates to duplicates folder"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without executing"),
    duplicates_dir: Path = typer.Option(None, help="Duplicates folder for --move"),
) -> None:
    """Find and handle duplicate files."""
    # Console created inside function so CliRunner captures output in tests
    console = Console(force_terminal=False, highlight=False)

    # Validate conflicting flags
    if delete and move:
        console.print("[red]Error:[/red] cannot use both --delete and --move")
        raise typer.Exit(code=1)

    cfg = load_config(config)
    scan_paths = [Path(d).expanduser() for d in dirs]

    # Validate all paths before touching the filesystem
    invalid = [p for p in scan_paths if not p.is_dir()]
    if invalid:
        for p in invalid:
            console.print(f"[red]Error:[/red] not a directory: {p}")
        raise typer.Exit(code=1)

    # Import inside function for lazy loading
    from fileforge.actions.mover import move_file

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
        all_patterns = list(cfg.ignore.patterns)
        for root in scan_paths:
            forgeignore = root / ".forgeignore"
            if forgeignore.exists():
                for line in forgeignore.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        all_patterns.append(line)
        scanner = Scanner(ignore_patterns=all_patterns, max_depth=cfg.general.max_depth)

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

        if not dup_groups:
            console.print("[green]No duplicates found.[/green]")
            return

        # Calculate stats
        total_dupes = sum(len(group) - 1 for group in dup_groups)  # -1 for original
        total_size = sum(
            group[0].size_bytes * (len(group) - 1)
            for group in dup_groups
            if group[0].size_bytes
        )

        console.print(f"\n[cyan]Found {len(dup_groups)} duplicate groups[/cyan]")
        console.print(f"[cyan]Total duplicate files: {total_dupes}[/cyan]")
        console.print(f"[cyan]Space recoverable: {total_size:,} bytes[/cyan]\n")

        # Print duplicate groups
        for i, group in enumerate(dup_groups, 1):
            console.print(f"[bold]Group {i}:[/bold] ({len(group)} files)")
            for j, record in enumerate(group):
                marker = (
                    "[green]ORIGINAL[/green]"
                    if j == 0
                    else "[yellow]DUPLICATE[/yellow]"
                )
                console.print(f"  {marker} {record.path}")
            console.print()

        # Default: just show report, no actions
        if not delete and not move:
            console.print("[dim]Run with --delete or --move to take action[/dim]")
            return

        # Build list of duplicates to process (all except first in each group)
        duplicates_to_process: list[tuple[FileRecord, str]] = []  # (record, action)
        for group in dup_groups:
            for i, record in enumerate(group):
                if i > 0:  # First file is original, rest are duplicates
                    action = "delete" if delete else "move"
                    duplicates_to_process.append((record, action))

        # Dry-run: just print what would happen
        if dry_run:
            console.print(
                "\n[yellow][DRY RUN][/yellow] The following actions would be taken:"
            )
            console.print("[dim](No files will be modified)[/dim]\n")

            for record, action in duplicates_to_process:
                if action == "delete":
                    console.print(f"  [red]DELETE[/red] {record.path}")
                else:
                    dest = (duplicates_dir or Path.home() / "Duplicates") / record.name
                    console.print(f"  [yellow]MOVE[/yellow] {record.path} -> {dest}")

            console.print(
                f"\n[dim]Total files affected: {len(duplicates_to_process)}[/dim]"
            )
            return

        # Execute actions
        console.print(f"\nProcessing {len(duplicates_to_process)} duplicate files...")

        # Set up default duplicates directory for --move
        if move and duplicates_dir is None:
            duplicates_dir = Path.home() / "Duplicates"

        deleted_count = 0
        moved_count = 0
        error_count = 0

        for record, action in duplicates_to_process:
            try:
                if action == "delete":
                    # Permanently delete
                    record.path.unlink()
                    db.log_action(
                        session_id=session_id,
                        record_id=record.id or 0,
                        action_type="delete_duplicate",
                        source_path=record.path,
                        destination_path=None,
                        status="completed",
                    )
                    deleted_count += 1
                else:
                    # Move to duplicates folder
                    dest = duplicates_dir / record.name
                    final_dest = move_file(record.path, dest, create_dirs=True)
                    db.log_action(
                        session_id=session_id,
                        record_id=record.id or 0,
                        action_type="move_duplicate",
                        source_path=record.path,
                        destination_path=final_dest,
                        status="completed",
                    )
                    moved_count += 1

            except (FileNotFoundError, PermissionError, OSError) as e:
                console.print(f"[red]Error processing {record.path.name}:[/red] {e}")
                db.log_action(
                    session_id=session_id,
                    record_id=record.id or 0,
                    action_type=action,
                    source_path=record.path,
                    destination_path=None,
                    status="failed",
                    error_message=str(e),
                )
                error_count += 1

        # Print summary
        console.print("\n[green]Duplicate handling complete![/green]")
        if delete:
            console.print(f"  Deleted: {deleted_count}")
        else:
            console.print(f"  Moved: {moved_count}")
        if error_count:
            console.print(f"  [red]Errors: {error_count}[/red]")

    finally:
        db.close()


@app.command()
def status() -> None:
    """Show current session info and stats."""
    console = Console(force_terminal=False, highlight=False)
    console.print("No active session.")
