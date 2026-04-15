"""Phase 1 plain-text report. Full HTML report added in Phase 3."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from fileforge.models import FileRecord


def print_scan_summary(
    console: Console,
    records: list[FileRecord],
    duplicate_groups: list[list[FileRecord]],
    stale_records: list[FileRecord] | None = None,
    near_dup_groups: list[list[FileRecord]] | None = None,
) -> None:
    """Print a plain-text summary of scan results to the console.

    Args:
        console: Rich console for output.
        records: All scanned file records.
        duplicate_groups: Groups of duplicate files.
        stale_records: Optional list of stale records (Phase 2).
        near_dup_groups: Optional near-duplicate groups (Phase 2).
    """
    total_size = sum(r.size_bytes for r in records)

    console.print(f"\n[bold green]Scan complete.[/] {len(records)} files scanned.")
    console.print(f"Total size: {_fmt_bytes(total_size)}")

    if duplicate_groups:
        dup_count = sum(len(g) - 1 for g in duplicate_groups)
        dup_size = sum(r.size_bytes for g in duplicate_groups for r in g[1:])
        console.print(
            f"\n[bold yellow]{len(duplicate_groups)} duplicate group(s)[/] found — "
            f"{dup_count} redundant files ({_fmt_bytes(dup_size)} reclaimable)"
        )
        table = Table("Group", "File", "Size", "Path")
        for i, group in enumerate(duplicate_groups, 1):
            for j, r in enumerate(group):
                label = "keep" if j == 0 else "dup"
                table.add_row(
                    f"#{i} [{label}]",
                    r.name,
                    _fmt_bytes(r.size_bytes),
                    str(r.path),
                )
        console.print(table)
    else:
        console.print("[green]No exact duplicates found.[/]")

    # Phase 2: Stale files section
    if stale_records:
        console.print("\n[bold]Stale Files[/bold]")
        for record in stale_records:
            console.print(f"  {record.name} — {record.stale_reason}")

    # Phase 2: Near-duplicates section
    if near_dup_groups:
        console.print("\n[bold]Near-Duplicates (High Similarity)[/bold]")
        for i, group in enumerate(near_dup_groups, 1):
            console.print(f"  Group {i}: {len(group)} similar files")
            for record in group:
                console.print(f"    - {record.path}")


def _fmt_bytes(n: int) -> str:
    """Human-readable byte size.

    Args:
        n: Size in bytes.

    Returns:
        String like '4.2 MB' or '512.0 B'.
    """
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
