"""FastAPI application entrypoint for the Prady orchestration engine.

Singletons (bus, approvals, conductor, activity) are created inside the
lifespan context manager so they share the same event-loop as the server.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from app.activity_log import ActivityLogger
from app.approvals import ApprovalStore
from app.bus import MessageBus
from app.conductor import Conductor
from app.config import load_config
from app.schemas import ApprovalDecision, ApprovalRecord, TaskRecord, TaskRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level singletons (set during lifespan)
_conductor: Conductor | None = None
_bus: MessageBus | None = None
_approvals: ApprovalStore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _conductor, _bus, _approvals

    cfg = load_config()
    cfg.log_dir.mkdir(parents=True, exist_ok=True)

    activity = ActivityLogger(cfg.log_dir)

    _approvals = ApprovalStore()

    _bus = MessageBus(cfg.redis_url)
    await _bus.connect()
    logger.info("Redis connected: %s", cfg.redis_url)

    _conductor = Conductor(
        bus=_bus,
        approvals=_approvals,
        activity=activity,
        gateway_url=cfg.model_gateway_url,
        playwright_runner_url=cfg.playwright_runner_url,
        gateway_model=cfg.gateway_model,
        approval_timeout=cfg.approval_timeout_seconds,
    )
    logger.info(
        "Conductor ready — gateway=%s model=%s", cfg.model_gateway_url, cfg.gateway_model
    )

    yield

    await _bus.disconnect()
    logger.info("Redis disconnected")


app = FastAPI(
    title="Prady Orchestration Engine",
    description="Workflow engine with conductor agent, DAG tracking, and approval flows.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/healthz", tags=["health"])
async def healthz() -> Dict[str, Any]:
    redis_ok = False
    if _bus:
        try:
            redis_ok = await _bus.ping()
        except Exception:
            pass
    return {"status": "ok", "redis": redis_ok}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@app.post(
    "/tasks",
    response_model=TaskRecord,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["tasks"],
)
async def create_task(req: TaskRequest) -> TaskRecord:
    if _conductor is None:
        raise HTTPException(status_code=503, detail="Conductor not initialised")
    record = await _conductor.enqueue(req)
    return record


@app.get("/tasks", tags=["tasks"])
async def list_tasks() -> Dict[str, List[TaskRecord]]:
    if _conductor is None:
        raise HTTPException(status_code=503, detail="Conductor not initialised")
    return {"tasks": _conductor.list_tasks()}


@app.get("/tasks/{task_id}", response_model=TaskRecord, tags=["tasks"])
async def get_task(task_id: str) -> TaskRecord:
    if _conductor is None:
        raise HTTPException(status_code=503, detail="Conductor not initialised")
    record = _conductor.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found")
    return record


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


@app.get("/approvals/pending", tags=["approvals"])
async def pending_approvals() -> Dict[str, List[ApprovalRecord]]:
    if _approvals is None:
        raise HTTPException(status_code=503, detail="Approvals store not initialised")
    return {"pending": _approvals.pending()}


@app.post("/approvals/submit", response_model=ApprovalRecord, tags=["approvals"])
async def submit_approval(decision: ApprovalDecision) -> ApprovalRecord:
    if _approvals is None:
        raise HTTPException(status_code=503, detail="Approvals store not initialised")
    record = await _approvals.submit(decision)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"Approval {decision.approval_id!r} not found"
        )
    return record
