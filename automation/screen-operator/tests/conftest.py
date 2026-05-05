from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.rate_limiter import RateLimiter
from app.safety_log import ActionLogger


class FakeExecutor:
    def __init__(self) -> None:
        self.display_server = "x11"
        self.available_tools = {
            "ydotool": False,
            "xdotool": True,
            "grim": False,
            "scrot": True,
            "python_xlib": True,
        }
        self.calls: list[tuple[str, dict]] = []

    def execute(self, action_type: str, payload: dict):
        self.calls.append((action_type, payload))
        if action_type == "screenshot":
            return {
                "success": True,
                "message": "ok",
                "screenshot_base64": "dGVzdA==",
            }
        return {"success": True, "message": "ok"}


@pytest.fixture()
def app_client(tmp_path: Path):
    logger = ActionLogger(tmp_path / "actions.jsonl")
    executor = FakeExecutor()
    limiter = RateLimiter(max_actions=10, per_seconds=1.0)
    app = create_app(executor=executor, logger=logger, limiter=limiter)
    return TestClient(app), executor, logger
