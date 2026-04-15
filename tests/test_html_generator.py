from datetime import UTC, datetime
from pathlib import Path
import tempfile
from fileforge.report.html_generator import generate_html_report
from fileforge.models import FileRecord


def test_generate_html_report_creates_file() -> None:
    """HTML report is generated and contains expected content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test records
        records = [
            FileRecord(
                path=Path("doc1.txt"),
                name="doc1.txt",
                extension=".txt",
                size_bytes=1024,
                modified_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
                category="Work/Documents",
            ),
            FileRecord(
                path=Path("duplicate.txt"),
                name="duplicate.txt",
                extension=".txt",
                size_bytes=1024,
                modified_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
                is_duplicate=True,
            ),
        ]

        # Generate report
        output = tmpdir / "report.html"
        result = generate_html_report(records, output)

        # Verify file created
        assert result == output
        assert output.exists()

        # Verify content
        html = output.read_text()
        assert "FileForge Scan Report" in html
        assert "doc1.txt" in html
        assert "Duplicate" in html


def test_generate_html_report_handles_empty_records() -> None:
    """HTML report handles empty record list gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        output = tmpdir / "report.html"
        result = generate_html_report([], output)

        assert output.exists()
        html = output.read_text()
        assert "FileForge Scan Report" in html
