"""biz_docs_service.py — FastAPI service for investor-ready documentation."""
from __future__ import annotations

import io
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

VERSION = "1.0.0"
SERVICE_NAME = "biz-docs"
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

INVENTOR_ENGINE_URL = os.getenv("INVENTOR_ENGINE_URL", "http://inventor-engine:8022")
MARKET_INTEL_URL = os.getenv("MARKET_INTEL_URL", "http://market-intel:8024")
AUDIT_LOG_URL = os.getenv("AUDIT_LOG_URL", "http://audit-log:8112")
VYREX_URL = os.getenv("VYREX_URL", "http://vyrex-proxy:8105")
DATA_DIR = Path(os.getenv("DATA_DIR", "/data/biz-docs"))

generated_docs: dict[str, dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Prady OS Business Docs", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/docs/generate/{project_id}")
async def generate_docs(project_id: str) -> dict[str, Any]:
    project_resp = httpx.get(f"{INVENTOR_ENGINE_URL}/inventor/projects/{project_id}", timeout=10.0)
    if project_resp.status_code != 200:
        raise HTTPException(404, "Project not found")
    project = project_resp.json()
    market = {}
    try:
        market_resp = httpx.post(f"{MARKET_INTEL_URL}/market/analyse/{project_id}", timeout=30.0)
        if market_resp.status_code == 200:
            market = market_resp.json()
    except Exception:
        pass

    pitch = await _generate_pitch(project, market)
    metrics = _build_metrics(project)
    readme = await _enhance_readme(project)
    pitch_path = DATA_DIR / f"{project_id}_pitch.md"
    pitch_path.write_text(pitch)
    metrics_path = DATA_DIR / f"{project_id}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    result = {
        "project_id": project_id,
        "pitch_pdf_url": f"/docs/{project_id}/pitch",
        "readme_url": f"/docs/{project_id}/readme",
        "metrics_url": f"/docs/{project_id}/metrics",
        "investor_summary_url": f"/docs/{project_id}/pitch",
    }
    generated_docs[project_id] = {"pitch": pitch, "metrics": metrics, "readme": readme}
    return result


@app.get("/docs/{project_id}/pitch")
async def get_pitch(project_id: str) -> Response:
    docs = generated_docs.get(project_id)
    if not docs:
        raise HTTPException(404, "Docs not generated. POST /docs/generate/{project_id} first.")
    return Response(content=docs["pitch"], media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename={project_id}_pitch.md"})


@app.get("/docs/{project_id}/metrics")
async def get_metrics(project_id: str) -> dict[str, Any]:
    docs = generated_docs.get(project_id)
    if not docs:
        raise HTTPException(404, "Docs not generated. POST /docs/generate/{project_id} first.")
    return docs["metrics"]


@app.get("/docs/{project_id}/readme")
async def get_readme(project_id: str) -> Response:
    docs = generated_docs.get(project_id)
    if not docs:
        raise HTTPException(404, "Docs not generated. POST /docs/generate/{project_id} first.")
    return Response(content=docs["readme"], media_type="text/markdown")


async def _generate_pitch(project: dict[str, Any], market: dict[str, Any]) -> str:
    verified = project.get("verified", False)
    return f"""# {project.get('name', 'Project')} — Investor Pitch

## Problem
{project.get('name', 'This project')} addresses a verified need in the market.

## Traction
- Test pass rate: {project.get('test_pass_rate', 0) * 100:.0f}%
- Verified from cold start: {'Yes' if verified else 'No'}
- Build time: Honest estimate from automated build pipeline

## Market
- Opportunity score: {market.get('opportunity_score', 'N/A')}
- Similar projects found: {len(market.get('competitors', []))}
- {market.get('honest_assessment', 'Market data unavailable — analysis was not completed.')}

## Risk
This project was built autonomously by Prax on Prady OS.
The following risks apply:
1. Market validation is preliminary — based on public repository data only
2. No revenue has been generated
3. No user base exists beyond the automated test suite
4. {('The confidence level is experimental — expect iteration.' if not verified else 'The confidence level is high based on verified test results.')}

## Technology
Built by Prax on Prady OS (open source)
https://github.com/prady4the4bady/prady-os
"""


def _build_metrics(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "tests_passing": project.get("test_pass_rate", 0),
        "verified": bool(project.get("verified", False)),
        "build_time_hours": project.get("build_time", "unknown"),
        "github_stars": 0,
        "downloads": 0,
        "active_users": None,
        "note": "active_users is null until real usage data exists — never fabricated.",
    }


async def _enhance_readme(project: dict[str, Any]) -> str:
    return f"""# {project.get('name', 'Project')}

Built autonomously by Prax on Prady OS.

## Status
- Tests: {project.get('test_pass_rate', 0) * 100:.0f}% passing
- Verified from cold start: {'Yes' if project.get('verified') else 'No'}

## Installation
```bash
pip install {project.get('name', 'project').lower().replace(' ', '-')}
```

## Usage
See the API documentation for usage details.

## Limitations
This project was built by an autonomous AI agent.
Review the code before using in production.

## License
MIT — Built by Prax on Prady OS
"""


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}
