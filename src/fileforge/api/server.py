"""FastAPI server for FileForge web UI."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fileforge import __version__
from fileforge.config import FileForgeConfig, load_config

app = FastAPI(title="FileForge API", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend")


def _config_path() -> Path:
    """User config path — prefer XDG, fall back to legacy ~/.fileforge location."""
    xdg = Path.home() / ".config" / "fileforge" / "fileforge.toml"
    legacy = Path.home() / ".fileforge" / "fileforge.toml"
    if legacy.exists() and not xdg.exists():
        return legacy
    return xdg


def _esc_toml(s: str) -> str:
    """Escape a string for use inside TOML basic quotes (no newlines)."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _to_toml(data: dict) -> str:
    """Serialize a 2-level dict to TOML (covers all FileForgeConfig field types)."""
    lines: list[str] = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        for key, val in values.items():
            if isinstance(val, bool):
                lines.append(f"{key} = {'true' if val else 'false'}")
            elif isinstance(val, str):
                if "\n" in val:
                    # Multiline basic string; leading newline is trimmed by TOML spec
                    body = val.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
                    lines.append(f'{key} = """\n{body}"""')
                else:
                    lines.append(f'{key} = "{_esc_toml(val)}"')
            elif isinstance(val, list):
                items = ", ".join(
                    f'"{_esc_toml(x)}"' if isinstance(x, str) else str(x) for x in val
                )
                lines.append(f"{key} = [{items}]")
            else:
                lines.append(f"{key} = {val}")
        lines.append("")
    return "\n".join(lines)


_scan_jobs: dict[str, dict] = {}

# sys.argv[0] is the fileforge entry-point that launched this server process
_FILEFORGE_BIN = str(Path(sys.argv[0]).resolve())


class ScanRequest(BaseModel):
    directories: list[str]
    config: str | None = None
    no_classify: bool = False
    phase_2: bool = False
    dry_run: bool = False


class ScanResponse(BaseModel):
    success: bool
    message: str
    job_id: str | None = None
    session_id: int | None = None


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    html_path = FRONTEND_DIR / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>FileForge UI</h1><p>Frontend not found</p>")


@app.get("/api/health")
async def health_check() -> dict[str, str | int]:
    return {"status": "ok", "version": __version__}


def _latest_session_id() -> int | None:
    """Return the highest session ID from the DB, or None."""
    try:
        from fileforge.db import SessionDB

        db_path = Path.home() / ".fileforge" / "sessions.db"
        if not db_path.exists():
            return None
        db = SessionDB(db_path)
        try:
            sessions = db.list_sessions()
            return sessions[0]["id"] if sessions else None
        finally:
            db.close()
    except Exception:
        return None


