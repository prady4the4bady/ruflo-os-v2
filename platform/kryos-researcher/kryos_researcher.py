"""Kryos Researcher — continuous background research service.

Pulls fresh signal from public sources (arXiv, GitHub trending, RSS)
on a schedule, normalises each item into a small research-note record,
and stores the notes in a local SQLite database. Periodically, the
service invokes Lumyn to review the last N notes and synthesise at
most one high-quality project proposal. Proposals are emitted as
notifications on the notification-bus so the desktop shell can show
them to the user for approval.

Explicit non-goals for v1.0:

- No web scraping beyond documented public feeds.
- No auto-execution of proposals. Human approval is always required.
- No transmission of user data off the machine. Only outbound reads
  from the public feeds and local LLM calls through Vyrex.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import uuid
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    import aiosqlite
except Exception:  # pragma: no cover - optional import fallback
    aiosqlite = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DB_PATH = DATA_DIR / "researcher.db"

NOTIFICATION_BUS_URL = os.environ.get(
    "NOTIFICATION_BUS_URL", "http://notification-bus:8111"
)
MEMORY_SERVICE_URL = os.environ.get(
    "MEMORY_SERVICE_URL", "http://memory-service:8108"
)
LUMYN_URL = os.environ.get("LUMYN_URL", "http://agents-lumyn:8030")
MODEL_GATEWAY_URL = os.environ.get(
    "MODEL_GATEWAY_URL", "http://model-gateway:8000"
)

# Minutes between each research cycle. Kept conservative so rate limits
# on arxiv / github don't kick in if someone runs the OS 24/7.
RESEARCH_INTERVAL_MIN = int(os.environ.get("RESEARCH_INTERVAL_MIN", "60"))

# Minutes between each proposal synthesis pass.
PROPOSAL_INTERVAL_MIN = int(os.environ.get("PROPOSAL_INTERVAL_MIN", "240"))

# Max proposals the researcher can generate in a rolling 24h window.
# We want the user's approval queue to stay manageable.
DAILY_PROPOSAL_BUDGET = int(os.environ.get("DAILY_PROPOSAL_BUDGET", "3"))

# Hard caps so one misbehaving feed cannot blow up the DB.
MAX_NOTES_PER_CYCLE = int(os.environ.get("MAX_NOTES_PER_CYCLE", "30"))
MAX_NOTES_TOTAL = int(os.environ.get("MAX_NOTES_TOTAL", "5000"))

# Let the operator disable continuous research entirely; the REST
# endpoints for inspecting notes stay available.
RESEARCH_ENABLED = os.environ.get("RESEARCH_ENABLED", "true").lower() == "true"

# Default feeds. The operator can override by dropping a JSON file at
# /data/feeds.json with {"arxiv": [...], "rss": [...],
# "github_trending_languages": [...]}.
_DEFAULT_FEEDS: dict[str, Any] = {
    "arxiv": [
        "cs.AI",
        "cs.CL",
        "cs.DC",
        "cs.SE",
    ],
    "rss": [
        "https://news.ycombinator.com/rss",
    ],
    "github_trending_languages": [
        "python",
        "rust",
        "typescript",
    ],
}

USER_AGENT = "Prady-OS-Kryos-Researcher/1.0 (+https://github.com/prady4the4bady/prady-os)"

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


@dataclass
class ResearchNote:
    id: str
    source: str            # "arxiv" | "rss" | "github"
    source_id: str         # upstream id (arXiv id, rss guid, repo name)
    title: str
    summary: str
    url: str
    tags: list[str]
    discovered_at: str     # ISO 8601
    content_hash: str      # sha256(title + summary) — used for dedupe


class NoteListResponse(BaseModel):
    notes: list[dict[str, Any]]
    total: int


class ProposalResponse(BaseModel):
    id: str
    title: str
    rationale: str
    plan: list[str]
    sources: list[str]
    created_at: str


class ResearchStatus(BaseModel):
    enabled: bool
    last_research_at: str | None
    last_proposal_at: str | None
    total_notes: int
    total_proposals: int
    daily_proposals_used: int
    next_research_in_s: int | None


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ddl = """
    CREATE TABLE IF NOT EXISTS notes (
      id TEXT PRIMARY KEY,
      source TEXT NOT NULL,
      source_id TEXT NOT NULL,
      title TEXT NOT NULL,
      summary TEXT NOT NULL,
      url TEXT NOT NULL,
      tags TEXT NOT NULL,
      discovered_at TEXT NOT NULL,
      content_hash TEXT NOT NULL UNIQUE
    );
    CREATE INDEX IF NOT EXISTS idx_notes_source ON notes(source);
    CREATE INDEX IF NOT EXISTS idx_notes_discovered_at ON notes(discovered_at);

    CREATE TABLE IF NOT EXISTS proposals (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      rationale TEXT NOT NULL,
      plan TEXT NOT NULL,
      sources TEXT NOT NULL,
      created_at TEXT NOT NULL,
      notification_id TEXT
    );

    CREATE TABLE IF NOT EXISTS cycles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      kind TEXT NOT NULL,            -- 'research' | 'proposal'
      started_at TEXT NOT NULL,
      finished_at TEXT,
      ok INTEGER NOT NULL DEFAULT 0,
      detail TEXT NOT NULL DEFAULT ''
    );
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


