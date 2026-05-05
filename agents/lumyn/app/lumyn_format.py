from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .schemas import ToolCall


TOOL_CALL_PATTERN = re.compile(r"<tool_call>(?P<payload>.*?)</tool_call>", re.DOTALL)


@dataclass
class ParsedLumynResponse:
    thought: str
    tool_call: ToolCall | None


def build_lumyn_prompt(system_text: str, user_text: str, history: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    parts.append(f"<|im_start|>system\n{system_text}\n<|im_end|>")
    for role, content in history:
        parts.append(f"<|im_start|>{role}\n{content}\n<|im_end|>")
    parts.append(f"<|im_start|>user\n{user_text}\n<|im_end|>")
    parts.append("<|im_start|>assistant")
    return "\n".join(parts)


def parse_tool_call(xml_text: str) -> ToolCall | None:
    match = TOOL_CALL_PATTERN.search(xml_text)
    if not match:
        return None

    payload = match.group("payload").strip()
    if not payload:
        return None

    data: dict[str, Any] = json.loads(payload)
    name = str(data.get("name", "")).strip()
    if not name:
        return None

    arguments = data.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}

    return ToolCall(name=name, arguments=arguments)


def strip_tool_call_block(text: str) -> str:
    return TOOL_CALL_PATTERN.sub("", text).strip()
