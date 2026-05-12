"""Vision Agent FastAPI service — port 8091."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from vision_agent import VisionAgent

logger = logging.getLogger(__name__)

app = FastAPI(title="Kryos Vision Agent", version="1.0.0")
_agent: Optional[VisionAgent] = None


def _get_agent() -> VisionAgent:
    global _agent
    if _agent is None:
        _agent = VisionAgent()
    return _agent


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "vision-agent", "version": "1.0.0"}


@app.get("/")
async def root() -> Dict[str, Any]:
    return {"service": "vision-agent", "version": "1.0.0"}


class DescribeRequest(BaseModel):
    prompt: Optional[str] = None


class FindElementRequest(BaseModel):
    description: str


@app.post("/capture")
async def capture() -> Dict[str, Any]:
    agent = _get_agent()
    try:
        image_bytes = agent.capture_screen_bytes()
        return {"bytes": len(image_bytes), "status": "ok"}
    except Exception as exc:  # pragma: no cover — runtime dependency
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/describe")
async def describe(_: DescribeRequest) -> Dict[str, Any]:
    agent = _get_agent()
    try:
        image = agent.capture_screen()
        description = await agent.describe_screen(image)
        return {"description": description}
    except Exception as exc:  # pragma: no cover — runtime dependency
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/find-element")
async def find_element(req: FindElementRequest) -> Dict[str, Any]:
    agent = _get_agent()
    try:
        bbox = await agent.find_element(req.description)
        return {"bbox": bbox.to_dict() if bbox else None}
    except Exception as exc:  # pragma: no cover — runtime dependency
        raise HTTPException(status_code=502, detail=str(exc)) from exc