def _load_feeds() -> dict[str, Any]:
    override = DATA_DIR / "feeds.json"
    if override.exists():
        try:
            return json.loads(override.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Invalid feeds.json (%s); using defaults", exc)
    return _DEFAULT_FEEDS


# ---------------------------------------------------------------------------
# Source adapters
# ---------------------------------------------------------------------------


async def _fetch_arxiv(client: httpx.AsyncClient, category: str) -> list[ResearchNote]:
    """Pull the 5 newest submissions for an arXiv category via the official
    Atom feed at export.arxiv.org. This is a public, no-auth endpoint."""
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query=cat:{category}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
    )
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=15.0)
        resp.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.info("arxiv %s fetch failed: %s", category, exc)
        return []

    notes: list[ResearchNote] = []
    try:
        # arXiv Atom namespace
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.text)
        for entry in root.findall("a:entry", ns):
            arxiv_id = (entry.findtext("a:id", "", ns) or "").strip()
            if not arxiv_id:
                continue
            title = (entry.findtext("a:title", "", ns) or "").strip()
            summary = (entry.findtext("a:summary", "", ns) or "").strip()
            if not title:
                continue
            note = _make_note(
                source="arxiv",
                source_id=arxiv_id,
                title=title,
                summary=summary,
                url=arxiv_id,
                tags=[category],
            )
            notes.append(note)
    except ET.ParseError as exc:
        logger.info("arxiv %s parse failed: %s", category, exc)
    return notes


async def _fetch_rss(client: httpx.AsyncClient, url: str) -> list[ResearchNote]:
    """Generic minimal RSS 2.0 reader. No third-party feedparser dep so the
    image stays small and we know exactly what we're parsing."""
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=15.0)
        resp.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.info("rss %s fetch failed: %s", url, exc)
        return []

    notes: list[ResearchNote] = []
    try:
        root = ET.fromstring(resp.text)
        # RSS 2.0: channel/item
        channel = root.find("channel")
        if channel is None:
            return []
        for item in channel.findall("item")[:10]:
            title = (item.findtext("title", "") or "").strip()
            link = (item.findtext("link", "") or "").strip()
            description = (item.findtext("description", "") or "").strip()
            guid = (item.findtext("guid", "") or link).strip()
            if not title or not link:
                continue
            notes.append(
                _make_note(
                    source="rss",
                    source_id=guid,
                    title=title,
                    summary=description[:800],
                    url=link,
                    tags=[_host_of(url)],
                )
            )
    except ET.ParseError as exc:
        logger.info("rss %s parse failed: %s", url, exc)
    return notes


async def _fetch_github_trending(
    client: httpx.AsyncClient, language: str
) -> list[ResearchNote]:
    """Pull the newest repos in a language via the public search API.
    No token required for unauthenticated use under the anonymous rate
    limit (60 req/h) which fits our hourly schedule easily."""
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    q = f"language:{language} created:>{since}"
    url = f"https://api.github.com/search/repositories?q={httpx.QueryParams({'q': q})['q']}&sort=stars&order=desc&per_page=5"
    try:
        resp = await client.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
            timeout=15.0,
        )
        resp.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.info("github %s fetch failed: %s", language, exc)
        return []

    notes: list[ResearchNote] = []
    try:
        data = resp.json()
    except ValueError:
        return []

    for repo in (data.get("items") or [])[:5]:
        full_name = repo.get("full_name") or ""
        title = full_name
        description = repo.get("description") or ""
        html_url = repo.get("html_url") or ""
        if not full_name or not html_url:
            continue
        stars = repo.get("stargazers_count", 0)
        notes.append(
            _make_note(
                source="github",
                source_id=full_name,
                title=f"{title} ({stars}\u2605)",
                summary=description,
                url=html_url,
                tags=[f"lang:{language}", "trending"],
            )
        )
    return notes


