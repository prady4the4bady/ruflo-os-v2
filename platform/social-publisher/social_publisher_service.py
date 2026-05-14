"""social_publisher_service.py — FastAPI service for posting project announcements."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

VERSION = "1.0.0"
SERVICE_NAME = "social-publisher"
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

INVENTOR_ENGINE_URL = os.getenv("INVENTOR_ENGINE_URL", "http://inventor-engine:8022")
AUDIT_LOG_URL = os.getenv("AUDIT_LOG_URL", "http://audit-log:8112")
VYREX_URL = os.getenv("VYREX_URL", "http://vyrex-proxy:8105")

pending_posts: dict[str, list[dict[str, Any]]] = {}
publish_history: dict[str, list[dict[str, Any]]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Prady OS Social Publisher", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/publish/project/{project_id}")
async def publish_project(project_id: str) -> dict[str, Any]:
    project_resp = httpx.get(f"{INVENTOR_ENGINE_URL}/inventor/projects/{project_id}", timeout=10.0)
    if project_resp.status_code != 200:
        raise HTTPException(404, "Project not found")
    project = project_resp.json()

    content = await _generate_content(project)
    platforms = []
    if os.getenv("TWITTER_BEARER_TOKEN"):
        platforms.append("twitter")
    if os.getenv("REDDIT_CLIENT_ID"):
        platforms.append("reddit")
    if os.getenv("PRODUCTHUNT_API_KEY"):
        platforms.append("producthunt")

    post_record = {"project_id": project_id, "content": content, "platforms": platforms, "status": "queued", "created_ts": datetime.now(timezone.utc).isoformat()}
    if project_id not in pending_posts:
        pending_posts[project_id] = []
    pending_posts[project_id].append(post_record)
    if project_id not in publish_history:
        publish_history[project_id] = []
    publish_history[project_id].append(post_record)
    return {"posts_queued": len(platforms), "platforms": platforms, "project_id": project_id}


@app.get("/publish/status/{project_id}")
async def publish_status(project_id: str) -> list[dict[str, Any]]:
    return publish_history.get(project_id, [])


@app.get("/publish/metrics/{project_id}")
async def publish_metrics(project_id: str) -> dict[str, Any]:
    return {"project_id": project_id, "metrics": {}, "note": "Real metrics require platform API credentials and posting history"}


@app.post("/publish/schedule")
async def publish_schedule(body: dict[str, Any]) -> dict[str, str]:
    return {"status": "scheduled", "project_id": body.get("project_id", ""), "scheduled_ts": body.get("post_at_ts", "")}


async def _generate_content(project: dict[str, Any]) -> str:
    prompt = f"""Generate an honest social media post about this project:

Name: {project.get('name', 'Unknown')}
Test pass rate: {project.get('test_pass_rate', 0)}
Verified: {'yes' if project.get('verified') else 'no'}

Rules:
- Never claim the project is revolutionary or #1
- Always include: 'Built by Prax on Prady OS (open source)'
- Include the actual test pass rate
- Never inflate numbers
- If confidence is experimental, say so
- Keep under 280 characters"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(
                f"{VYREX_URL}/v1/chat/completions",
                json={"model": "active", "messages": [{"role": "system", "content": "You write honest project announcements."}, {"role": "user", "content": prompt}], "max_tokens": 200, "temperature": 0.3},
            )
            return r.json()["choices"][0]["message"]["content"][:500]
    except Exception as e:
        logger.warning("Content generation failed: %s", e)
        return f"Built by Prax on Prady OS (open source) — {project.get('name', 'Unknown')} — Tests: {project.get('test_pass_rate', 0)*100:.0f}% passing"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}
