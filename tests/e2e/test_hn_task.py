from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

ORCHESTRATION_BASE = os.getenv("ORCHESTRATION_BASE_URL", "http://127.0.0.1:11431")
ACTIVITY_LOG_PATH = Path(
    os.getenv("E2E_ACTIVITY_LOG", "orchestration/workflow-engine/logs/activity.jsonl")
)
DESKTOP_OUTPUT = Path.home() / "Desktop" / "top-story.txt"


def _read_activity_events(task_id: str) -> List[Dict[str, Any]]:
    if not ACTIVITY_LOG_PATH.exists():
        return []
    events: List[Dict[str, Any]] = []
    for line in ACTIVITY_LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("task_id") == task_id:
            events.append(event)
    return events


def _wait_for_task(task_id: str, timeout_seconds: int = 180) -> Dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_payload: Dict[str, Any] = {}

    while time.time() < deadline:
        resp = requests.get(f"{ORCHESTRATION_BASE}/tasks/{task_id}", timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        last_payload = payload
        if payload.get("status") in {"completed", "failed"}:
            return payload
        time.sleep(1.0)

    raise TimeoutError(f"Task {task_id} did not finish in {timeout_seconds}s. Last state: {last_payload}")


def test_hn_top_story_goal_end_to_end() -> None:
    DESKTOP_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if DESKTOP_OUTPUT.exists():
        DESKTOP_OUTPUT.unlink()

    goal = (
        "Open news.ycombinator.com, extract the top story title, and save it to "
        "~/Desktop/top-story.txt"
    )

    create_resp = requests.post(
        f"{ORCHESTRATION_BASE}/tasks",
        json={"goal": goal, "policy": "default"},
        timeout=30,
    )
    create_resp.raise_for_status()
    created = create_resp.json()
    task_id = created["task_id"]

    final = _wait_for_task(task_id)
    activity_events = _read_activity_events(task_id)

    print("\n=== E2E ACTIVITY TRACE ===")
    for event in activity_events:
        print(json.dumps(event, ensure_ascii=True))

    assert final.get("status") == "completed", f"Task failed. Final payload: {final}"

    subtasks = final.get("subtasks", [])
    assert len(subtasks) >= 2, f"Expected browser+file subtasks, got: {subtasks}"
    assert any(s.get("agent_type") == "browser" for s in subtasks)
    assert any(s.get("agent_type") == "file" for s in subtasks)

    assert DESKTOP_OUTPUT.exists(), f"Expected output file at {DESKTOP_OUTPUT}"
    content = DESKTOP_OUTPUT.read_text(encoding="utf-8").strip()
    assert content, "Expected non-empty top story title in output file"

    browser_subtasks = [s for s in subtasks if s.get("agent_type") == "browser"]
    assert browser_subtasks, "Expected at least one browser subtask"
    browser_result = browser_subtasks[0].get("result") or {}
    extracted_title = str(browser_result.get("top_story_title", "")).strip()
    assert extracted_title, f"Browser extraction missing title. Result: {browser_result}"

    print("\n=== E2E PASS ===")
    print(f"Task ID: {task_id}")
    print(f"Extracted title: {extracted_title}")
    print(f"File content: {content}")
