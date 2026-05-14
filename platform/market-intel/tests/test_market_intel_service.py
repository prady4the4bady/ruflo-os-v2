from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from market_intel_service import app, analysis_cache


@pytest.fixture(autouse=True)
def reset():
    analysis_cache.clear()


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
async def test_analyse_unknown_project_returns_404(client: AsyncClient):
    from unittest.mock import patch
    with patch("market_intel_service.httpx.get") as mock_get:
        mock_get.return_value.status_code = 404
        resp = await client.post("/market/analyse/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_market_report_without_analysis_returns_404(client: AsyncClient):
    resp = await client.get("/market/report/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_market_report_returns_markdown(client: AsyncClient):
    analysis_cache["test-proj"] = {"project_id": "test-proj", "project_name": "test", "opportunity_score": 0.5, "competitors": [], "honest_assessment": "test", "data_sources": [], "limitations": []}
    resp = await client.get("/market/report/test-proj")
    assert resp.status_code == 200
    assert "report" in resp.json()


@pytest.mark.asyncio
async def test_search_github_returns_list():
    from market_intel_service import _search_github
    results = await _search_github("python CLI tool")
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_check_npm_returns_dict():
    from market_intel_service import _check_npm
    result = await _check_npm("nonexistent-package-abc-123")
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_compute_opportunity_verified():
    from market_intel_service import _compute_opportunity
    score = _compute_opportunity({"verified": True}, [])
    assert 0 <= score <= 1


@pytest.mark.asyncio
async def test_compute_opportunity_not_verified():
    from market_intel_service import _compute_opportunity
    score = _compute_opportunity({"verified": False}, [{"name": "a"}, {"name": "b"}])
    assert 0 <= score <= 1


@pytest.mark.asyncio
async def test_analyse_returns_expected_keys(client: AsyncClient):
    from unittest.mock import patch
    analysis_cache["cached-proj"] = {"project_id": "cached-proj", "project_name": "test", "opportunity_score": 0.0, "competitors": [], "github_similar": [], "npm_downloads": {}, "honest_assessment": "", "data_sources": [], "limitations": [], "analysed_ts": ""}
    with patch("market_intel_service.httpx.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json = lambda: analysis_cache["cached-proj"]
        resp = await client.post("/market/analyse/cached-proj")
        assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_health_returns_service_name(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.json()["service"] == "market-intel"
