"""Ahnis — MemPalace-Aya memory and retrieval system for Prady OS.

Pluggable semantic memory with local embedding fallback.
Categories: conversation, task, skill, project, summary, failure_lesson.
Qdrant integration when available; in-memory fallback always works.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

VERSION = "1.0.0"
SERVICE_NAME = "ahnis"

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
AUDIT_URL = os.getenv("AUDIT_LOG_URL", "http://audit-log:8112")

# --- Memory Categories ---
CATEGORIES = {"conversation", "task", "skill", "project", "summary", "failure_lesson"}

# --- Scoring weights for retrieval ---
SCORE_EXACT_MATCH = 1.0
SCORE_TOKEN_OVERLAP = 0.7
SCORE_FUZZY = 0.4
SCORE_FALLBACK = 0.1

_qdrant_available = False
_memory_store: dict[str, list[dict[str, Any]]] = {c: [] for c in CATEGORIES}
_consolidation_ts: str = ""
_hit_count = 0
_miss_count = 0
_embedding_dim = 0


@dataclass
class MemoryEntry:
    id: str
    category: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    relevance: float = 0.0
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp or _utc_now(),
            "relevance": round(self.relevance, 4),
        }


class WriteRequest(BaseModel):
    category: str = "conversation"
    content: str = ""
    metadata: dict[str, Any] = {}


class SearchRequest(BaseModel):
    query: str = ""
    category: str | None = None
    limit: int = 10
    min_relevance: float = 0.0
    include_embeddings: bool = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _audit(event: str, detail: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            await c.post(f"{AUDIT_URL}/events", json={"event": event, "service": "ahnis", "detail": detail})
    except Exception:
        pass


def _compute_local_embedding(text: str) -> list[float]:
    """Deterministic local embedding using hash-based token projection."""
    tokens = re.findall(r'\w+', text.lower())
    dim = 64
    vec = [0.0] * dim
    if not tokens:
        return vec
    for token in tokens:
        h = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16)
        for i in range(dim):
            vec[i] += (1.0 if (h >> (i % 32)) & 1 else -1.0)
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _score_entries(query: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not query:
        return [{**e, "relevance": SCORE_FALLBACK} for e in entries]
    q_terms = set(re.findall(r'\w+', query.lower()))
    scored = []
    for entry in entries:
        content = entry.get("content", "")
        content_lower = content.lower()
        # Exact substring match
        if query.lower() in content_lower:
            score = SCORE_EXACT_MATCH
        else:
            c_terms = set(re.findall(r'\w+', content_lower))
            if q_terms and c_terms:
                overlap = len(q_terms & c_terms)
                ratio = overlap / max(len(q_terms), 1)
                score = SCORE_TOKEN_OVERLAP * ratio
            else:
                score = SCORE_FALLBACK
        if score < SCORE_FUZZY and query.lower()[:3] in content_lower:
            score = SCORE_FUZZY
        scored.append({**entry, "relevance": round(min(score, 1.0), 4)})
    scored.sort(key=lambda x: x.get("relevance", 0), reverse=True)
    return scored


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _qdrant_available, _embedding_dim
    if QDRANT_HOST:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(f"http://{QDRANT_HOST}:{QDRANT_PORT}/health")
                _qdrant_available = r.status_code == 200
        except Exception:
            _qdrant_available = False
    if _qdrant_available:
        logger.info("Ahnis connected to qdrant at %s:%d with %d-dim embeddings", QDRANT_HOST, QDRANT_PORT, _embedding_dim or 64)
    else:
        logger.info("Ahnis running in local-embedding fallback mode (no qdrant)")
    yield


app = FastAPI(title="Prady OS Ahnis — Memory Palace", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}


@app.get("/ahnis/status")
async def ahnis_status() -> dict[str, Any]:
    total = sum(len(v) for v in _memory_store.values())
    return {
        "qdrant_available": _qdrant_available,
        "backend": "qdrant" if _qdrant_available else "in-memory (local embeddings)",
        "total_entries": total,
        "by_category": {k: len(v) for k, v in _memory_store.items()},
        "last_consolidation_ts": _consolidation_ts,
        "hit_count": _hit_count,
        "miss_count": _miss_count,
        "embedding_dim": _embedding_dim or 64,
        "embedding_provider": "local" if not _qdrant_available else "qdrant",
    }


@app.post("/memory/write")
async def memory_write(req: WriteRequest) -> dict[str, str]:
    if req.category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category: {req.category}. Valid: {sorted(CATEGORIES)}")
    emb = _compute_local_embedding(req.content) if not _qdrant_available else None
    entry = MemoryEntry(
        id=str(uuid.uuid4()),
        category=req.category,
        content=req.content,
        metadata=req.metadata,
        timestamp=_utc_now(),
        embedding=emb,
    )
    _memory_store[req.category].append(entry.to_dict())
    cap = 10000
    if len(_memory_store[req.category]) > cap:
        _memory_store[req.category] = _memory_store[req.category][-5000:]
    await _audit("memory_write", {"category": req.category, "entry_id": entry.id, "content_length": len(req.content)})
    return {"status": "written", "entry_id": entry.id}


@app.post("/memory/search")
async def memory_search(req: SearchRequest) -> dict[str, Any]:
    global _hit_count, _miss_count
    candidates = _memory_store.get(req.category, []) if req.category else [e for v in _memory_store.values() for e in v]
    scored = _score_entries(req.query, candidates)
    if req.min_relevance > 0:
        scored = [e for e in scored if e.get("relevance", 0) >= req.min_relevance]
    results = scored[:max(1, min(req.limit, 50))]
    if not req.include_embeddings:
        for r in results:
            r.pop("embedding", None)
    if results:
        _hit_count += 1
    else:
        _miss_count += 1
    return {"results": results, "count": len(results), "backend": "qdrant" if _qdrant_available else "in-memory (local embeddings)", "query": req.query}


@app.post("/memory/summarize")
async def memory_summarize(body: dict[str, Any]) -> dict[str, Any]:
    category = body.get("category", "conversation")
    entries = _memory_store.get(category, [])
    if not entries:
        return {"summary": "", "count": 0}
    summary_text = f"{len(entries)} entries in {category}. Latest: {entries[-1].get('content', '')[:300]}"
    summary_entry = MemoryEntry(id=str(uuid.uuid4()), category="summary", content=summary_text, metadata={"source_category": category, "count": len(entries)}, timestamp=_utc_now())
    _memory_store["summary"].append(summary_entry.to_dict())
    return {"summary": summary_text, "count": len(entries)}


@app.post("/memory/consolidate")
async def memory_consolidate() -> dict[str, Any]:
    global _consolidation_ts
    total_before = sum(len(v) for v in _memory_store.values())
    for cat in CATEGORIES:
        if len(_memory_store[cat]) > 2000:
            _memory_store[cat] = _memory_store[cat][-1000:]
    _consolidation_ts = _utc_now()
    total_after = sum(len(v) for v in _memory_store.values())
    await _audit("memory_consolidated", {"entries_before": total_before, "entries_after": total_after})
    return {"status": "consolidated", "entries_before": total_before, "entries_after": total_after, "ts": _consolidation_ts}


@app.delete("/memory/{entry_id}")
async def memory_delete(entry_id: str) -> dict[str, str]:
    for cat in CATEGORIES:
        before = len(_memory_store[cat])
        _memory_store[cat] = [e for e in _memory_store[cat] if e.get("id") != entry_id]
        if len(_memory_store[cat]) < before:
            await _audit("memory_deleted", {"category": cat, "entry_id": entry_id})
            return {"status": "deleted", "entry_id": entry_id}
    raise HTTPException(404, f"Entry {entry_id} not found")


@app.get("/memory/skills")
async def memory_skills() -> list[dict[str, Any]]:
    return _memory_store.get("skill", [])


@app.get("/memory/projects")
async def memory_projects() -> list[dict[str, Any]]:
    return _memory_store.get("project", [])