def _make_note(
    *,
    source: str,
    source_id: str,
    title: str,
    summary: str,
    url: str,
    tags: list[str],
) -> ResearchNote:
    content = (title + "\n" + summary).strip()
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return ResearchNote(
        id=str(uuid.uuid4()),
        source=source,
        source_id=source_id,
        title=title,
        summary=summary,
        url=url,
        tags=tags,
        discovered_at=_now_iso(),
        content_hash=content_hash,
    )


def _host_of(url: str) -> str:
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc or "rss"
    except Exception:
        return "rss"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


async def _save_notes(notes: Iterable[ResearchNote]) -> int:
    """Insert notes, dedupe on content_hash. Returns the number of new rows."""
    rows = list(notes)
    if not rows:
        return 0

    inserted = 0
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            for n in rows:
                try:
                    await db.execute(
                        "INSERT INTO notes (id, source, source_id, title, summary, url, tags, discovered_at, content_hash) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            n.id,
                            n.source,
                            n.source_id,
                            n.title,
                            n.summary,
                            n.url,
                            json.dumps(n.tags),
                            n.discovered_at,
                            n.content_hash,
                        ),
                    )
                    inserted += 1
                except Exception:
                    # content_hash UNIQUE violation => duplicate; skip
                    continue
            # Enforce max-notes cap by trimming oldest rows.
            cur = await db.execute("SELECT COUNT(*) FROM notes")
            total_row = await cur.fetchone()
            total = total_row[0] if total_row else 0
            if total > MAX_NOTES_TOTAL:
                delete_n = total - MAX_NOTES_TOTAL
                await db.execute(
                    "DELETE FROM notes WHERE id IN ("
                    " SELECT id FROM notes ORDER BY discovered_at ASC LIMIT ?"
                    ")",
                    (delete_n,),
                )
            await db.commit()
        return inserted

    def _sync_save() -> int:
        nonlocal inserted
        conn = sqlite3.connect(DB_PATH)
        try:
            for n in rows:
                try:
                    conn.execute(
                        "INSERT INTO notes (id, source, source_id, title, summary, url, tags, discovered_at, content_hash) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            n.id,
                            n.source,
                            n.source_id,
                            n.title,
                            n.summary,
                            n.url,
                            json.dumps(n.tags),
                            n.discovered_at,
                            n.content_hash,
                        ),
                    )
                    inserted += 1
                except Exception:
                    continue
            total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            if total > MAX_NOTES_TOTAL:
                conn.execute(
                    "DELETE FROM notes WHERE id IN ("
                    " SELECT id FROM notes ORDER BY discovered_at ASC LIMIT ?"
                    ")",
                    (total - MAX_NOTES_TOTAL,),
                )
            conn.commit()
            return inserted
        finally:
            conn.close()

    return await asyncio.to_thread(_sync_save)


async def _recent_notes(limit: int = 30) -> list[dict[str, Any]]:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM notes ORDER BY discovered_at DESC LIMIT ?", (limit,)
            )
            rows = await cur.fetchall()
            return [_row_to_note(r) for r in rows]

    def _sync() -> list[dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY discovered_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [_row_to_note(r) for r in rows]
        finally:
            conn.close()

    return await asyncio.to_thread(_sync)


def _row_to_note(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source": row["source"],
        "source_id": row["source_id"],
        "title": row["title"],
        "summary": row["summary"],
        "url": row["url"],
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "discovered_at": row["discovered_at"],
    }


async def _count_notes() -> int:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM notes")
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    def _sync() -> int:
        conn = sqlite3.connect(DB_PATH)
        try:
            return int(conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0])
        finally:
            conn.close()

    return await asyncio.to_thread(_sync)


async def _count_proposals_since(since: datetime) -> int:
    iso = since.isoformat()
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM proposals WHERE created_at >= ?", (iso,)
            )
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    def _sync() -> int:
        conn = sqlite3.connect(DB_PATH)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM proposals WHERE created_at >= ?", (iso,)
            ).fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()

    return await asyncio.to_thread(_sync)


