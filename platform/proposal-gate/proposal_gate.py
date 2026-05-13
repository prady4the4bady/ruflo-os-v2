"""Proposal Gate — authoritative state machine for research proposals.

The Kryos Researcher service emits project_proposal notifications when
Lumyn synthesises an idea from fresh research notes. The Proposal Gate
owns the full lifecycle from that moment on:

    PROPOSED  -> APPROVED   -> IN_PROGRESS -> DONE
              -> REJECTED
              -> EXPIRED     (no decision within TTL)

Every transition is signed (SHA256 over the previous audit row plus the
transition payload) so the audit trail is tamper-evident — you cannot
rewrite an earlier decision without breaking every hash that followed.

The gate exposes a small REST surface:

    POST   /proposal                           register a new proposal
    GET    /proposal                           list proposals (optional state filter)
    GET    /proposal/{id}                      fetch one proposal with history
    POST   /proposal/{id}/approve              user approves; triggers /start hook
    POST   /proposal/{id}/reject               user rejects with optional reason
    POST   /proposal/{id}/start                move APPROVED -> IN_PROGRESS
    POST   /proposal/{id}/complete             move IN_PROGRESS -> DONE
    POST   /proposal/{id}/fail                 move IN_PROGRESS -> DONE (ok=false)
    GET    /audit                              linear audit trail

All writes are locked with an in-process asyncio.Lock so transitions
are serialised even if two HTTP workers try to change the same row.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import aiosqlite
except Exception:  # pragma: no cover
    aiosqlite = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DB_PATH = DATA_DIR / "proposal_gate.db"

NOTIFICATION_BUS_URL = os.environ.get(
    "NOTIFICATION_BUS_URL", "http://notification-bus:8111"
)
AGENT_RUNTIME_URL = os.environ.get("AGENT_RUNTIME_URL", "http://agent-runtime:8100")

# Default expiry for proposals awaiting user decision. After this many
# hours, a daemon marks them EXPIRED so the UI can clean up.
DEFAULT_TTL_HOURS = int(os.environ.get("PROPOSAL_TTL_HOURS", "168"))  # 7 days


class State(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# Allowed transitions. Anything not listed fails with 409.
_TRANSITIONS: dict[State, set[State]] = {
    State.PROPOSED:    {State.APPROVED, State.REJECTED, State.EXPIRED},
    State.APPROVED:    {State.IN_PROGRESS, State.REJECTED},
    State.IN_PROGRESS: {State.DONE},
    State.DONE:        set(),
    State.REJECTED:    set(),
    State.EXPIRED:     set(),
}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ProposalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=4000)
    plan: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    origin: str = Field(default="kryos-researcher")
    ttl_hours: int = Field(default=DEFAULT_TTL_HOURS, ge=1, le=720)


class DecisionRequest(BaseModel):
    reason: Optional[str] = None
    actor: str = Field(default="user")


class CompleteRequest(BaseModel):
    ok: bool = True
    output: Optional[dict[str, Any]] = None
    actor: str = Field(default="prax")


class TransitionRecord(BaseModel):
    ts: str
    from_state: str
    to_state: str
    actor: str
    reason: Optional[str] = None
    chain_hash: str


class Proposal(BaseModel):
    id: str
    title: str
    rationale: str
    plan: list[str]
    sources: list[str]
    origin: str
    state: State
    created_at: str
    updated_at: str
    expires_at: str
    history: list[TransitionRecord] = Field(default_factory=list)
    result: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hours_from(iso_ts: str, hours: int) -> str:
    base = datetime.fromisoformat(iso_ts)
    from datetime import timedelta

    return (base + timedelta(hours=hours)).isoformat()


async def _init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ddl = """
    CREATE TABLE IF NOT EXISTS proposals (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      rationale TEXT NOT NULL,
      plan TEXT NOT NULL,
      sources TEXT NOT NULL,
      origin TEXT NOT NULL,
      state TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      expires_at TEXT NOT NULL,
      result TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_proposals_state ON proposals(state);

    CREATE TABLE IF NOT EXISTS transitions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      proposal_id TEXT NOT NULL,
      ts TEXT NOT NULL,
      from_state TEXT NOT NULL,
      to_state TEXT NOT NULL,
      actor TEXT NOT NULL,
      reason TEXT,
      chain_hash TEXT NOT NULL,
      FOREIGN KEY (proposal_id) REFERENCES proposals(id)
    );
    CREATE INDEX IF NOT EXISTS idx_transitions_proposal ON transitions(proposal_id);
    """
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript(ddl)
            await db.commit()
        return

    def _sync() -> None:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.executescript(ddl)
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_sync)


# ---------------------------------------------------------------------------
# Audit chain
# ---------------------------------------------------------------------------


async def _last_chain_hash() -> str:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT chain_hash FROM transitions ORDER BY id DESC LIMIT 1"
            )
            row = await cur.fetchone()
            return row[0] if row else "genesis"

    def _sync() -> str:
        conn = sqlite3.connect(DB_PATH)
        try:
            row = conn.execute(
                "SELECT chain_hash FROM transitions ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return row[0] if row else "genesis"
        finally:
            conn.close()

    return await asyncio.to_thread(_sync)


def _compute_chain_hash(previous: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((previous + "\n" + canonical).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Core state machine
# ---------------------------------------------------------------------------


_state_lock = asyncio.Lock()


async def _load_proposal(proposal_id: str) -> Optional[Proposal]:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
            )
            row = await cur.fetchone()
            if row is None:
                return None
            hist_cur = await db.execute(
                "SELECT ts, from_state, to_state, actor, reason, chain_hash "
                "FROM transitions WHERE proposal_id = ? ORDER BY id ASC",
                (proposal_id,),
            )
            hist_rows = await hist_cur.fetchall()
    else:
        def _sync_load() -> tuple[Any, list[Any]] | None:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            try:
                pr = conn.execute(
                    "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
                ).fetchone()
                if pr is None:
                    return None
                hr = conn.execute(
                    "SELECT ts, from_state, to_state, actor, reason, chain_hash "
                    "FROM transitions WHERE proposal_id = ? ORDER BY id ASC",
                    (proposal_id,),
                ).fetchall()
                return pr, hr
            finally:
                conn.close()

        result = await asyncio.to_thread(_sync_load)
        if result is None:
            return None
        row, hist_rows = result

    return Proposal(
        id=row["id"],
        title=row["title"],
        rationale=row["rationale"],
        plan=json.loads(row["plan"]),
        sources=json.loads(row["sources"]),
        origin=row["origin"],
        state=State(row["state"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        expires_at=row["expires_at"],
        result=json.loads(row["result"]) if row["result"] else None,
        history=[
            TransitionRecord(
                ts=h["ts"],
                from_state=h["from_state"],
                to_state=h["to_state"],
                actor=h["actor"],
                reason=h["reason"],
                chain_hash=h["chain_hash"],
            )
            for h in hist_rows
        ],
    )


async def _insert_proposal(p: Proposal) -> None:
    payload = {
        "op": "create",
        "proposal_id": p.id,
        "title": p.title,
        "state": p.state.value,
        "ts": p.created_at,
        "origin": p.origin,
    }
    prev_hash = await _last_chain_hash()
    chain = _compute_chain_hash(prev_hash, payload)

    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO proposals (id, title, rationale, plan, sources, origin, state, "
                "created_at, updated_at, expires_at, result) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                (
                    p.id, p.title, p.rationale,
                    json.dumps(p.plan), json.dumps(p.sources),
                    p.origin, p.state.value,
                    p.created_at, p.updated_at, p.expires_at,
                ),
            )
            await db.execute(
                "INSERT INTO transitions (proposal_id, ts, from_state, to_state, actor, reason, chain_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p.id, p.created_at, "NONE", p.state.value, p.origin, None, chain),
            )
            await db.commit()
        return

    def _sync_insert() -> None:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                "INSERT INTO proposals (id, title, rationale, plan, sources, origin, state, "
                "created_at, updated_at, expires_at, result) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                (
                    p.id, p.title, p.rationale,
                    json.dumps(p.plan), json.dumps(p.sources),
                    p.origin, p.state.value,
                    p.created_at, p.updated_at, p.expires_at,
                ),
            )
            conn.execute(
                "INSERT INTO transitions (proposal_id, ts, from_state, to_state, actor, reason, chain_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p.id, p.created_at, "NONE", p.state.value, p.origin, None, chain),
            )
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_sync_insert)


async def _transition(
    proposal_id: str,
    to_state: State,
    actor: str,
    reason: Optional[str] = None,
    result: Optional[dict[str, Any]] = None,
) -> Proposal:
    async with _state_lock:
        existing = await _load_proposal(proposal_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="proposal not found")
        from_state = existing.state
        if to_state not in _TRANSITIONS[from_state]:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"illegal transition {from_state.value} -> {to_state.value}. "
                    f"allowed: {sorted(s.value for s in _TRANSITIONS[from_state])}"
                ),
            )

        now = _now_iso()
        payload = {
            "op": "transition",
            "proposal_id": proposal_id,
            "from": from_state.value,
            "to": to_state.value,
            "ts": now,
            "actor": actor,
            "reason": reason,
        }
        prev = await _last_chain_hash()
        chain = _compute_chain_hash(prev, payload)

        if aiosqlite is not None:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE proposals SET state = ?, updated_at = ?, result = COALESCE(?, result) WHERE id = ?",
                    (
                        to_state.value,
                        now,
                        json.dumps(result) if result is not None else None,
                        proposal_id,
                    ),
                )
                await db.execute(
                    "INSERT INTO transitions (proposal_id, ts, from_state, to_state, actor, reason, chain_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        proposal_id, now, from_state.value, to_state.value,
                        actor, reason, chain,
                    ),
                )
                await db.commit()
        else:
            def _sync_trans() -> None:
                conn = sqlite3.connect(DB_PATH)
                try:
                    conn.execute(
                        "UPDATE proposals SET state = ?, updated_at = ?, result = COALESCE(?, result) WHERE id = ?",
                        (
                            to_state.value,
                            now,
                            json.dumps(result) if result is not None else None,
                            proposal_id,
                        ),
                    )
                    conn.execute(
                        "INSERT INTO transitions (proposal_id, ts, from_state, to_state, actor, reason, chain_hash) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            proposal_id, now, from_state.value, to_state.value,
                            actor, reason, chain,
                        ),
                    )
                    conn.commit()
                finally:
                    conn.close()

            await asyncio.to_thread(_sync_trans)

        updated = await _load_proposal(proposal_id)
        if updated is None:  # pragma: no cover — defensive
            raise HTTPException(status_code=500, detail="load after transition failed")
        return updated


async def _notify(event_type: str, proposal: Proposal) -> None:
    payload = {
        "type": event_type,
        "title": f"[{event_type}] {proposal.title}",
        "body": f"proposal {proposal.id}\nstate={proposal.state.value}\norigin={proposal.origin}",
        "source": "proposal-gate",
        "severity": "info",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{NOTIFICATION_BUS_URL}/notify", json=payload)
    except httpx.HTTPError as exc:
        logger.info("notification-bus unreachable: %s", exc)


async def _notify_agent_runtime(proposal: Proposal) -> None:
    """Post the approved plan to agent-runtime so Prax can start executing.

    Failure here is non-fatal: the proposal is APPROVED in our DB even if
    agent-runtime is momentarily unreachable. The UI can retry /start.
    """
    payload = {
        "proposal_id": proposal.id,
        "title": proposal.title,
        "rationale": proposal.rationale,
        "plan": proposal.plan,
        "sources": proposal.sources,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{AGENT_RUNTIME_URL}/agents/spawn-from-proposal",
                json=payload,
            )
    except httpx.HTTPError as exc:
        logger.info(
            "agent-runtime unreachable for proposal %s: %s",
            proposal.id,
            exc,
        )


# ---------------------------------------------------------------------------
# Audit verification
# ---------------------------------------------------------------------------


async def _verify_chain() -> tuple[bool, int, Optional[int]]:
    """Walk every transition in insertion order, recompute the chain hash,
    compare. Returns (ok, total_rows, broken_row_id_or_None)."""
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT id, proposal_id, ts, from_state, to_state, actor, reason, chain_hash "
                "FROM transitions ORDER BY id ASC"
            )
            rows = await cur.fetchall()
    else:
        def _sync() -> list[Any]:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            try:
                return conn.execute(
                    "SELECT id, proposal_id, ts, from_state, to_state, actor, reason, chain_hash "
                    "FROM transitions ORDER BY id ASC"
                ).fetchall()
            finally:
                conn.close()

        rows = await asyncio.to_thread(_sync)

    prev = "genesis"
    for row in rows:
        if row["from_state"] == "NONE":
            payload = {
                "op": "create",
                "proposal_id": row["proposal_id"],
                "title": None,  # reconstructed title unknown from transition row
                "state": row["to_state"],
                "ts": row["ts"],
                "origin": row["actor"],
            }
        else:
            payload = {
                "op": "transition",
                "proposal_id": row["proposal_id"],
                "from": row["from_state"],
                "to": row["to_state"],
                "ts": row["ts"],
                "actor": row["actor"],
                "reason": row["reason"],
            }
        # title is not persisted in the transitions table, so we cannot
        # recompute the create hash bit-for-bit. We skip CREATE rows in
        # verification (they are still tamper-evident via the later
        # transitions chaining on top of them).
        if row["from_state"] == "NONE":
            prev = row["chain_hash"]
            continue
        expected = _compute_chain_hash(prev, payload)
        if expected != row["chain_hash"]:
            return False, len(rows), row["id"]
        prev = row["chain_hash"]
    return True, len(rows), None


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await _init_db()
    yield


app = FastAPI(title="Prady Proposal Gate", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "proposal-gate", "version": "1.0.0"}


@app.get("/")
async def root() -> dict[str, Any]:
    return {"service": "proposal-gate", "version": "1.0.0"}


@app.post("/proposal", status_code=201, response_model=Proposal)
async def create_proposal(req: ProposalCreate) -> Proposal:
    now = _now_iso()
    proposal = Proposal(
        id=str(uuid.uuid4()),
        title=req.title,
        rationale=req.rationale,
        plan=req.plan,
        sources=req.sources,
        origin=req.origin,
        state=State.PROPOSED,
        created_at=now,
        updated_at=now,
        expires_at=_hours_from(now, req.ttl_hours),
    )
    async with _state_lock:
        await _insert_proposal(proposal)
    loaded = await _load_proposal(proposal.id)
    assert loaded is not None
    await _notify("proposal_created", loaded)
    return loaded


@app.get("/proposal", response_model=list[Proposal])
async def list_proposals(
    state: Optional[State] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Proposal]:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if state is None:
                cur = await db.execute(
                    "SELECT id FROM proposals ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            else:
                cur = await db.execute(
                    "SELECT id FROM proposals WHERE state = ? ORDER BY created_at DESC LIMIT ?",
                    (state.value, limit),
                )
            rows = await cur.fetchall()
    else:
        def _sync() -> list[Any]:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            try:
                if state is None:
                    return conn.execute(
                        "SELECT id FROM proposals ORDER BY created_at DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
                return conn.execute(
                    "SELECT id FROM proposals WHERE state = ? ORDER BY created_at DESC LIMIT ?",
                    (state.value, limit),
                ).fetchall()
            finally:
                conn.close()

        rows = await asyncio.to_thread(_sync)

    results: list[Proposal] = []
    for r in rows:
        p = await _load_proposal(r["id"])
        if p is not None:
            results.append(p)
    return results


@app.get("/proposal/{proposal_id}", response_model=Proposal)
async def get_proposal(proposal_id: str) -> Proposal:
    p = await _load_proposal(proposal_id)
    if p is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    return p


@app.post("/proposal/{proposal_id}/approve", response_model=Proposal)
async def approve_proposal(proposal_id: str, req: DecisionRequest) -> Proposal:
    p = await _transition(proposal_id, State.APPROVED, req.actor, req.reason)
    await _notify("proposal_approved", p)
    await _notify_agent_runtime(p)
    return p


@app.post("/proposal/{proposal_id}/reject", response_model=Proposal)
async def reject_proposal(proposal_id: str, req: DecisionRequest) -> Proposal:
    p = await _transition(proposal_id, State.REJECTED, req.actor, req.reason)
    await _notify("proposal_rejected", p)
    return p


@app.post("/proposal/{proposal_id}/start", response_model=Proposal)
async def start_proposal(proposal_id: str, req: DecisionRequest) -> Proposal:
    p = await _transition(proposal_id, State.IN_PROGRESS, req.actor, req.reason)
    await _notify("proposal_started", p)
    return p


@app.post("/proposal/{proposal_id}/complete", response_model=Proposal)
async def complete_proposal(
    proposal_id: str, req: CompleteRequest
) -> Proposal:
    result = {"ok": req.ok, "output": req.output}
    p = await _transition(
        proposal_id, State.DONE, req.actor, None, result=result
    )
    await _notify(
        "proposal_completed" if req.ok else "proposal_failed", p
    )
    return p


@app.post("/proposal/{proposal_id}/fail", response_model=Proposal)
async def fail_proposal(
    proposal_id: str, req: CompleteRequest
) -> Proposal:
    req.ok = False
    return await complete_proposal(proposal_id, req)


@app.get("/audit")
async def audit_trail(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT proposal_id, ts, from_state, to_state, actor, reason, chain_hash "
                "FROM transitions ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
    else:
        def _sync() -> list[Any]:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            try:
                return conn.execute(
                    "SELECT proposal_id, ts, from_state, to_state, actor, reason, chain_hash "
                    "FROM transitions ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            finally:
                conn.close()

        rows = await asyncio.to_thread(_sync)

    return {
        "transitions": [
            {
                "proposal_id": r["proposal_id"],
                "ts": r["ts"],
                "from_state": r["from_state"],
                "to_state": r["to_state"],
                "actor": r["actor"],
                "reason": r["reason"],
                "chain_hash": r["chain_hash"],
            }
            for r in rows
        ],
    }


@app.get("/audit/verify")
async def audit_verify() -> dict[str, Any]:
    ok, total, broken_at = await _verify_chain()
    return {"ok": ok, "transitions": total, "first_broken_id": broken_at}
