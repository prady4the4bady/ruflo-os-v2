from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture()
async def client() -> AsyncClient:
    service_dir = Path(__file__).resolve().parents[1]
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))

    test_config_dir = Path(__file__).resolve().parent / ".tmp-config"
    test_config_dir.mkdir(parents=True, exist_ok=True)
    os.environ["KRYOS_CONFIG_DIR"] = str(test_config_dir)

    import system_health_service

    transport = ASGITransport(app=system_health_service.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
