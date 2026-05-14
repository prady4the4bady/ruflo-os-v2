from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, metrics, _retry_queue, _scheduled_actions


@pytest.fixture(autouse=True)
def reset():
    metrics.cycle_count = 0
    metrics.failures = 0
    metrics.actions_triggered = 0
    _retry_queue.clear()
    _scheduled_actions.clear()


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
    assert resp.json()["status"] == "paused"
    resp = await client.post("/neila/resume")
    assert resp.json()["status"] == "resumed"


@pytest.mark.asyncio
async def test_metrics_track_cycle(client: AsyncClient):
    metrics.cycle_count = 42
    resp = await client.get("/neila/status")
    assert resp.json()["metrics"]["cycle_count"] == 42


@pytest.mark.asyncio
async def test_enqueue_adds_to_queue(client: AsyncClient):
    resp = await client.post("/neila/enqueue", json={"task_type": "test", "target_url": "http://example.com/task", "payload": {"key": "val"}})
    assert resp.status_code == 200
    assert resp.json()["status"] == "enqueued"
    assert len(_retry_queue) == 1


@pytest.mark.asyncio
async def test_enqueue_rejects_no_target(client: AsyncClient):
    resp = await client.post("/neila/enqueue", json={"task_type": "test"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_queue_returns_list(client: AsyncClient):
    resp = await client.get("/neila/queue")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_schedule_adds_action(client: AsyncClient):
    resp = await client.post("/neila/schedule", json={"action_type": "digest", "target_url": "http://example.com/digest", "delay_minutes": 30})
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"


@pytest.mark.asyncio
async def test_scheduled_returns_list(client: AsyncClient):
    resp = await client.get("/neila/scheduled")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    metrics.cycle_count = 10
    resp = await client.get("/neila/metrics")
    assert resp.status_code == 200
    assert resp.json()["cycles_total"] == 10
    assert "last_cycle_ts" in resp.json()
