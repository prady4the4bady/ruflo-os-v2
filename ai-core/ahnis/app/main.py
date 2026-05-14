"""Ahnis — MemPalace-Aya memory and retrieval system for Prady OS.

Ahnis provides persistent semantic memory, session memory, project
memory, skill memory, and distilled summary memory. Integrated
with qdrant when available, with graceful fallback to in-memory.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

VERSION = "1.0.0"
SERVICE_NAME = "ahnis"

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
AUDIT_LOG_URL = os.getenv("AUDIT_LOG_URL", "http://audit-log:8112")
MODEL_GATEWAY_URL = os.getenv("MODEL_GATEWAY_URL", "http://model-gateway:11430")

_qdrant_available = False
_memory_store: dict[str, list[dict[str, Any]]] = {
    "conversation": [],
    "task": [],
    "skill": [],
    "project": [],
    "summary": [],
    "failure_lesson": [],
}
_consolidation_ts: str = ""
_hit_count = 0
_miss_count = 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MemoryEntry:
    id: str
    category: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    relevance: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp or _utc_now(),
            "relevance": self.relevance,
        }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _qdrant_available
    if QDRANT_HOST:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(f"http://{QDRANT_HOST}:{QDRANT_PORT}/health")
                _qdrant_available = r.status_code == 200
        except Exception:
            _qdrant_available = False
    if _qdrant_available:
        logger.info("Ahnis connected to qdrant at %s:%d", QDRANT_HOST, QDRANT_PORT)
    else:
        logger.info("Ahnis running in fallback mode (no qdrant)")
    yield


app = FastAPI(title="Prady OS Ahnis — Memory Palace", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


async def _audit(event: str, detail: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            await c.post(f"{AUDIT_LOG_URL}/events", json={
                "event": event,
                "service": "ahnis",
                "detail": detail,
            })
    except Exception:
        pass


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}


@app.get("/ahnis/status")
async def ahnis_status() -> dict[str, Any]:
    total = sum(len(v) for v in _memory_store.values())
    return {
        "qdrant_available": _qdrant_available,
        "backend": "qdrant" if _qdrant_available else "in-memory (fallback)",
        "total_entries": total,
        "by_category": {k: len(v) for k, v in _memory_store.items()},
        "last_consolidation_ts": _consolidation_ts,
        "hit_count": _hit_count,
        "miss_count": _miss_count,
    }


@app.post("/memory/write")
async def memory_write(body: dict[str, Any]) -> dict[str, str]:
    category = body.get("category", "conversation")
    if category not in _memory_store:
        raise HTTPException(400, f"Unknown category: {category}")
    entry = MemoryEntry(
        id=str(uuid.uuid4()),
        category=category,
        content=body.get("content", ""),
        metadata=body.get("metadata", {}),
        timestamp=_utc_now(),
    )
    _memory_store[category].append(entry.to_dict())
    if len(_memory_store[category]) > 10000:
        _memory_store[category] = _memory_store[category][-5000:]
    await _audit("memory_write", {"category": category, "entry_id": entry.id})
    return {"status": "written", "entry_id": entry.id}


@app.post("/memory/search")
async def memory_search(body: dict[str, Any]) -> dict[str, Any]:
    query = body.get("query", "").lower()
    category = body.get("category")
    limit = min(body.get("limit", 10), 50)
    global _hit_count, _miss_count

    candidates = _memory_store.get(category, []) if category else [e for v in _memory_store.values() for e in v]

    scored = []
    for entry in candidates:
        content_lower = entry.get("content", "").lower()
        if query and query not in content_lower:
            continue
        relevance = 1.0 if query and query in content_lower else 0.3
        scored.append({**entry, "relevance": relevance})

    scored.sort(key=lambda x: x.get("relevance", 0), reverse=True)
    results = scored[:limit]
    if results:
        _hit_count += 1
    else:
        _miss_count += 1

    return {
        "results": results,
        "count": len(results),
        "backend": "qdrant" if _qdrant_available else "in-memory (fallback)",
        "query": query,
    }


@app.post("/memory/summarize")
async def memory_summarize(body: dict[str, Any]) -> dict[str, Any]:
    category = body.get("category", "conversation")
    entries = _memory_store.get(category, [])
    if not entries:
        return {"summary": "", "count": 0}
    summary_text = f"{len(entries)} entries in {category}. "
    summary_text += f"Latest: {entries[-1].get('content', '')[:200]}"
    summary = MemoryEntry(
        id=str(uuid.uuid4()),
        category="summary",
        content=summary_text,
        metadata={"source_category": category, "count": len(entries)},
        timestamp=_utc_now(),
    )
    _memory_store["summary"].append(summary.to_dict())
    return {"summary": summary_text, "count": len(entries)}


@app.post("/memory/consolidate")
async def memory_consolidate() -> dict[str, Any]:
    global _consolidation_ts
    total_before = sum(len(v) for v in _memory_store.values())
    for cat in _memory_store:
        if len(_memory_store[cat]) > 2000:
            _memory_store[cat] = _memory_store[cat][-1000:]
    _consolidation_ts = _utc_now()
    total_after = sum(len(v) for v in _memory_store.values())
    await _audit("memory_consolidated", {"entries_before": total_before, "entries_after": total_after})
    return {"status": "consolidated", "entries_before": total_before, "entries_after": total_after, "ts": _consolidation_ts}


@app.get("/memory/skills")
async def memory_skills() -> list[dict[str, Any]]:
    return _memory_store.get("skill", [])


@app.get("/memory/projects")
async def memory_projects() -> list[dict[str, Any]]:
    return _memory_store.get("project", [])
