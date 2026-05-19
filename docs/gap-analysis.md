# FileForge — Gap Analysis

**As of v0.1.7 (2026-05-19)**

This document records discrepancies between the documented design and the current codebase, and tracks features planned but not yet implemented.

---

## Code Gaps (Documented but Not Implemented)

### 1. `extractor/xlsx.py` — Missing

**Impact:** Medium  
**Dependency installed:** `openpyxl >= 3`  
**Current behavior:** `.xlsx` and `.xls` files are scanned and hashed but produce no text snippet. Classification falls back to filename-based inference.  
**Documented as:** Supported in `tech-stack.md` and old `architecture.md`.  
**Fix:** Implement `extractor/xlsx.py` using `openpyxl.load_workbook()` to extract cell text from the first N sheets.

---

### 2. `extractor/image.py` — Missing (OCR)

**Impact:** Medium  
**Dependency installed:** `pytesseract >= 0.3` (optional `[ocr]` extra), `Pillow >= 10`  
**Current behavior:** Image files (`.png`, `.jpg`, `.jpeg`, etc.) produce no text snippet. They are scanned and hashed only.  
**Documented as:** Optional OCR capability in `tech-stack.md`.  
**Fix:** Implement `extractor/image.py` using `pytesseract.image_to_string()`, guarded by a try-import so non-OCR installs degrade gracefully.

---

### 3. `actions/logger.py` — Does Not Exist

**Impact:** Low (functional workaround in place)  
**Current behavior:** Action logging is implemented through `SessionDB.log_action()` in `db.py`. The `action_logs` table exists and is written to by actions.  
**Previously documented as:** A standalone `fileforge.actions.logger` module with `ActionLog`, `log_action()`, and `undo_action()` in the old `api.md`.  
**Status:** Removed from `api.md`. The `db.py` API docs should be updated to document `log_action()` and `list_action_logs()` when those methods are public.

---

### 4. Web API Not Documented (Now Fixed)

**Impact:** Medium  
**Previous state:** `api.md` documented only the Python library API. The REST API served by `api/server.py` had no documentation.  
**Status:** REST API section added to `api.md` in this release.

---

## Feature Gaps (Planned, Not Started)

### 5. Phase 5 — React PWA

**Priority:** Roadmap  
**Description:** Replace the vanilla JS `frontend/index.html` SPA with a React-based PWA with offline capability and a service worker.  
**Blocked by:** None — independent of Phase 1–4 features.

---

### 6. Phase 6 — Cross-Device Sync

**Priority:** Roadmap  
**Description:** Sync scan results and file actions across multiple machines (e.g., Raspberry Pi nodes in NEXUS).  
**Blocked by:** Phase 5 (stable PWA layer needed for sync UI).

---

### 7. RTF Extractor

**Priority:** Low  
**Description:** Extract text from `.rtf` files. Can use `striprtf` or `pyrtf-ng`.  
**Mentioned in:** CHANGELOG.md Unreleased section.

---

### 8. EPUB Extractor

**Priority:** Low  
**Description:** Extract text from `.epub` files. Can use `ebooklib`.  
**Mentioned in:** CHANGELOG.md Unreleased section.

---

### 9. `actions/prune.py` Not Exposed in CLI

**Impact:** Low  
**Description:** `prune.py` implements empty-directory removal but there is no CLI command for it. It is called indirectly from `organize`.  
**Fix (optional):** Add `fileforge prune <dirs>` command or document that it runs automatically after `organize`.

---

## Documentation Gaps (Fixed in This Release)

| Issue | Status |
|-------|--------|
| `overview.md` version said 0.1.0 | Fixed → 0.1.7 |
| `overview.md` missing `fileforge server` command | Fixed |
| `architecture.md` listed `extractor/xlsx.py`, `extractor/html.py`, `extractor/image.py` (don't exist) | Fixed |
| `architecture.md` missing web server in architecture diagram | Fixed |
| `api.md` referenced `actions/logger.py` (doesn't exist) | Fixed — section removed |
| `api.md` had no REST API documentation | Fixed — REST API section added |
| `setup.md` referenced `fileforge[ui]` extra (correct: `fileforge[web]`) | Fixed |
| `setup.md` missing `fileforge server` command | Fixed |
| `tech-stack.md` fastapi/uvicorn/Jinja2 listed as optional; they are core deps | Fixed |
| `docs/superpowers/plans/` — stale planning docs for phases now complete | Removed |

---

## Notes

- The `extractor/html.py` gap from architecture.md is not actually a gap: HTML files are handled by `extractor/text.py` via BeautifulSoup tag-stripping. The architecture doc incorrectly implied a separate module.
- The `api/__init__.py` is absent from the `api/` package but the FastAPI app imports correctly without it. Not a functional gap.
