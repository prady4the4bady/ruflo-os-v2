from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel


class SystemAbout(BaseModel):
    name: str
    version: str
    channel: str
    build: str


app = FastAPI(title="Kryos System Health", version="1.0.0")

CONFIG_DIR = Path(os.getenv("KRYOS_CONFIG_DIR", "/opt/kryos-os/config"))
OOBE_MARKER_PATH = CONFIG_DIR / ".oobe_complete"
BOOT_TS = datetime.now(timezone.utc)


def _about() -> SystemAbout:
    return SystemAbout(
        name=os.getenv("RELEASE_NAME", "Prady OS"),
        version=os.getenv("RELEASE_VERSION", "1.0.0"),
        channel=os.getenv("RELEASE_CHANNEL", "stable"),
        build=os.getenv("RELEASE_BUILD", "phase-38"),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/system/about")
async def system_about() -> SystemAbout:
    return _about()


@app.get("/api/system/version")
async def system_version() -> dict[str, str]:
    about = _about()
    return {
        "name": about.name,
        "version": about.version,
        "channel": about.channel,
        "build": about.build,
    }


@app.get("/api/system/first-boot-status")
async def first_boot_status() -> dict[str, bool]:
    return {"complete": OOBE_MARKER_PATH.exists()}


@app.post("/api/system/first-boot-complete")
async def first_boot_complete() -> dict[str, str]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    OOBE_MARKER_PATH.write_text("complete\n", encoding="utf-8")
    os.chmod(OOBE_MARKER_PATH, 0o600)
    return {"status": "ok"}


@app.get("/api/system/health")
async def system_health() -> dict[str, object]:
    now = datetime.now(timezone.utc).isoformat()
    uptime = int((datetime.now(timezone.utc) - BOOT_TS).total_seconds())
    oobe_complete = OOBE_MARKER_PATH.exists()

    checks = {
        "oobe": "ok" if oobe_complete else "pending",
        "hardware": "ok",
        "sdk_registry": "ok",
    }
    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"

    return {
        "status": status,
        "timestamp": now,
        "uptime_seconds": uptime,
        "checks": checks,
        "first_boot_complete": oobe_complete,
        "release": _about().model_dump(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("system_health_service:app", host="0.0.0.0", port=8021, reload=False)
