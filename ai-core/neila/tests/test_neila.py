from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, metrics


@pytest.fixture(autouse=True)
def reset():
    metrics.cycle_count = 0
    metrics.failures = 0
    metrics.actions_triggered = 0


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["service"] == "neila"


@pytest.mark.asyncio
async def test_status_returns_metrics(client: AsyncClient):
    resp = await client.get("/neila/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "paused" in data
    assert "loop_active" in data
    assert "metrics" in data


@pytest.mark.asyncio
async def test_pause_resume(client: AsyncClient):
    resp = await client.post("/neila/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"

    resp = await client.post("/neila/resume")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resumed"


@pytest.mark.asyncio
async def test_metrics_track_cycle(client: AsyncClient):
    metrics.cycle_count = 42
    resp = await client.get("/neila/status")
    assert resp.json()["metrics"]["cycle_count"] == 42
