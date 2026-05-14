from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, _memory_store, _hit_count, _miss_count, CATEGORIES


@pytest.fixture(autouse=True)
def reset():
    for c in CATEGORIES:
        _memory_store[c].clear()


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
    assert "embedding_provider" in data


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
async def test_search_with_min_relevance(client: AsyncClient):
    await client.post("/memory/write", json={"category": "conversation", "content": "important deployment pipeline"})
    resp = await client.post("/memory/search", json={"query": "deployment", "min_relevance": 0.5})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_summarize_empty_category(client: AsyncClient):
    resp = await client.post("/memory/summarize", json={"category": "conversation"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 0 or resp.json()["count"] == "0"


@pytest.mark.asyncio
async def test_summarize_nonempty(client: AsyncClient):
    await client.post("/memory/write", json={"category": "conversation", "content": "entry one"})
    resp = await client.post("/memory/summarize", json={"category": "conversation"})
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


@pytest.mark.asyncio
async def test_consolidate(client: AsyncClient):
    for i in range(10):
        await client.post("/memory/write", json={"category": "conversation", "content": f"entry {i}"})
    resp = await client.post("/memory/consolidate", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "consolidated"


@pytest.mark.asyncio
async def test_delete_existing_entry(client: AsyncClient):
    write = await client.post("/memory/write", json={"category": "conversation", "content": "to delete"})
    eid = write.json()["entry_id"]
    resp = await client.delete(f"/memory/{eid}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(client: AsyncClient):
    resp = await client.delete("/memory/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_skills_endpoint(client: AsyncClient):
    resp = await client.get("/memory/skills")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_projects_endpoint(client: AsyncClient):
    resp = await client.get("/memory/projects")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_local_embedding_deterministic():
    from app.main import _compute_local_embedding
    v1 = _compute_local_embedding("hello world")
    v2 = _compute_local_embedding("hello world")
    assert v1 == v2
    assert len(v1) == 64


@pytest.mark.asyncio
async def test_local_embedding_differs_for_diff_text():
    from app.main import _compute_local_embedding
    v1 = _compute_local_embedding("hello world")
    v2 = _compute_local_embedding("goodbye world")
    assert v1 != v2


@pytest.mark.asyncio
async def test_score_entries_exact_match():
    from app.main import _score_entries
    entries = [{"content": "this is a deployment pipeline test"}, {"content": "unrelated note"}]
    scored = _score_entries("deployment pipeline", entries)
    assert scored[0]["relevance"] > scored[1]["relevance"]


@pytest.mark.asyncio
async def test_score_entries_empty_query():
    from app.main import _score_entries
    entries = [{"content": "any content"}]
    scored = _score_entries("", entries)
    assert scored[0]["relevance"] > 0
