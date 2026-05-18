"""FastAPI server for FileForge web UI."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
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


class ScanRequest(BaseModel):
    directories: list[str]
    config: str | None = None
    no_classify: bool = False
    phase_2: bool = False
    interactive: bool = True
    dry_run: bool = False


class ScanResponse(BaseModel):
    success: bool
    message: str
    files_scanned: int = 0
    duplicates_found: int = 0
    stale_found: int = 0


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    html_path = FRONTEND_DIR / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>FileForge UI</h1><p>Frontend not found</p>")


@app.get("/api/health")
async def health_check() -> dict[str, str | int]:
    return {"status": "ok", "version": __version__}


@app.post("/api/scan", response_model=ScanResponse)
async def scan_endpoint(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
) -> Any:
    try:
        invalid_dirs = [d for d in request.directories if not Path(d).is_dir()]
        if invalid_dirs:
            raise HTTPException(
                status_code=400, detail=f"Invalid directories: {invalid_dirs}"
            )

        cmd = ["fileforge", "scan"] + request.directories
        if request.config:
            cmd.extend(["--config", request.config])
        if request.no_classify:
            cmd.append("--no-classify")
        if request.phase_2:
            cmd.append("--phase-2")
        if not request.interactive:
            cmd.append("--interactive")
        if request.dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Scan failed: {result.stderr}")

        return ScanResponse(
            success=True,
            message="Scan completed successfully",
            files_scanned=0,
            duplicates_found=0,
            stale_found=0,
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Scan timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
