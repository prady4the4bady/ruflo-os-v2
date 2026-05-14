from __future__ import annotations

import os
import pytest
from httpx import ASGITransport, AsyncClient

from system_organizer_service import app, scans, NEVER_PATHS


@pytest.fixture(autouse=True)
def reset():
    scans.clear()


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
async def test_status_returns_schema(client: AsyncClient):
    resp = await client.get("/organizer/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "last_scan_ts" in data
    assert "duplicates_found" in data
    assert "space_wasted_mb" in data


@pytest.mark.asyncio
async def test_scan_returns_scan_id(client: AsyncClient):
    resp = await client.post("/organizer/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert "scan_id" in data
    assert data["status"] == "started"


@pytest.mark.asyncio
async def test_scan_result_unknown_returns_404(client: AsyncClient):
    resp = await client.get("/organizer/scan/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_apply_unknown_suggestion_returns_404(client: AsyncClient):
    resp = await client.post("/organizer/apply/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_archive_unknown_project_returns_404(client: AsyncClient):
    resp = await client.post("/organizer/archive/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_never_paths_not_empty():
    assert len(NEVER_PATHS) > 0
    assert all(p.startswith("/") for p in NEVER_PATHS)


@pytest.mark.asyncio
async def test_is_safe_scan_path():
    from system_organizer_service import _is_safe_scan_path
    from pathlib import Path, PureWindowsPath
    if os.name == "nt":
        assert True
        return
    assert not _is_safe_scan_path(Path("/etc/passwd"))
    assert not _is_safe_scan_path(Path("/boot/vmlinuz"))
    assert not _is_safe_scan_path(Path("/proc/cpuinfo"))
    assert _is_safe_scan_path(Path("/var/prady/projects/test"))


@pytest.mark.asyncio
async def test_scan_result_has_required_keys(client: AsyncClient):
    scans["test-scan"] = {"status": "complete", "scan_ts": "", "duplicates": [], "space_wasted_mb": 0, "suggestions": [], "total_files_scanned": 0, "total_size_mb": 0}
    resp = await client.get("/organizer/scan/test-scan")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "duplicates" in data


@pytest.mark.asyncio
async def test_health_returns_service_name(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.json()["service"] == "system-organizer"
