"""
Shared fixtures for screen-agent tests.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    """Synchronous HTTPX test client wired to a fresh FastAPI instance."""
    return TestClient(create_app())
