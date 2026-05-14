"""market_intel_service.py — FastAPI service for market opportunity analysis."""
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
SERVICE_NAME = "market-intel"
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

INVENTOR_ENGINE_URL = os.getenv("INVENTOR_ENGINE_URL", "http://inventor-engine:8022")
AUDIT_LOG_URL = os.getenv("AUDIT_LOG_URL", "http://audit-log:8112")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

analysis_cache: dict[str, dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Prady OS Market Intel", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/market/analyse/{project_id}")
async def analyse_market(project_id: str) -> dict[str, Any]:
    project_resp = httpx.get(f"{INVENTOR_ENGINE_URL}/inventor/projects/{project_id}", timeout=10.0)
    if project_resp.status_code != 200:
        raise HTTPException(404, "Project not found")
    project = project_resp.json()
    name = project.get("name", "")
    github_similar = await _search_github(name)
    npm_stats = await _check_npm(name)
    competitors = [{"name": s.get("full_name", ""), "stars": s.get("stargazers_count", 0), "description": (s.get("description") or "")[:100]} for s in github_similar[:5]]
    result = {
        "project_id": project_id,
        "project_name": name,
        "github_similar": github_similar[:5],
        "npm_downloads": npm_stats,
        "competitors": competitors,
        "opportunity_score": max(0, min(1, _compute_opportunity(project, github_similar))),
        "honest_assessment": f"Found {len(github_similar)} similar projects on GitHub. Market opportunity is preliminary — based on public repository data only.",
        "data_sources": ["GitHub search API (unauthenticated)", "npm registry API"],
        "limitations": "GitHub unauthenticated API: 10 req/min. npm stats only for published packages.",
        "analysed_ts": datetime.now(timezone.utc).isoformat(),
    }
    analysis_cache[project_id] = result
    return result


@app.get("/market/report/{project_id}")
async def market_report(project_id: str) -> dict[str, Any]:
    result = analysis_cache.get(project_id)
    if not result:
        raise HTTPException(404, "Analysis not found. POST /market/analyse/{project_id} first.")
    report = f"""# Market Analysis: {result['project_name']}

## Opportunity Score: {result['opportunity_score']:.2f}

### Competitors
| Project | Stars | Description |
|---|---|---|
"""
    for c in result["competitors"]:
        report += f"| {c['name']} | {c['stars']} | {c['description']} |\n"
    report += f"\n### Honest Assessment\n{result['honest_assessment']}\n"
    report += f"\n### Data Sources\n" + "\n".join(f"- {s}" for s in result["data_sources"])
    report += f"\n\n### Limitations\n" + "\n".join(f"- {l}" for l in result["limitations"])
    return {"report": report}


async def _search_github(query: str) -> list[dict[str, Any]]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://api.github.com/search/repositories", params={"q": query, "per_page": 10, "sort": "stars"}, headers=headers)
            if r.status_code == 200:
                return r.json().get("items", [])
    except Exception as e:
        logger.warning("GitHub search failed: %s", e)
    return []


async def _check_npm(name: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(f"https://api.npmjs.org/downloads/point/last-week/{name}")
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return {"error": "Package not found on npm or API unavailable"}


def _compute_opportunity(project: dict[str, Any], similar: list[dict[str, Any]]) -> float:
    verified = 1.0 if project.get("verified") else 0.5
    competition = max(0, 1 - len(similar) / 20)
    return round(verified * 0.6 + competition * 0.4, 2)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}
