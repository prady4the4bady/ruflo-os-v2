"""Neila — Ouroboros autonomous background daemon for Prady OS.

Runs as a persistent async daemon below Prax. Handles:
- Retry queue for failed-but-retryable jobs
- Stalled-task resurfacing
- Digest candidate generation
- Memory consolidation triggers
- Scheduled follow-up reminders
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

VERSION = "1.0.0"
SERVICE_NAME = "neila"

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

TICK_INTERVAL = int(os.getenv("NEILA_TICK_INTERVAL", "60"))
INVENTOR_URL = os.getenv("INVENTOR_ENGINE_URL", "http://inventor-engine:8022")
AUDIT_URL = os.getenv("AUDIT_LOG_URL", "http://audit-log:8112")
NOTIFY_URL = os.getenv("NOTIFICATION_BUS_URL", "http://notification-bus:8111")
SELF_LEARN_URL = os.getenv("SELF_LEARNING_URL", "http://self-learning:8018")
AHNIS_URL = os.getenv("AHNIS_URL", "http://ahnis:8028")
MODEL_URL = os.getenv("MODEL_GATEWAY_URL", "http://model-gateway:11430")

HTTP_TIMEOUT = float(os.getenv("NEILA_HTTP_TIMEOUT", "10.0"))


class RetryState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FAILED = "failed"
    EXHAUSTED = "exhausted"


@dataclass
class RetryEntry:
    id: str
    task_type: str
    target_url: str
    payload: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    attempt: int = 0
    state: RetryState = RetryState.PENDING
    last_error: str = ""
    created_ts: str = ""
    next_attempt_ts: str = ""


@dataclass
class ScheduledAction:
    id: str
    action_type: str
    target_url: str
    payload: dict[str, Any] = field(default_factory=dict)
    due_ts: str = ""
    trigger_ts: str = ""
    completed: bool = False


@dataclass
class LoopMetrics:
    cycle_count: int = 0
    last_cycle_ts: str = ""
    tasks_scanned: int = 0
    actions_triggered: int = 0
    actions_deferred: int = 0
    retry_queue_depth: int = 0
    scheduled_count: int = 0
    digests_generated: int = 0
    failures: int = 0


metrics = LoopMetrics()
_paused = False
_loop_task: asyncio.Task | None = None
_retry_queue: list[RetryEntry] = []
_scheduled_actions: list[ScheduledAction] = []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _audit(event: str, detail: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
            await c.post(f"{AUDIT_URL}/events", json={"event": event, "service": "neila", "detail": detail})
    except Exception:
        pass


async def _http_post(url: str, json_data: dict | None = None) -> httpx.Response | None:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
            return await c.post(url, json=json_data or {})
    except Exception as e:
        logger.debug("HTTP POST %s: %s", url, e)
        return None


async def _http_get(url: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
            r = await c.get(url)
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        logger.debug("HTTP GET %s: %s", url, e)
    return None


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
    while True:
        try:
            if _paused:
                await asyncio.sleep(TICK_INTERVAL)
                continue
            metrics.cycle_count += 1
            metrics.last_cycle_ts = _utc_now()
            cycle_start = time.perf_counter()

            # 1. Scan inventor-engine proposals
            data = await _http_get(f"{INVENTOR_URL}/inventor/proposals")
            proposals = data if isinstance(data, list) else []
            metrics.tasks_scanned = len(proposals)
            if proposals:
                logger.info("Neila: %d pending proposals found", len(proposals))

            # 2. Process retry queue
            metrics.retry_queue_depth = len(_retry_queue)
            now = _utc_now()
            for entry in _retry_queue:
                if entry.state != RetryState.PENDING:
                    continue
                if entry.next_attempt_ts and entry.next_attempt_ts > now:
                    continue
                entry.state = RetryState.RUNNING
                entry.attempt += 1
                try:
                    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
                        resp = await c.post(entry.target_url, json=entry.payload)
                    if resp.status_code < 500:
                        entry.state = RetryState.FAILED
                        _retry_queue.remove(entry)
                        metrics.actions_triggered += 1
                    else:
                        raise IOError(f"HTTP {resp.status_code}")
                except Exception as e:
                    entry.last_error = str(e)
                    if entry.attempt >= entry.max_retries:
                        entry.state = RetryState.EXHAUSTED
                        logger.warning("Retry exhausted for %s/%s: %s", entry.task_type, entry.id, e)
                    else:
                        entry.state = RetryState.PENDING
                        backoff_sec = min(60 * (2 ** (entry.attempt - 1)), 3600)
                        entry.next_attempt_ts = (datetime.now(timezone.utc) + timedelta(seconds=backoff_sec)).isoformat()
                        metrics.actions_deferred += 1

            # 3. Process scheduled actions
            now_dt = datetime.now(timezone.utc)
            for action in list(_scheduled_actions):
                if action.completed:
                    continue
                if action.due_ts and action.due_ts <= _utc_now():
                    result = await _http_post(action.target_url, action.payload)
                    action.completed = True
                    action.trigger_ts = _utc_now()
                    metrics.actions_triggered += 1
                    await _audit("scheduled_action_triggered", {"action_type": action.action_type, "id": action.id})
            metrics.scheduled_count = len([a for a in _scheduled_actions if not a.completed])

            # 4. Memory consolidation via Ahnis
            await _http_post(f"{AHNIS_URL}/memory/consolidate")

            # 5. Digest candidate generation (every 10 cycles)
            if metrics.cycle_count % 10 == 0:
                digest = await _http_get(f"{INVENTOR_URL}/inventor/digest")
                if digest:
                    metrics.digests_generated += 1
                    await _http_post(f"{NOTIFY_URL}/notify", {
                        "title": "Prax Digest Snapshot",
                        "body": f"Cycle {metrics.cycle_count}: {digest.get('honest_summary', '')[:200]}",
                        "severity": "info", "source": "neila",
                    })
                    await _audit("digest_generated", {"cycle": metrics.cycle_count, "summary": str(digest)[:200]})

            # 6. Stalled-task resurfacing: check proposals older than 24h
            for p in proposals:
                created = p.get("created_ts", "")
                if created and created < (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat():
                    await _http_post(f"{NOTIFY_URL}/notify", {
                        "title": "Stalled Proposal Resurfaced",
                        "body": f"Proposal {p.get('proposal_id', '')} has been pending >24h",
                        "severity": "info", "source": "neila",
                    })
                    break

            # 7. Log cycle to audit
            cycle_ms = int((time.perf_counter() - cycle_start) * 1000)
            await _audit("neila_cycle", {"cycle": metrics.cycle_count, "duration_ms": cycle_ms, "proposals_found": len(proposals)})

            backoff = TICK_INTERVAL
            await asyncio.sleep(TICK_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            metrics.failures += 1
            logger.error("Ouroboros loop error: %s", e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, TICK_INTERVAL * 16)


# --- Endpoints ---

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
            "retry_queue_depth": metrics.retry_queue_depth,
            "scheduled_count": metrics.scheduled_count,
            "digests_generated": metrics.digests_generated,
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


class EnqueueRequest(BaseModel):
    task_type: str
    target_url: str
    payload: dict[str, Any] = {}
    max_retries: int = 3


@app.post("/neila/enqueue")
async def neila_enqueue(req: EnqueueRequest) -> dict[str, str]:
    entry = RetryEntry(
        id=str(uuid.uuid4()),
        task_type=req.task_type,
        target_url=req.target_url,
        payload=req.payload,
        max_retries=max(1, req.max_retries),
        created_ts=_utc_now(),
    )
    _retry_queue.append(entry)
    await _audit("enqueued", {"task_type": req.task_type, "id": entry.id})
    return {"status": "enqueued", "entry_id": entry.id}


@app.get("/neila/queue")
async def neila_queue() -> list[dict[str, Any]]:
    return [{"id": e.id, "task_type": e.task_type, "state": e.state.value, "attempt": e.attempt, "max_retries": e.max_retries, "last_error": e.last_error} for e in _retry_queue]


class ScheduleRequest(BaseModel):
    action_type: str
    target_url: str
    payload: dict[str, Any] = {}
    delay_minutes: int = 0


@app.post("/neila/schedule")
async def neila_schedule(req: ScheduleRequest) -> dict[str, str]:
    due = (datetime.now(timezone.utc) + timedelta(minutes=max(0, req.delay_minutes))).isoformat()
    action = ScheduledAction(id=str(uuid.uuid4()), action_type=req.action_type, target_url=req.target_url, payload=req.payload, due_ts=due)
    _scheduled_actions.append(action)
    return {"status": "scheduled", "action_id": action.id}


@app.get("/neila/scheduled")
async def neila_scheduled() -> list[dict[str, Any]]:
    return [{"id": a.id, "action_type": a.action_type, "due_ts": a.due_ts, "completed": a.completed} for a in _scheduled_actions if not a.completed]


@app.get("/neila/metrics")
async def neila_metrics() -> dict[str, Any]:
    return {
        "cycles_total": metrics.cycle_count,
        "last_cycle_ts": metrics.last_cycle_ts,
        "tasks_scanned_total": metrics.tasks_scanned,
        "actions_triggered_total": metrics.actions_triggered,
        "actions_deferred_total": metrics.actions_deferred,
        "retry_queue_depth": metrics.retry_queue_depth,
        "scheduled_pending": metrics.scheduled_count,
        "digests_generated_total": metrics.digests_generated,
        "failures_total": metrics.failures,
        "paused": _paused,
        "uptime_seconds": int(time.time() - _uptime_start) if '_uptime_start' in dir() else 0,
    }

_uptime_start = time.time()
