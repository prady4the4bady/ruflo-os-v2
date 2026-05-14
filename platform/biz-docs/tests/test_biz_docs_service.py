from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from biz_docs_service import app, generated_docs


@pytest.fixture(autouse=True)
def reset():
    generated_docs.clear()


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
async def test_generate_unknown_project_returns_404(client: AsyncClient):
    from unittest.mock import patch
    with patch("biz_docs_service.httpx.get") as mock_get:
        mock_get.return_value.status_code = 404
        resp = await client.post("/docs/generate/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_pitch_without_generate_returns_404(client: AsyncClient):
    resp = await client.get("/docs/test-123/pitch")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_metrics_without_generate_returns_404(client: AsyncClient):
    resp = await client.get("/docs/test-123/metrics")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_readme_without_generate_returns_404(client: AsyncClient):
    resp = await client.get("/docs/test-123/readme")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_pitch_includes_prady_os():
    from biz_docs_service import _generate_pitch
    pitch = await _generate_pitch({"name": "test", "test_pass_rate": 0.9, "verified": True}, {})
    assert "Prady OS" in pitch


@pytest.mark.asyncio
async def test_generate_pitch_includes_test_rate():
    from biz_docs_service import _generate_pitch
    pitch = await _generate_pitch({"name": "test", "test_pass_rate": 0.75, "verified": False}, {})
    assert "75%" in pitch or "75" in pitch


@pytest.mark.asyncio
async def test_build_metrics_has_required_keys():
    from biz_docs_service import _build_metrics
    metrics = _build_metrics({"test_pass_rate": 0.8, "verified": True})
    assert "tests_passing" in metrics
    assert "verified" in metrics
    assert "active_users" in metrics
    assert metrics["active_users"] is None


@pytest.mark.asyncio
async def test_health_returns_service_name(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.json()["service"] == "biz-docs"


@pytest.mark.asyncio
async def test_health_returns_version(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.json()["version"] == "1.0.0"
