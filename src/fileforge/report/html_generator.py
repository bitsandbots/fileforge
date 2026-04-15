"""Generate interactive HTML reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from fileforge.models import FileRecord


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable size.

    Args:
        bytes_val: Number of bytes.

    Returns:
        Formatted string (e.g., "1.5 MB").
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


def datetime_format(dt: datetime) -> str:
    """Format datetime for display.

    Args:
        dt: Datetime to format.

    Returns:
        Formatted string (YYYY-MM-DD HH:MM).
    """
    return dt.strftime("%Y-%m-%d %H:%M")


def total_size(records: list[FileRecord]) -> int:
    """Calculate total size of records.

    Args:
        records: List of FileRecords.

    Returns:
        Total bytes.
    """
    return sum(r.size_bytes for r in records)


def generate_html_report(
    records: list[FileRecord],
    output_path: Path,
    template_dir: Path | None = None,
) -> Path:
    """Generate interactive HTML report from scan results.

    Args:
        records: FileRecords to report.
        output_path: Where to save HTML file.
        template_dir: Template directory (defaults to package templates/).

    Returns:
        Path to generated HTML file.
    """
    if template_dir is None:
        # Get package templates directory
        template_dir = Path(__file__).parent.parent.parent.parent / "templates"

    env = Environment(loader=FileSystemLoader(template_dir))
    env.filters["datetimeformat"] = datetime_format
    env.filters["total_size"] = total_size

    template = env.get_template("report.html")

    # Group by category
    by_category: dict[str, list[FileRecord]] = {}
    for record in records:
        category = record.category or "Uncategorized"
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(record)

    # Count duplicates and stale
    duplicates_count = sum(1 for r in records if r.is_duplicate)
    stale_count = sum(1 for r in records if r.is_stale)

    # Render
    html = template.render(
        records=records,
        by_category=by_category,
        duplicates_count=duplicates_count,
        stale_count=stale_count,
        report_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        format_bytes=format_bytes,
    )

    output_path.write_text(html)
    return output_path
