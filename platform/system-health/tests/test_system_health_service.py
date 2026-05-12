from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health(client) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_system_about(client) -> None:
    response = await client.get("/api/system/about")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Prady OS"
    assert payload["version"]


@pytest.mark.asyncio
async def test_system_health(client) -> None:
    response = await client.get("/api/system/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert payload["checks"]["oobe"] in {"ok", "pending"}


@pytest.mark.asyncio
async def test_system_version(client) -> None:
    response = await client.get("/api/system/version")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Prady OS"
    assert payload["version"]


@pytest.mark.asyncio
async def test_first_boot_status_and_complete(client) -> None:
    before = await client.get("/api/system/first-boot-status")
    assert before.status_code == 200
    assert "complete" in before.json()

    complete = await client.post("/api/system/first-boot-complete")
    assert complete.status_code == 200
    assert complete.json()["status"] == "ok"

    after = await client.get("/api/system/first-boot-status")
    assert after.status_code == 200
    assert after.json()["complete"] is True