async def _save_proposal(proposal: ProposalResponse, notification_id: str | None) -> None:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO proposals (id, title, rationale, plan, sources, created_at, notification_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    proposal.id,
                    proposal.title,
                    proposal.rationale,
                    json.dumps(proposal.plan),
                    json.dumps(proposal.sources),
                    proposal.created_at,
                    notification_id,
                ),
            )
            await db.commit()
        return

    def _sync() -> None:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                "INSERT INTO proposals (id, title, rationale, plan, sources, created_at, notification_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    proposal.id,
                    proposal.title,
                    proposal.rationale,
                    json.dumps(proposal.plan),
                    json.dumps(proposal.sources),
                    proposal.created_at,
                    notification_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_sync)


async def _record_cycle(kind: str, ok: bool, detail: str) -> None:
    now = _now_iso()
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO cycles (kind, started_at, finished_at, ok, detail) "
                "VALUES (?, ?, ?, ?, ?)",
                (kind, now, now, 1 if ok else 0, detail[:1000]),
            )
            await db.commit()
        return

    def _sync() -> None:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                "INSERT INTO cycles (kind, started_at, finished_at, ok, detail) "
                "VALUES (?, ?, ?, ?, ?)",
                (kind, now, now, 1 if ok else 0, detail[:1000]),
            )
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_sync)


