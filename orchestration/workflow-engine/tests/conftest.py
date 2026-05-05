"""Shared pytest fixtures for the orchestration engine test suite."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import fakeredis.aioredis as fake_aioredis
import pytest

from app.activity_log import ActivityLogger
from app.approvals import ApprovalStore
from app.bus import MessageBus
from app.conductor import Conductor


@pytest.fixture()
def log_dir(tmp_path: Path) -> Path:
    d = tmp_path / "logs"
    d.mkdir()
    return d


@pytest.fixture()
def activity(log_dir: Path) -> ActivityLogger:
    return ActivityLogger(log_dir)


@pytest.fixture()
def approvals() -> ApprovalStore:
    return ApprovalStore()


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture()
async def fake_bus() -> MessageBus:
    """MessageBus backed by an in-process fakeredis server."""
    server = fakeredis.FakeServer()
    bus = MessageBus.__new__(MessageBus)
    bus._redis_url = "redis://localhost:6379"
    bus._client = fake_aioredis.FakeRedis(server=server, decode_responses=True)
    return bus


@pytest.fixture()
def conductor(fake_bus: MessageBus, approvals: ApprovalStore, activity: ActivityLogger) -> Conductor:
    return Conductor(
        bus=fake_bus,
        approvals=approvals,
        activity=activity,
        gateway_url="http://localhost:11430",
        playwright_runner_url="http://localhost:11432",
        gateway_model="test-model",
        approval_timeout=5.0,
    )
