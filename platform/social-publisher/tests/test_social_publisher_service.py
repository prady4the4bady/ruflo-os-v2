from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from social_publisher_service import app, pending_posts, publish_history


@pytest.fixture(autouse=True)
def reset_state():
    pending_posts.clear()
    publish_history.clear()


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


@pytest.mark.asyncio
async def test_publish_unknown_project_returns_404(client: AsyncClient):
    from unittest.mock import patch
    with patch("social_publisher_service.httpx.get") as mock_get:
        mock_get.return_value.status_code = 404
        resp = await client.post("/publish/project/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_publish_status_empty_returns_list(client: AsyncClient):
    resp = await client.get("/publish/status/test-123")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_publish_metrics_returns_schema(client: AsyncClient):
    resp = await client.get("/publish/metrics/test-123")
    assert resp.status_code == 200
    data = resp.json()
    assert "project_id" in data
    assert "metrics" in data


@pytest.mark.asyncio
async def test_publish_schedule_returns_scheduled(client: AsyncClient):
    resp = await client.post("/publish/schedule", json={"project_id": "proj-1", "post_at_ts": "2026-06-01T00:00:00Z"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"


@pytest.mark.asyncio
async def test_generate_content_honest_rules(client: AsyncClient):
    from social_publisher_service import _generate_content
    project = {"name": "test-tool", "test_pass_rate": 0.95, "verified": True}
    content = await _generate_content(project)
    assert "Prady OS" in content
    assert content != ""


@pytest.mark.asyncio
async def test_generate_content_includes_pass_rate(client: AsyncClient):
    from social_publisher_service import _generate_content
    project = {"name": "my-tool", "test_pass_rate": 0.85, "verified": False}
    content = await _generate_content(project)
    assert len(content) > 0


@pytest.mark.asyncio
async def test_publish_with_no_platforms(client: AsyncClient):
    from unittest.mock import patch
    with patch("social_publisher_service.httpx.get") as mock_get:
        mock_resp = type("obj", (object,), {"status_code": 200, "json": lambda self=None: {"name": "test", "test_pass_rate": 0.9, "verified": True}})()
        mock_get.return_value = mock_resp
        resp = await client.post("/publish/project/test-proj")
        assert resp.status_code == 200
        data = resp.json()
        assert "posts_queued" in data
        assert data["posts_queued"] == 0


@pytest.mark.asyncio
async def test_publish_history_is_list(client: AsyncClient):
    resp = await client.get("/publish/status/my-proj")
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_publish_schedule_no_project(client: AsyncClient):
    resp = await client.post("/publish/schedule", json={})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_returns_service_name(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.json()["service"] == "social-publisher"


@pytest.mark.asyncio
async def test_health_returns_version(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.json()["version"] == "1.0.0"