def _run_scan(job_id: str, cmd: list[str]) -> None:
    """Blocking scan worker — runs in a thread pool executor."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            _scan_jobs[job_id] = {
                "status": "error",
                "error": result.stderr[-1000:] or "Scan exited with non-zero status",
            }
            return
        _scan_jobs[job_id] = {"status": "complete", "session_id": _latest_session_id()}
    except subprocess.TimeoutExpired:
        _scan_jobs[job_id] = {"status": "error", "error": "Scan timed out after 1 hour"}
    except Exception as e:
        _scan_jobs[job_id] = {"status": "error", "error": str(e)}


@app.post("/api/scan", response_model=ScanResponse)
async def scan_endpoint(request: ScanRequest) -> Any:
    if any(j["status"] == "running" for j in _scan_jobs.values()):
        raise HTTPException(status_code=409, detail="A scan is already running")

    expanded_dirs = [str(Path(d).expanduser()) for d in request.directories]
    invalid_dirs = [d for d in expanded_dirs if not Path(d).is_dir()]
    if invalid_dirs:
        raise HTTPException(
            status_code=400, detail=f"Invalid directories: {invalid_dirs}"
        )

    cmd = [_FILEFORGE_BIN, "scan"] + expanded_dirs
    if request.config:
        cmd.extend(["--config", request.config])
    if request.no_classify:
        cmd.append("--no-classify")
    if request.phase_2:
        cmd.append("--phase-2")
    if request.dry_run:
        cmd.append("--dry-run")

    job_id = uuid.uuid4().hex[:10]
    _scan_jobs[job_id] = {"status": "running", "session_id": None, "error": None}

    asyncio.get_running_loop().run_in_executor(None, _run_scan, job_id, cmd)

    return ScanResponse(success=True, message="Scan started", job_id=job_id)


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """Poll for async scan job status."""
    if job_id not in _scan_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _scan_jobs[job_id]


@app.get("/api/stats")
async def get_stats() -> dict:
    try:
        from fileforge.db import SessionDB

        output_dir = Path.home() / ".fileforge"
        config_path = Path.home() / ".fileforge" / "fileforge.toml"
        if config_path.exists():
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    tomllib = None

            if tomllib:
                try:
                    with open(config_path, "rb") as f:
                        config = tomllib.load(f)
                    if "general" in config and "output_dir" in config["general"]:
                        output_dir = Path(config["general"]["output_dir"]).expanduser()
                except Exception:
                    pass

        db_path = output_dir / "sessions.db"
        if not db_path.exists():
            return {
                "total_files": 0,
                "total_size": 0,
                "duplicates": 0,
                "duplicates_size": 0,
                "stale": 0,
                "categories": 0,
            }

        db = SessionDB(db_path)
        try:
            records = db.get_all_records()
        finally:
            db.close()

        total_files = len(records)
        total_size = sum(r.size_bytes for r in records)
        duplicates = [r for r in records if r.is_duplicate]
        stale = [r for r in records if r.is_stale]
        categories = set(r.category or "Other" for r in records)

        return {
            "total_files": total_files,
            "total_size": total_size,
            "duplicates": len(duplicates),
            "duplicates_size": sum(r.size_bytes for r in duplicates),
            "stale": len(stale),
            "categories": len(categories),
            "records": [r.model_dump() for r in records[:100]],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_sessions() -> dict[str, list]:
    try:
        from fileforge.db import SessionDB

        output_dir = Path.home() / ".fileforge"
        db_path = output_dir / "sessions.db"

        if not db_path.exists():
            return {"sessions": []}

        db = SessionDB(db_path)
        try:
            sessions = db.list_sessions()
        finally:
            db.close()

        return {"sessions": sessions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}")
async def get_session(session_id: int) -> dict:
    try:
        from fileforge.db import SessionDB

        output_dir = Path.home() / ".fileforge"
        db_path = output_dir / "sessions.db"

        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        db = SessionDB(db_path)
        try:
            records = db.get_session_records(session_id)
        finally:
            db.close()

        return {"session_id": session_id, "records": [r.model_dump() for r in records]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config() -> dict:
    """Return the current FileForge configuration as JSON."""
    path = _config_path()
    try:
        cfg = load_config(path) if path.exists() else FileForgeConfig()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {e}")
    return cfg.model_dump()


@app.post("/api/config")
async def update_config(cfg: FileForgeConfig) -> dict[str, str]:
    """Validate and persist configuration to fileforge.toml."""
    path = _config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_to_toml(cfg.model_dump()))
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to write config: {e}")
    return {"status": "saved", "path": str(path)}


@app.get("/api/browse")
async def browse_directory(path: str = "") -> dict:
    """List subdirectories at *path* for the filesystem browser widget."""
    target = Path(path).expanduser() if path else Path.home()
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {target}")
    try:
        entries = sorted(
            [
                {"name": e.name, "path": str(e)}
                for e in target.iterdir()
                if e.is_dir() and not e.name.startswith(".")
            ],
            key=lambda x: x["name"].lower(),
        )
        return {
            "path": str(target),
            "parent": str(target.parent) if target != target.parent else None,
            "entries": entries,
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {target}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
