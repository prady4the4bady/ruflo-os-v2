"""Neila — Ouroboros autonomous background daemon for Prady OS.

Neila runs as a persistent async daemon below Prax, performing
background cognition: memory consolidation, idle-time research
triggers, retry scheduling, stale task resurfacing, digest hooks.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

VERSION = "1.0.0"
SERVICE_NAME = "neila"

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

TICK_INTERVAL = int(os.getenv("NEILA_TICK_INTERVAL", "60"))
INVENTOR_ENGINE_URL = os.getenv("INVENTOR_ENGINE_URL", "http://inventor-engine:8022")
AUDIT_LOG_URL = os.getenv("AUDIT_LOG_URL", "http://audit-log:8112")
NOTIFICATION_BUS_URL = os.getenv("NOTIFICATION_BUS_URL", "http://notification-bus:8111")
SELF_LEARNING_URL = os.getenv("SELF_LEARNING_URL", "http://self-learning:8018")
AHNIS_URL = os.getenv("AHNIS_URL", "http://ahnis:8027")
MODEL_GATEWAY_URL = os.getenv("MODEL_GATEWAY_URL", "http://model-gateway:11430")


@dataclass
class LoopMetrics:
    cycle_count: int = 0
    last_cycle_ts: str = ""
    tasks_scanned: int = 0
    actions_triggered: int = 0
    actions_deferred: int = 0
    failures: int = 0


metrics = LoopMetrics()
_paused = False
_loop_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop_task
    _loop_task = asyncio.create_task(_ouroboros_loop())
    yield
    if _loop_task and not _loop_task.done():
        _loop_task.cancel()
        try:
            await _loop_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Prady OS Neila — Ouroboros Daemon", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


async def _ouroboros_loop():
    backoff = TICK_INTERVAL
    backoff_max = TICK_INTERVAL * 16

    while True:
        try:
            if _paused:
                await asyncio.sleep(TICK_INTERVAL)
                continue

            metrics.cycle_count += 1
            metrics.last_cycle_ts = datetime.now(timezone.utc).isoformat()
            cycle_start = time.perf_counter()

            # Scan inventor-engine for pending proposals and stalled builds
            try:
                async with httpx.AsyncClient(timeout=10.0) as c:
                    proposals_resp = await c.get(f"{INVENTOR_ENGINE_URL}/inventor/proposals")
                    if proposals_resp.status_code == 200:
                        proposals = proposals_resp.json()
                        metrics.tasks_scanned = len(proposals)
                        if proposals:
                            logger.info("Found %d pending proposals", len(proposals))
            except Exception as e:
                logger.debug("Inventor-engine scan: %s", e)

            # Trigger memory consolidation via Ahnis
            try:
                async with httpx.AsyncClient(timeout=15.0) as c:
                    await c.post(f"{AHNIS_URL}/memory/consolidate", json={})
            except Exception as e:
                logger.debug("Memory consolidation trigger: %s", e)

            # Check self-learning for new skills to consolidate
            try:
                async with httpx.AsyncClient(timeout=10.0) as c:
                    await c.get(f"{SELF_LEARNING_URL}/learn/stats")
            except Exception:
                pass

            # Log cycle to audit
            cycle_ms = int((time.perf_counter() - cycle_start) * 1000)
            try:
                async with httpx.AsyncClient(timeout=5.0) as c:
                    await c.post(f"{AUDIT_LOG_URL}/events", json={
                        "event": "neila_cycle",
                        "cycle": metrics.cycle_count,
                        "duration_ms": cycle_ms,
                        "service": "neila",
                    })
            except Exception:
                pass

            backoff = TICK_INTERVAL
            metrics.actions_triggered += 1
            await asyncio.sleep(TICK_INTERVAL)

        except asyncio.CancelledError:
            break
        except Exception as e:
            metrics.failures += 1
            logger.error("Ouroboros loop error: %s", e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, backoff_max)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}


@app.get("/neila/status")
async def neila_status() -> dict[str, Any]:
    return {
        "paused": _paused,
        "loop_active": _loop_task is not None and not _loop_task.done(),
        "metrics": {
            "cycle_count": metrics.cycle_count,
            "last_cycle_ts": metrics.last_cycle_ts,
            "tasks_scanned": metrics.tasks_scanned,
            "actions_triggered": metrics.actions_triggered,
            "actions_deferred": metrics.actions_deferred,
            "failures": metrics.failures,
        },
    }


@app.post("/neila/pause")
async def neila_pause() -> dict[str, str]:
    global _paused
    _paused = True
    logger.info("Neila paused")
    return {"status": "paused"}


@app.post("/neila/resume")
async def neila_resume() -> dict[str, str]:
    global _paused
    _paused = False
    logger.info("Neila resumed")
    return {"status": "resumed"}