async def _last_cycle_at(kind: str) -> str | None:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT finished_at FROM cycles WHERE kind = ? ORDER BY id DESC LIMIT 1",
                (kind,),
            )
            row = await cur.fetchone()
            return row[0] if row else None

    def _sync() -> str | None:
        conn = sqlite3.connect(DB_PATH)
        try:
            row = conn.execute(
                "SELECT finished_at FROM cycles WHERE kind = ? ORDER BY id DESC LIMIT 1",
                (kind,),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    return await asyncio.to_thread(_sync)


# ---------------------------------------------------------------------------
# Research cycle
# ---------------------------------------------------------------------------


async def _run_research_cycle() -> int:
    """Fetch a bounded set of new notes from all configured feeds and store
    them. Returns the number of new notes inserted."""
    feeds = _load_feeds()
    notes: list[ResearchNote] = []
    async with httpx.AsyncClient() as client:
        for category in feeds.get("arxiv", []):
            if len(notes) >= MAX_NOTES_PER_CYCLE:
                break
            notes.extend(await _fetch_arxiv(client, category))
        for url in feeds.get("rss", []):
            if len(notes) >= MAX_NOTES_PER_CYCLE:
                break
            notes.extend(await _fetch_rss(client, url))
        for language in feeds.get("github_trending_languages", []):
            if len(notes) >= MAX_NOTES_PER_CYCLE:
                break
            notes.extend(await _fetch_github_trending(client, language))

    notes = notes[:MAX_NOTES_PER_CYCLE]
    inserted = await _save_notes(notes)
    await _record_cycle(
        "research",
        ok=True,
        detail=f"fetched={len(notes)} inserted={inserted}",
    )
    logger.info("research cycle: fetched=%d inserted=%d", len(notes), inserted)
    return inserted


# ---------------------------------------------------------------------------
# Proposal synthesis
# ---------------------------------------------------------------------------


def _render_prompt(notes: list[dict[str, Any]]) -> str:
    bullet_lines = []
    for n in notes[:20]:
        tags = ",".join(n.get("tags") or [])
        bullet_lines.append(
            f"- [{n['source']}|{tags}] {n['title']}\n  {n['summary'][:400]}\n  {n['url']}"
        )
    bullets = "\n".join(bullet_lines)
    return (
        "You are Lumyn, Prady OS's deep reasoning sub-agent.\n"
        "You just received the following fresh research notes from the"
        " continuous Kryos researcher. Identify ONE concrete software"
        " project that a local autonomous agent could build over the"
        " next 1-3 days that would meaningfully help human civilization,"
        " match the latest public research, and stay well within the"
        " capabilities of a single-user desktop machine.\n\n"
        "Rules:\n"
        " 1. Propose at most ONE project.\n"
        " 2. Be specific and buildable. No vague mission statements.\n"
        " 3. No malicious or privacy-violating uses.\n"
        " 4. Cite which notes inspired the idea (by URL).\n\n"
        f"Notes:\n{bullets}\n\n"
        "Respond as JSON with keys: title (string), rationale (string, 2-4"
        " sentences), plan (list of 3-7 concrete steps), sources (list of"
        " URLs from the notes above)."
    )


async def _call_lumyn(prompt: str) -> dict[str, Any] | None:
    """Ask the model-gateway for a completion; if it returns JSON we use
    it, otherwise we bail out and skip proposal synthesis this cycle."""
    body = {
        "model": os.environ.get("LUMYN_PROPOSAL_MODEL", "llama3.2:3b"),
        "messages": [
            {"role": "system", "content": "Reply with JSON only. No prose."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 700,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{MODEL_GATEWAY_URL}/v1/chat/completions", json=body
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.info("model-gateway unreachable for proposal synthesis: %s", exc)
        return None

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None

    content = content.strip()
    if content.startswith("```"):
        # strip ``` fences if the model added them anyway
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


async def _emit_notification(proposal: ProposalResponse) -> str | None:
    body_lines = [proposal.rationale, ""]
    body_lines.append("Plan:")
    for i, step in enumerate(proposal.plan, start=1):
        body_lines.append(f"  {i}. {step}")
    if proposal.sources:
        body_lines.append("")
        body_lines.append("Sources:")
        for url in proposal.sources:
            body_lines.append(f"  - {url}")

    payload = {
        "type": "project_proposal",
        "title": proposal.title,
        "body": "\n".join(body_lines),
        "source": "kryos-researcher",
        "severity": "info",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{NOTIFICATION_BUS_URL}/notify", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("id")
    except httpx.HTTPError as exc:
        logger.info("notification-bus unreachable: %s", exc)
        return None


async def _run_proposal_cycle() -> ProposalResponse | None:
    """Budget-check, fetch recent notes, ask Lumyn for a proposal,
    persist it and emit a notification."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    used = await _count_proposals_since(since)
    if used >= DAILY_PROPOSAL_BUDGET:
        await _record_cycle(
            "proposal",
            ok=True,
            detail=f"skipped: daily budget {used}/{DAILY_PROPOSAL_BUDGET} used",
        )
        return None

    notes = await _recent_notes(limit=25)
    if len(notes) < 5:
        await _record_cycle(
            "proposal",
            ok=True,
            detail=f"skipped: only {len(notes)} notes available",
        )
        return None

    parsed = await _call_lumyn(_render_prompt(notes))
    if parsed is None:
        await _record_cycle(
            "proposal",
            ok=False,
            detail="skipped: no structured response from model-gateway",
        )
        return None

    title = str(parsed.get("title") or "").strip()
    rationale = str(parsed.get("rationale") or "").strip()
    plan = parsed.get("plan") or []
    sources = parsed.get("sources") or []
    if not title or not rationale or not isinstance(plan, list):
        await _record_cycle(
            "proposal",
            ok=False,
            detail="skipped: malformed proposal from model",
        )
        return None

    proposal = ProposalResponse(
        id=str(uuid.uuid4()),
        title=title,
        rationale=rationale,
        plan=[str(s) for s in plan][:10],
        sources=[str(s) for s in sources][:20],
        created_at=_now_iso(),
    )
    notif_id = await _emit_notification(proposal)
    await _save_proposal(proposal, notif_id)
    await _record_cycle(
        "proposal",
        ok=True,
        detail=f"new proposal id={proposal.id} notif={notif_id}",
    )
    logger.info(
        "proposal emitted: title=%r notif=%s", proposal.title, notif_id
    )
    return proposal


# ---------------------------------------------------------------------------
# Lifespan + scheduler
# ---------------------------------------------------------------------------


_scheduler: AsyncIOScheduler | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await _init_db()

    global _scheduler
    if RESEARCH_ENABLED:
        _scheduler = AsyncIOScheduler(timezone="UTC")
        _scheduler.add_job(
            _safe_research_cycle,
            "interval",
            minutes=RESEARCH_INTERVAL_MIN,
            id="research",
            next_run_time=datetime.now(timezone.utc) + timedelta(seconds=30),
        )
        _scheduler.add_job(
            _safe_proposal_cycle,
            "interval",
            minutes=PROPOSAL_INTERVAL_MIN,
            id="proposal",
            next_run_time=datetime.now(timezone.utc)
            + timedelta(minutes=max(RESEARCH_INTERVAL_MIN, 5)),
        )
        _scheduler.start()
        logger.info(
            "Kryos researcher scheduler started: research/%dm proposal/%dm",
            RESEARCH_INTERVAL_MIN,
            PROPOSAL_INTERVAL_MIN,
        )
    else:
        _scheduler = None
        logger.info(
            "Kryos researcher running with RESEARCH_ENABLED=false; "
            "REST endpoints remain available"
        )
    try:
        yield
    finally:
        if _scheduler is not None:
            try:
                _scheduler.shutdown(wait=False)
            except Exception:
                # Event loop may already be gone in test scenarios;
                # that's safe to ignore.
                pass
            _scheduler = None


async def _safe_research_cycle() -> None:
    try:
        await _run_research_cycle()
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("research cycle crashed: %s", exc)
        await _record_cycle("research", ok=False, detail=f"crash: {exc}")


async def _safe_proposal_cycle() -> None:
    try:
        await _run_proposal_cycle()
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("proposal cycle crashed: %s", exc)
        await _record_cycle("proposal", ok=False, detail=f"crash: {exc}")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


app = FastAPI(
    title="Kryos Researcher", version="1.0.0", lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "kryos-researcher",
        "version": "1.0.0",
        "enabled": RESEARCH_ENABLED,
    }


@app.get("/")
async def root() -> dict[str, Any]:
    return {"service": "kryos-researcher", "version": "1.0.0"}


@app.get("/notes", response_model=NoteListResponse)
async def list_notes(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> NoteListResponse:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            total_cur = await db.execute("SELECT COUNT(*) FROM notes")
            total_row = await total_cur.fetchone()
            total = int(total_row[0]) if total_row else 0
            cur = await db.execute(
                "SELECT * FROM notes ORDER BY discovered_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = await cur.fetchall()
            return NoteListResponse(
                notes=[_row_to_note(r) for r in rows], total=total
            )

    def _sync() -> NoteListResponse:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            total = int(
                conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            )
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY discovered_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return NoteListResponse(
                notes=[_row_to_note(r) for r in rows], total=total
            )
        finally:
            conn.close()

    return await asyncio.to_thread(_sync)


@app.get("/proposals")
async def list_proposals(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict[str, Any]]:
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM proposals ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
            return [_row_to_proposal(r) for r in rows]

    def _sync() -> list[dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM proposals ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [_row_to_proposal(r) for r in rows]
        finally:
            conn.close()

    return await asyncio.to_thread(_sync)


def _row_to_proposal(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "rationale": row["rationale"],
        "plan": json.loads(row["plan"]) if row["plan"] else [],
        "sources": json.loads(row["sources"]) if row["sources"] else [],
        "created_at": row["created_at"],
        "notification_id": row["notification_id"],
    }


@app.post("/research/run")
async def force_research_cycle() -> dict[str, Any]:
    """Manually trigger a research cycle. Useful for testing and for
    the desktop shell 'Refresh now' button."""
    inserted = await _safe_research_and_return_count()
    return {"ok": True, "inserted": inserted}


async def _safe_research_and_return_count() -> int:
    try:
        return await _run_research_cycle()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/proposal/run")
async def force_proposal_cycle() -> dict[str, Any]:
    """Manually trigger a proposal synthesis pass."""
    try:
        proposal = await _run_proposal_cycle()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if proposal is None:
        return {"ok": True, "proposal": None, "reason": "see /status"}
    return {"ok": True, "proposal": proposal.model_dump()}


@app.get("/status", response_model=ResearchStatus)
async def status() -> ResearchStatus:
    last_r = await _last_cycle_at("research")
    last_p = await _last_cycle_at("proposal")
    total_notes = await _count_notes()
    daily = await _count_proposals_since(
        datetime.now(timezone.utc) - timedelta(hours=24)
    )
    # Total proposals all time
    if aiosqlite is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM proposals")
            row = await cur.fetchone()
            total_p = int(row[0]) if row else 0
    else:
        def _sync() -> int:
            conn = sqlite3.connect(DB_PATH)
            try:
                return int(conn.execute("SELECT COUNT(*) FROM proposals").fetchone()[0])
            finally:
                conn.close()

        total_p = await asyncio.to_thread(_sync)

    next_in: int | None = None
    if _scheduler is not None:
        job = _scheduler.get_job("research")
        if job and job.next_run_time is not None:
            delta = (
                job.next_run_time - datetime.now(timezone.utc)
            ).total_seconds()
            next_in = max(int(delta), 0)

    return ResearchStatus(
        enabled=RESEARCH_ENABLED,
        last_research_at=last_r,
        last_proposal_at=last_p,
        total_notes=total_notes,
        total_proposals=total_p,
        daily_proposals_used=daily,
        next_research_in_s=next_in,
    )
