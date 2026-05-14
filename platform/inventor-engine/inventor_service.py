"""Prady OS — Inventor Engine (Phase 41)
Port 8022 — Prax autonomous project discovery, building, and weekly reporting."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite
import httpx
import psutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from build_team import BuildTeam
from inventor_db import InventorDB
from project_releaser import ProjectReleaser
from proposal_engine import ProposalCard, ProposalEngine
from research_agent import ResearchAgent
from verifier_agent import VerifierAgent

VERSION = "1.0.0"
SERVICE_NAME = "inventor-engine"

SCAN_INTERVAL_HOURS = int(os.getenv("SCAN_INTERVAL_HOURS", "6"))
MIN_PROBLEM_SCORE = float(os.getenv("MIN_PROBLEM_SCORE", "0.6"))

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


class InventorState:
    def __init__(self):
        self.loop_active = False
        self.current_phase = "idle"
        self.active_project: dict | None = None
        self.completed_projects: int = 0
        self.pending_proposal: dict | None = None
        self.last_scan_ts: str = ""
        self._loop_task: asyncio.Task | None = None
        self._idle_task: asyncio.Task | None = None
        self._digest_task: asyncio.Task | None = None
        self.db: InventorDB | None = None


state = InventorState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.db = InventorDB()
    await state.db.init()
    state._idle_task = asyncio.create_task(_idle_monitor_loop())
    state._digest_task = asyncio.create_task(_weekly_digest_loop())
    yield
    state.loop_active = False
    for task in (state._loop_task, state._idle_task, state._digest_task):
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Prady OS Inventor Engine", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _idle_monitor_loop():
    """Check system idle every 5 minutes. Start research when idle for 30+ min."""
    consecutive_idle = 0
    while True:
        await asyncio.sleep(300)
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            is_idle = cpu < 15.0 and ram.available > ram.total * 0.3
            if is_idle:
                consecutive_idle += 1
            else:
                consecutive_idle = 0

            if consecutive_idle >= 6 and not state.loop_active:
                logger.info("System idle for 30+ minutes — starting Prax research")
                state.loop_active = True
                state._loop_task = asyncio.create_task(inventor_loop())
        except Exception as e:
            logger.warning("Idle monitor error: %s", e)


async def _collect_weekly_stats() -> dict[str, Any]:
    """Collect stats from the past 7 days for the weekly digest."""
    one_week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    db_path = os.getenv("INVENTOR_DB_PATH", "/data/inventor/inventor.db")
    stats: dict[str, Any] = {
        "problems_scanned": 0, "proposals_created": 0,
        "projects_verified": 0, "projects_published": 0,
        "projects_failed": 0, "skills_added": 0, "storage_mb": 0.0,
    }
    try:
        async with aiosqlite.connect(db_path) as db:
            for key, sql in (
                ("problems_scanned", "SELECT COUNT(*) FROM problems WHERE discovered_ts >= ?"),
                ("proposals_created", "SELECT COUNT(*) FROM proposals WHERE created_ts >= ?"),
                ("projects_verified", "SELECT COUNT(*) FROM projects WHERE verified=1 AND build_started >= ?"),
                ("projects_published", "SELECT COUNT(*) FROM projects WHERE repo_url IS NOT NULL AND repo_url != '' AND build_started >= ?"),
                ("projects_failed", "SELECT COUNT(*) FROM projects WHERE status='failed' AND build_started >= ?"),
            ):
                async with db.execute(sql, (one_week_ago,)) as cur:
                    row = await cur.fetchone()
                    stats[key] = row[0] if row else 0
    except Exception as e:
        logger.warning("Weekly stats DB query failed: %s", e)

    try:
        sl_url = os.getenv("SELF_LEARNING_URL", "http://self-learning:8018")
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{sl_url}/learn/stats")
            if r.status_code == 200:
                stats["skills_added"] = r.json().get("total_skills", 0)
    except Exception:
        pass

    try:
        project_root = os.getenv("WORKSPACE_BASE", "/var/prady/projects")
        import shutil
        _, used, _ = shutil.disk_usage(project_root)
        stats["storage_mb"] = used / (1024 * 1024)
    except Exception:
        pass

    return stats


async def _weekly_digest_loop():
    """Send a weekly digest every Monday at 9AM local time."""
    while True:
        now = datetime.now()
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour >= 9:
            days_until_monday = 7
        next_monday = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_until_monday)
        wait_seconds = (next_monday - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        try:
            stats = await _collect_weekly_stats()
            notify_url = os.getenv("NOTIFICATION_BUS_URL", "http://notification-bus:8111")
            digest_body = (
                f"This week Prax researched {stats['problems_scanned']} problems, "
                f"generated {stats['proposals_created']} proposals, "
                f"completed {stats['projects_verified']} verified projects, "
                f"and published {stats['projects_published']} to GitHub. "
                f"Skills learned: {stats['skills_added']}. "
                f"Attempts that did not succeed: {stats['projects_failed']}. "
                f"Total project storage: {stats['storage_mb']:.1f} MB."
            )
            async with httpx.AsyncClient(timeout=10.0) as c:
                await c.post(f"{notify_url}/notify", json={
                    "title": "Prax Weekly Digest",
                    "body": digest_body,
                    "severity": "info",
                    "source": "inventor-engine",
                })
            logger.info("Weekly digest sent")
        except Exception as e:
            logger.warning("Weekly digest failed: %s", e)


async def inventor_loop():
    """Background loop: research -> propose -> wait for approval -> build -> verify -> release."""
    research_agent = ResearchAgent()
    proposal_engine = ProposalEngine()

    while state.loop_active:
        try:
            state.current_phase = "researching"

            problems = await research_agent.scan()

            novel_problems = []
            for problem in problems:
                if await research_agent.verify_novelty(problem):
                    novel_problems.append(problem)

            if not novel_problems:
                state.current_phase = "idle"
                await asyncio.sleep(SCAN_INTERVAL_HOURS * 3600)
                continue

            state.current_phase = "proposing"
            problem = novel_problems[0]

            research = await research_agent.deep_research(problem)
            proposal = await proposal_engine.generate(research)

            await state.db.save_proposal(proposal)
            state.last_scan_ts = datetime.now(timezone.utc).isoformat()

            state.current_phase = "awaiting_approval"
            state.pending_proposal = {
                "proposal_id": proposal.proposal_id,
                "problem_summary": proposal.problem_summary,
                "created_ts": proposal.created_ts,
            }

            polling_cycles = 0
            max_poll_cycles = (SCAN_INTERVAL_HOURS * 3600) // 30
            while state.loop_active and polling_cycles < max_poll_cycles:
                pending = await state.db.get_pending_proposals()
                approved = [p for p in pending if p["status"] == "approved"]

                rejected_proposals = [p for p in pending if p["status"] == "rejected" and p["proposal_id"] == proposal.proposal_id]
                if rejected_proposals:
                    state.pending_proposal = None
                    break

                if approved:
                    approved_proposal = approved[0]
                    state.pending_proposal = None
                    await _build_and_verify(approved_proposal)
                    break

                await asyncio.sleep(30)
                polling_cycles += 1

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("inventor_loop error: %s", e)
            await asyncio.sleep(60)

    state.current_phase = "idle"


async def _build_and_verify(proposal_data: dict):
    """Build a project and verify it."""
    project_id = str(uuid.uuid4())
    proposal_card = ProposalCard(
        proposal_id=proposal_data["proposal_id"],
        problem_summary=proposal_data["problem_summary"],
        why_it_matters=proposal_data.get("why_it_matters", ""),
        what_to_build=proposal_data.get("what_to_build", ""),
        tools=proposal_data.get("tools", []),
        time_estimate_hours=proposal_data.get("time_estimate_hrs", 8),
        deliverables=proposal_data.get("deliverables", []),
        confidence_level=proposal_data.get("confidence_level", "medium"),
        honest_caveats=proposal_data.get("honest_caveats", []),
        created_ts=proposal_data.get("created_ts", datetime.now(timezone.utc).isoformat()),
    )

    state.current_phase = "building"
    state.active_project = {"project_id": project_id, "status": "building"}

    await state.db.approve_proposal(proposal_card.proposal_id, project_id)

    build_team = BuildTeam()
    await state.db.log_agent_step(project_id, "architect", "running")
    result = await build_team.build(proposal_card, project_id)
    await state.db.log_agent_step(project_id, "architect", "completed", result.arch_output.output if result.arch_output else "")

    state.current_phase = "verifying"
    await state.db.update_project_status(project_id, "verifying", current_agent="verifier")

    verifier = VerifierAgent()
    verification = await verifier.verify(result, proposal_card)

    await state.db.update_project_status(
        project_id,
        status="completed" if verification.verified else "failed",
        current_agent="verifier",
        test_pass_rate=verification.test_pass_rate,
        verified=verification.verified,
        failure_details=verification.failure_details,
    )

    if verification.verified:
        state.current_phase = "releasing"
        releaser = ProjectReleaser()
        project = await state.db.get_project(project_id)
        if project:
            release_result = await releaser.release(project)
            await state.db.update_project_status(project_id, "released", repo_url=release_result.urls.get("github"))
            if release_result.urls.get("github"):
                await state.db.update_project_status(project_id, "released", repo_url=release_result.urls["github"])
        state.completed_projects += 1

    state.active_project = None
    state.current_phase = "idle"


@app.get("/inventor/status")
async def inventor_status() -> dict[str, Any]:
    return {
        "loop_active": state.loop_active,
        "current_phase": state.current_phase,
        "active_project": state.active_project,
        "completed_projects": state.completed_projects,
        "pending_proposal": state.pending_proposal,
        "last_scan_ts": state.last_scan_ts,
    }


@app.post("/inventor/start")
async def inventor_start() -> dict[str, str]:
    if state.loop_active:
        return {"status": "already_running"}
    state.loop_active = True
    state._loop_task = asyncio.create_task(inventor_loop())
    return {"status": "started"}


@app.post("/inventor/stop")
async def inventor_stop() -> dict[str, str]:
    if not state.loop_active:
        return {"status": "already_stopped"}
    state.loop_active = False
    if state._loop_task and not state._loop_task.done():
        state._loop_task.cancel()
    return {"status": "stopped"}


@app.get("/inventor/proposals")
async def inventor_proposals() -> list[dict[str, Any]]:
    return await state.db.get_pending_proposals()


@app.post("/inventor/proposals/{proposal_id}/approve")
async def inventor_approve(proposal_id: str) -> dict[str, Any]:
    proposals = await state.db.get_pending_proposals()
    proposal = next((p for p in proposals if p["proposal_id"] == proposal_id), None)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    project_id = str(uuid.uuid4())
    await state.db.approve_proposal(proposal_id, project_id)

    asyncio.create_task(_build_and_verify(proposal))

    return {"status": "building", "project_id": project_id}


@app.post("/inventor/proposals/{proposal_id}/reject")
async def inventor_reject(proposal_id: str) -> dict[str, str]:
    proposals = await state.db.get_pending_proposals()
    proposal = next((p for p in proposals if p["proposal_id"] == proposal_id), None)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    await state.db.reject_proposal(proposal_id)
    return {"status": "rejected"}


@app.get("/inventor/projects")
async def inventor_projects() -> list[dict[str, Any]]:
    return await state.db.get_all_projects()


@app.get("/inventor/projects/{project_id}/progress")
async def inventor_project_progress(project_id: str) -> dict[str, Any]:
    project = await state.db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    steps_log = project.get("steps_log", "[]")
    try:
        import json
        steps = json.loads(steps_log) if isinstance(steps_log, str) else steps_log
    except (json.JSONDecodeError, TypeError):
        steps = []

    return {
        "project_id": project["project_id"],
        "name": project["name"],
        "status": project["status"],
        "current_agent": project.get("current_agent", ""),
        "steps_completed": steps,
        "steps_remaining": [],
        "latest_commit": "",
        "test_results": {"passed": 0, "failed": 0},
        "verified": bool(project["verified"]),
        "eta_minutes": 0,
    }


@app.post("/inventor/projects/{project_id}/release")
async def release_project(project_id: str) -> dict[str, Any]:
    project = await state.db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project["verified"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot release unverified project. Prax does not release what it cannot confirm works.",
        )
    releaser = ProjectReleaser()
    result = await releaser.release(project)
    return {"status": "released", "urls": result.urls}


@app.get("/inventor/digest")
async def get_weekly_digest() -> dict[str, Any]:
    stats = await _collect_weekly_stats()
    return {
        "period": "last_7_days",
        "generated_ts": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "honest_summary": (
            f"Prax researched {stats['problems_scanned']} problems "
            f"and completed {stats['projects_verified']} verified "
            f"projects. {stats['projects_failed']} attempts did "
            f"not succeed — this is normal for experimental AI "
            f"development. All failures are logged."
        ),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}
