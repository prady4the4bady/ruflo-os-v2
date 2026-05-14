from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, _memory_store, _hit_count, _miss_count


@pytest.fixture(autouse=True)
def reset():
    _memory_store["conversation"].clear()
    _memory_store["task"].clear()
    _memory_store["skill"].clear()
    _memory_store["project"].clear()
    _memory_store["summary"].clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_status_shows_store_stats(client: AsyncClient):
    resp = await client.get("/ahnis/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_entries" in data
    assert "by_category" in data


@pytest.mark.asyncio
async def test_write_and_search_memory(client: AsyncClient):
    resp = await client.post("/memory/write", json={"category": "conversation", "content": "Hello from test"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "written"

    resp = await client.post("/memory/search", json={"query": "Hello", "category": "conversation"})
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


@pytest.mark.asyncio
async def test_write_unknown_category_returns_400(client: AsyncClient):
    resp = await client.post("/memory/write", json={"category": "nonexistent", "content": "test"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_all_categories(client: AsyncClient):
    await client.post("/memory/write", json={"category": "task", "content": "deploy pipeline"})
    resp = await client.post("/memory/search", json={"query": "deploy"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_summarize_empty_category(client: AsyncClient):
    resp = await client.post("/memory/summarize", json={"category": "conversation"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 0 or resp.json()["count"] == "0"


@pytest.mark.asyncio
async def test_consolidate(client: AsyncClient):
    for i in range(10):
        await client.post("/memory/write", json={"category": "conversation", "content": f"entry {i}"})
    resp = await client.post("/memory/consolidate", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "consolidated"


@pytest.mark.asyncio
async def test_skills_endpoint(client: AsyncClient):
    resp = await client.get("/memory/skills")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_projects_endpoint(client: AsyncClient):
    resp = await client.get("/memory/projects")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
