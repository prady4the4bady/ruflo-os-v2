import json
from pathlib import Path

from app.safety_log import ActionLogger


def test_safety_logger_writes_jsonl(tmp_path: Path):
    path = tmp_path / "actions.jsonl"
    logger = ActionLogger(path)

    logger.log("click", {"x": 10, "y": 20}, True, "ok")

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["type"] == "click"
    assert payload["params"]["x"] == 10
    assert payload["success"] is True


def test_last_actions_keeps_only_five(tmp_path: Path):
    logger = ActionLogger(tmp_path / "actions.jsonl")

    for i in range(7):
        logger.log("type", {"text": f"item-{i}"}, True, "ok")

    recent = logger.last_actions()
    assert len(recent) == 5
    assert recent[0]["params"]["text"] == "item-2"
    assert recent[-1]["params"]["text"] == "item-6"
