"""Tests for conductor goal decomposition."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx
import httpx

from app.activity_log import ActivityLogger
from app.approvals import ApprovalStore
from app.conductor import Conductor

pytestmark = pytest.mark.anyio


@pytest.fixture()
def conductor_no_bus(activity: ActivityLogger, approvals: ApprovalStore) -> Conductor:
    bus = MagicMock()
    bus.publish = AsyncMock(return_value="0-0")
    return Conductor(
        bus=bus,
        approvals=approvals,
        activity=activity,
        gateway_url="http://gateway",
        playwright_runner_url="http://playwright-runner",
        gateway_model="test-model",
        approval_timeout=5.0,
    )


def _mock_gateway_response(items: list, respx_mock) -> None:
    content = json.dumps(items)
    respx_mock.post("http://gateway/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": content}}
                ]
            },
        )
    )


async def test_valid_json_array_produces_subtasks(conductor_no_bus: Conductor):
    items = [
        {"agent_type": "shell", "action": "run", "params": {"command": "ls"}, "depends_on": []},
        {"agent_type": "file", "action": "write", "params": {"path": "/tmp/out.txt", "content": "done"}, "depends_on": [0]},
    ]
    with respx.mock:
        _mock_gateway_response(items, respx)
        subtasks = await conductor_no_bus._decompose("list files and save", "task-1")

    assert len(subtasks) == 2
    assert subtasks[0].agent_type == "shell"
    assert subtasks[0].action == "run"
    assert subtasks[0].depends_on == []
    # subtasks[1] must depend on subtasks[0]'s real UUID
    assert subtasks[1].depends_on == [subtasks[0].subtask_id]


async def test_gateway_failure_produces_fallback(conductor_no_bus: Conductor):
    with respx.mock:
        respx.post("http://gateway/v1/chat/completions").mock(
            return_value=httpx.Response(500, text="error")
        )
        subtasks = await conductor_no_bus._decompose("do something", "task-2")

    assert len(subtasks) == 1
    assert subtasks[0].agent_type == "research"


async def test_invalid_json_produces_fallback(conductor_no_bus: Conductor):
    with respx.mock:
        respx.post("http://gateway/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "not json at all"}}]},
            )
        )
        subtasks = await conductor_no_bus._decompose("invalid goal", "task-3")

    assert len(subtasks) == 1
    assert subtasks[0].agent_type == "research"


async def test_json_embedded_in_prose_is_extracted(conductor_no_bus: Conductor):
    prose_with_json = (
        'Sure! Here is the plan:\n'
        '[{"agent_type": "browser", "action": "search", '
        '"params": {"query": "hello"}, "depends_on": []}]\n'
        'Let me know if you need changes.'
    )
    with respx.mock:
        respx.post("http://gateway/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": prose_with_json}}]},
            )
        )
        subtasks = await conductor_no_bus._decompose("search for hello", "task-4")

    assert len(subtasks) == 1
    assert subtasks[0].agent_type == "browser"
    assert subtasks[0].action == "search"


async def test_independent_subtasks_have_no_deps(conductor_no_bus: Conductor):
    items = [
        {"agent_type": "shell", "action": "run", "params": {"command": "date"}, "depends_on": []},
        {"agent_type": "shell", "action": "run", "params": {"command": "uname"}, "depends_on": []},
    ]
    with respx.mock:
        _mock_gateway_response(items, respx)
        subtasks = await conductor_no_bus._decompose("check system", "task-5")

    assert all(len(st.depends_on) == 0 for st in subtasks)


async def test_parse_json_array_direct():
    assert Conductor._parse_json_array("[1, 2]") == [1, 2]
    assert Conductor._parse_json_array("not json") is None
    assert Conductor._parse_json_array('prefix [{"a": 1}] suffix') == [{"a": 1}]
