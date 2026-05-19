"""Excel spreadsheet extraction using openpyxl."""

from __future__ import annotations

from pathlib import Path

import openpyxl


def extract(path: Path, max_chars: int = 2000) -> str | None:
    """Extract text from an Excel workbook (.xlsx, .xlsm).

    Reads sheets in order, emitting a header for each sheet followed by
    row values joined with ' | '. Stops once max_chars is reached.
    Empty cells are skipped; empty sheets are skipped entirely.

    Args:
        path: Path to the .xlsx or .xlsm file.
        max_chars: Maximum characters to return.

    Returns:
        Extracted text snippet, or None if the workbook has no readable text.
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    parts: list[str] = []
    total = 0

    try:
        for sheet in wb.worksheets:
            if total >= max_chars:
                break

            sheet_lines: list[str] = []
            for row in sheet.iter_rows(values_only=True):
                if total >= max_chars:
                    break
                cells = [
                    str(v).strip() for v in row if v is not None and str(v).strip()
                ]
                if not cells:
                    continue
                line = " | ".join(cells)
                remaining = max_chars - total
                sheet_lines.append(line[:remaining])
                total += len(line)

            if sheet_lines:
                parts.append(f"[{sheet.title}]\n" + "\n".join(sheet_lines))
    finally:
        wb.close()

    combined = "\n\n".join(parts).strip()
    return combined if combined else None
