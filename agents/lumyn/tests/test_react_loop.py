from __future__ import annotations

import asyncio
import pytest

from app.react_loop import ReactEngine


class FakeGateway:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.idx = 0

    async def chat(self, *, prompt: str, model: str | None = None, temperature: float = 0.2) -> str:
        await asyncio.sleep(0)
        out = self.responses[min(self.idx, len(self.responses) - 1)]
        self.idx += 1
        return out


class FakeTools:
    def tool_schemas(self) -> list[dict]:
        return [{"name": "run_shell", "parameters": {"type": "object"}}]

    async def execute(self, name: str, args: dict) -> str:
        await asyncio.sleep(0)
        return "ok"


@pytest.mark.asyncio
async def test_react_loop_stops_on_final_answer() -> None:
    engine = ReactEngine(
        gateway=FakeGateway(["Here is the final answer."]),
        tools=FakeTools(),
        max_iterations=10,
        model_name=None,
        static_system_context="base",
    )

    res = await engine.run(
        user_message="hello",
        session_context=None,
        retrieved_memories=None,
        prior_history=[],
    )
    assert res.status == "completed"
    assert "final answer" in res.answer.lower()
    assert len(res.trace) == 1


@pytest.mark.asyncio
async def test_react_loop_hits_max_iterations_when_model_only_calls_tools() -> None:
    always_tool = '<tool_call>{"name":"run_shell","arguments":{"command":"pwd"}}</tool_call>'
    engine = ReactEngine(
        gateway=FakeGateway([always_tool, always_tool, always_tool]),
        tools=FakeTools(),
        max_iterations=2,
        model_name=None,
        static_system_context="base",
    )

    res = await engine.run(
        user_message="loop",
        session_context=None,
        retrieved_memories=None,
        prior_history=[],
    )
    assert res.status == "max_iterations"
    assert len(res.trace) == 2
    assert all(t.action == "run_shell" for t in res.trace)
