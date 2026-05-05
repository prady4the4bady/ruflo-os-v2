from __future__ import annotations

import json
from typing import Any

from .lumyn_format import build_lumyn_prompt, parse_tool_call, strip_tool_call_block
from .model_gateway import GatewayClient
from .schemas import ChatResponse, ToolTrace
from .tooling import LumynTools


def _tool_response_block(name: str, response: str) -> str:
    payload = {"name": name, "response": response}
    return f"<tool_response>{json.dumps(payload, ensure_ascii=True)}</tool_response>"


class ReactEngine:
    def __init__(
        self,
        *,
        gateway: GatewayClient,
        tools: LumynTools,
        max_iterations: int,
        model_name: str | None,
        static_system_context: str,
    ) -> None:
        self.gateway = gateway
        self.tools = tools
        self.max_iterations = max_iterations
        self.model_name = model_name
        self.static_system_context = static_system_context

    async def run(
        self,
        *,
        user_message: str,
        session_context: dict[str, Any] | None,
        retrieved_memories: list[str] | None,
        prior_history: list[tuple[str, str]],
    ) -> ChatResponse:
        traces: list[ToolTrace] = []
        history = list(prior_history)

        tools_json = json.dumps(self.tools.tool_schemas(), ensure_ascii=True)
        mem_text = "\n".join(retrieved_memories or [])
        ctx_text = json.dumps(session_context or {}, ensure_ascii=True)

        system_text = (
            f"{self.static_system_context}\n"
            "You are Lumyn. Follow ReAct.\n"
            "When using a tool, respond with exactly one <tool_call>{json}</tool_call> block.\n"
            "Available tools JSON schema:\n"
            f"{tools_json}\n"
            "Prior similar sessions:\n"
            f"{mem_text}\n"
            "Session context:\n"
            f"{ctx_text}"
        )

        for iteration in range(1, self.max_iterations + 1):
            prompt = build_lumyn_prompt(system_text=system_text, user_text=user_message, history=history)
            assistant = await self.gateway.chat(prompt=prompt, model=self.model_name)

            thought = strip_tool_call_block(assistant)
            tool_call = parse_tool_call(assistant)
            if tool_call is None:
                traces.append(ToolTrace(iteration=iteration, thought=thought or "Final answer produced."))
                return ChatResponse(
                    session_id="",
                    answer=thought or assistant,
                    status="completed",
                    trace=traces,
                )

            trace = ToolTrace(
                iteration=iteration,
                thought=thought or "Tool selected",
                action=tool_call.name,
                action_input=tool_call.arguments,
            )
            try:
                result = await self.tools.execute(tool_call.name, tool_call.arguments)
                trace.observation = result
                history.append(("assistant", assistant))
                history.append(("user", _tool_response_block(tool_call.name, result)))
            except Exception as exc:  # noqa: BLE001
                trace.error = str(exc)
                history.append(("assistant", assistant))
                history.append(("user", _tool_response_block(tool_call.name, f"ERROR: {exc}")))
            traces.append(trace)

        return ChatResponse(
            session_id="",
            answer="I reached the maximum reasoning iterations before a final answer.",
            status="max_iterations",
            trace=traces,
        )
