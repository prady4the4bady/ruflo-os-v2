from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb

from .schemas import MemoryHit


class LumynMemory:
    def __init__(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(path))
        self._collection = self._client.get_or_create_collection("lumyn_sessions")
        self._dims = 256

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dims
        for token in text.lower().split():
            h = hashlib.sha256(token.encode("utf-8")).hexdigest()
            idx = int(h[:8], 16) % self._dims
            sign = -1.0 if int(h[8:10], 16) % 2 else 1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    def add_conversation(self, *, session_id: str, content: str, outcome: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        self._collection.upsert(
            ids=[f"{session_id}:{ts}"],
            documents=[content],
            metadatas=[{"session_id": session_id, "timestamp": ts, "outcome": outcome}],
            embeddings=[self._embed(content)],
        )

    def search(self, query: str, top_k: int = 3) -> list[MemoryHit]:
        if top_k < 1:
            top_k = 1
        out = self._collection.query(
            query_embeddings=[self._embed(query)],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        docs = (out.get("documents") or [[]])[0]
        metas = (out.get("metadatas") or [[]])[0]
        dists = (out.get("distances") or [[]])[0]

        hits: list[MemoryHit] = []
        for i, doc in enumerate(docs):
            md = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
            dist = float(dists[i]) if i < len(dists) else 1.0
            hits.append(
                MemoryHit(
                    session_id=str(md.get("session_id", "unknown")),
                    score=max(0.0, 1.0 - dist),
                    content=str(doc),
                    metadata={str(k): v for k, v in md.items()},
                )
            )
        return hits
