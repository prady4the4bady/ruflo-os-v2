"""system_organizer_service.py — FastAPI service for automated system maintenance."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import tarfile
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

VERSION = "1.0.0"
SERVICE_NAME = "system-organizer"
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

SCAN_ROOT = Path(os.getenv("SCAN_ROOT", "/var/prady/projects"))
AUDIT_LOG_URL = os.getenv("AUDIT_LOG_URL", "http://audit-log:8112")
NOTIFICATION_BUS_URL = os.getenv("NOTIFICATION_BUS_URL", "http://notification-bus:8111")
DATA_DIR = Path(os.getenv("DATA_DIR", "/data/organizer"))

scans: dict[str, dict[str, Any]] = {}
suggestions: dict[str, list[dict[str, Any]]] = {}
NEVER_PATHS = ["/etc/", "/boot/", "/sys/", "/proc/", "/dev/", "/root/"]


def _is_safe_scan_path(path: Path) -> bool:
    resolved = str(path.resolve())
    for np in NEVER_PATHS:
        if resolved.startswith(np):
            return False
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Prady OS System Organizer", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/organizer/status")
async def organizer_status() -> dict[str, Any]:
    total_duplicates = sum(len(s.get("duplicates", [])) for s in scans.values())
    total_space = sum(s.get("space_wasted_mb", 0) for s in scans.values())
    return {
        "last_scan_ts": max((s.get("scan_ts", "") for s in scans.values()), default=""),
        "duplicates_found": total_duplicates,
        "space_wasted_mb": round(total_space, 2),
        "suggestions": sum(len(s.get("suggestions", [])) for s in scans.values()),
    }


@app.post("/organizer/scan")
async def organizer_scan() -> dict[str, str]:
    scan_id = f"scan-{int(time.time())}"
    scans[scan_id] = {"status": "running", "scan_ts": datetime.now(timezone.utc).isoformat(), "duplicates": [], "space_wasted_mb": 0, "suggestions": []}
    asyncio.create_task(_run_scan(scan_id))
    return {"scan_id": scan_id, "status": "started"}


@app.get("/organizer/scan/{scan_id}")
async def organizer_scan_result(scan_id: str) -> dict[str, Any]:
    scan = scans.get(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    return scan


@app.post("/organizer/apply/{suggestion_id}")
async def organizer_apply(suggestion_id: str) -> dict[str, Any]:
    for scan in scans.values():
        for s in scan.get("suggestions", []):
            if s.get("id") == suggestion_id:
                try:
                    path = Path(s["path"])
                    if path.exists():
                        size = path.stat().st_size
                        path.unlink()
                        scan["space_wasted_mb"] = max(0, scan.get("space_wasted_mb", 0) - size / (1024 * 1024))
                        return {"applied": True, "space_freed_mb": round(size / (1024 * 1024), 2)}
                except Exception as e:
                    raise HTTPException(500, f"Failed to apply: {e}")
    raise HTTPException(404, "Suggestion not found")


@app.post("/organizer/archive/{project_id}")
async def organizer_archive(project_id: str) -> dict[str, str]:
    project_dir = SCAN_ROOT / project_id
    if not project_dir.exists():
        raise HTTPException(404, "Project directory not found")
    archive_path = DATA_DIR / f"{project_id}.tar.gz"
    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(project_dir, arcname=project_id)
        return {"status": "archived", "path": str(archive_path), "note": "User approval required before deleting original"}
    except Exception as e:
        raise HTTPException(500, f"Archive failed: {e}")


async def _run_scan(scan_id: str) -> None:
    if not SCAN_ROOT.exists():
        scans[scan_id] = {"status": "complete", "scan_ts": datetime.now(timezone.utc).isoformat(), "duplicates": [], "space_wasted_mb": 0, "suggestions": [], "message": f"Scan root {SCAN_ROOT} does not exist"}
        return

    file_hashes: dict[str, list[Path]] = {}
    total_size = 0
    for f in SCAN_ROOT.rglob("*"):
        if f.is_file() and f.stat().st_size > 0:
            try:
                h = hashlib.sha256(f.read_bytes()).hexdigest()
                if h not in file_hashes:
                    file_hashes[h] = []
                file_hashes[h].append(f)
                total_size += f.stat().st_size
            except Exception:
                pass

    found_duplicates = []
    for h, files in file_hashes.items():
        if len(files) > 1:
            found_duplicates.append({"hash": h[:16], "files": [str(f) for f in files], "size_kb": round(files[0].stat().st_size / 1024, 2)})

    suggestion_list = []
    for d in found_duplicates[:20]:
        suggestion_id = f"sug-{d['hash']}"
        suggestion_list.append({"id": suggestion_id, "type": "duplicate", "path": d["files"][1], "size_kb": d["size_kb"], "description": f"Duplicate of {d['files'][0]}"})
        suggestions.setdefault(scan_id, []).append(suggestion_id)

    scans[scan_id] = {
        "status": "complete",
        "scan_ts": datetime.now(timezone.utc).isoformat(),
        "duplicates": found_duplicates,
        "space_wasted_mb": round(sum(d["size_kb"] for d in found_duplicates) / 1024, 2),
        "suggestions": suggestion_list,
        "total_files_scanned": len(file_hashes),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}
