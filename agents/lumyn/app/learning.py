from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model_gateway import GatewayClient
from .schemas import SessionRecord


def is_failed_session(session: SessionRecord) -> bool:
    for turn in session.turns:
        if turn.status in {"max_iterations", "error"}:
            return True
        if "that was wrong" in turn.user.lower():
            return True
        if any(step.error for step in turn.trace):
            return True
    return False


def build_reflection_prompt(failed_sessions: list[SessionRecord]) -> str:
    compact = []
    for s in failed_sessions:
        compact.append(
            {
                "session_id": s.session_id,
                "turns": [
                    {
                        "user": t.user,
                        "assistant": t.assistant,
                        "status": t.status,
                        "errors": [tr.error for tr in t.trace if tr.error],
                    }
                    for t in s.turns
                ],
            }
        )

    return (
        "<|im_start|>system\n"
        "You are Lumyn self-improvement critic. Analyze failures and propose concrete strategy updates. "
        "Return strict JSON list with objects: {\"suggestion\": string, \"approved\": bool}.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        f"Failed sessions in last 24h:\n{json.dumps(compact, ensure_ascii=True)}\n"
        "<|im_end|>\n"
        "<|im_start|>assistant"
    )


async def run_nightly_reflection(
    *,
    sessions: list[SessionRecord],
    gateway: GatewayClient,
    learnings_file: Path,
) -> int:
    failed = [s for s in sessions if is_failed_session(s)]
    if not failed:
        return 0

    prompt = build_reflection_prompt(failed)
    content = await gateway.chat(prompt=prompt)
    data: list[dict[str, Any]] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return 0

    await asyncio.to_thread(learnings_file.parent.mkdir, parents=True, exist_ok=True)
    added = 0
    lines: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        suggestion = str(item.get("suggestion", "")).strip()
        approved = bool(item.get("approved", False))
        if not suggestion or not approved:
            continue
        rec = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "suggestion": suggestion,
        }
        lines.append(json.dumps(rec, ensure_ascii=True) + "\n")
        added += 1

    if lines:
        await asyncio.to_thread(_append_lines, learnings_file, lines)
    return added


def _append_lines(path: Path, lines: list[str]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.writelines(lines)


def load_learnings(path: Path) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        suggestion = str(obj.get("suggestion", "")).strip()
        if suggestion:
            out.append(suggestion)
    return out
